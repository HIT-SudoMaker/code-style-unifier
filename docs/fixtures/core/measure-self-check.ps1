[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Workspace,
    [Parameter(Mandatory)][string]$OutputPath
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-FileIdentity {
    param([Parameter(Mandatory)][string]$RelativePath)

    return [pscustomobject][ordered]@{
        path = $RelativePath
        sha256 = (Get-FileHash -LiteralPath (
            Join-Path $repositoryRoot $RelativePath
        ) -Algorithm SHA256).Hash.ToLowerInvariant()
    }
}

$repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "../../.."))
$outputFullPath = [IO.Path]::GetFullPath($OutputPath)
$targetPrefix = (Join-Path $repositoryRoot "target") +
    [IO.Path]::DirectorySeparatorChar
if (-not $outputFullPath.StartsWith(
        $targetPrefix, [StringComparison]::OrdinalIgnoreCase
    ) -or (Test-Path -LiteralPath $outputFullPath)) {
    throw "Self-check output must be a new file under the repository target directory"
}
$workspacePath = [IO.Path]::GetFullPath($Workspace)
if (-not (Test-Path -LiteralPath $workspacePath -PathType Container)) {
    throw "Missing corpus workspace: $workspacePath"
}
for ($parent = Get-Item -LiteralPath $workspacePath; $null -ne $parent;
    $parent = $parent.Parent) {
    if ($parent.Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)) {
        throw "Corpus workspace must not traverse a reparse point"
    }
}
$workspacePrefix = $workspacePath.TrimEnd("\", "/") +
    [IO.Path]::DirectorySeparatorChar
if ($outputFullPath.StartsWith(
        $workspacePrefix, [StringComparison]::OrdinalIgnoreCase
    )) {
    throw "Self-check output must be outside the corpus workspace"
}
$outputParent = Split-Path -Parent $outputFullPath
if (-not (Test-Path -LiteralPath $outputParent -PathType Container)) {
    throw "Self-check output parent must already exist"
}
for ($parent = Get-Item -LiteralPath $outputParent; $null -ne $parent;
    $parent = $parent.Parent) {
    if ($parent.Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)) {
        throw "Self-check output must not traverse a reparse point"
    }
}

$verifier = Join-Path $PSScriptRoot "verify-inputs.ps1"
$before = (& $verifier -VerifyCorpusDirectory $Workspace -PrepareMeasurement |
    Out-String) | ConvertFrom-Json
$candidate = $before.measured_candidate
if ($null -eq $candidate) {
    throw "Candidate preparation returned no source identity"
}
$performance = (& $verifier -VerifyReleaseEvidenceOnly | Out-String) |
    ConvertFrom-Json
if ($null -eq $performance.release_evidence) {
    throw "The current candidate has no verified performance receipt"
}
$cargoManifest = Join-Path $repositoryRoot "Cargo.toml"
& cargo fmt --manifest-path $cargoManifest --all -- --check
if ($LASTEXITCODE -ne 0) { throw "Candidate formatting failed" }
& cargo clippy --manifest-path $cargoManifest --locked --all-targets -- -D warnings
if ($LASTEXITCODE -ne 0) { throw "Candidate Clippy failed" }
& cargo test --manifest-path $cargoManifest --locked
if ($LASTEXITCODE -ne 0) { throw "Candidate tests failed" }

