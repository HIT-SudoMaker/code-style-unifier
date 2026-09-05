[CmdletBinding()]
param(
    [string]$Executable = "target/release/csu.exe",
    [Parameter(Mandatory)][string]$AuthorityDirectory,
    [Parameter(Mandatory)][string]$Workspace,
    [ValidateRange(1, 1000)][int]$Runs = 30,
    [ValidateRange(0, 100)][int]$WarmupRuns = 1,
    [switch]$DiagnosticIncomplete,
    [Parameter(Mandatory)][string]$OutputPath
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-Sha256Text {
    param([Parameter(Mandatory)][AllowEmptyString()][string]$Text)

    $bytes = [Text.Encoding]::UTF8.GetBytes($Text)
    $hash = [Security.Cryptography.SHA256]::HashData($bytes)
    return [Convert]::ToHexString($hash).ToLowerInvariant()
}

function Get-JsonSha256 {
    param([Parameter(Mandatory)][AllowEmptyCollection()]$Value)

    $json = ConvertTo-Json -InputObject $Value -Depth 20 -Compress
    return Get-Sha256Text -Text $json
}

function Get-PositiveCountSum {
    param([Parameter(Mandatory)][AllowEmptyCollection()][object[]]$Rows)

    [long]$sum = 0
    foreach ($row in $Rows) {
        [long]$count = $row.count
        if ($count -le 0 -or [double]$row.count -ne [double]$count) {
            throw "Summary rows must contain positive integer counts"
        }
        $sum += $count
    }
    return $sum
}

function New-ReviewSummary {
    param([Parameter(Mandatory)]$Projection)

    if ($Projection.schema_version -ne 4 -or $null -eq $Projection.review) {
        throw "Review returned an unsupported projection schema"
    }
    $review = $Projection.review
    $summaryFields = @($review.finding_summary.PSObject.Properties.Name |
        Sort-Object)
    if (($summaryFields -join ",") -ne
        "hard_violation,review_required,total") {
        throw "Review returned an unsupported Finding summary"
    }
    $scopeFiles = @($review.scope.value.files)
    if ($review.scope.kind -ne "workspace" -or $scopeFiles.Count -eq 0) {
        throw "Review did not return a complete workspace scope"
    }
    $findingCounts = [Collections.Generic.SortedDictionary[string, int]]::new(
        [StringComparer]::Ordinal
    )
    foreach ($finding in @($review.findings)) {
        if ($finding.grade -notin @(
                "hard_violation",
                "review_required"
            ) -or [string]::IsNullOrWhiteSpace([string]$finding.rule)) {
            throw "Review returned an invalid Finding grade or rule"
        }
        $key = "$($finding.grade)`t$($finding.rule)"
        if ($findingCounts.ContainsKey($key)) {
            $findingCounts[$key] += 1
        } else {
            $findingCounts.Add($key, 1)
        }
    }
    [object[]]$findingRuleSummary = @(
        $findingCounts.GetEnumerator() | ForEach-Object {
            $parts = $_.Key.Split("`t", 2)
            [pscustomobject][ordered]@{
                grade = $parts[0]
                rule = $parts[1]
                count = $_.Value
            }
        }
    )
    $findings = @($review.findings)
    $hardCount = @(
        $findings | Where-Object grade -EQ "hard_violation"
    ).Count
    $reviewCount = @(
        $findings | Where-Object grade -EQ "review_required"
    ).Count
    if ($review.finding_summary.total -lt 0 -or
        $review.finding_summary.hard_violation -lt 0 -or
        $review.finding_summary.review_required -lt 0 -or
        $review.finding_summary.total -ne $findings.Count -or
        $review.finding_summary.hard_violation -ne $hardCount -or
        $review.finding_summary.review_required -ne $reviewCount -or
        $review.finding_summary.total -ne ($hardCount + $reviewCount) -or
        (Get-PositiveCountSum -Rows $findingRuleSummary) -ne
            $findings.Count) {
        throw "Review Finding summary does not match its complete Finding list"
    }

    $blockedCounts = [Collections.Generic.SortedDictionary[string, int]]::new(
        [StringComparer]::Ordinal
    )
    foreach ($blocked in @($review.blocked_family_details)) {
        $family = [string]$blocked.family
        if ([string]::IsNullOrWhiteSpace($family)) {
            throw "Review returned an unnamed blocked family"
        }
        if ($blockedCounts.ContainsKey($family)) {
            $blockedCounts[$family] += 1
        } else {
            $blockedCounts.Add($family, 1)
        }
    }
    [object[]]$blockedFamilySummary = @(
        $blockedCounts.GetEnumerator() | ForEach-Object {
            [pscustomobject][ordered]@{
                family = $_.Key
                count = $_.Value
            }
        }
    )
    $blockedDetails = @($review.blocked_family_details)
    if ($review.blocked_families -ne $blockedDetails.Count -or
        (Get-PositiveCountSum -Rows $blockedFamilySummary) -ne
            $blockedDetails.Count) {
        throw "Review blocked-family summary does not match its details"
    }
    if ($review.metrics.files_read -ne $scopeFiles.Count -or
        $review.metrics.byte_sweeps -ne $scopeFiles.Count -or
        $review.metrics.structural_parses -ne $scopeFiles.Count) {
        throw "Review lifecycle metrics do not equal the admitted file set"
    }

    $summary = [ordered]@{
        terminal = [string]$Projection.terminal
        disposition = [string]$Projection.disposition
        completion = [string]$review.completion
        scope_kind = [string]$review.scope.kind
        seal = [string]$review.seal
        finding_summary = [pscustomobject][ordered]@{
            total = [int]$review.finding_summary.total
            hard_violation = [int]$review.finding_summary.hard_violation
            review_required = [int]$review.finding_summary.review_required
        }
        finding_rule_summary = $findingRuleSummary
        findings_sha256 = Get-JsonSha256 -Value @($review.findings)
        blocked_families = [int]$review.blocked_families
        blocked_family_summary = $blockedFamilySummary
        blocked_family_details_sha256 = Get-JsonSha256 -Value @(
            $review.blocked_family_details
        )
        admitted_files = [int]$scopeFiles.Count
        metrics = [pscustomobject][ordered]@{
            files_read = [int]$review.metrics.files_read
            byte_sweeps = [int]$review.metrics.byte_sweeps
            structural_parses = [int]$review.metrics.structural_parses
        }
    }
    $summaryObject = [pscustomobject]$summary
    $summary.Add(
        "semantic_summary_sha256",
        (Get-JsonSha256 -Value $summaryObject)
    )
    return [pscustomobject]$summary
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
    $summary = New-ReviewSummary -Projection $projection
    $stderrBytes = [Text.Encoding]::UTF8.GetByteCount($stderr)
    if ($stderrBytes -ne 0) {
        throw "Review emitted stderr despite returning structured evidence: $stderr"
    }
    $accepted =
        ($exitCode -eq 0 -and $summary.terminal -eq "sealed" -and
            $summary.disposition -eq "clean") -or
        ($exitCode -eq 1 -and $summary.terminal -eq "sealed" -and
            $summary.disposition -eq "findings") -or
        ($AllowIncomplete -and $exitCode -eq 2 -and
            $summary.terminal -eq "sealed" -and
            $summary.disposition -eq "incomplete")
    if (-not $accepted) {
        throw (
            "Review terminal/exit mismatch: exit=${exitCode}, " +
            "terminal=$($summary.terminal), " +
            "disposition=$($summary.disposition), stderr=$stderr"
        )
    }
    return [pscustomobject]@{
        elapsed_ms = $stopwatch.Elapsed.TotalMilliseconds
        peak_working_set_bytes = $peakWorkingSetBytes
        exit_code = $exitCode
        stdout_bytes = [Text.Encoding]::UTF8.GetByteCount($stdout)
        stdout_sha256 = Get-Sha256Text -Text $stdout
        stderr_bytes = $stderrBytes
        stderr_sha256 = Get-Sha256Text -Text $stderr
        review_summary = $summary
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
$manifestPath = Join-Path $PSScriptRoot "benchmark-manifest.json"
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 |
    ConvertFrom-Json
if ($manifest.schema_version -ne 1 -or
    (@($manifest.PSObject.Properties.Name | Sort-Object) -join ",") -ne
        "available_scale,candidate_gates,corpus_200k,grammars,parser_admission,release_evidence,runner,schema_version,targets,targets_root") {
    throw "Unsupported benchmark manifest schema"
}
$canonicalReceiptPath = [IO.Path]::GetFullPath(
    (Join-Path $PSScriptRoot $manifest.release_evidence.path)
)
$outputFullPath = [IO.Path]::GetFullPath($OutputPath)
if ($outputFullPath -eq $canonicalReceiptPath) {
    throw "Measurement must write staging evidence before verifier promotion"
}
if (Test-Path -LiteralPath $outputFullPath) {
    throw "Measurement staging output already exists: $outputFullPath"
}
$outputParent = Split-Path -Parent $outputFullPath
if (-not (Test-Path -LiteralPath $outputParent -PathType Container)) {
    throw "Measurement staging parent does not exist: $outputParent"
}
if ((Get-Item -LiteralPath $outputParent).Attributes.HasFlag(
        [IO.FileAttributes]::ReparsePoint
    )) {
    throw "Measurement staging parent cannot be a reparse point"
}
$workspacePrefix = $workspacePath.TrimEnd("\", "/") +
    [IO.Path]::DirectorySeparatorChar
if ($outputFullPath.StartsWith(
        $workspacePrefix,
        [StringComparison]::OrdinalIgnoreCase
    )) {
    throw "Measurement staging output must be outside the corpus workspace"
}
$writeProbe = Join-Path $outputParent ".csu-write-$([Guid]::NewGuid().ToString('N'))"
$probeStream = $null
try {
    $probeStream = [IO.File]::Open(
        $writeProbe,
        [IO.FileMode]::CreateNew,
        [IO.FileAccess]::Write,
        [IO.FileShare]::None
    )
    $probeStream.Flush($true)
    $probeStream.Dispose()
}
finally {
    if ($null -ne $probeStream) {
        $probeStream.Dispose()
    }
    if (Test-Path -LiteralPath $writeProbe) {
        Remove-Item -LiteralPath $writeProbe -Force
    }
}
$authorityHash = (
    Get-FileHash -LiteralPath (Join-Path $authorityPath "authority.json") `
        -Algorithm SHA256
).Hash.ToLowerInvariant()
if ($authorityHash -ne $manifest.corpus_200k.authority.sha256) {
    throw "Measurement Authority is not the frozen Performance Authority"
}
$repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "../../.."))
$cargoLockHash = (
    Get-FileHash -LiteralPath (Join-Path $repositoryRoot "Cargo.lock") `
        -Algorithm SHA256
).Hash.ToLowerInvariant()
$runnerScriptHash = (
    Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256
).Hash.ToLowerInvariant()
$verifierScriptHash = (
    Get-FileHash -LiteralPath $verifierPath -Algorithm SHA256
).Hash.ToLowerInvariant()
$manifestHash = (
    Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256
).Hash.ToLowerInvariant()
$executableHash = (
    Get-FileHash -LiteralPath $executablePath -Algorithm SHA256
).Hash.ToLowerInvariant()
if ($runnerScriptHash -ne $manifest.runner.script.sha256 -or
    $verifierScriptHash -ne $manifest.runner.verifier.sha256) {
    throw "Measurement scripts do not match the frozen manifest"
}
$inputReceipt = (
    & $verifierPath -VerifyCorpusDirectory $workspacePath `
        -PrepareMeasurement | Out-String
) | ConvertFrom-Json
$measuredCandidate = $inputReceipt.measured_candidate
$measuredCandidateHash = Get-JsonSha256 -Value $measuredCandidate
$premeasurementFullPatchHash = $inputReceipt.premeasurement_full_patch_sha256
if ($null -eq $measuredCandidate -or
    $measuredCandidate.executable.sha256 -ne $executableHash -or
    $measuredCandidate.benchmark_manifest_sha256 -ne $manifestHash -or
    $measuredCandidate.performance_authority_sha256 -ne $authorityHash -or
    $measuredCandidate.cargo_lock_sha256 -ne $cargoLockHash -or
    $measuredCandidateHash -notmatch "^[0-9a-f]{64}$" -or
    $premeasurementFullPatchHash -notmatch "^[0-9a-f]{64}$") {
    throw "Measurement candidate receipt does not identify the supplied inputs"
}

$lockedInputs = [Collections.Generic.List[IO.FileStream]]::new()
$lockedPaths = [Collections.Generic.HashSet[string]]::new(
    [StringComparer]::OrdinalIgnoreCase
)
try {
foreach ($path in @(
        $executablePath,
        (Join-Path $authorityPath "authority.json"),
        (Join-Path $repositoryRoot "Cargo.lock"),
        $PSCommandPath,
        $verifierPath,
        $manifestPath
    ) + @(Get-ChildItem -LiteralPath $workspacePath -Recurse -File |
        ForEach-Object FullName)) {
    $fullPath = [IO.Path]::GetFullPath($path)
    if ($lockedPaths.Add($fullPath)) {
        $lockedInputs.Add([IO.File]::Open(
                $fullPath,
                [IO.FileMode]::Open,
                [IO.FileAccess]::Read,
                [IO.FileShare]::Read
            ))
    }
}

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
    $measurements.Add([pscustomobject][ordered]@{
        run = $run
        elapsed_ms = $measurement.elapsed_ms
        peak_working_set_bytes = $measurement.peak_working_set_bytes
        exit_code = $measurement.exit_code
        stdout_bytes = $measurement.stdout_bytes
        stdout_sha256 = $measurement.stdout_sha256
        stderr_bytes = $measurement.stderr_bytes
        stderr_sha256 = $measurement.stderr_sha256
        review_summary = $measurement.review_summary
    })
}

$postInputReceipt = (
    & $verifierPath -VerifyCorpusDirectory $workspacePath `
        -PrepareMeasurement | Out-String
) | ConvertFrom-Json
$postExecutableHash = (
    Get-FileHash -LiteralPath $executablePath -Algorithm SHA256
).Hash.ToLowerInvariant()
$postAuthorityHash = (
    Get-FileHash -LiteralPath (Join-Path $authorityPath "authority.json") `
        -Algorithm SHA256
).Hash.ToLowerInvariant()
$postCargoLockHash = (
    Get-FileHash -LiteralPath (Join-Path $repositoryRoot "Cargo.lock") `
        -Algorithm SHA256
).Hash.ToLowerInvariant()
$postRunnerHash = (
    Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256
).Hash.ToLowerInvariant()
$postVerifierHash = (
    Get-FileHash -LiteralPath $verifierPath -Algorithm SHA256
).Hash.ToLowerInvariant()
$postManifestHash = (
    Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256
).Hash.ToLowerInvariant()
if ($postExecutableHash -ne $executableHash -or
    $postAuthorityHash -ne $authorityHash -or
    $postCargoLockHash -ne $cargoLockHash -or
    $postRunnerHash -ne $runnerScriptHash -or
    $postVerifierHash -ne $verifierScriptHash -or
    $postManifestHash -ne $manifestHash -or
    (Get-JsonSha256 -Value $postInputReceipt) -ne
        (Get-JsonSha256 -Value $inputReceipt)) {
    throw "A pinned measurement input changed during the fresh-process run"
}

$sortedElapsed = @($measurements.elapsed_ms | Sort-Object)
$p95Index = [Math]::Ceiling(0.95 * $Runs) - 1
$uniqueProjectionDigests = @(
    $measurements.stdout_sha256 | Sort-Object -Unique
)
$uniqueSemanticDigests = @(
    $measurements.review_summary.semantic_summary_sha256 |
        Sort-Object -Unique
)
$receipt = [pscustomobject][ordered]@{
    schema_version = 4
    recorded_at_utc = [DateTimeOffset]::UtcNow.ToString("O")
    executable_sha256 = $executableHash
    cargo_lock_sha256 = $cargoLockHash
    runner_identity = $manifest.runner.identity
    runner_script_sha256 = $runnerScriptHash
    verifier_script_sha256 = $verifierScriptHash
    runner_environment = $inputReceipt.runner_environment
    authority_sha256 = $authorityHash
    workspace = $workspacePath
    corpus_files = $inputReceipt.corpus_files
    corpus_physical_lines = $inputReceipt.corpus_physical_lines
    corpus_digest = $inputReceipt.corpus_digest
    inventory_sha256 = $inputReceipt.inventory_sha256
    benchmark_manifest_sha256 = $manifestHash
    measured_candidate_sha256 = $measuredCandidateHash
    premeasurement_full_patch_sha256 = $premeasurementFullPatchHash
    runs = $Runs
    warmup_runs = $WarmupRuns
    p95_method = "nearest_rank_ceiling_0.95_times_n"
    p95_elapsed_ms = $sortedElapsed[$p95Index]
    p95_optimization_target_met = (
        $sortedElapsed[$p95Index] -le
            $manifest.release_evidence.p95_optimization_target_ms
    )
    maximum_peak_working_set_bytes = (
        $measurements.peak_working_set_bytes | Measure-Object -Maximum
    ).Maximum
    deterministic_projection = $uniqueProjectionDigests.Count -eq 1
    diagnostic_incomplete = [bool]$DiagnosticIncomplete
    projection_digests = $uniqueProjectionDigests
    semantic_summary_digests = $uniqueSemanticDigests
    review_summary = $measurements[0].review_summary
    measurements = $measurements
    status = "unverified_measurement_staging"
}
$receiptJson = ($receipt | ConvertTo-Json -Depth 20).Replace("`r`n", "`n")
$receiptBytes = [Text.UTF8Encoding]::new($false).GetBytes($receiptJson + "`n")
$receiptStream = [IO.FileStream]::new(
    $outputFullPath,
    [IO.FileMode]::CreateNew,
    [IO.FileAccess]::Write,
    [IO.FileShare]::None,
    4096,
    [IO.FileOptions]::WriteThrough
)
try {
    $receiptStream.Write($receiptBytes, 0, $receiptBytes.Length)
    $receiptStream.Flush($true)
}
finally {
    $receiptStream.Dispose()
}
}
finally {
foreach ($lockedInput in $lockedInputs) {
    if ($null -ne $lockedInput) {
        $lockedInput.Dispose()
    }
}
}
