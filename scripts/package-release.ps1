param(
    [string]$Configuration = "release",
    [string]$OutDir = "dist",
    [string]$TargetName = "",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

$cargoToml = Get-Content -LiteralPath "Cargo.toml" -Raw
if ($cargoToml -notmatch '(?m)^version\s*=\s*"([^"]+)"') {
    throw "Cannot read package version from Cargo.toml"
}
$version = $Matches[1]

if ([string]::IsNullOrWhiteSpace($TargetName)) {
    $os = if ([System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::Windows)) {
        "windows"
    } elseif ([System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::OSX)) {
        "macos"
    } elseif ([System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::Linux)) {
        "linux"
    } else {
        throw "Unsupported operating system"
    }

    $arch = switch ([System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture) {
        "X64" { "x86_64" }
        "Arm64" { "aarch64" }
        default { throw "Unsupported architecture: $($_)" }
    }

    $TargetName = "$os-$arch"
}

if (-not $SkipBuild) {
    cargo build "--$Configuration"
}

$binaryName = if ($TargetName.StartsWith("windows")) { "csu.exe" } else { "csu" }
$binaryPath = Join-Path "target/$Configuration" $binaryName
if (-not (Test-Path -LiteralPath $binaryPath)) {
    throw "Built binary not found: $binaryPath"
}

$packageName = "csu-$version-$TargetName"
$outRoot = Join-Path $repoRoot $OutDir
$stage = Join-Path $outRoot $packageName

if (Test-Path -LiteralPath $stage) {
    Remove-Item -LiteralPath $stage -Recurse -Force
}

New-Item -ItemType Directory -Force -Path `
    (Join-Path $stage "bin"), `
    (Join-Path $stage "profiles"), `
    (Join-Path $stage "agent-skills/csu"), `
    (Join-Path $stage "examples") | Out-Null

Copy-Item -LiteralPath $binaryPath -Destination (Join-Path $stage "bin/$binaryName")
Copy-Item -LiteralPath "README.md" -Destination (Join-Path $stage "README.md")
Copy-Item -LiteralPath "LICENSE" -Destination (Join-Path $stage "LICENSE")
Copy-Item -LiteralPath "profiles/default.toml" -Destination (Join-Path $stage "profiles/default.toml")
Copy-Item -LiteralPath "agent-skills/csu/SKILL.md" -Destination (Join-Path $stage "agent-skills/csu/SKILL.md")
Copy-Item -LiteralPath "examples/commands.md" -Destination (Join-Path $stage "examples/commands.md")

if ($TargetName.StartsWith("windows")) {
    $archive = Join-Path $outRoot "$packageName.zip"
    if (Test-Path -LiteralPath $archive) {
        Remove-Item -LiteralPath $archive -Force
    }
    Compress-Archive -Path $stage -DestinationPath $archive
} else {
    $archive = Join-Path $outRoot "$packageName.tar.gz"
    if (Test-Path -LiteralPath $archive) {
        Remove-Item -LiteralPath $archive -Force
    }
    tar -czf $archive -C $outRoot $packageName
}

Write-Output $archive
