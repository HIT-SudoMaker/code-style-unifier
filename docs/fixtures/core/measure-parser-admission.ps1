[CmdletBinding()]
param(
    [string]$Executable = "target/release/csu.exe",
    [string]$OutputPath = "docs/fixtures/core/parser-admission.json"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-Sha256Bytes {
    param([Parameter(Mandatory)][AllowEmptyCollection()][byte[]]$Bytes)

    return [Convert]::ToHexString(
        [Security.Cryptography.SHA256]::HashData($Bytes)
    ).ToLowerInvariant()
}

function Get-Sha256Text {
    param([Parameter(Mandatory)][AllowEmptyString()][string]$Text)

    return Get-Sha256Bytes -Bytes ([Text.Encoding]::UTF8.GetBytes($Text))
}

function Get-PhysicalLineCount {
    param([Parameter(Mandatory)][AllowEmptyCollection()][byte[]]$Bytes)

    if ($Bytes.Length -eq 0) {
        return 0
    }
    [long]$lines = 0
    foreach ($byte in $Bytes) {
        if ($byte -eq 10) {
            $lines += 1
        }
    }
    if ($Bytes[$Bytes.Length - 1] -ne 10) {
        $lines += 1
    }
    return $lines
}

function Get-LineSum {
    param([Parameter(Mandatory)][AllowEmptyCollection()][object[]]$Records)

    [long]$sum = 0
    foreach ($record in $Records) {
        $sum += [long]$record.physical_lines
    }
    return $sum
}

function Get-RecordDigest {
    param([Parameter(Mandatory)][object[]]$Records)

    $builder = [Text.StringBuilder]::new()
    foreach ($record in $Records) {
        [void]$builder.Append($record.profile)
        [void]$builder.Append("`t")
        [void]$builder.Append($record.key)
        [void]$builder.Append("`t")
        [void]$builder.Append($record.bytes)
        [void]$builder.Append("`t")
        [void]$builder.Append($record.physical_lines)
        [void]$builder.Append("`t")
        [void]$builder.Append($record.sha256)
        [void]$builder.Append("`n")
    }
    return Get-Sha256Text -Text $builder.ToString()
}

function Sort-ByPath {
    param([Parameter(Mandatory)][AllowEmptyCollection()][object[]]$Records)

    $comparison = [Collections.Generic.Comparer[object]]::Create({
        param($left, $right)
        return [StringComparer]::Ordinal.Compare($left.path, $right.path)
    })
    [Array]::Sort($Records, $comparison)
    return $Records
}

function Sort-ByKey {
    param([Parameter(Mandatory)][AllowEmptyCollection()][object[]]$Records)

    $comparison = [Collections.Generic.Comparer[object]]::Create({
        param($left, $right)
        return [StringComparer]::Ordinal.Compare($left.key, $right.key)
    })
    [Array]::Sort($Records, $comparison)
    return $Records
}

function Open-FrozenFile {
    param([Parameter(Mandatory)][string]$Path)

    $stream = [IO.FileStream]::new(
        $Path,
        [IO.FileMode]::Open,
        [IO.FileAccess]::Read,
        [IO.FileShare]::Read
    )
    try {
        $bytes = [IO.File]::ReadAllBytes($Path)
        return [pscustomobject]@{
            path = $Path
            bytes = $bytes
            sha256 = Get-Sha256Bytes -Bytes $bytes
            stream = $stream
        }
    } catch {
        $stream.Dispose()
        throw
    }
}

function Get-CandidateRecords {
    param(
        [Parameter(Mandatory)][string]$TargetsRoot,
        [Parameter(Mandatory)]$Target,
        [Parameter(Mandatory)]$HeaderOwners
    )

    $targetRoot = Join-Path $TargetsRoot $Target.directory
    if (-not (Test-Path -LiteralPath $targetRoot -PathType Container)) {
        throw "Missing frozen target: $targetRoot"
    }
    $records = [Collections.Generic.List[object]]::new()
    foreach ($file in Get-ChildItem -LiteralPath $targetRoot -Recurse -File) {
        $extension = $file.Extension
        $relativePath = [IO.Path]::GetRelativePath(
            $targetRoot,
            $file.FullName
        ).Replace("\", "/")
        if ([IO.Path]::IsPathRooted($relativePath) -or
            $relativePath -eq ".." -or $relativePath.StartsWith("../")) {
            throw "Candidate escaped frozen target: $($file.FullName)"
        }
        $profile = switch ($extension) {
            ".py" { "python" }
            ".rs" { "rust" }
            ".c" { "c" }
            { $_ -in @(".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx") } {
                "cpp"
            }
            ".h" {
                $headerKey = "$($Target.directory)/$relativePath"
                if (-not $HeaderOwners.ContainsKey($headerKey)) {
                    throw "Ambiguous header lacks an exact Project Fact: $headerKey"
                }
                [string]$HeaderOwners[$headerKey]
            }
            default { $null }
        }
        if ([string]::IsNullOrEmpty([string]$profile)) {
            continue
        }
        $bytes = [IO.File]::ReadAllBytes($file.FullName)
        $records.Add([pscustomobject][ordered]@{
            key = "$($Target.directory)/$relativePath"
            path = "$profile/$($Target.directory)/$relativePath"
            target = [string]$Target.directory
            profile = $profile
            relative_path = $relativePath
            extension = $extension
            content = $bytes
            bytes = [long]$bytes.Length
            physical_lines = [long](Get-PhysicalLineCount -Bytes $bytes)
            sha256 = Get-Sha256Bytes -Bytes $bytes
        })
    }
    return Sort-ByKey -Records @($records)
}

function Get-RecordedRecords {
    param(
        [Parameter(Mandatory)][object[]]$Records,
        [Parameter(Mandatory)]$Target
    )

    $recorded = [Collections.Generic.List[object]]::new()
    foreach ($record in $Records) {
        $profileProperty = $Target.extensions.PSObject.Properties |
            Where-Object Name -CEQ $record.extension |
            Select-Object -First 1
        if ($null -eq $profileProperty) {
            continue
        }
        $profile = [string]$profileProperty.Value
        $recorded.Add([pscustomobject][ordered]@{
            key = $record.key
            path = "$profile/$($record.key)"
            target = $record.target
            profile = $profile
            relative_path = $record.relative_path
            extension = $record.extension
            content = $record.content
            bytes = $record.bytes
            physical_lines = $record.physical_lines
            sha256 = $record.sha256
        })
    }
    return Sort-ByKey -Records @($recorded)
}

function Assert-ExactFields {
    param(
        [Parameter(Mandatory)]$Value,
        [Parameter(Mandatory)][string[]]$Fields,
        [Parameter(Mandatory)][string]$Owner
    )

    $actual = @($Value.PSObject.Properties.Name | Sort-Object)
    $expected = @($Fields | Sort-Object)
    if (($actual -join ",") -cne ($expected -join ",")) {
        throw "$Owner has unsupported fields"
    }
}

function Invoke-AdmissionReview {
    param(
        [Parameter(Mandatory)][string]$ExecutablePath,
        [Parameter(Mandatory)][string]$AuthorityPath,
        [Parameter(Mandatory)][string]$WorkspacePath
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
        "review", "--authority", $AuthorityPath,
        "--workspace", $WorkspacePath, "--format", "json"
    )) {
        [void]$startInfo.ArgumentList.Add($argument)
    }
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    if (-not $process.Start()) {
        throw "Failed to start parser-admission review"
    }
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $process.WaitForExit()
    $stdout = $stdoutTask.GetAwaiter().GetResult()
    $stderr = $stderrTask.GetAwaiter().GetResult()
    $exitCode = $process.ExitCode
    $process.Dispose()
    if (-not [string]::IsNullOrEmpty($stderr)) {
        throw "Parser-admission review emitted stderr: $stderr"
    }
    try {
        $projection = $stdout | ConvertFrom-Json -ErrorAction Stop
    } catch {
        throw "Parser-admission review returned invalid JSON: $_"
    }
    if ($projection.schema_version -ne 4 -or
        $projection.terminal -ne "sealed" -or
        $projection.review.completion -ne "incomplete" -or
        $projection.disposition -ne "incomplete" -or $exitCode -ne 2) {
        throw (
            "Parser-admission review terminal mismatch: " +
            "exit=$exitCode terminal=$($projection.terminal) " +
            "disposition=$($projection.disposition) " +
            "completion=$($projection.review.completion)"
        )
    }
    return [pscustomobject][ordered]@{
        exit_code = $exitCode
        stdout_sha256 = Get-Sha256Text -Text $stdout
        projection = $projection
    }
}

$fixtureRoot = $PSScriptRoot
$repositoryRoot = [IO.Path]::GetFullPath((Join-Path $fixtureRoot "../../.."))
$manifestPath = Join-Path $fixtureRoot "benchmark-manifest.json"
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 |
    ConvertFrom-Json
if ($manifest.schema_version -ne 1 -or @($manifest.targets).Count -ne 8) {
    throw "Unsupported benchmark target manifest"
}
$targetsRoot = [IO.Path]::GetFullPath(
    (Join-Path $fixtureRoot $manifest.targets_root)
)
$authorityDirectory = Join-Path $fixtureRoot "parser-admission-authority"
$authorityPath = Join-Path $authorityDirectory "authority.json"
$cargoLockPath = Join-Path $repositoryRoot "Cargo.lock"
$scriptPath = [IO.Path]::GetFullPath($PSCommandPath)
$executablePath = [IO.Path]::GetFullPath((Join-Path $repositoryRoot $Executable))
foreach ($path in @($authorityPath, $cargoLockPath, $scriptPath, $executablePath)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Missing parser-admission input: $path"
    }
}
$frozenInputs = @(
    Open-FrozenFile -Path $authorityPath
    Open-FrozenFile -Path $cargoLockPath
    Open-FrozenFile -Path $scriptPath
    Open-FrozenFile -Path $executablePath
)
try {
$frozenAuthority = $frozenInputs[0]
$frozenCargoLock = $frozenInputs[1]
$frozenScript = $frozenInputs[2]
$frozenExecutable = $frozenInputs[3]
$strictUtf8 = [Text.UTF8Encoding]::new($false, $true)
$authority = $strictUtf8.GetString($frozenAuthority.bytes) | ConvertFrom-Json
Assert-ExactFields -Value $authority -Owner "Parser-admission Authority" `
    -Fields @(
        "schema_version", "public_callables", "token_vocabulary",
        "quantity_concepts", "header_languages",
        "external_fixed_identifiers", "dependency_authority"
    )
$headerFacts = @($authority.header_languages.PSObject.Properties)
$headerOwners = [Collections.Generic.Dictionary[string, string]]::new(
    [StringComparer]::Ordinal
)
foreach ($fact in $headerFacts) {
    if ($fact.Name -notmatch "^(c|cpp)/(.+[.]h)$" -or
        $fact.Value -cne $Matches[1] -or
        -not $headerOwners.TryAdd($Matches[2], [string]$fact.Value)) {
        throw "Parser-admission Authority contains an invalid header fact"
    }
}
if ($authority.schema_version -ne 4 -or $headerFacts.Count -ne 315 -or
    @($headerFacts | Where-Object Value -CEQ "c").Count -ne 289 -or
    @($headerFacts | Where-Object Value -CEQ "cpp").Count -ne 26 -or
    @($authority.public_callables.PSObject.Properties).Count -ne 0 -or
    @($authority.token_vocabulary).Count -ne 0 -or
    @($authority.quantity_concepts.PSObject.Properties).Count -ne 0 -or
    @($authority.external_fixed_identifiers).Count -ne 0 -or
    $null -ne $authority.dependency_authority) {
    throw "Parser-admission Authority must contain only 315 exact header facts"
}
$allRecords = [Collections.Generic.List[object]]::new()
$targetReceipts = [Collections.Generic.List[object]]::new()
foreach ($target in $manifest.targets) {
    $records = @(Get-CandidateRecords -TargetsRoot $targetsRoot `
        -Target $target -HeaderOwners $headerOwners)
    $recorded = @(Get-RecordedRecords -Records $records -Target $target)
    $recordedLines = Get-LineSum -Records $recorded
    $recordedBytes = ($recorded | Measure-Object bytes -Sum).Sum
    $recordedDigest = Get-RecordDigest -Records $recorded
    if ($recorded.Count -ne $target.accepted_files -or
        $recordedLines -ne $target.physical_lines -or
        $recordedBytes -ne $target.bytes -or
        $recordedDigest -cne $target.digest) {
        throw "Frozen target identity mismatch: $($target.directory)"
    }
    $candidateLines = Get-LineSum -Records $records
    $candidateBytes = ($records | Measure-Object bytes -Sum).Sum
    $candidateDigest = Get-RecordDigest -Records $records
    $targetReceipts.Add([pscustomobject][ordered]@{
        directory = [string]$target.directory
        revision = [string]$target.revision
        recorded_files = $recorded.Count
        recorded_physical_lines = [long]$recordedLines
        recorded_bytes = [long]$recordedBytes
        recorded_digest = $recordedDigest
        candidate_files = $records.Count
        candidate_physical_lines = [long]$candidateLines
        candidate_bytes = [long]$candidateBytes
        candidate_digest = $candidateDigest
    })
    foreach ($record in $records) {
        $allRecords.Add($record)
    }
}
$records = @(Sort-ByPath -Records @($allRecords))
if ($records.Count -ne 2467) {
    throw "Frozen complete candidate scale mismatch: $($records.Count)"
}
foreach ($record in @($records | Where-Object {
    [IO.Path]::GetExtension($_.relative_path) -ceq ".h"
})) {
    if (-not $headerOwners.ContainsKey($record.key) -or
        $headerOwners[$record.key] -cne $record.profile) {
        throw "Parser-admission Authority does not own header $($record.key)"
    }
}

$temporaryRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd(
    "\", "/"
)
$stageRoot = [IO.Path]::GetFullPath((Join-Path $temporaryRoot (
    "csu-parser-admission-" + [Guid]::NewGuid().ToString("N")
)))
if (-not $stageRoot.StartsWith(
        ($temporaryRoot + [IO.Path]::DirectorySeparatorChar),
        [StringComparison]::OrdinalIgnoreCase
    ) -or -not (Split-Path -Leaf $stageRoot).StartsWith(
        "csu-parser-admission-",
        [StringComparison]::Ordinal
    )) {
    throw "Parser-admission staging path escaped the temporary root"
}
[void][IO.Directory]::CreateDirectory($stageRoot)
$lockedStageFiles = [Collections.Generic.List[IO.FileStream]]::new()
try {
    foreach ($record in $records) {
        $destination = Join-Path $stageRoot $record.path
        [void][IO.Directory]::CreateDirectory((Split-Path -Parent $destination))
        [IO.File]::WriteAllBytes($destination, $record.content)
        $stageBytes = [IO.File]::ReadAllBytes($destination)
        if ($stageBytes.Length -ne $record.bytes -or
            (Get-PhysicalLineCount -Bytes $stageBytes) -ne
                $record.physical_lines -or
            (Get-Sha256Bytes -Bytes $stageBytes) -ne $record.sha256) {
            throw "Parser-admission staging changed captured bytes: $($record.path)"
        }
        $lockedStageFiles.Add([IO.FileStream]::new(
            $destination,
            [IO.FileMode]::Open,
            [IO.FileAccess]::Read,
            [IO.FileShare]::Read
        ))
    }
    $runs = @(
        Invoke-AdmissionReview -ExecutablePath $executablePath `
            -AuthorityPath $authorityDirectory -WorkspacePath $stageRoot
        Invoke-AdmissionReview -ExecutablePath $executablePath `
            -AuthorityPath $authorityDirectory -WorkspacePath $stageRoot
    )
} finally {
    foreach ($stream in $lockedStageFiles) {
        $stream.Dispose()
    }
    if (Test-Path -LiteralPath $stageRoot -PathType Container) {
        Remove-Item -LiteralPath $stageRoot -Recurse -Force
    }
}
foreach ($input in $frozenInputs) {
    $currentBytes = [IO.File]::ReadAllBytes($input.path)
    if ((Get-Sha256Bytes -Bytes $currentBytes) -ne $input.sha256) {
        throw "Parser-admission input changed during repeated runs: $($input.path)"
    }
}