$authority = Get-FileIdentity -RelativePath "docs/authority/csu-self/authority.json"
$authorityDirectory = Split-Path -Parent (Join-Path $repositoryRoot $authority.path)
$executable = Join-Path $repositoryRoot $candidate.executable.path
$scopes = foreach ($scope in @("src", "tests")) {
    $sourcePath = Join-Path $repositoryRoot $scope
    $projection = (& $executable review --authority $authorityDirectory --workspace $sourcePath --format json |
        Out-String) | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or $projection.terminal -ne "sealed" -or
        $projection.disposition -ne "clean" -or
        $projection.review.completion -ne "complete" -or
        $projection.review.finding_summary.total -ne 0 -or
        $projection.review.blocked_families -ne 0) {
        throw "Current source self-review failed for $scope"
    }
    $review = $projection.review
    $files = @($review.scope.value.files).Count
    if ($files -eq 0 -or $review.metrics.files_read -ne $files -or
        $review.metrics.byte_sweeps -ne $files -or
        $review.metrics.structural_parses -ne $files) {
        throw "Current self-review did not capture and observe each source exactly once"
    }
    [pscustomobject][ordered]@{
        path = $scope
        physical_lines = if ($scope -eq "src") {
            $candidate.line_counts.product_rust
        } else { $candidate.line_counts.test_rust }
        terminal = $projection.terminal
        disposition = $projection.disposition
        completion = $review.completion
        seal = $review.seal
        admitted_files = $files
        findings = $review.finding_summary
        blocked_families = $review.blocked_families
        metrics = $review.metrics
    }
}
$after = (& $verifier -VerifyCorpusDirectory $Workspace -PrepareMeasurement |
    Out-String) | ConvertFrom-Json
if (($before | ConvertTo-Json -Depth 20 -Compress) -ne
    ($after | ConvertTo-Json -Depth 20 -Compress)) {
    throw "Candidate identity changed during self-check measurement"
}
$sourceCandidate = [pscustomobject][ordered]@{
    state = "wip_unpublished"
    base_head = $candidate.base_head
    tracked_patch_sha256 = $before.premeasurement_full_patch_sha256
    untracked_inputs = @($candidate.untracked_inputs)
    untracked_maintenance = @($candidate.untracked_maintenance)
    retained_local_planning_material = $candidate.retained_local_planning_material
    cargo_lock_sha256 = $candidate.cargo_lock_sha256
    executable = $candidate.executable
    semantic_authority_digest = $candidate.semantic_authority_digest
    runner_environment = $before.runner_environment
}
$standards = Get-FileIdentity -RelativePath "docs/coding_standards.md"
$standards | Add-Member -NotePropertyName physical_lines -NotePropertyValue (
    $candidate.line_counts.normative_standard
)
$receipt = [pscustomobject][ordered]@{
    schema_version = 3
    source_candidate = $sourceCandidate
    measured_candidate = $candidate
    self_review = [pscustomobject][ordered]@{
        authority = $authority
        scopes = @($scopes)
        compiled_test_catalog = $candidate.compiled_test_catalog
    }
    candidate_inputs = [pscustomobject][ordered]@{
        fixture_manifest = Get-FileIdentity "docs/fixtures/core/fixture-manifest.json"
        benchmark_manifest = Get-FileIdentity "docs/fixtures/core/benchmark-manifest.json"
        parser_admission = Get-FileIdentity "docs/fixtures/core/parser-admission.json"
        release_workflow = Get-FileIdentity ".github/workflows/release.yml"
        release_evidence = Get-FileIdentity "docs/fixtures/core/release_runs.json"
        standards = $standards
        corpus = $candidate.corpus
        skills = [pscustomobject][ordered]@{
            agent_skill_path = ".agents/skills/csu-review/SKILL.md"
            claude_skill_path = ".claude/skills/csu-review/SKILL.md"
            lock_path = "skills-lock.json"
            skill_sha256 = $candidate.skills.skill_sha256
            agent_folder_sha256 = $candidate.skills.folder_sha256
            lock_sha256 = $candidate.skills.lock_sha256
        }
    }
    evidence_tracks = [pscustomobject][ordered]@{
        semantic = "verified"
        self_review = "verified"
        fixture_input = "verified"
        performance = "verified_current_inputs"
        provenance = "pinned_release_candidate"
        overall = "release_candidate_evidence_complete_unpublished"
    }
}
$bytes = [Text.UTF8Encoding]::new($false).GetBytes(
    (($receipt | ConvertTo-Json -Depth 20).Replace("`r`n", "`n")) + "`n"
)
$stream = [IO.FileStream]::new(
    $outputFullPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write,
    [IO.FileShare]::None, 4096, [IO.FileOptions]::WriteThrough
)
try {
    $stream.Write($bytes, 0, $bytes.Length)
    $stream.Flush($true)
}
finally { $stream.Dispose() }
Write-Output $outputFullPath
