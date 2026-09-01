[CmdletBinding()]
param(
    [string]$Executable = "target/release/csu.exe",
    [Parameter(Mandatory)][string]$AuthorityDirectory,
    [Parameter(Mandatory)][string]$Workspace,
    [ValidateRange(1, 1000)][int]$Runs = 30,
    [ValidateRange(0, 100)][int]$WarmupRuns = 1,
    [switch]$DiagnosticIncomplete
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-Sha256Text {
    param([Parameter(Mandatory)][AllowEmptyString()][string]$Text)

    $bytes = [Text.Encoding]::UTF8.GetBytes($Text)
    $hash = [Security.Cryptography.SHA256]::HashData($bytes)
    return [Convert]::ToHexString($hash).ToLowerInvariant()
}

function Invoke-ReviewProcess {
    param(
        [Parameter(Mandatory)][string]$ExecutablePath,
        [Parameter(Mandatory)][string]$AuthorityPath,
        [Parameter(Mandatory)][string]$WorkspacePath,
        [switch]$AllowIncomplete
    )

    $startInfo = [Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $ExecutablePath
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.StandardOutputEncoding = [Text.UTF8Encoding]::new($false)
    $startInfo.StandardErrorEncoding = [Text.UTF8Encoding]::new($false)
    foreach ($argument in @(
        "review",
        "--authority",
        $AuthorityPath,
        "--workspace",
        $WorkspacePath,
        "--format",
        "json"
    )) {
        [void]$startInfo.ArgumentList.Add($argument)
    }

    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    $stopwatch = [Diagnostics.Stopwatch]::StartNew()
    if (-not $process.Start()) {
        throw "Failed to start release reviewer"
    }
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    [long]$peakWorkingSetBytes = 0
    while (-not $process.HasExited) {
        try {
            $process.Refresh()
            $peakWorkingSetBytes = [Math]::Max(
                $peakWorkingSetBytes,
                $process.WorkingSet64
            )
        }
        catch [InvalidOperationException] {
            # The process may exit between HasExited and Refresh.
        }
        Start-Sleep -Milliseconds 20
    }
    $process.WaitForExit()
    $stopwatch.Stop()
    $stdout = $stdoutTask.GetAwaiter().GetResult()
    $stderr = $stderrTask.GetAwaiter().GetResult()
    try {
        $process.Refresh()
        $peakWorkingSetBytes = [Math]::Max(
            $peakWorkingSetBytes,
            $process.PeakWorkingSet64
        )
    }
    catch [InvalidOperationException] {
        # The sampled peak remains valid after the process handle closes.
    }
    $exitCode = $process.ExitCode
    $process.Dispose()

    try {
        $projection = $stdout | ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        throw "Review returned invalid JSON with exit code ${exitCode}: $_"
    }
    $terminal = [string]$projection.terminal
    $disposition = [string]$projection.disposition
    $accepted =
        ($exitCode -eq 0 -and $terminal -eq "sealed" -and
            $disposition -eq "clean") -or
        ($exitCode -eq 1 -and $terminal -eq "sealed" -and
            $disposition -eq "findings") -or
        ($AllowIncomplete -and $exitCode -eq 2 -and
            $terminal -eq "sealed" -and $disposition -eq "incomplete")
    if (-not $accepted) {
        throw (
            "Review terminal/exit mismatch: exit=${exitCode}, " +
            "terminal=$terminal, disposition=$disposition, stderr=$stderr"
        )
    }
    return [pscustomobject]@{
        elapsed_ms = $stopwatch.Elapsed.TotalMilliseconds
        peak_working_set_bytes = $peakWorkingSetBytes
        exit_code = $exitCode
        terminal = $terminal
        disposition = $disposition
        stdout_bytes = [Text.Encoding]::UTF8.GetByteCount($stdout)
        stdout_sha256 = Get-Sha256Text -Text $stdout
    }
}

$executablePath = [IO.Path]::GetFullPath($Executable)
$authorityPath = [IO.Path]::GetFullPath($AuthorityDirectory)
$workspacePath = [IO.Path]::GetFullPath($Workspace)
if (-not (Test-Path -LiteralPath $executablePath -PathType Leaf)) {
    throw "Missing release executable: $executablePath"
}
if (-not (Test-Path -LiteralPath $authorityPath -PathType Container)) {
    throw "Missing Authority directory: $authorityPath"
}
if (-not (Test-Path -LiteralPath $workspacePath -PathType Container)) {
    throw "Missing corpus workspace: $workspacePath"
}
$verifierPath = Join-Path $PSScriptRoot "verify-inputs.ps1"
$inputReceipt = (
    & $verifierPath -VerifyCorpusDirectory $workspacePath | Out-String
) | ConvertFrom-Json

for ($warmup = 0; $warmup -lt $WarmupRuns; $warmup += 1) {
    [void](Invoke-ReviewProcess `
        -ExecutablePath $executablePath `
        -AuthorityPath $authorityPath `
        -WorkspacePath $workspacePath `
        -AllowIncomplete:$DiagnosticIncomplete)
}

$measurements = [Collections.Generic.List[object]]::new()
for ($run = 1; $run -le $Runs; $run += 1) {
    $measurement = Invoke-ReviewProcess `
        -ExecutablePath $executablePath `
        -AuthorityPath $authorityPath `
        -WorkspacePath $workspacePath `
        -AllowIncomplete:$DiagnosticIncomplete
    $measurements.Add([pscustomobject]@{
        run = $run
        elapsed_ms = $measurement.elapsed_ms
        peak_working_set_bytes = $measurement.peak_working_set_bytes
        exit_code = $measurement.exit_code
        terminal = $measurement.terminal
        disposition = $measurement.disposition
        stdout_bytes = $measurement.stdout_bytes
        stdout_sha256 = $measurement.stdout_sha256
    })
}

$sortedElapsed = @($measurements.elapsed_ms | Sort-Object)
$p95Index = [Math]::Ceiling(0.95 * $Runs) - 1
$uniqueProjectionDigests = @(
    $measurements.stdout_sha256 | Sort-Object -Unique
)
[pscustomobject]@{
    schema_version = 2
    executable_sha256 = (
        Get-FileHash -LiteralPath $executablePath -Algorithm SHA256
    ).Hash.ToLowerInvariant()
    authority_sha256 = (
        Get-FileHash -LiteralPath (Join-Path $authorityPath "authority.json") `
            -Algorithm SHA256
    ).Hash.ToLowerInvariant()
    workspace = $workspacePath
    corpus_files = $inputReceipt.corpus_files
    corpus_physical_lines = $inputReceipt.corpus_physical_lines
    corpus_digest = $inputReceipt.corpus_digest
    inventory_sha256 = $inputReceipt.inventory_sha256
    runs = $Runs
    warmup_runs = $WarmupRuns
    p95_method = "nearest_rank_ceiling_0.95_times_n"
    p95_elapsed_ms = $sortedElapsed[$p95Index]
    maximum_peak_working_set_bytes = (
        $measurements.peak_working_set_bytes | Measure-Object -Maximum
    ).Maximum
    deterministic_projection = $uniqueProjectionDigests.Count -eq 1
    diagnostic_incomplete = [bool]$DiagnosticIncomplete
    projection_digests = $uniqueProjectionDigests
    measurements = $measurements
} | ConvertTo-Json -Depth 5