$recordsByPath = [Collections.Generic.Dictionary[string, object]]::new(
    [StringComparer]::Ordinal
)
foreach ($record in $records) {
    $recordsByPath.Add($record.path, $record)
}
$runReceipts = [Collections.Generic.List[object]]::new()
$referenceInventory = $null
$referenceCounts = $null
$referenceExclusions = $null
foreach ($run in $runs) {
    $review = $run.projection.review
    $scopeFiles = @($review.scope.value.files)
    if ($review.scope.kind -ne "workspace" -or
        $scopeFiles.Count -ne $records.Count -or
        $review.metrics.files_read -ne $records.Count -or
        $review.metrics.byte_sweeps -ne $records.Count -or
        $review.metrics.structural_parses -lt 0 -or
        $review.metrics.structural_parses -gt $records.Count) {
        throw (
            "Admission review lifecycle does not cover every candidate once: " +
            "scope=$($scopeFiles.Count) expected=$($records.Count) " +
            "read=$($review.metrics.files_read) " +
            "sweep=$($review.metrics.byte_sweeps) " +
            "parse=$($review.metrics.structural_parses)"
        )
    }
    $parseFindings = @(
        $review.findings | Where-Object rule -CEQ "source.parseability"
    )
    $excluded = [Collections.Generic.List[object]]::new()
    $excludedPaths = [Collections.Generic.HashSet[string]]::new(
        [StringComparer]::Ordinal
    )
    foreach ($finding in $parseFindings) {
        $path = ([string]$finding.path).Replace("\", "/")
        if (-not $recordsByPath.ContainsKey($path) -or
            -not $excludedPaths.Add($path) -or
            [string]::IsNullOrWhiteSpace([string]$finding.observation)) {
            throw "Invalid or duplicate parseability exclusion: $path"
        }
        $record = $recordsByPath[$path]
        $excluded.Add([pscustomobject][ordered]@{
            path = $path
            profile = $record.profile
            physical_lines = $record.physical_lines
            sha256 = $record.sha256
            reason = [string]$finding.observation
            reason_sha256 = Get-Sha256Text -Text ([string]$finding.observation)
            classification = "excluded_not_reviewed_not_complete_not_clean"
        })
    }
    $exclusions = @(Sort-ByPath -Records @($excluded))
    $scopeSet = [Collections.Generic.HashSet[string]]::new(
        [StringComparer]::Ordinal
    )
    foreach ($scopeFile in $scopeFiles) {
        $path = ([string]$scopeFile).Replace("\", "/")
        if (-not $recordsByPath.ContainsKey($path) -or
            -not $scopeSet.Add($path)) {
            throw "Admission scope contains an unknown or duplicate path: $path"
        }
    }
    $coverageByPath = [Collections.Generic.Dictionary[string, object]]::new(
        [StringComparer]::Ordinal
    )
    foreach ($record in $records) {
        $coverageByPath.Add($record.path, [ordered]@{
            capture = "complete"
            physical_lines = "complete"
            structure = "complete"
            identifier = "complete"
            documentation = "complete"
            dependency_declaration = "complete"
        })
    }
    $blockedKeys = [Collections.Generic.HashSet[string]]::new(
        [StringComparer]::Ordinal
    )
    foreach ($blocked in @($review.blocked_family_details)) {
        $path = ([string]$blocked.file).Replace("\", "/")
        $family = [string]$blocked.family
        $key = "$path`t$family"
        if (-not $coverageByPath.ContainsKey($path) -or
            -not $blockedKeys.Add($key) -or
            $family -notin @(
                "capture", "physical_lines", "structure", "identifier",
                "documentation", "dependency_declaration"
            ) -or [string]::IsNullOrWhiteSpace([string]$blocked.reason)) {
            throw "Admission coverage contains an invalid blocked cell: $key"
        }
        $coverageByPath[$path][$family] = [string]$blocked.reason
    }
    $exclusionsByPath = [Collections.Generic.Dictionary[string, object]]::new(
        [StringComparer]::Ordinal
    )
    foreach ($exclusion in $exclusions) {
        $exclusionsByPath.Add($exclusion.path, $exclusion)
        $coverage = $coverageByPath[$exclusion.path]
        if ($coverage.capture -cne "complete" -or
            $coverage.physical_lines -cne "complete") {
            throw "Excluded source lost capture or physical-line evidence"
        }
        foreach ($family in @(
            "structure", "identifier", "documentation",
            "dependency_declaration"
        )) {
            if ($coverage[$family] -cne $exclusion.reason) {
                throw "Excluded source lacks matching blocked evidence: $($exclusion.path)"
            }
        }
    }
    foreach ($record in $records) {
        if (-not $exclusionsByPath.ContainsKey($record.path) -and
            $coverageByPath[$record.path].structure -cne "complete") {
            throw "Parser-admitted source lacks Complete structure evidence"
        }
    }
    $inventoryRows = [Collections.Generic.List[object]]::new()
    foreach ($record in $records) {
        $exclusion = if ($exclusionsByPath.ContainsKey($record.path)) {
            $exclusionsByPath[$record.path]
        } else {
            $null
        }
        $inventoryRows.Add([pscustomobject][ordered]@{
            path = $record.path
            profile = $record.profile
            physical_lines = $record.physical_lines
            sha256 = $record.sha256
            classification = if ($null -eq $exclusion) {
                "parser_admitted"
            } else {
                "excluded"
            }
            reason_sha256 = if ($null -eq $exclusion) {
                $null
            } else {
                $exclusion.reason_sha256
            }
        })
    }
    $inventoryJson = ConvertTo-Json -InputObject @($inventoryRows) `
        -Depth 5 -Compress
    $counts = [ordered]@{}
    foreach ($profile in @("c", "cpp", "python", "rust")) {
        $candidateRows = @($records | Where-Object profile -CEQ $profile)
        $excludedRows = @($exclusions | Where-Object profile -CEQ $profile)
        $excludedSet = [Collections.Generic.HashSet[string]]::new(
            [StringComparer]::Ordinal
        )
        foreach ($row in $excludedRows) {
            [void]$excludedSet.Add($row.path)
        }
        $admittedRows = @(
            $candidateRows | Where-Object { -not $excludedSet.Contains($_.path) }
        )
        $counts[$profile] = [pscustomobject][ordered]@{
            candidate_files = $candidateRows.Count
            candidate_physical_lines = Get-LineSum -Records $candidateRows
            admitted_files = $admittedRows.Count
            admitted_physical_lines = Get-LineSum -Records $admittedRows
            excluded_files = $excludedRows.Count
            excluded_physical_lines = Get-LineSum -Records $excludedRows
            admission_ratio = [Math]::Round(
                $admittedRows.Count / $candidateRows.Count,
                12
            )
        }
    }
    $countsJson = ConvertTo-Json -InputObject $counts -Depth 5 -Compress
    $inventoryIdentity = Get-Sha256Text -Text $inventoryJson
    $countsIdentity = Get-Sha256Text -Text $countsJson
    if ($null -eq $referenceInventory) {
        $referenceInventory = $inventoryIdentity
        $referenceCounts = $countsIdentity
        $referenceExclusions = $exclusions
    } elseif ($inventoryIdentity -cne $referenceInventory -or
        $countsIdentity -cne $referenceCounts -or
        (ConvertTo-Json $exclusions -Depth 5 -Compress) -cne
            (ConvertTo-Json $referenceExclusions -Depth 5 -Compress)) {
        throw "Repeated parser-admission runs produced different evidence"
    }
    $runReceipts.Add([pscustomobject][ordered]@{
        exit_code = $run.exit_code
        projection_sha256 = $run.stdout_sha256
        inventory_sha256 = $inventoryIdentity
        counts_sha256 = $countsIdentity
    })
}

$targetIdentity = Get-Sha256Text -Text (
    ConvertTo-Json -InputObject @($targetReceipts) -Depth 5 -Compress
)
$receipt = [pscustomobject][ordered]@{
    schema_version = 1
    status = "transparent_admission_evidence_no_release_threshold"
    algorithm_revision = "single-capture-standard-law-extensions-and-exact-header-facts-v3"
    inputs = [pscustomobject][ordered]@{
        targets_identity_sha256 = $targetIdentity
        targets = @($targetReceipts)
        grammars = [pscustomobject][ordered]@{
            cargo_lock_sha256 = $frozenCargoLock.sha256
            python = "tree-sitter-python@0.25.0+direct-source-facts-v3"
            rust = "tree-sitter-rust@0.24.2+direct-source-facts-v3"
            c = "tree-sitter-c@0.24.2+direct-source-facts-v3"
            cpp = "tree-sitter-cpp@8b5b49eb+direct-source-facts-v3"
        }
        executable_sha256 = $frozenExecutable.sha256
        authority_sha256 = $frozenAuthority.sha256
        authority_schema_version = 4
        ambiguous_header_facts = $headerFacts.Count
        fixed_extensions = [pscustomobject][ordered]@{
            ".py" = "python"
            ".rs" = "rust"
            ".c" = "c"
            ".h" = "authority"
            ".cc" = "cpp"
            ".cpp" = "cpp"
            ".cxx" = "cpp"
            ".hpp" = "cpp"
            ".hh" = "cpp"
            ".hxx" = "cpp"
        }
        evidence_script_sha256 = $frozenScript.sha256
    }
    corpus_identity = "separate_from_corpus_200k"
    profiles = [pscustomobject]$counts
    exclusions = @($referenceExclusions)
    repeated_runs = @($runReceipts)
    deterministic_inventory_sha256 = $referenceInventory
}
$outputFullPath = [IO.Path]::GetFullPath((Join-Path $repositoryRoot $OutputPath))
[void][IO.Directory]::CreateDirectory((Split-Path -Parent $outputFullPath))
[IO.File]::WriteAllText(
    $outputFullPath,
    (($receipt | ConvertTo-Json -Depth 12).Replace("`r`n", "`n") + "`n"),
    [Text.UTF8Encoding]::new($false)
)
} finally {
    foreach ($input in $frozenInputs) {
        $input.stream.Dispose()
    }
}
