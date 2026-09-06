[CmdletBinding()]
param(
    [switch]$BuildCorpus,
    [string]$OutputDirectory,
    [string]$VerifyCorpusDirectory,
    [switch]$PrepareMeasurement,
    [string]$ReleaseEvidencePath,
    [switch]$VerifyReleaseEvidenceOnly,
    [string]$ExpectedStagingSha256,
    [switch]$PromoteReleaseEvidence,
    [string]$SelfCheckEvidencePath,
    [string]$ExpectedSelfCheckStagingSha256,
    [switch]$PromoteSelfCheckEvidence
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$hasOutputDirectory = -not [string]::IsNullOrWhiteSpace($OutputDirectory)
$hasCorpusDirectory = -not [string]::IsNullOrWhiteSpace($VerifyCorpusDirectory)
$hasReleaseEvidence = -not [string]::IsNullOrWhiteSpace($ReleaseEvidencePath)
$hasStagingHash = -not [string]::IsNullOrWhiteSpace($ExpectedStagingSha256)
$hasSelfCheckEvidence = -not [string]::IsNullOrWhiteSpace(
    $SelfCheckEvidencePath
)
$hasSelfCheckStagingHash = -not [string]::IsNullOrWhiteSpace(
    $ExpectedSelfCheckStagingSha256
)
$corpusMode = $BuildCorpus -or $hasCorpusDirectory -or $PrepareMeasurement
$releaseMode = $hasReleaseEvidence -or $VerifyReleaseEvidenceOnly -or
    $hasStagingHash -or $PromoteReleaseEvidence
$selfCheckMode = $hasSelfCheckEvidence -or $hasSelfCheckStagingHash -or
    $PromoteSelfCheckEvidence
if ($BuildCorpus -and $hasCorpusDirectory) {
    throw "Use either -BuildCorpus or -VerifyCorpusDirectory"
}
if ($hasOutputDirectory -ne [bool]$BuildCorpus) {
    throw "-OutputDirectory is required exactly when -BuildCorpus is present"
}
if ($corpusMode -and ($releaseMode -or $selfCheckMode)) {
    throw "Corpus preparation and staging verification are separate modes"
}
if ($releaseMode -and $selfCheckMode) {
    throw "Release and self-check staging are verified separately"
}
if ($PrepareMeasurement -and -not $BuildCorpus -and -not $hasCorpusDirectory) {
    throw "-PrepareMeasurement requires a built or verified corpus"
}
if (($BuildCorpus -or $hasCorpusDirectory) -ne [bool]$PrepareMeasurement) {
    throw "Corpus construction or verification requires -PrepareMeasurement"
}
if ($releaseMode -and
    (-not $hasReleaseEvidence -or -not $VerifyReleaseEvidenceOnly -or
        -not $hasStagingHash)) {
    throw "Staging verification requires its path, exact hash, and release-only mode"
}
if ($hasStagingHash -and $ExpectedStagingSha256 -notmatch "^[0-9a-f]{64}$") {
    throw "The staging receipt hash must be lowercase SHA-256"
}
if ($selfCheckMode -and
    (-not $hasSelfCheckEvidence -or -not $hasSelfCheckStagingHash -or
        -not $PromoteSelfCheckEvidence)) {
    throw "Self-check promotion requires its staging path and exact hash"
}
if ($hasSelfCheckStagingHash -and
    $ExpectedSelfCheckStagingSha256 -notmatch "^[0-9a-f]{64}$") {
    throw "The self-check staging hash must be lowercase SHA-256"
}

function Get-Sha256Text {
    param([Parameter(Mandatory)][AllowEmptyString()][string]$Text)

    $bytes = [Text.Encoding]::UTF8.GetBytes($Text)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try {
        $hash = $algorithm.ComputeHash($bytes)
    }
    finally {
        $algorithm.Dispose()
    }
    return -join ($hash | ForEach-Object { $_.ToString("x2") })
}

function Get-Sha256Bytes {
    param([Parameter(Mandatory)][AllowEmptyCollection()][byte[]]$Bytes)

    $hash = [Security.Cryptography.SHA256]::HashData($Bytes)
    return [Convert]::ToHexString($hash).ToLowerInvariant()
}

function Get-JsonSha256 {
    param([Parameter(Mandatory)][AllowEmptyCollection()]$Value)

    return Get-Sha256Text -Text (
        ConvertTo-Json -InputObject $Value -Depth 20 -Compress
    )
}

function Install-VerifiedReceipt {
    param(
        [Parameter(Mandatory)][string]$CanonicalPath,
        [Parameter(Mandatory)][byte[]]$VerifiedBytes,
        [Parameter(Mandatory)][string]$VerifiedSha256,
        [AllowNull()][string]$ExpectedCanonicalSha256,
        [Parameter(Mandatory)][string]$ArtifactStem
    )

    if ((Get-Sha256Bytes -Bytes $VerifiedBytes) -ne $VerifiedSha256) {
        throw "Verified receipt bytes do not own their SHA-256"
    }
    $directory = Split-Path -Parent $CanonicalPath
    $promotionPath = Join-Path $directory `
        ".$ArtifactStem.$([Guid]::NewGuid().ToString('N')).tmp"
    $lockPath = Join-Path $directory ".$ArtifactStem.promote.lock"
    $backupPath = Join-Path $directory `
        ".$ArtifactStem.$([Guid]::NewGuid().ToString('N')).bak"
    $lock = $null
    $lockAcquired = $false
    $stream = [IO.FileStream]::new(
        $promotionPath,
        [IO.FileMode]::CreateNew,
        [IO.FileAccess]::Write,
        [IO.FileShare]::None,
        4096,
        [IO.FileOptions]::WriteThrough
    )
    try {
        $stream.Write($VerifiedBytes, 0, $VerifiedBytes.Length)
        $stream.Flush($true)
    }
    finally {
        $stream.Dispose()
    }
    try {
        $promotionHash = (
            Get-FileHash -LiteralPath $promotionPath -Algorithm SHA256
        ).Hash.ToLowerInvariant()
        if ($promotionHash -ne $VerifiedSha256) {
            throw "Receipt promotion bytes differ from verified bytes"
        }
        $lock = [IO.FileStream]::new(
            $lockPath,
            [IO.FileMode]::CreateNew,
            [IO.FileAccess]::Write,
            [IO.FileShare]::None
        )
        $lockAcquired = $true
        try {
            $canonicalExists = Test-Path -LiteralPath $CanonicalPath `
                -PathType Leaf
            $currentCanonicalSha256 = if ($canonicalExists) {
                (Get-FileHash -LiteralPath $CanonicalPath `
                    -Algorithm SHA256).Hash.ToLowerInvariant()
            } else {
                $null
            }
            if ($currentCanonicalSha256 -ne $ExpectedCanonicalSha256) {
                throw "Canonical receipt changed during staging verification"
            }
            if ($canonicalExists) {
                [IO.File]::Replace($promotionPath, $CanonicalPath, $backupPath)
            } else {
                [IO.File]::Move($promotionPath, $CanonicalPath)
            }
        }
        finally {
            $lock.Dispose()
            $lock = $null
        }
    }
    finally {
        if ($null -ne $lock) {
            $lock.Dispose()
        }
        if ($lockAcquired -and (Test-Path -LiteralPath $lockPath -PathType Leaf)) {
            Remove-Item -LiteralPath $lockPath -Force
        }
        if (Test-Path -LiteralPath $promotionPath -PathType Leaf) {
            Remove-Item -LiteralPath $promotionPath -Force
        }
    }
    $canonicalSha256 = (
        Get-FileHash -LiteralPath $CanonicalPath -Algorithm SHA256
    ).Hash.ToLowerInvariant()
    if ($canonicalSha256 -ne $VerifiedSha256) {
        throw "Promoted receipt differs from verified bytes"
    }
    if (Test-Path -LiteralPath $backupPath -PathType Leaf) {
        Remove-Item -LiteralPath $backupPath -Force
    }
    return $canonicalSha256
}

function Assert-ExactFields {
    param(
        [Parameter(Mandatory)]$Value,
        [Parameter(Mandatory)][string[]]$Fields,
        [Parameter(Mandatory)][string]$Owner
    )

    $actual = @($Value.PSObject.Properties.Name | Sort-Object)
    $expected = @($Fields | Sort-Object)
    if (($actual -join ",") -ne ($expected -join ",")) {
        throw "$Owner contains missing or unowned fields"
    }
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

function Get-SkillFolderHash {
    param([Parameter(Mandatory)][string]$Path, [switch]$SharedOnly)

    $root = [IO.Path]::GetFullPath($Path).TrimEnd("\", "/")
    $files = @(Get-ChildItem -LiteralPath $root -Recurse -File -ErrorAction Stop |
        ForEach-Object {
            [pscustomobject]@{
                relative = $_.FullName.Substring($root.Length + 1).Replace("\", "/")
                path = $_.FullName
            }
        } | Sort-Object relative)
    $stream = [IO.MemoryStream]::new()
    try {
        foreach ($file in $files) {
            if ($SharedOnly -and $file.relative -ceq "agents/openai.yaml") {
                continue
            }
            $pathBytes = [Text.Encoding]::UTF8.GetBytes($file.relative)
            $stream.Write($pathBytes, 0, $pathBytes.Length)
            $content = [IO.File]::ReadAllBytes($file.path)
            $stream.Write($content, 0, $content.Length)
        }
        $hash = [Security.Cryptography.SHA256]::HashData($stream.ToArray())
    }
    finally {
        $stream.Dispose()
    }
    return [Convert]::ToHexString($hash).ToLowerInvariant()
}

function Get-RunnerEnvironment {
    param([Parameter(Mandatory)][string]$WorkspacePath)

    if (-not $IsWindows) {
        throw "This frozen release runner requires Windows"
    }
    $processors = @(Get-CimInstance Win32_Processor)
    $physicalMemory = @(
        Get-CimInstance Win32_PhysicalMemory |
            Measure-Object Capacity -Sum
    ).Sum
    $workspaceRoot = [IO.Path]::GetPathRoot([IO.Path]::GetFullPath($WorkspacePath))
    $drive = $workspaceRoot.Substring(0, 1)
    $volume = Get-Volume -DriveLetter $drive
    $disk = Get-Partition -DriveLetter $drive | Get-Disk
    $rustcVerbose = ((& rustc --version --verbose) -join "`n").Trim()
    $powerPlan = ((& powercfg /GETACTIVESCHEME) -join "`n")
    if ($LASTEXITCODE -ne 0 -or
        $powerPlan -notmatch "(?i)[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}") {
        throw "Cannot identify the active Windows power plan"
    }
    $powerPlanGuid = $Matches[0].ToLowerInvariant()
    return [pscustomobject][ordered]@{
        os_description = [Runtime.InteropServices.RuntimeInformation]::OSDescription
        os_architecture = (
            [Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()
        )
        cpu_name = ([string]($processors.Name -join "; ")).Trim()
        physical_cores = [int](
            $processors | Measure-Object NumberOfCores -Sum
        ).Sum
        logical_processors = [int](
            $processors | Measure-Object NumberOfLogicalProcessors -Sum
        ).Sum
        installed_memory_bytes = [long]$physicalMemory
        storage_model = ([string]($disk.Model -join "; ")).Trim()
        storage_bus = [string]($disk.BusType -join "; ")
        storage_filesystem = [string]$volume.FileSystem
        observed_tools = [pscustomobject][ordered]@{
            rustc_verbose = $rustcVerbose
            cargo = ((& cargo --version) -join "`n").Trim()
            rustfmt = ((& rustfmt --version) -join "`n").Trim()
            clippy_driver = ((& clippy-driver --version) -join "`n").Trim()
            powershell = "PowerShell Core $($PSVersionTable.PSVersion)"
            git = ((& git --version) -join "`n").Trim()
        }
        active_power_plan_guid = $powerPlanGuid
    }
}

function Get-ReviewSummaryDigest {
    param([Parameter(Mandatory)]$Summary)

    $canonical = [pscustomobject][ordered]@{
        terminal = [string]$Summary.terminal
        disposition = [string]$Summary.disposition
        completion = [string]$Summary.completion
        scope_kind = [string]$Summary.scope_kind
        seal = [string]$Summary.seal
        finding_summary = [pscustomobject][ordered]@{
            total = [int]$Summary.finding_summary.total
            hard_violation = [int]$Summary.finding_summary.hard_violation
            review_required = [int]$Summary.finding_summary.review_required
        }
        finding_rule_summary = @($Summary.finding_rule_summary)
        findings_sha256 = [string]$Summary.findings_sha256
        blocked_families = [int]$Summary.blocked_families
        blocked_family_summary = @($Summary.blocked_family_summary)
        blocked_family_details_sha256 = [string](
            $Summary.blocked_family_details_sha256
        )
        admitted_files = [int]$Summary.admitted_files
        metrics = [pscustomobject][ordered]@{
            files_read = [int]$Summary.metrics.files_read
            byte_sweeps = [int]$Summary.metrics.byte_sweeps
            structural_parses = [int]$Summary.metrics.structural_parses
        }
    }
    return Get-JsonSha256 -Value $canonical
}

function Get-PhysicalLineCount {
    param([byte[]]$Bytes)

    if ($Bytes.Length -eq 0) {
        return 0
    }
    $newlines = 0
    foreach ($byte in $Bytes) {
        if ($byte -eq 10) {
            $newlines += 1
        }
    }
    if ($Bytes[-1] -eq 10) {
        return $newlines
    }
    return $newlines + 1
}

function Get-RustPhysicalLineCount {
    param([Parameter(Mandatory)][string]$Path)

    $physicalLines = 0
    foreach ($file in Get-ChildItem -LiteralPath $Path -Recurse -File `
        -Filter "*.rs") {
        $physicalLines += Get-PhysicalLineCount -Bytes (
            [IO.File]::ReadAllBytes($file.FullName)
        )
    }
    return $physicalLines
}

function Get-TrackedPatchHash {
    param(
        [Parameter(Mandatory)][string]$RepositoryRoot,
        [Parameter(Mandatory)][string]$BaseHead,
        [string[]]$ExcludedPaths = @()
    )

    $startInfo = [Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = "git"
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $arguments = [Collections.Generic.List[string]]::new()
    foreach ($argument in @(
        "-C", $RepositoryRoot, "diff", "--binary", "--full-index",
        "--no-ext-diff", $BaseHead, "--", "."
    )) {
        $arguments.Add($argument)
    }
    foreach ($path in $ExcludedPaths) {
        if ([string]::IsNullOrWhiteSpace($path) -or
            [IO.Path]::IsPathRooted($path) -or $path.Contains("`n")) {
            throw "Functional patch exclusion must be a relative repository path"
        }
        $arguments.Add(":(exclude)$($path.Replace('\', '/'))")
    }
    foreach ($argument in $arguments) {
        [void]$startInfo.ArgumentList.Add($argument)
    }

    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    if (-not $process.Start()) {
        throw "Cannot start git to identify the tracked WIP patch"
    }
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try {
        $hash = $algorithm.ComputeHash($process.StandardOutput.BaseStream)
    }
    finally {
        $algorithm.Dispose()
    }
    $process.WaitForExit()
    $stderr = $stderrTask.GetAwaiter().GetResult()
    if ($process.ExitCode -ne 0) {
        throw "Cannot identify the tracked WIP patch: $stderr"
    }
    return -join ($hash | ForEach-Object { $_.ToString("x2") })
}

function Get-UntrackedFileRecords {
    param(
        [Parameter(Mandatory)][string]$RepositoryRoot,
        [Parameter(Mandatory)][AllowEmptyCollection()][string[]]$Paths
    )

    [object[]]$records = @(
        $Paths | ForEach-Object {
            [pscustomobject][ordered]@{
                path = $_
                sha256 = (
                    Get-FileHash -LiteralPath (Join-Path $RepositoryRoot $_) `
                        -Algorithm SHA256
                ).Hash.ToLowerInvariant()
            }
        }
    )
    $comparison = [Collections.Generic.Comparer[object]]::Create({
        param($left, $right)
        return [StringComparer]::Ordinal.Compare($left.path, $right.path)
    })
    [Array]::Sort($records, $comparison)
    return ,$records
}

function Get-CompiledTestCatalog {
    param([Parameter(Mandatory)][string]$CargoManifestPath)

    $output = @(
        & cargo test --manifest-path $CargoManifestPath --locked -- --list
    )
    if ($LASTEXITCODE -ne 0) {
        throw "Cannot enumerate the compiled test catalog"
    }
    [string[]]$tests = @($output | Where-Object { $_ -match ": test$" })
    [Array]::Sort($tests, [StringComparer]::Ordinal)
    return [pscustomobject][ordered]@{
        tests = $tests.Count
        sha256 = Get-Sha256Text -Text (($tests -join "`n") + "`n")
    }
}

function Get-CurrentMeasuredCandidate {
    $compiledTestCatalog = Get-CompiledTestCatalog `
        -CargoManifestPath $cargoManifestPath
    $baseHead = (& git -C $repositoryRoot rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "Cannot identify the measurement candidate base HEAD"
    }
    $fullPatchHash = Get-TrackedPatchHash -RepositoryRoot $repositoryRoot `
        -BaseHead $baseHead
    $functionalExclusions = @("docs/fixtures/core/release_runs.json")
    $functionalPatchHash = Get-TrackedPatchHash `
        -RepositoryRoot $repositoryRoot -BaseHead $baseHead `
        -ExcludedPaths $functionalExclusions

    [string[]]$untrackedInputs = @(
        & git -C $repositoryRoot ls-files --others --exclude-standard -- `
            src tests docs .agents/skills/csu-review .claude/skills/csu-review
    )
    if ($LASTEXITCODE -ne 0) {
        throw "Cannot enumerate intended untracked candidate inputs"
    }
    [Array]::Sort($untrackedInputs, [StringComparer]::Ordinal)
    $untrackedInputRecords = Get-UntrackedFileRecords `
        -RepositoryRoot $repositoryRoot -Paths $untrackedInputs

    [string[]]$untrackedMaintenance = @(
        & git -C $repositoryRoot ls-files --others --exclude-standard -- `
            .gitattributes
    )
    if ($LASTEXITCODE -ne 0) {
        throw "Cannot enumerate intended untracked maintenance"
    }
    [Array]::Sort($untrackedMaintenance, [StringComparer]::Ordinal)
    $maintenanceRecords = Get-UntrackedFileRecords `
        -RepositoryRoot $repositoryRoot -Paths $untrackedMaintenance

    $planningRoot = ".scratch"
    $planningEntries = @(
        Get-ChildItem -LiteralPath (Join-Path $repositoryRoot $planningRoot) `
            -Recurse -Force
    )
    if (@($planningEntries | Where-Object {
                $_.Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)
            }).Count -ne 0) {
        throw "Retained local planning material must not traverse a reparse point"
    }
    [string[]]$planningPaths = @(
        $planningEntries | Where-Object { -not $_.PSIsContainer } |
            ForEach-Object {
                [IO.Path]::GetRelativePath(
                    $repositoryRoot, $_.FullName
                ).Replace("\", "/")
            }
    )
    if (@($planningPaths | Where-Object {
                [IO.Path]::GetExtension($_) -notin @(".md", ".json")
            }).Count -ne 0) {
        throw "Retained measurement planning contains an unsupported file"
    }
    [Array]::Sort($planningPaths, [StringComparer]::Ordinal)
    $planningRecords = Get-UntrackedFileRecords `
        -RepositoryRoot $repositoryRoot -Paths $planningPaths

    [string[]]$allUntracked = @(
        & git -C $repositoryRoot ls-files --others --exclude-standard
    )
    if ($LASTEXITCODE -ne 0) {
        throw "Cannot enumerate the measurement candidate"
    }
    $ownedUntracked = @($untrackedInputs) + @($untrackedMaintenance) +
        @($planningPaths)
    $unexpectedUntracked = @($allUntracked | Where-Object {
            $_ -notin $ownedUntracked
        })
    if ($unexpectedUntracked.Count -ne 0) {
        throw "Unclassified untracked measurement input: $unexpectedUntracked"
    }

    $candidateExecutablePath = Join-Path $repositoryRoot "target/release/csu.exe"
    if (-not (Test-Path -LiteralPath $candidateExecutablePath -PathType Leaf)) {
        throw "Missing release executable for measurement candidate"
    }
    $candidate = [pscustomobject][ordered]@{
        base_head = $baseHead
        functional_patch_sha256 = $functionalPatchHash
        functional_patch_exclusions = $functionalExclusions
        untracked_inputs = $untrackedInputRecords
        untracked_maintenance = $maintenanceRecords
        retained_local_planning_material = [pscustomobject][ordered]@{
            path = $planningRoot
            classification = "immutable_requirement_snapshot"
            files = $planningRecords.Count
            sha256 = Get-JsonSha256 -Value $planningRecords
        }
        cargo_lock_sha256 = $cargoLockHash
        executable = [pscustomobject][ordered]@{
            path = "target/release/csu.exe"
            sha256 = (
                Get-FileHash -LiteralPath $candidateExecutablePath `
                    -Algorithm SHA256
            ).Hash.ToLowerInvariant()
        }
        semantic_authority_digest = $fixtureManifest.semantic_authority_digest
        fixture_manifest_sha256 = $fixtureManifestHash
        benchmark_manifest_sha256 = $benchmarkManifestHash
        performance_authority_sha256 = $performanceAuthorityHash
        parser_admission_sha256 = $parserAdmissionManifest.receipt.sha256
        release_workflow_sha256 = $releaseWorkflowHash
        corpus = [pscustomobject][ordered]@{
            files = $selectedRecords.Count
            physical_lines = $selectedLines
            digest = $aggregateDigest
            inventory_sha256 = $inventoryHash
        }
        line_counts = [pscustomobject][ordered]@{
            product_rust = $productPhysicalLines
            test_rust = $testPhysicalLines
            normative_standard = $standardsLines
        }
        standards_sha256 = $standardsHash
        compiled_test_catalog = $compiledTestCatalog
        skills = [pscustomobject][ordered]@{
            skill_sha256 = $agentSkillHash
            folder_sha256 = $skillFolderHash
            lock_sha256 = $skillsLockHash
        }
        toolchain = $runnerEnvironment.observed_tools
    }
    return [pscustomobject][ordered]@{
        candidate = $candidate
        full_patch_sha256 = $fullPatchHash
    }
}

function Sort-Records {
    param([Parameter(Mandatory)][object[]]$Records)

    $comparison = [Collections.Generic.Comparer[object]]::Create({
        param($left, $right)
        return [StringComparer]::Ordinal.Compare($left.Key, $right.Key)
    })
    [Array]::Sort($Records, $comparison)
    return $Records
}

function Get-TargetRecords {
    param(
        [Parameter(Mandatory)][string]$TargetsRoot,
        [Parameter(Mandatory)]$Target
    )

    $targetRoot = Join-Path $TargetsRoot $Target.directory
    if (-not (Test-Path -LiteralPath $targetRoot -PathType Container)) {
        throw "Missing frozen target: $targetRoot"
    }
    $records = [Collections.Generic.List[object]]::new()
    foreach ($file in Get-ChildItem -LiteralPath $targetRoot -Recurse -File) {
        $extension = $file.Extension.ToLowerInvariant()
        $languageProperty = $Target.extensions.PSObject.Properties |
            Where-Object Name -EQ $extension |
            Select-Object -First 1
        if ($null -eq $languageProperty) {
            continue
        }
        $language = $languageProperty.Value
        $fullPath = [IO.Path]::GetFullPath($file.FullName)
        $relativePath = [IO.Path]::GetRelativePath(
            $targetRoot,
            $fullPath
        ).Replace("\", "/")
        if ([IO.Path]::IsPathRooted($relativePath) -or
            $relativePath -eq ".." -or $relativePath.StartsWith("../")) {
            throw "Target file escaped frozen root: $fullPath"
        }
        $bytes = [IO.File]::ReadAllBytes($file.FullName)
        $records.Add([pscustomobject]@{
            Target = [string]$Target.directory
            Language = [string]$language
            Path = $relativePath
            Key = "$($Target.directory)/$relativePath"
            FullPath = $file.FullName
            Bytes = [int64]$bytes.Length
            PhysicalLines = [int](Get-PhysicalLineCount -Bytes $bytes)
            Sha256 = (Get-FileHash -LiteralPath $file.FullName `
                -Algorithm SHA256).Hash.ToLowerInvariant()
        })
    }
    return Sort-Records -Records @($records)
}

function Get-ParserAdmissionRecords {
    param(
        [Parameter(Mandatory)][string]$TargetsRoot,
        [Parameter(Mandatory)]$Target,
        [Parameter(Mandatory)]$HeaderOwners
    )

    $targetRoot = Join-Path $TargetsRoot $Target.directory
    $records = [Collections.Generic.List[object]]::new()
    foreach ($file in Get-ChildItem -LiteralPath $targetRoot -Recurse -File) {
        $extension = $file.Extension
        $relativePath = [IO.Path]::GetRelativePath(
            $targetRoot,
            $file.FullName
        ).Replace("\", "/")
        $language = switch ($extension) {
            ".py" { "python" }
            ".rs" { "rust" }
            ".c" { "c" }
            ".h" {
                $key = "$($Target.directory)/$relativePath"
                if (-not $HeaderOwners.ContainsKey($key)) {
                    throw "Parser-admission header lacks Authority: $key"
                }
                [string]$HeaderOwners[$key]
            }
            { $_ -in @(".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx") } {
                "cpp"
            }
            default { $null }
        }
        if ([string]::IsNullOrEmpty([string]$language)) {
            continue
        }
        $bytes = [IO.File]::ReadAllBytes($file.FullName)
        $records.Add([pscustomobject]@{
            Target = [string]$Target.directory
            Language = [string]$language
            Path = $relativePath
            Key = "$($Target.directory)/$relativePath"
            FullPath = $file.FullName
            Bytes = [int64]$bytes.Length
            PhysicalLines = [int](Get-PhysicalLineCount -Bytes $bytes)
            Sha256 = Get-Sha256Bytes -Bytes $bytes
        })
    }
    return Sort-Records -Records @($records)
}

function Get-RecordDigest {
    param([Parameter(Mandatory)][object[]]$Records)

    $builder = [Text.StringBuilder]::new()
    foreach ($record in $Records) {
        [void]$builder.Append($record.Language)
        [void]$builder.Append("`t")
        [void]$builder.Append($record.Key)
        [void]$builder.Append("`t")
        [void]$builder.Append($record.Bytes)
        [void]$builder.Append("`t")
        [void]$builder.Append($record.PhysicalLines)
        [void]$builder.Append("`t")
        [void]$builder.Append($record.Sha256)
        [void]$builder.Append("`n")
    }
    return Get-Sha256Text -Text $builder.ToString()
}

function Select-ExactLanguageCorpus {
    param(
        [Parameter(Mandatory)][object[]]$Records,
        [Parameter(Mandatory)][string]$Language,
        [Parameter(Mandatory)][int]$PhysicalLines
    )

    $candidates = @($Records | Where-Object Language -eq $Language)
    $candidates = Sort-Records -Records $candidates
    $seen = [bool[]]::new($PhysicalLines + 1)
    $parentSum = [int[]]::new($PhysicalLines + 1)
    $parentFile = [int[]]::new($PhysicalLines + 1)
    for ($index = 0; $index -le $PhysicalLines; $index += 1) {
        $parentSum[$index] = -1
        $parentFile[$index] = -1
    }
    $seen[0] = $true

    :candidateLoop for ($fileIndex = 0; $fileIndex -lt $candidates.Count;
        $fileIndex += 1) {
        $weight = $candidates[$fileIndex].PhysicalLines
        if ($weight -le 0 -or $weight -gt $PhysicalLines) {
            continue
        }
        for ($sum = $PhysicalLines; $sum -ge $weight; $sum -= 1) {
            if (-not $seen[$sum] -and $seen[$sum - $weight]) {
                $seen[$sum] = $true
                $parentSum[$sum] = $sum - $weight
                $parentFile[$sum] = $fileIndex
            }
        }
        if ($seen[$PhysicalLines]) {
            break candidateLoop
        }
    }
    if (-not $seen[$PhysicalLines]) {
        throw "Cannot select exactly $PhysicalLines lines for $Language"
    }

    $selected = [Collections.Generic.List[object]]::new()
    $sum = $PhysicalLines
    while ($sum -gt 0) {
        $fileIndex = $parentFile[$sum]
        $selected.Add($candidates[$fileIndex])
        $sum = $parentSum[$sum]
    }
    return Sort-Records -Records @($selected)
}

$fixtureRoot = $PSScriptRoot
$repositoryRoot = [IO.Path]::GetFullPath(
    (Join-Path $fixtureRoot "../../..")
)
$fixtureManifestPath = Join-Path $fixtureRoot "fixture-manifest.json"
$fixtureManifest = Get-Content -LiteralPath $fixtureManifestPath `
    -Raw -Encoding UTF8 |
    ConvertFrom-Json
$fixtureManifestHash = (
    Get-FileHash -LiteralPath $fixtureManifestPath -Algorithm SHA256
).Hash.ToLowerInvariant()
if ($fixtureManifest.schema_version -ne 2) {
    throw "Frozen fixture manifest must use executable-oracle schema 2"
}
$authorityPath = Join-Path $fixtureRoot $fixtureManifest.authority.path
$authorityHash = (Get-FileHash -LiteralPath $authorityPath `
    -Algorithm SHA256).Hash.ToLowerInvariant()
if ($authorityHash -ne $fixtureManifest.authority.sha256) {
    throw "Frozen Authority fixture identity mismatch"
}
$authority = Get-Content -LiteralPath $authorityPath `
    -Raw -Encoding UTF8 | ConvertFrom-Json
$requiredLanguages = @("c", "cpp", "python", "rust")
$authorityFields = @($authority.PSObject.Properties.Name | Sort-Object)
$projectFactFields = @(
    "dependency_authority",
    "external_fixed_identifiers",
    "header_languages",
    "public_callables",
    "quantity_concepts",
    "schema_version",
    "token_vocabulary"
)
if ($authority.schema_version -ne 4 -or
    ($authorityFields -join ",") -ne ($projectFactFields -join ",")) {
    throw "Frozen Authority fixture must contain only schema 4 Project Facts"
}
$scenarioNames = @($fixtureManifest.scenario_contracts.PSObject.Properties.Name)
if ($scenarioNames.Count -ne 5 -or @($fixtureManifest.documents).Count -ne 20) {
    throw "Frozen behavior map must contain exactly five four-Profile scenarios"
}

foreach ($scenario in $scenarioNames) {
    $contract = $fixtureManifest.scenario_contracts.$scenario
    if ($contract.terminal -ne "sealed" -or
        $contract.completion -notin @("complete", "incomplete") -or
        $contract.disposition -notin @("clean", "findings", "incomplete") -or
        $null -eq $contract.findings -or
        $null -eq $contract.blocked_families) {
        throw "Scenario $scenario lacks an exact terminal oracle"
    }
    foreach ($finding in @($contract.findings)) {
        if ([string]::IsNullOrWhiteSpace($finding.rule) -or
            $finding.grade -notin @(
                "hard_violation",
                "review_required"
            ) -or
            [string]::IsNullOrWhiteSpace($finding.subject)) {
            throw "Scenario $scenario contains an invalid Finding oracle"
        }
    }
    $documents = @(
        $fixtureManifest.documents | Where-Object scenario -EQ $scenario
    )
    $languages = @($documents.language | Sort-Object -Unique)
    if ($documents.Count -ne 4 -or
        ($languages -join ",") -ne ($requiredLanguages -join ",")) {
        throw "Scenario $scenario must have exactly four language cells"
    }
}
foreach ($document in $fixtureManifest.documents) {
    $documentPath = Join-Path $fixtureRoot $document.path
    $documentHash = (Get-FileHash -LiteralPath $documentPath `
        -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($documentHash -ne $document.sha256) {
        throw "Frozen document fixture identity mismatch: $($document.path)"
    }
}

$manifestPath = Join-Path $fixtureRoot "benchmark-manifest.json"
$manifest = Get-Content -LiteralPath $manifestPath `
    -Raw -Encoding UTF8 | ConvertFrom-Json
$benchmarkManifestHash = (
    Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256
).Hash.ToLowerInvariant()
$manifestFields = @($manifest.PSObject.Properties.Name | Sort-Object)
$expectedManifestFields = @(
    "available_scale",
    "candidate_gates",
    "corpus_200k",
    "grammars",
    "parser_admission",
    "release_evidence",
    "runner",
    "schema_version",
    "targets",
    "targets_root"
)
if ($manifest.schema_version -ne 1 -or
    ($manifestFields -join ",") -ne ($expectedManifestFields -join ",")) {
    throw "Unsupported benchmark manifest schema"
}
$runnerScriptPath = Join-Path $fixtureRoot $manifest.runner.script.path
$runnerScriptHash = (
    Get-FileHash -LiteralPath $runnerScriptPath -Algorithm SHA256
).Hash.ToLowerInvariant()
$verifierScriptPath = Join-Path $fixtureRoot $manifest.runner.verifier.path
$verifierScriptHash = (
    Get-FileHash -LiteralPath $verifierScriptPath -Algorithm SHA256
).Hash.ToLowerInvariant()
if ($runnerScriptHash -ne $manifest.runner.script.sha256 -or
    $verifierScriptHash -ne $manifest.runner.verifier.sha256) {
    throw "Frozen measurement script identity mismatch"
}
$runnerEnvironment = $null
$verifiedReleaseEvidence = $null
$cargoLockPath = Join-Path $repositoryRoot "Cargo.lock"
$cargoLockHash = (
    Get-FileHash -LiteralPath $cargoLockPath -Algorithm SHA256
).Hash.ToLowerInvariant()
if ($cargoLockHash -ne $manifest.grammars.cargo_lock_sha256) {
    throw "Frozen Cargo.lock identity mismatch"
}
$packageMetadata = (& cargo metadata --manifest-path (
        Join-Path $repositoryRoot "Cargo.toml"
    ) --locked --no-deps --format-version 1 | Out-String) | ConvertFrom-Json
$package = @($packageMetadata.packages | Where-Object {
        $_.name -ceq "code-style-unifier"
    })
if ($LASTEXITCODE -ne 0 -or $package.Count -ne 1 -or
    [string]$package[0].version -cne "3.0.1") {
    throw "Package metadata and lockfile must identify version 3.0.1"
}
$releaseWorkflowPath = Join-Path $repositoryRoot ".github/workflows/release.yml"
$releaseWorkflowText = [IO.File]::ReadAllText($releaseWorkflowPath)
$releaseWorkflowHash = (
    Get-FileHash -LiteralPath $releaseWorkflowPath -Algorithm SHA256
).Hash.ToLowerInvariant()
$workflowTargets = @(
    [regex]::Matches(
        $releaseWorkflowText,
        "(?m)^\s+target:\s+([a-z0-9_-]+)\s*$"
    ) | ForEach-Object { $_.Groups[1].Value } | Sort-Object
)
$expectedWorkflowTargets = @(
    "linux-aarch64", "linux-x86_64", "macos-aarch64", "macos-x86_64",
    "windows-x86_64"
)
$assetContracts = @(
    "csu-`$version-windows-x86_64.zip",
    "csu-`$version-linux-x86_64.tar.gz",
    "csu-`$version-linux-aarch64.tar.gz",
    "csu-`$version-macos-x86_64.tar.gz",
    "csu-`$version-macos-aarch64.tar.gz"
)
if (($workflowTargets -join ",") -cne
        ($expectedWorkflowTargets -join ",") -or
    -not $releaseWorkflowText.Contains(
        '$env:GITHUB_REF_NAME -ne "v$version"',
        [StringComparison]::Ordinal
    ) -or @($assetContracts | Where-Object {
        -not $releaseWorkflowText.Contains($_, [StringComparison]::Ordinal)
    }).Count -ne 0) {
    throw "Five-target packaging workflow contract mismatch"
}
$parserAdmissionManifest = $manifest.parser_admission
Assert-ExactFields -Value $parserAdmissionManifest `
    -Owner "Parser-admission manifest" -Fields @(
        "algorithm_revision", "candidates", "script", "authority", "receipt",
        "repeated_runs"
    )
Assert-ExactFields -Value $parserAdmissionManifest.candidates `
    -Owner "Parser-admission candidate scale" -Fields @(
        "files", "physical_lines", "bytes"
    )
Assert-ExactFields -Value $parserAdmissionManifest.script `
    -Owner "Parser-admission script identity" -Fields @("path", "sha256")
Assert-ExactFields -Value $parserAdmissionManifest.authority `
    -Owner "Parser-admission Authority identity" -Fields @(
        "path", "schema_version", "header_facts", "sha256"
    )
Assert-ExactFields -Value $parserAdmissionManifest.receipt `
    -Owner "Parser-admission receipt identity" -Fields @(
        "path", "schema_version", "exclusions", "sha256"
    )
if ($parserAdmissionManifest.algorithm_revision -cne
        "single-capture-standard-law-extensions-and-exact-header-facts-v3" -or
    $parserAdmissionManifest.repeated_runs -ne 2 -or
    $parserAdmissionManifest.candidates.files -ne 2467 -or
    $parserAdmissionManifest.candidates.physical_lines -ne 846337 -or
    $parserAdmissionManifest.candidates.bytes -ne 28930034 -or
    $parserAdmissionManifest.authority.schema_version -ne 4 -or
    $parserAdmissionManifest.authority.header_facts -ne 315 -or
    $parserAdmissionManifest.receipt.schema_version -ne 1 -or
    $parserAdmissionManifest.receipt.exclusions -lt 371 -or
    $parserAdmissionManifest.authority.path -ceq
        $manifest.corpus_200k.authority.path) {
    throw "Parser-admission manifest contract mismatch"
}
$parserAdmissionScriptPath = Join-Path $fixtureRoot (
    $parserAdmissionManifest.script.path
)
$parserAdmissionAuthorityPath = Join-Path $fixtureRoot (
    "$($parserAdmissionManifest.authority.path)/authority.json"
)
$parserAdmissionReceiptPath = Join-Path $fixtureRoot (
    $parserAdmissionManifest.receipt.path
)
if ((Get-FileHash -LiteralPath $parserAdmissionScriptPath `
        -Algorithm SHA256).Hash.ToLowerInvariant() -cne
        $parserAdmissionManifest.script.sha256 -or
    (Get-FileHash -LiteralPath $parserAdmissionAuthorityPath `
        -Algorithm SHA256).Hash.ToLowerInvariant() -cne
        $parserAdmissionManifest.authority.sha256 -or
    (Get-FileHash -LiteralPath $parserAdmissionReceiptPath `
        -Algorithm SHA256).Hash.ToLowerInvariant() -cne
        $parserAdmissionManifest.receipt.sha256) {
    throw "Parser-admission artifact identity mismatch"
}
$parserAdmissionAuthority = Get-Content `
    -LiteralPath $parserAdmissionAuthorityPath -Raw -Encoding UTF8 |
    ConvertFrom-Json
Assert-ExactFields -Value $parserAdmissionAuthority `
    -Owner "Parser-admission Authority" -Fields @(
        "schema_version", "public_callables", "token_vocabulary",
        "quantity_concepts", "header_languages",
        "external_fixed_identifiers", "dependency_authority"
    )
$parserHeaderFacts = @(
    $parserAdmissionAuthority.header_languages.PSObject.Properties
)
$parserHeaderOwners = [Collections.Generic.Dictionary[string, string]]::new(
    [StringComparer]::Ordinal
)
foreach ($fact in $parserHeaderFacts) {
    if ($fact.Name -notmatch "^(c|cpp)/(.+[.]h)$" -or
        $fact.Value -cne $Matches[1] -or
        -not $parserHeaderOwners.TryAdd($Matches[2], [string]$fact.Value)) {
        throw "Parser-admission Authority contains an invalid header fact"
    }
}
if ($parserAdmissionAuthority.schema_version -ne 4 -or
    $parserHeaderFacts.Count -ne 315 -or
    @($parserHeaderFacts | Where-Object Value -CEQ "c").Count -ne 289 -or
    @($parserHeaderFacts | Where-Object Value -CEQ "cpp").Count -ne 26 -or
    @($parserAdmissionAuthority.public_callables.PSObject.Properties).Count -ne 0 -or
    @($parserAdmissionAuthority.token_vocabulary).Count -ne 0 -or
    @($parserAdmissionAuthority.quantity_concepts.PSObject.Properties).Count -ne 0 -or
    @($parserAdmissionAuthority.external_fixed_identifiers).Count -ne 0 -or
    $null -ne $parserAdmissionAuthority.dependency_authority) {
    throw "Parser-admission Authority is not the exact dedicated header law"
}
$parserAdmissionReceipt = Get-Content `
    -LiteralPath $parserAdmissionReceiptPath -Raw -Encoding UTF8 |
    ConvertFrom-Json
Assert-ExactFields -Value $parserAdmissionReceipt `
    -Owner "Parser-admission receipt" -Fields @(
        "schema_version", "status", "algorithm_revision", "inputs",
        "corpus_identity", "profiles", "exclusions", "repeated_runs",
        "deterministic_inventory_sha256"
    )
Assert-ExactFields -Value $parserAdmissionReceipt.inputs `
    -Owner "Parser-admission receipt inputs" -Fields @(
        "targets_identity_sha256", "targets", "grammars",
        "executable_sha256", "authority_sha256",
        "authority_schema_version", "ambiguous_header_facts",
        "fixed_extensions", "evidence_script_sha256"
    )
Assert-ExactFields -Value $parserAdmissionReceipt.inputs.grammars `
    -Owner "Parser-admission grammar identities" -Fields @(
        "cargo_lock_sha256", "python", "rust", "c", "cpp"
    )
Assert-ExactFields -Value $parserAdmissionReceipt.profiles `
    -Owner "Parser-admission profiles" -Fields @(
        "c", "cpp", "python", "rust"
    )
Assert-ExactFields -Value $parserAdmissionReceipt.inputs.fixed_extensions `
    -Owner "Parser-admission fixed extensions" -Fields @(
        ".py", ".rs", ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp",
        ".hh", ".hxx"
    )
if ($parserAdmissionReceipt.schema_version -ne 1 -or
    $parserAdmissionReceipt.status -cne
        "transparent_admission_evidence_no_release_threshold" -or
    $parserAdmissionReceipt.algorithm_revision -cne
        $parserAdmissionManifest.algorithm_revision -or
    $parserAdmissionReceipt.corpus_identity -cne
        "separate_from_corpus_200k" -or
    $parserAdmissionReceipt.inputs.grammars.cargo_lock_sha256 -cne
        $cargoLockHash -or
    $parserAdmissionReceipt.inputs.grammars.python -cne
        "tree-sitter-python@0.25.0+direct-source-facts" -or
    $parserAdmissionReceipt.inputs.grammars.rust -cne
        "tree-sitter-rust@0.24.2+direct-source-facts" -or
    $parserAdmissionReceipt.inputs.grammars.c -cne
        "tree-sitter-c@0.24.2+direct-source-facts" -or
    $parserAdmissionReceipt.inputs.grammars.cpp -cne
        "tree-sitter-cpp@8b5b49eb+direct-source-facts" -or
    $parserAdmissionReceipt.inputs.executable_sha256 -notmatch
        "^[0-9a-f]{64}$" -or
    $parserAdmissionReceipt.inputs.authority_sha256 -cne
        $parserAdmissionManifest.authority.sha256 -or
    $parserAdmissionReceipt.inputs.authority_schema_version -ne 4 -or
    $parserAdmissionReceipt.inputs.ambiguous_header_facts -ne 315 -or
    $parserAdmissionReceipt.inputs.fixed_extensions.".py" -cne "python" -or
    $parserAdmissionReceipt.inputs.fixed_extensions.".rs" -cne "rust" -or
    $parserAdmissionReceipt.inputs.fixed_extensions.".c" -cne "c" -or
    $parserAdmissionReceipt.inputs.fixed_extensions.".h" -cne "authority" -or
    @(".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx" | Where-Object {
        $parserAdmissionReceipt.inputs.fixed_extensions.$_ -cne "cpp"
    }).Count -ne 0) {
    throw "Parser-admission receipt input contract mismatch"
}
if ($parserAdmissionReceipt.inputs.evidence_script_sha256 -cne
    $parserAdmissionManifest.script.sha256) {
    throw "Parser-admission receipt used a different evidence script"
}
$parserAdmissionExecutablePath = Join-Path $repositoryRoot "target/release/csu.exe"
if (-not (Test-Path -LiteralPath $parserAdmissionExecutablePath -PathType Leaf) -or
    (Get-FileHash -LiteralPath $parserAdmissionExecutablePath `
        -Algorithm SHA256).Hash.ToLowerInvariant() -cne
        $parserAdmissionReceipt.inputs.executable_sha256) {
    throw "Parser-admission receipt does not bind the current release executable"
}
$performanceAuthorityPath = Join-Path $fixtureRoot (
    "$($manifest.corpus_200k.authority.path)/authority.json"
)
$performanceAuthorityHash = (
    Get-FileHash -LiteralPath $performanceAuthorityPath -Algorithm SHA256
).Hash.ToLowerInvariant()
if ($performanceAuthorityHash -ne $manifest.corpus_200k.authority.sha256) {
    throw "Frozen Performance Authority identity mismatch"
}
$performanceAuthority = Get-Content -LiteralPath $performanceAuthorityPath `
    -Raw -Encoding UTF8 | ConvertFrom-Json
if ($performanceAuthority.schema_version -ne 4 -or
    @($performanceAuthority.public_callables.PSObject.Properties).Count -ne 0 -or
    @($performanceAuthority.token_vocabulary).Count -ne 0 -or
    @($performanceAuthority.quantity_concepts.PSObject.Properties).Count -ne 0 -or
    @($performanceAuthority.external_fixed_identifiers).Count -ne 0 -or
    $null -ne $performanceAuthority.dependency_authority) {
    throw "Performance Authority contains facts outside corpus admission"
}
$targetsRoot = [IO.Path]::GetFullPath(
    (Join-Path $fixtureRoot $manifest.targets_root)
)
$allRecords = [Collections.Generic.List[object]]::new()
$allParserRecords = [Collections.Generic.List[object]]::new()
$parserRecordsByTarget = [Collections.Generic.Dictionary[string, object]]::new(
    [StringComparer]::Ordinal
)
$targetDirectories = [Collections.Generic.HashSet[string]]::new(
    [StringComparer]::Ordinal
)

foreach ($target in $manifest.targets) {
    if (-not $targetDirectories.Add([string]$target.directory) -or
        $target.revision -notmatch "^[0-9a-f]{40}$" -or
        -not ([string]$target.directory).EndsWith(
            $target.revision.Substring(0, 8),
            [StringComparison]::Ordinal
        ) -or [string]::IsNullOrWhiteSpace([string]$target.source_ref)) {
        throw "Frozen target provenance is incomplete or duplicated"
    }
    $records = @(Get-TargetRecords -TargetsRoot $targetsRoot -Target $target)
    $actualLines = ($records | Measure-Object PhysicalLines -Sum).Sum
    $actualBytes = ($records | Measure-Object Bytes -Sum).Sum
    $actualDigest = Get-RecordDigest -Records $records
    if ($records.Count -ne $target.accepted_files -or
        $actualLines -ne $target.physical_lines -or
        $actualBytes -ne $target.bytes -or
        $actualDigest -ne $target.digest) {
        throw "Frozen target identity mismatch: $($target.directory)"
    }
    foreach ($record in $records) {
        $allRecords.Add($record)
    }
    $parserRecords = @(Get-ParserAdmissionRecords -TargetsRoot $targetsRoot `
        -Target $target -HeaderOwners $parserHeaderOwners)
    $parserRecordsByTarget.Add([string]$target.directory, $parserRecords)
    foreach ($record in $parserRecords) {
        $allParserRecords.Add($record)
    }
}
$availableLines = ($allRecords | Measure-Object PhysicalLines -Sum).Sum
$availableBytes = ($allRecords | Measure-Object Bytes -Sum).Sum
if ($allRecords.Count -ne $manifest.available_scale.accepted_files -or
    $availableLines -ne $manifest.available_scale.physical_lines -or
    $availableBytes -ne $manifest.available_scale.bytes) {
    throw "Frozen available-source scale mismatch"
}
foreach ($language in @("c", "cpp", "python", "rust")) {
    $languageRecords = @($allRecords | Where-Object Language -EQ $language)
    $expectedScale = $manifest.available_scale.languages.$language
    if ($languageRecords.Count -ne $expectedScale.files -or
        ($languageRecords | Measure-Object PhysicalLines -Sum).Sum -ne
            $expectedScale.physical_lines -or
        ($languageRecords | Measure-Object Bytes -Sum).Sum -ne
            $expectedScale.bytes) {
        throw "Frozen available-source scale mismatch: $language"
    }
}

$exclusionsPath = Join-Path $fixtureRoot (
    $manifest.corpus_200k.parseability_exclusions.path
)
$exclusionsHash = (
    Get-FileHash -LiteralPath $exclusionsPath -Algorithm SHA256
).Hash.ToLowerInvariant()
if ($exclusionsHash -ne
    $manifest.corpus_200k.parseability_exclusions.sha256) {
    throw "Frozen parseability exclusion identity mismatch"
}
$exclusions = Get-Content -LiteralPath $exclusionsPath `
    -Raw -Encoding UTF8 | ConvertFrom-Json
if ($exclusions.schema_version -ne
        $manifest.corpus_200k.parseability_exclusions.schema_version -or
    @($exclusions.entries).Count -ne
        $manifest.corpus_200k.parseability_exclusions.entries) {
    throw "Frozen parseability exclusion shape mismatch"
}
$recordsByWorkspacePath = [Collections.Generic.Dictionary[string, object]]::new(
    [StringComparer]::Ordinal
)
foreach ($record in $allRecords) {
    $workspacePath = "$($record.Language)/$($record.Key)"
    $recordsByWorkspacePath.Add($workspacePath, $record)
}
$excludedPaths = [Collections.Generic.HashSet[string]]::new(
    [StringComparer]::Ordinal
)
foreach ($entry in $exclusions.entries) {
    $workspacePath = [string]$entry.path
    if (-not $excludedPaths.Add($workspacePath) -or
        -not $recordsByWorkspacePath.ContainsKey($workspacePath)) {
        throw "Unknown or duplicate parseability exclusion: $workspacePath"
    }
    $record = $recordsByWorkspacePath[$workspacePath]
    if ($entry.language -ne $record.Language -or
        $entry.sha256 -ne $record.Sha256 -or
        [string]::IsNullOrWhiteSpace($entry.reason)) {
        throw "Invalid parseability exclusion evidence: $workspacePath"
    }
}
$parserTargetRows = @($parserAdmissionReceipt.inputs.targets)
if ($parserTargetRows.Count -ne @($manifest.targets).Count -or
    (Get-JsonSha256 -Value $parserTargetRows) -cne
        $parserAdmissionReceipt.inputs.targets_identity_sha256) {
    throw "Parser-admission target identity mismatch"
}
for ($targetIndex = 0; $targetIndex -lt $parserTargetRows.Count;
    $targetIndex += 1) {
    $actual = $parserTargetRows[$targetIndex]
    $expected = $manifest.targets[$targetIndex]
    $candidateRows = @($parserRecordsByTarget[[string]$expected.directory])
    $candidateLines = ($candidateRows | Measure-Object PhysicalLines -Sum).Sum
    $candidateBytes = ($candidateRows | Measure-Object Bytes -Sum).Sum
    $candidateDigest = Get-RecordDigest -Records $candidateRows
    Assert-ExactFields -Value $actual -Owner "Parser-admission target" `
        -Fields @(
            "directory", "revision", "recorded_files",
            "recorded_physical_lines", "recorded_bytes", "recorded_digest",
            "candidate_files", "candidate_physical_lines", "candidate_bytes",
            "candidate_digest"
        )
    if ($actual.directory -cne $expected.directory -or
        $actual.revision -cne $expected.revision -or
        $actual.recorded_files -ne $expected.accepted_files -or
        $actual.recorded_physical_lines -ne $expected.physical_lines -or
        $actual.recorded_bytes -ne $expected.bytes -or
        $actual.recorded_digest -cne $expected.digest -or
        $actual.candidate_files -ne $candidateRows.Count -or
        $actual.candidate_physical_lines -ne $candidateLines -or
        $actual.candidate_bytes -ne $candidateBytes -or
        $actual.candidate_digest -cne $candidateDigest) {
        throw "Parser-admission target receipt drift: $($expected.directory)"
    }
}
$parserRecords = @($allParserRecords)
$parserRecordComparison = [Collections.Generic.Comparer[object]]::Create({
    param($left, $right)
    return [StringComparer]::Ordinal.Compare(
        "$($left.Language)/$($left.Key)",
        "$($right.Language)/$($right.Key)"
    )
})
[Array]::Sort($parserRecords, $parserRecordComparison)
$parserLines = ($parserRecords | Measure-Object PhysicalLines -Sum).Sum
$parserBytes = ($parserRecords | Measure-Object Bytes -Sum).Sum
if ($parserRecords.Count -ne $parserAdmissionManifest.candidates.files -or
    $parserLines -ne $parserAdmissionManifest.candidates.physical_lines -or
    $parserBytes -ne $parserAdmissionManifest.candidates.bytes) {
    throw "Parser-admission complete candidate scale drift"
}
$allHeaders = @($parserRecords | Where-Object {
    [IO.Path]::GetExtension($_.Path) -ceq ".h"
})
if ($allHeaders.Count -ne $parserHeaderFacts.Count) {
    throw "Parser-admission header cardinality drift"
}
foreach ($header in $allHeaders) {
    $path = "$($header.Language)/$($header.Key)"
    $fact = $parserAdmissionAuthority.header_languages.PSObject.Properties[$path]
    if ($null -eq $fact -or $fact.Value -cne $header.Language) {
        throw "Parser-admission header fact mismatch: $path"
    }
}
$parserRecordsByPath = [Collections.Generic.Dictionary[string, object]]::new(
    [StringComparer]::Ordinal
)
foreach ($record in $parserRecords) {
    $parserRecordsByPath.Add("$($record.Language)/$($record.Key)", $record)
}
$newExclusions = @($parserAdmissionReceipt.exclusions)
$newExclusionPaths = [Collections.Generic.HashSet[string]]::new(
    [StringComparer]::Ordinal
)
$newExclusionsByPath = [Collections.Generic.Dictionary[string, object]]::new(
    [StringComparer]::Ordinal
)
if ($newExclusions.Count -ne $parserAdmissionManifest.receipt.exclusions) {
    throw "Parser-admission exclusion count mismatch"
}
foreach ($entry in $newExclusions) {
    Assert-ExactFields -Value $entry -Owner "Parser-admission exclusion" `
        -Fields @(
            "path", "profile", "physical_lines", "sha256", "reason",
            "reason_sha256", "classification"
    )
    $path = [string]$entry.path
    if (-not $newExclusionPaths.Add($path) -or
        -not $parserRecordsByPath.ContainsKey($path)) {
        throw "Unknown or duplicate parser-admission exclusion: $path"
    }
    $record = $parserRecordsByPath[$path]
    if ($entry.profile -cne $record.Language -or
        $entry.physical_lines -ne $record.PhysicalLines -or
        $entry.sha256 -cne $record.Sha256 -or
        [string]::IsNullOrWhiteSpace([string]$entry.reason) -or
        $entry.reason_sha256 -cne (Get-Sha256Text -Text $entry.reason) -or
        $entry.classification -cne
            "excluded_not_reviewed_not_complete_not_clean") {
        throw "Parser-admission exclusion evidence drift: $path"
    }
    $newExclusionsByPath.Add($path, $entry)
}
foreach ($old in $exclusions.entries) {
    $path = [string]$old.path
    if (-not $newExclusionsByPath.ContainsKey($path)) {
        throw "Historical performance exclusion disappeared: $path"
    }
    $current = $newExclusionsByPath[$path]
    if ($current.profile -cne $old.language -or
        $current.sha256 -cne $old.sha256) {
        throw "Historical performance exclusion source identity drift: $path"
    }
}
$profileFields = @(
    "candidate_files", "candidate_physical_lines", "admitted_files",
    "admitted_physical_lines", "excluded_files",
    "excluded_physical_lines", "admission_ratio"
)
$recomputedProfiles = [ordered]@{}
foreach ($profile in @("c", "cpp", "python", "rust")) {
    $profileReceipt = $parserAdmissionReceipt.profiles.$profile
    Assert-ExactFields -Value $profileReceipt `
        -Owner "Parser-admission profile $profile" -Fields $profileFields
    $candidateRows = @($parserRecords | Where-Object Language -CEQ $profile)
    $excludedRows = @($newExclusions | Where-Object profile -CEQ $profile)
    [long]$candidateLines = 0
    [long]$excludedLines = 0
    foreach ($row in $candidateRows) {
        $candidateLines += $row.PhysicalLines
    }
    foreach ($row in $excludedRows) {
        $excludedLines += $row.physical_lines
    }
    $admittedFiles = $candidateRows.Count - $excludedRows.Count
    $admittedLines = $candidateLines - $excludedLines
    $ratio = [Math]::Round($admittedFiles / $candidateRows.Count, 12)
    $recomputedProfiles[$profile] = [pscustomobject][ordered]@{
        candidate_files = $candidateRows.Count
        candidate_physical_lines = [long]$candidateLines
        admitted_files = $admittedFiles
        admitted_physical_lines = [long]$admittedLines
        excluded_files = $excludedRows.Count
        excluded_physical_lines = [long]$excludedLines
        admission_ratio = $ratio
    }
    if ($profileReceipt.candidate_files -ne $candidateRows.Count -or
        $profileReceipt.candidate_physical_lines -ne $candidateLines -or
        $profileReceipt.admitted_files -ne $admittedFiles -or
        $profileReceipt.admitted_physical_lines -ne $admittedLines -or
        $profileReceipt.excluded_files -ne $excludedRows.Count -or
        $profileReceipt.excluded_physical_lines -ne $excludedLines -or
        $profileReceipt.admission_ratio -ne $ratio) {
        throw "Parser-admission profile account mismatch: $profile"
    }
}
$inventoryRows = [Collections.Generic.List[object]]::new()
foreach ($record in $parserRecords) {
    $path = "$($record.Language)/$($record.Key)"
    $exclusion = if ($newExclusionsByPath.ContainsKey($path)) {
        $newExclusionsByPath[$path]
    } else {
        $null
    }
    $inventoryRows.Add([pscustomobject][ordered]@{
        path = $path
        profile = $record.Language
        physical_lines = $record.PhysicalLines
        sha256 = $record.Sha256
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
$recomputedInventory = Get-Sha256Text -Text (
    ConvertTo-Json -InputObject @($inventoryRows) -Depth 5 -Compress
)
$recomputedCounts = Get-Sha256Text -Text (
    ConvertTo-Json -InputObject $recomputedProfiles -Depth 5 -Compress
)
if ($parserAdmissionReceipt.deterministic_inventory_sha256 -cne
    $recomputedInventory) {
    throw "Parser-admission canonical inventory identity drift"
}
$admissionRuns = @($parserAdmissionReceipt.repeated_runs)
if ($admissionRuns.Count -ne $parserAdmissionManifest.repeated_runs) {
    throw "Parser-admission repetition count mismatch"
}
$projectionIdentity = $null
$countsIdentity = $null
foreach ($run in $admissionRuns) {
    Assert-ExactFields -Value $run -Owner "Parser-admission run" -Fields @(
        "exit_code", "projection_sha256", "inventory_sha256",
        "counts_sha256"
    )
    if ($run.exit_code -ne 2 -or
        $run.projection_sha256 -notmatch "^[0-9a-f]{64}$" -or
        $run.inventory_sha256 -cne $recomputedInventory -or
        $run.counts_sha256 -cne $recomputedCounts) {
        throw "Parser-admission run identity mismatch"
    }
    if ($null -eq $projectionIdentity) {
        $projectionIdentity = $run.projection_sha256
        $countsIdentity = $run.counts_sha256
    } elseif ($run.projection_sha256 -cne $projectionIdentity -or
        $run.counts_sha256 -cne $countsIdentity) {
        throw "Repeated parser-admission runs are not deterministic"
    }
}
$admittedRecords = @(
    $allRecords | Where-Object {
        -not $excludedPaths.Contains("$($_.Language)/$($_.Key)")
    }
)

$selectedRecords = [Collections.Generic.List[object]]::new()
$languageDigests = [ordered]@{}
foreach ($language in @("c", "cpp", "python", "rust")) {
    $expected = $manifest.corpus_200k.languages.$language
    $quota = [int]$manifest.corpus_200k.language_quotas.$language
    $records = @(Select-ExactLanguageCorpus -Records $admittedRecords `
        -Language $language `
        -PhysicalLines $quota)
    $actualLines = ($records | Measure-Object PhysicalLines -Sum).Sum
    $actualBytes = ($records | Measure-Object Bytes -Sum).Sum
    $actualDigest = Get-RecordDigest -Records $records
    if ($records.Count -ne $expected.files -or
        $actualLines -ne $expected.physical_lines -or
        $actualBytes -ne $expected.bytes -or
        $actualDigest -ne $expected.digest) {
        throw "Frozen 200k corpus identity mismatch: $language"
    }
    $languageDigests[$language] = $actualDigest
    foreach ($record in $records) {
        $selectedRecords.Add($record)
    }
}
$selectedLines = ($selectedRecords | Measure-Object PhysicalLines -Sum).Sum
$selectedBytes = ($selectedRecords | Measure-Object Bytes -Sum).Sum
if ($selectedRecords.Count -ne $manifest.corpus_200k.files -or
    $selectedLines -ne $manifest.corpus_200k.physical_lines -or
    $selectedBytes -ne $manifest.corpus_200k.bytes) {
    throw "Frozen 200k corpus aggregate scale mismatch"
}

$aggregateBuilder = [Text.StringBuilder]::new()
foreach ($language in @("c", "cpp", "python", "rust")) {
    [void]$aggregateBuilder.Append($language)
    [void]$aggregateBuilder.Append("`t")
    [void]$aggregateBuilder.Append($languageDigests[$language])
    [void]$aggregateBuilder.Append("`n")
}
$aggregateDigest = Get-Sha256Text -Text $aggregateBuilder.ToString()
if ($aggregateDigest -ne $manifest.corpus_200k.digest) {
    throw "Frozen 200k aggregate digest mismatch"
}

$inventoryEntries = [Collections.Generic.List[object]]::new()
foreach ($record in $selectedRecords) {
    $inventoryEntries.Add([pscustomobject][ordered]@{
        path = "$($record.Language)/$($record.Target)/$($record.Path)"
        language = $record.Language
    })
}
$inventoryArray = @($inventoryEntries)
$inventoryComparison = [Collections.Generic.Comparer[object]]::Create({
    param($left, $right)
    return [StringComparer]::Ordinal.Compare($left.path, $right.path)
})
[Array]::Sort($inventoryArray, $inventoryComparison)
$inventory = [pscustomobject][ordered]@{
    schema_version = 1
    entries = $inventoryArray
}
$inventoryJson = ($inventory | ConvertTo-Json -Depth 4 -Compress) + "`n"
$inventoryBytes = [Text.Encoding]::UTF8.GetByteCount($inventoryJson)
$inventoryHash = Get-Sha256Text -Text $inventoryJson
if ($inventoryArray.Count -ne $manifest.corpus_200k.inventory.entries -or
    $inventoryBytes -ne $manifest.corpus_200k.inventory.bytes -or
    $inventoryHash -ne $manifest.corpus_200k.inventory.sha256) {
    throw "Frozen corpus selection identity mismatch"
}
$selectedHeaders = @($inventoryArray | Where-Object path -Like "*.h")
$authorityHeaders = @($performanceAuthority.header_languages.PSObject.Properties)
if ($selectedHeaders.Count -ne 104 -or $authorityHeaders.Count -ne 104 -or
    @($selectedHeaders | Where-Object language -EQ "c").Count -ne 98 -or
    @($selectedHeaders | Where-Object language -EQ "cpp").Count -ne 6) {
    throw "Frozen corpus header facts have the wrong cardinality"
}
foreach ($header in $selectedHeaders) {
    $fact = $performanceAuthority.header_languages.PSObject.Properties[$header.path]
    if ($null -eq $fact -or $fact.Value -ne $header.language) {
        throw "Performance Authority header fact mismatch: $($header.path)"
    }
}

$productPhysicalLines = Get-RustPhysicalLineCount -Path (
    Join-Path $repositoryRoot "src"
)
$testPhysicalLines = Get-RustPhysicalLineCount -Path (
    Join-Path $repositoryRoot "tests"
)
$standardsPath = Join-Path $repositoryRoot "docs/coding_standards.md"
$standardsLines = Get-PhysicalLineCount -Bytes (
    [IO.File]::ReadAllBytes($standardsPath)
)
$standardsHash = (
    Get-FileHash -LiteralPath $standardsPath -Algorithm SHA256
).Hash.ToLowerInvariant()
$agentSkillPath = Join-Path $repositoryRoot ".agents/skills/csu-review/SKILL.md"
$claudeSkillPath = Join-Path $repositoryRoot ".claude/skills/csu-review/SKILL.md"
$agentSkillBytes = [IO.File]::ReadAllBytes($agentSkillPath)
$claudeSkillBytes = [IO.File]::ReadAllBytes($claudeSkillPath)
$agentSkillHash = (
    Get-FileHash -LiteralPath $agentSkillPath -Algorithm SHA256
).Hash.ToLowerInvariant()
$claudeSkillHash = (
    Get-FileHash -LiteralPath $claudeSkillPath -Algorithm SHA256
).Hash.ToLowerInvariant()
$skillFolderHash = Get-SkillFolderHash -Path (Split-Path -Parent $agentSkillPath)
$sharedSkillHash = Get-SkillFolderHash `
    -Path (Split-Path -Parent $agentSkillPath) -SharedOnly
$sharedClaudeHash = Get-SkillFolderHash `
    -Path (Split-Path -Parent $claudeSkillPath) -SharedOnly
$skillsLockPath = Join-Path $repositoryRoot "skills-lock.json"
$skillsLockHash = (
    Get-FileHash -LiteralPath $skillsLockPath -Algorithm SHA256
).Hash.ToLowerInvariant()
$skillsLock = Get-Content -LiteralPath $skillsLockPath -Raw -Encoding UTF8 |
    ConvertFrom-Json
if ($productPhysicalLines -gt
        $manifest.candidate_gates.product_rust_max_physical_lines -or
    $testPhysicalLines -gt
        $manifest.candidate_gates.test_rust_max_physical_lines -or
    $standardsLines -lt
        $manifest.candidate_gates.normative_standard_min_physical_lines -or
    $standardsLines -gt
        $manifest.candidate_gates.normative_standard_max_physical_lines -or
    $fixtureManifest.semantic_authority_digest -notmatch "^[0-9a-f]{64}$" -or
    $sharedSkillHash -ne $sharedClaudeHash -or
    $agentSkillHash -ne $claudeSkillHash -or
    -not [Linq.Enumerable]::SequenceEqual(
        [byte[]]$agentSkillBytes,
        [byte[]]$claudeSkillBytes
    ) -or
    $skillsLock.skills."csu-review".computedHash -ne $skillFolderHash) {
    throw "Current candidate LOC, Law, or skill projection gate failed"
}
$cargoManifestPath = Join-Path $repositoryRoot "Cargo.toml"

if (-not $corpusMode) {
$canonicalReleasePath = Join-Path $fixtureRoot $manifest.release_evidence.path
$releaseEvidencePath = if ([string]::IsNullOrWhiteSpace($ReleaseEvidencePath)) {
    [IO.Path]::GetFullPath($canonicalReleasePath)
} else {
    [IO.Path]::GetFullPath($ReleaseEvidencePath)
}
$releaseEvidenceBytes = [IO.File]::ReadAllBytes($releaseEvidencePath)
$releaseEvidenceHash = Get-Sha256Bytes -Bytes $releaseEvidenceBytes
$isStaging = $releaseEvidencePath -ne [IO.Path]::GetFullPath(
    $canonicalReleasePath
)
if ($releaseMode -and -not $isStaging) {
    throw "Release-only verification requires a non-canonical staging receipt"
}
if ($isStaging -and -not [string]::IsNullOrWhiteSpace(
        $ExpectedStagingSha256
    ) -and $releaseEvidenceHash -ne $ExpectedStagingSha256) {
    throw "Staging release evidence identity mismatch"
}
$utf8 = [Text.UTF8Encoding]::new($false, $true)
$releaseEvidence = $utf8.GetString($releaseEvidenceBytes) |
    ConvertFrom-Json -DateKind String
Assert-ExactFields -Value $releaseEvidence -Owner "Release evidence" -Fields @(
    "schema_version", "recorded_at_utc", "executable_sha256",
    "cargo_lock_sha256", "runner_identity", "runner_script_sha256",
    "verifier_script_sha256", "runner_environment", "authority_sha256",
    "workspace", "corpus_files", "corpus_physical_lines", "corpus_digest",
    "inventory_sha256", "benchmark_manifest_sha256",
    "measured_candidate_sha256", "premeasurement_full_patch_sha256",
    "runs", "warmup_runs", "p95_method",
    "p95_elapsed_ms", "p95_optimization_target_met",
    "maximum_peak_working_set_bytes", "deterministic_projection",
    "diagnostic_incomplete", "projection_digests", "semantic_summary_digests",
    "review_summary", "measurements", "status"
)
$canonicalReleaseHashBeforePromotion = if ($isStaging -and
    (Test-Path -LiteralPath $canonicalReleasePath -PathType Leaf)) {
    (Get-FileHash -LiteralPath $canonicalReleasePath `
        -Algorithm SHA256).Hash.ToLowerInvariant()
} else {
    $null
}
$runnerEnvironment = Get-RunnerEnvironment -WorkspacePath $releaseEvidence.workspace
$measurements = @($releaseEvidence.measurements)
$expectedStatus = if ($isStaging) {
    "unverified_measurement_staging"
} else {
    $manifest.release_evidence.expected_status
}
if ($releaseEvidence.schema_version -ne
        $manifest.release_evidence.schema_version -or
    $releaseEvidence.authority_sha256 -ne $performanceAuthorityHash -or
    $releaseEvidence.corpus_files -ne $selectedRecords.Count -or
    $releaseEvidence.corpus_physical_lines -ne
        $manifest.corpus_200k.physical_lines -or
    $releaseEvidence.corpus_digest -ne $aggregateDigest -or
    $releaseEvidence.inventory_sha256 -ne $inventoryHash -or
    $releaseEvidence.cargo_lock_sha256 -ne $cargoLockHash -or
    $releaseEvidence.runner_identity -ne $manifest.runner.identity -or
    $releaseEvidence.runner_script_sha256 -ne $runnerScriptHash -or
    $releaseEvidence.verifier_script_sha256 -ne $verifierScriptHash -or
    $releaseEvidence.benchmark_manifest_sha256 -ne $benchmarkManifestHash -or
    $releaseEvidence.measured_candidate_sha256 -notmatch "^[0-9a-f]{64}$" -or
    $releaseEvidence.premeasurement_full_patch_sha256 -notmatch
        "^[0-9a-f]{64}$" -or
    (Get-JsonSha256 -Value $releaseEvidence.runner_environment) -ne
        (Get-JsonSha256 -Value $runnerEnvironment) -or
    (Get-JsonSha256 -Value $releaseEvidence.runner_environment) -ne
        (Get-JsonSha256 -Value $manifest.runner.environment) -or
    $releaseEvidence.runs -ne $manifest.runner.fresh_process_runs -or
    $releaseEvidence.warmup_runs -ne
        $manifest.runner.warmup_runs_not_measured -or
    $releaseEvidence.p95_method -ne
        "nearest_rank_ceiling_0.95_times_n" -or
    -not $releaseEvidence.deterministic_projection -or
    $releaseEvidence.diagnostic_incomplete -ne
        $manifest.release_evidence.expected_diagnostic_incomplete -or
    $releaseEvidence.status -ne $expectedStatus -or
    $measurements.Count -ne $releaseEvidence.runs -or
    [string]::IsNullOrWhiteSpace([string]$releaseEvidence.recorded_at_utc) -or
    ([DateTimeOffset]$releaseEvidence.recorded_at_utc).Offset -ne [TimeSpan]::Zero) {
    throw "Frozen release evidence has inconsistent candidate inputs"
}

$actualOrdinals = @($measurements.run | ForEach-Object { [int]$_ })
$expectedOrdinals = @(1..([int]$releaseEvidence.runs))
if (($actualOrdinals -join ",") -ne ($expectedOrdinals -join ",")) {
    throw "Release measurements do not contain exact ordinals 1..runs"
}
$sortedElapsed = @($measurements.elapsed_ms | ForEach-Object { [double]$_ } |
    Sort-Object)
$p95Index = [Math]::Ceiling(0.95 * $measurements.Count) - 1
$recomputedP95 = $sortedElapsed[$p95Index]
$recomputedPeak = (
    $measurements.peak_working_set_bytes | Measure-Object -Maximum
).Maximum
if ([double]$releaseEvidence.p95_elapsed_ms -ne $recomputedP95 -or
    [bool]$releaseEvidence.p95_optimization_target_met -ne
        ($recomputedP95 -le
            $manifest.release_evidence.p95_optimization_target_ms) -or
    [double]$releaseEvidence.maximum_peak_working_set_bytes -ne
        [double]$recomputedPeak -or
    $recomputedP95 -ge $manifest.release_evidence.absolute_p95_budget_ms -or
    $recomputedPeak -gt
        $manifest.release_evidence.maximum_peak_working_set_bytes) {
    throw "Release timing or memory summary does not satisfy its absolute gate"
}

$projectionDigests = @($measurements.stdout_sha256 | Sort-Object -Unique)
$semanticDigests = @(
    $measurements.review_summary.semantic_summary_sha256 |
        Sort-Object -Unique
)
if ($projectionDigests.Count -ne 1 -or $semanticDigests.Count -ne 1 -or
    ($projectionDigests -join ",") -ne
        (@($releaseEvidence.projection_digests) -join ",") -or
    ($semanticDigests -join ",") -ne
        (@($releaseEvidence.semantic_summary_digests) -join ",")) {
    throw "Release measurements do not have one projection and semantic summary"
}

foreach ($measurement in $measurements) {
    Assert-ExactFields -Value $measurement -Owner "Release measurement" -Fields @(
        "run", "elapsed_ms", "peak_working_set_bytes", "exit_code",
        "stdout_bytes", "stdout_sha256", "stderr_bytes", "stderr_sha256",
        "review_summary"
    )
    $summary = $measurement.review_summary
    Assert-ExactFields -Value $summary -Owner "Review summary" -Fields @(
        "terminal", "disposition", "completion", "scope_kind", "seal",
        "finding_summary", "finding_rule_summary", "findings_sha256",
        "blocked_families", "blocked_family_summary",
        "blocked_family_details_sha256", "admitted_files", "metrics",
        "semantic_summary_sha256"
    )
    Assert-ExactFields -Value $summary.finding_summary `
        -Owner "Finding summary" -Fields @(
            "total", "hard_violation", "review_required"
        )
    Assert-ExactFields -Value $summary.metrics -Owner "Review metrics" `
        -Fields @("files_read", "byte_sweeps", "structural_parses")
    $findingSummary = $summary.finding_summary
    $ruleSummary = @($summary.finding_rule_summary)
    $blockedSummary = @($summary.blocked_family_summary)
    $ruleKeys = @($ruleSummary | ForEach-Object {
        "$($_.grade)`t$($_.rule)"
    })
    $blockedKeys = @($blockedSummary | ForEach-Object { [string]$_.family })
    foreach ($row in $ruleSummary) {
        Assert-ExactFields -Value $row -Owner "Finding rule summary" `
            -Fields @("grade", "rule", "count")
    }
    foreach ($row in $blockedSummary) {
        Assert-ExactFields -Value $row -Owner "Blocked family summary" `
            -Fields @("family", "count")
    }
    $validFindingCounts =
        $findingSummary.total -ge 0 -and
        $findingSummary.hard_violation -ge 0 -and
        $findingSummary.review_required -ge 0 -and
        $findingSummary.total -eq (
            $findingSummary.hard_violation +
            $findingSummary.review_required
        ) -and
        (Get-PositiveCountSum -Rows $ruleSummary) -eq
            $findingSummary.total
    $validBlockedCounts =
        $summary.blocked_families -ge 0 -and
        (Get-PositiveCountSum -Rows $blockedSummary) -eq
            $summary.blocked_families
    $validLifecycle =
        $summary.admitted_files -eq $selectedRecords.Count -and
        $summary.metrics.files_read -eq $summary.admitted_files -and
        $summary.metrics.byte_sweeps -eq $summary.admitted_files -and
        $summary.metrics.structural_parses -eq $summary.admitted_files
    if ($measurement.exit_code -ne
            $manifest.release_evidence.expected_exit_code -or
        $summary.terminal -ne $manifest.release_evidence.expected_terminal -or
        $summary.disposition -ne
            $manifest.release_evidence.expected_disposition -or
        $summary.completion -ne
            $manifest.release_evidence.expected_completion -or
        $summary.scope_kind -ne "workspace" -or
        $summary.seal -notmatch "^[0-9a-f]{64}$" -or
        $measurement.stdout_bytes -le 0 -or
        $measurement.stdout_sha256 -notmatch "^[0-9a-f]{64}$" -or
        $measurement.stderr_bytes -ne 0 -or
        $measurement.stderr_sha256 -ne (Get-Sha256Text -Text "") -or
        $measurement.elapsed_ms -le 0 -or
        $measurement.peak_working_set_bytes -le 0 -or
        -not $validFindingCounts -or -not $validBlockedCounts -or
        -not $validLifecycle -or
        @($ruleSummary | Where-Object {
            $_.grade -notin @(
                "hard_violation",
                "review_required"
            ) -or [string]::IsNullOrWhiteSpace([string]$_.rule)
        }).Count -ne 0 -or
        @($blockedSummary | Where-Object {
            [string]::IsNullOrWhiteSpace([string]$_.family)
        }).Count -ne 0 -or
        ($ruleKeys -join ",") -ne
            (@($ruleKeys | Sort-Object -Unique) -join ",") -or
        ($blockedKeys -join ",") -ne
            (@($blockedKeys | Sort-Object -Unique) -join ",") -or
        $summary.findings_sha256 -notmatch "^[0-9a-f]{64}$" -or
        $summary.blocked_family_details_sha256 -notmatch
            "^[0-9a-f]{64}$" -or
        $summary.semantic_summary_sha256 -ne
            (Get-ReviewSummaryDigest -Summary $summary)) {
        throw "Release measurement $($measurement.run) has invalid review evidence"
    }
}
if ($releaseEvidence.review_summary.semantic_summary_sha256 -ne
        $semanticDigests[0] -or
    (Get-ReviewSummaryDigest -Summary $releaseEvidence.review_summary) -ne
        $semanticDigests[0]) {
    throw "Top-level review summary is not derived from the measurements"
}
$verifiedReleaseEvidence = [pscustomobject][ordered]@{
    path = $releaseEvidencePath
    sha256 = $releaseEvidenceHash
    status = [string]$releaseEvidence.status
}

if ($isStaging) {
    $currentCandidateIdentity = Get-CurrentMeasuredCandidate
    $currentCandidateHash = Get-JsonSha256 `
        -Value $currentCandidateIdentity.candidate
    if ($releaseEvidence.executable_sha256 -ne
            $currentCandidateIdentity.candidate.executable.sha256 -or
        $releaseEvidence.premeasurement_full_patch_sha256 -ne
            $currentCandidateIdentity.full_patch_sha256 -or
        $releaseEvidence.measured_candidate_sha256 -ne $currentCandidateHash) {
        throw "Staged release evidence does not match the current candidate"
    }
}

if ($PromoteReleaseEvidence) {
    $releaseEvidence.status = $manifest.release_evidence.expected_status
    $promotedJson = ($releaseEvidence | ConvertTo-Json -Depth 20).Replace(
        "`r`n",
        "`n"
    )
    $promotedBytes = [Text.UTF8Encoding]::new($false).GetBytes(
        $promotedJson + "`n"
    )
    $expectedPromotionHash = Get-Sha256Bytes -Bytes $promotedBytes
    $releaseEvidenceHash = Install-VerifiedReceipt `
        -CanonicalPath $canonicalReleasePath `
        -VerifiedBytes $promotedBytes `
        -VerifiedSha256 $expectedPromotionHash `
        -ExpectedCanonicalSha256 $canonicalReleaseHashBeforePromotion `
        -ArtifactStem "release_runs"
    $verifiedReleaseEvidence = [pscustomobject][ordered]@{
        path = [IO.Path]::GetFullPath($canonicalReleasePath)
        sha256 = $releaseEvidenceHash
        status = [string]$releaseEvidence.status
    }
}

if (-not $VerifyReleaseEvidenceOnly) {
$canonicalSelfCheckPath = Join-Path $fixtureRoot "self_check.json"
$selfCheckPath = if ($selfCheckMode) {
    [IO.Path]::GetFullPath($SelfCheckEvidencePath)
} else {
    $canonicalSelfCheckPath
}
$canonicalSelfCheckHashBeforePromotion = if (
    Test-Path -LiteralPath $canonicalSelfCheckPath -PathType Leaf
) {
    (Get-FileHash -LiteralPath $canonicalSelfCheckPath `
        -Algorithm SHA256).Hash.ToLowerInvariant()
} else {
    $null
}
if (-not (Test-Path -LiteralPath $selfCheckPath -PathType Leaf) -or
    ($selfCheckMode -and
        [IO.Path]::GetFullPath($selfCheckPath) -eq
            [IO.Path]::GetFullPath($canonicalSelfCheckPath))) {
    throw "Self-check staging must be a distinct existing file"
}
$repositoryPrefix = $repositoryRoot.TrimEnd("\", "/") +
    [IO.Path]::DirectorySeparatorChar
$targetPrefix = (Join-Path $repositoryRoot "target").TrimEnd("\", "/") +
    [IO.Path]::DirectorySeparatorChar
if ($selfCheckMode -and
    $selfCheckPath.StartsWith(
        $repositoryPrefix,
        [StringComparison]::OrdinalIgnoreCase
    ) -and
    -not $selfCheckPath.StartsWith(
        $targetPrefix,
        [StringComparison]::OrdinalIgnoreCase
    )) {
    throw "Self-check staging inside the repository must stay under target"
}
$selfCheckBytes = [IO.File]::ReadAllBytes($selfCheckPath)
$selfCheckStagingHash = Get-Sha256Bytes -Bytes $selfCheckBytes
if ($selfCheckMode -and
    $selfCheckStagingHash -ne $ExpectedSelfCheckStagingSha256) {
    throw "Self-check staging bytes do not match the expected SHA-256"
}
$strictUtf8 = [Text.UTF8Encoding]::new($false, $true)
$selfCheck = $strictUtf8.GetString($selfCheckBytes) | ConvertFrom-Json
if ($selfCheck.schema_version -ne 3 -or
    $selfCheck.source_candidate.state -ne
        "wip_unpublished" -or
    $selfCheck.source_candidate.semantic_authority_digest -ne
        $fixtureManifest.semantic_authority_digest) {
    throw "Current self-check receipt has an unsupported schema or state"
}
$measuredCandidate = $selfCheck.measured_candidate
if ($null -eq $measuredCandidate -or
    (Get-JsonSha256 -Value $measuredCandidate) -ne
        $releaseEvidence.measured_candidate_sha256) {
    throw "Current self-check does not own the measured candidate identity"
}

$currentHead = (& git -C $repositoryRoot rev-parse HEAD).Trim()
$patchHash = Get-TrackedPatchHash -RepositoryRoot $repositoryRoot `
    -BaseHead $currentHead
$functionalExclusions = @("docs/fixtures/core/release_runs.json")
$functionalPatchHash = Get-TrackedPatchHash -RepositoryRoot $repositoryRoot `
    -BaseHead $currentHead -ExcludedPaths $functionalExclusions
[string[]]$untrackedInputs = @(
    & git -C $repositoryRoot ls-files --others --exclude-standard -- `
        src tests docs .agents/skills/csu-review .claude/skills/csu-review
)
[Array]::Sort($untrackedInputs, [StringComparer]::Ordinal)
[object[]]$untrackedInputRecords = Get-UntrackedFileRecords `
    -RepositoryRoot $repositoryRoot -Paths $untrackedInputs
$expectedUntracked = @($selfCheck.source_candidate.untracked_inputs)
if ($LASTEXITCODE -ne 0 -or
    $currentHead -ne $selfCheck.source_candidate.base_head -or
    $patchHash -ne $selfCheck.source_candidate.tracked_patch_sha256 -or
    $currentHead -ne $measuredCandidate.base_head -or
    ($functionalExclusions -join ",") -ne
        (@($measuredCandidate.functional_patch_exclusions) -join ",") -or
    $functionalPatchHash -ne $measuredCandidate.functional_patch_sha256 -or
    (Get-JsonSha256 -Value $untrackedInputRecords) -ne
        (Get-JsonSha256 -Value $expectedUntracked) -or
    (Get-JsonSha256 -Value $untrackedInputRecords) -ne
        (Get-JsonSha256 -Value @($measuredCandidate.untracked_inputs))) {
    throw "Current self-check tracked patch identity mismatch"
}

$expectedMaintenance = @($selfCheck.source_candidate.untracked_maintenance)
foreach ($entry in $expectedMaintenance) {
    $entryPath = Join-Path $repositoryRoot $entry.path
    $entryHash = (
        Get-FileHash -LiteralPath $entryPath -Algorithm SHA256
    ).Hash.ToLowerInvariant()
    if ($entryHash -ne $entry.sha256) {
        throw "Current untracked maintenance identity mismatch: $($entry.path)"
    }
}
if ((Get-JsonSha256 -Value $expectedMaintenance) -ne
    (Get-JsonSha256 -Value @($measuredCandidate.untracked_maintenance))) {
    throw "Measured and final maintenance identities differ"
}
$planning = $selfCheck.source_candidate.retained_local_planning_material
$planningPath = Join-Path $repositoryRoot $planning.path
if ($planning.classification -ne "immutable_requirement_snapshot" -or
    -not (Test-Path -LiteralPath $planningPath -PathType Container) -or
    $measuredCandidate.retained_local_planning_material.path -ne $planning.path -or
    $measuredCandidate.retained_local_planning_material.classification -ne
        $planning.classification) {
    throw "Retained requirement snapshot is not the frozen immutable tree"
}
$planningEntries = @(Get-ChildItem -LiteralPath $planningPath -Recurse -Force)
if (@($planningEntries | Where-Object {
            $_.Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)
        }).Count -ne 0) {
    throw "Retained local planning material must not traverse a reparse point"
}
[object[]]$planningFiles = @(
    $planningEntries | Where-Object { -not $_.PSIsContainer } |
        ForEach-Object {
            $relative = [IO.Path]::GetRelativePath(
                $repositoryRoot,
                $_.FullName
            ).Replace("\", "/")
            [pscustomobject][ordered]@{
                path = $relative
                sha256 = (
                    Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256
                ).Hash.ToLowerInvariant()
            }
        }
)
if (@($planningFiles | Where-Object {
            [IO.Path]::GetExtension($_.path) -notin @(".md", ".json")
        }).Count -ne 0) {
    throw "Retained local planning material contains an unsupported file"
}
$planningComparison = [Collections.Generic.Comparer[object]]::Create({
    param($left, $right)
    return [StringComparer]::Ordinal.Compare($left.path, $right.path)
})
[Array]::Sort($planningFiles, $planningComparison)
$planningDigest = Get-JsonSha256 -Value $planningFiles
if ($planningFiles.Count -ne $planning.files -or
    $planningDigest -ne $planning.sha256 -or
    $planningFiles.Count -ne
        $measuredCandidate.retained_local_planning_material.files -or
    $planningDigest -ne
        $measuredCandidate.retained_local_planning_material.sha256) {
    throw "Retained local planning identity drift"
}
[string[]]$allUntracked = @(
    & git -C $repositoryRoot ls-files --others --exclude-standard
)
if ($LASTEXITCODE -ne 0) {
    throw "Cannot enumerate the complete untracked candidate inventory"
}
$classifiedPaths = @($untrackedInputs) + @(
    $expectedMaintenance | ForEach-Object { $_.path }
)
$unexpectedUntracked = @($allUntracked | Where-Object {
    $_ -ne "docs/fixtures/core/self_check.json" -and
    $_ -notin $classifiedPaths -and
    -not $_.StartsWith("$($planning.path)/")
})
if ($unexpectedUntracked.Count -ne 0) {
    throw "Unclassified untracked candidate material: $unexpectedUntracked"
}

if ($cargoLockHash -ne $selfCheck.source_candidate.cargo_lock_sha256 -or
    (Get-JsonSha256 -Value $selfCheck.source_candidate.runner_environment) -ne
        (Get-JsonSha256 -Value $runnerEnvironment)) {
    throw "Current self-check toolchain or lockfile identity mismatch"
}

$candidateExecutablePath = Join-Path $repositoryRoot (
    $selfCheck.source_candidate.executable.path
)
$candidateExecutableHash = (
    Get-FileHash -LiteralPath $candidateExecutablePath -Algorithm SHA256
).Hash.ToLowerInvariant()
if ($candidateExecutableHash -ne
        $selfCheck.source_candidate.executable.sha256 -or
    $candidateExecutableHash -ne $releaseEvidence.executable_sha256 -or
    $candidateExecutableHash -ne $measuredCandidate.executable.sha256) {
    throw "Current candidate is not the measured release executable"
}
$selfAuthorityPath = Join-Path $repositoryRoot $selfCheck.self_review.authority.path
$selfAuthorityHash = (
    Get-FileHash -LiteralPath $selfAuthorityPath -Algorithm SHA256
).Hash.ToLowerInvariant()
if ($selfAuthorityHash -ne $selfCheck.self_review.authority.sha256) {
    throw "Current self-review Authority identity mismatch"
}

$candidateInputs = $selfCheck.candidate_inputs
if ($candidateInputs.fixture_manifest.path -ne
        "docs/fixtures/core/fixture-manifest.json" -or
    $candidateInputs.fixture_manifest.sha256 -ne $fixtureManifestHash -or
    $candidateInputs.benchmark_manifest.path -ne
        "docs/fixtures/core/benchmark-manifest.json" -or
    $candidateInputs.benchmark_manifest.sha256 -ne $benchmarkManifestHash -or
    $candidateInputs.parser_admission.path -ne
        "docs/fixtures/core/parser-admission.json" -or
    $candidateInputs.parser_admission.sha256 -ne
        $parserAdmissionManifest.receipt.sha256 -or
    $candidateInputs.release_workflow.path -ne
        ".github/workflows/release.yml" -or
    $candidateInputs.release_workflow.sha256 -ne $releaseWorkflowHash -or
    $candidateInputs.release_evidence.path -ne
        "docs/fixtures/core/release_runs.json" -or
    $candidateInputs.release_evidence.sha256 -ne $releaseEvidenceHash -or
    $candidateInputs.standards.path -ne "docs/coding_standards.md" -or
    $candidateInputs.standards.sha256 -ne $standardsHash -or
    $candidateInputs.standards.physical_lines -ne $standardsLines -or
    $standardsLines -lt
        $manifest.candidate_gates.normative_standard_min_physical_lines -or
    $standardsLines -gt
        $manifest.candidate_gates.normative_standard_max_physical_lines -or
    $candidateInputs.corpus.files -ne $selectedRecords.Count -or
    $candidateInputs.corpus.physical_lines -ne
        $manifest.corpus_200k.physical_lines -or
    $candidateInputs.corpus.digest -ne $aggregateDigest -or
    $candidateInputs.corpus.inventory_sha256 -ne $inventoryHash -or
    $measuredCandidate.fixture_manifest_sha256 -ne $fixtureManifestHash -or
    $measuredCandidate.benchmark_manifest_sha256 -ne $benchmarkManifestHash -or
    $measuredCandidate.performance_authority_sha256 -ne
        $performanceAuthorityHash -or
    $measuredCandidate.parser_admission_sha256 -ne
        $parserAdmissionManifest.receipt.sha256 -or
    $measuredCandidate.release_workflow_sha256 -ne $releaseWorkflowHash -or
    $measuredCandidate.semantic_authority_digest -ne
        $fixtureManifest.semantic_authority_digest -or
    $measuredCandidate.corpus.files -ne $selectedRecords.Count -or
    $measuredCandidate.corpus.physical_lines -ne $selectedLines -or
    $measuredCandidate.corpus.digest -ne $aggregateDigest -or
    $measuredCandidate.corpus.inventory_sha256 -ne $inventoryHash -or
    $measuredCandidate.line_counts.product_rust -ne $productPhysicalLines -or
    $measuredCandidate.line_counts.test_rust -ne $testPhysicalLines -or
    $measuredCandidate.line_counts.normative_standard -ne $standardsLines -or
    $measuredCandidate.standards_sha256 -ne $standardsHash -or
    $measuredCandidate.cargo_lock_sha256 -ne $cargoLockHash -or
    (Get-JsonSha256 -Value $measuredCandidate.toolchain) -ne
        (Get-JsonSha256 -Value $runnerEnvironment.observed_tools)) {
    throw "Current candidate fixture, corpus, documentation, or receipt identity drift"
}

$skillInputs = $candidateInputs.skills
if ($skillInputs.agent_skill_path -ne
        ".agents/skills/csu-review/SKILL.md" -or
    $skillInputs.claude_skill_path -ne
        ".claude/skills/csu-review/SKILL.md" -or
    $skillInputs.lock_path -ne "skills-lock.json" -or
    $skillInputs.skill_sha256 -ne $agentSkillHash -or
    $sharedSkillHash -ne $sharedClaudeHash -or
    $agentSkillHash -ne $claudeSkillHash -or
    -not [Linq.Enumerable]::SequenceEqual(
        [byte[]]$agentSkillBytes,
        [byte[]]$claudeSkillBytes
    ) -or
    $skillInputs.agent_folder_sha256 -ne $skillFolderHash -or
    $skillInputs.lock_sha256 -ne $skillsLockHash -or
    $skillsLock.skills."csu-review".computedHash -ne $skillFolderHash) {
    throw "Current candidate skill projection or lock identity drift"
}
if ($measuredCandidate.skills.skill_sha256 -ne $agentSkillHash -or
    $measuredCandidate.skills.folder_sha256 -ne $skillFolderHash -or
    $measuredCandidate.skills.lock_sha256 -ne $skillsLockHash) {
    throw "Measured candidate skill identity drift"
}

$scopeReceipts = @($selfCheck.self_review.scopes)
if (($scopeReceipts.path -join ",") -ne "src,tests") {
    throw "Current self-check must own exactly product and recursive tests"
}
foreach ($scopeReceipt in $scopeReceipts) {
    $scopePath = Join-Path $repositoryRoot $scopeReceipt.path
    $physicalLines = Get-RustPhysicalLineCount -Path $scopePath
    $reviewOutput = & $candidateExecutablePath review `
        --authority (Split-Path -Parent $selfAuthorityPath) `
        --workspace $scopePath --format json
    if ($LASTEXITCODE -ne 0) {
        throw "Current self-review failed for $($scopeReceipt.path)"
    }
    $review = (($reviewOutput -join "`n") | ConvertFrom-Json)
    $scopeValue = $review.review.scope.value
    if ($null -eq $scopeValue -or
        $scopeValue.PSObject.Properties.Name -notcontains "files" -or
        $null -eq $scopeValue.files) {
        throw "Current self-review omitted its admitted workspace file set"
    }
    $liveFiles = @($scopeValue.files)
    $liveSummaryFields = @(
        $review.review.finding_summary.PSObject.Properties.Name | Sort-Object
    )
    $scopeLineLimit = if ($scopeReceipt.path -eq "src") {
        [int]$manifest.candidate_gates.product_rust_max_physical_lines
    } else {
        [int]$manifest.candidate_gates.test_rust_max_physical_lines
    }
    if ($physicalLines -ne $scopeReceipt.physical_lines -or
        $physicalLines -gt $scopeLineLimit -or
        $review.schema_version -ne 4 -or
        ($liveSummaryFields -join ",") -ne
            "hard_violation,review_required,total" -or
        $review.terminal -ne $scopeReceipt.terminal -or
        $review.disposition -ne $scopeReceipt.disposition -or
        $review.review.completion -ne $scopeReceipt.completion -or
        $review.review.seal -ne $scopeReceipt.seal -or
        $review.review.scope.kind -ne "workspace" -or
        $liveFiles.Count -ne $scopeReceipt.admitted_files -or
        $liveFiles.Count -eq 0 -or
        @($review.review.findings).Count -ne 0 -or
        @($review.review.blocked_family_details).Count -ne 0 -or
        $review.review.finding_summary.total -ne $scopeReceipt.findings.total -or
        $review.review.finding_summary.hard_violation -ne
            $scopeReceipt.findings.hard_violation -or
        $review.review.finding_summary.review_required -ne
            $scopeReceipt.findings.review_required -or
        $review.review.blocked_families -ne $scopeReceipt.blocked_families -or
        $scopeReceipt.findings.total -ne 0 -or
        $scopeReceipt.findings.hard_violation -ne 0 -or
        $scopeReceipt.findings.review_required -ne 0 -or
        $scopeReceipt.blocked_families -ne 0 -or
        $review.review.metrics.files_read -ne $scopeReceipt.metrics.files_read -or
        $review.review.metrics.byte_sweeps -ne
            $scopeReceipt.metrics.byte_sweeps -or
        $review.review.metrics.structural_parses -ne
            $scopeReceipt.metrics.structural_parses -or
        $review.review.metrics.files_read -ne $liveFiles.Count -or
        $review.review.metrics.byte_sweeps -ne $liveFiles.Count -or
        $review.review.metrics.structural_parses -ne $liveFiles.Count) {
        throw "Current self-review receipt drift: $($scopeReceipt.path)"
    }
}

& cargo fmt --manifest-path $cargoManifestPath --all -- --check 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Current candidate failed cargo fmt --all -- --check"
}
& cargo clippy --manifest-path $cargoManifestPath --locked --all-targets -- `
    -D warnings 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Current candidate failed locked all-target Clippy"
}
& cargo test --manifest-path $cargoManifestPath --locked 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Current candidate failed the full locked test suite"
}
$compiledTestCatalog = Get-CompiledTestCatalog `
    -CargoManifestPath $cargoManifestPath
if ($compiledTestCatalog.tests -ne
        $selfCheck.self_review.compiled_test_catalog.tests -or
    $compiledTestCatalog.sha256 -ne
        $selfCheck.self_review.compiled_test_catalog.sha256 -or
    $compiledTestCatalog.tests -ne $measuredCandidate.compiled_test_catalog.tests -or
    $compiledTestCatalog.sha256 -ne
        $measuredCandidate.compiled_test_catalog.sha256) {
    throw "Current compiled test catalog identity mismatch"
}

$postPatchHash = Get-TrackedPatchHash -RepositoryRoot $repositoryRoot `
    -BaseHead $currentHead
$postHead = (& git -C $repositoryRoot rev-parse HEAD).Trim()
$postHeadExitCode = $LASTEXITCODE
[string[]]$postUntracked = @(
    & git -C $repositoryRoot ls-files --others --exclude-standard
)
if ($LASTEXITCODE -ne 0) {
    throw "Cannot recheck the untracked candidate inventory"
}
[Array]::Sort($postUntracked, [StringComparer]::Ordinal)
$postExecutableHash = (
    Get-FileHash -LiteralPath $candidateExecutablePath -Algorithm SHA256
).Hash.ToLowerInvariant()
$postRunnerEnvironment = Get-RunnerEnvironment `
    -WorkspacePath $releaseEvidence.workspace
if ($postHeadExitCode -ne 0 -or $postHead -ne $currentHead -or
    $postPatchHash -ne $patchHash -or
    ($postUntracked -join "`n") -ne ($allUntracked -join "`n") -or
    $postExecutableHash -ne $candidateExecutableHash -or
    (Get-JsonSha256 -Value $postRunnerEnvironment) -ne
        (Get-JsonSha256 -Value $runnerEnvironment)) {
    throw "Candidate identity changed during self-check execution"
}
foreach ($entry in @($expectedUntracked) + @($expectedMaintenance)) {
    $postHash = (
        Get-FileHash -LiteralPath (Join-Path $repositoryRoot $entry.path) `
            -Algorithm SHA256
    ).Hash.ToLowerInvariant()
    if ($postHash -ne $entry.sha256) {
        throw "Untracked candidate content changed during self-check"
    }
}
$postPlanningFiles = Get-UntrackedFileRecords `
    -RepositoryRoot $repositoryRoot -Paths @(
        $planningFiles | ForEach-Object { $_.path }
    )
if ($postPlanningFiles.Count -ne $planningFiles.Count -or
    (Get-JsonSha256 -Value $postPlanningFiles) -ne $planningDigest) {
    throw "Retained local planning identity changed during self-check"
}

$tracks = $selfCheck.evidence_tracks
if ($tracks.semantic -ne "verified" -or
    $tracks.self_review -ne "verified" -or
    $tracks.fixture_input -ne "verified" -or
    $tracks.performance -ne "verified_current_inputs" -or
    $tracks.provenance -ne "pinned_release_candidate" -or
    $tracks.overall -ne "release_candidate_evidence_complete_unpublished") {
    throw "Current evidence-track readiness is not truthful"
}
if ($selfCheckMode) {
    $stagingBytesAfterVerification = [IO.File]::ReadAllBytes($selfCheckPath)
    if ((Get-Sha256Bytes -Bytes $stagingBytesAfterVerification) -ne
        $selfCheckStagingHash) {
        throw "Self-check staging changed during verification"
    }
    Install-VerifiedReceipt `
        -CanonicalPath $canonicalSelfCheckPath `
        -VerifiedBytes $selfCheckBytes `
        -VerifiedSha256 $selfCheckStagingHash `
        -ExpectedCanonicalSha256 $canonicalSelfCheckHashBeforePromotion `
        -ArtifactStem "self_check" | Out-Null
}
}
}

if ($BuildCorpus) {
    if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
        throw "-OutputDirectory is required with -BuildCorpus"
    }
    $outputPath = [IO.Path]::GetFullPath($OutputDirectory)
    if (Test-Path -LiteralPath $outputPath) {
        if (@(Get-ChildItem -LiteralPath $outputPath -Force).Count -ne 0) {
            throw "Output directory must be empty: $outputPath"
        }
    } else {
        [void](New-Item -ItemType Directory -Path $outputPath)
    }
    foreach ($record in $selectedRecords) {
        $destination = Join-Path $outputPath (
            "$($record.Language)/$($record.Target)/$($record.Path)"
        )
        $destinationParent = Split-Path -Parent $destination
        [void](New-Item -ItemType Directory -Path $destinationParent -Force)
        Copy-Item -LiteralPath $record.FullPath -Destination $destination
    }
}

$verifiedPath = $null
$corpusPath = if ($BuildCorpus) {
    $outputPath
} elseif (-not [string]::IsNullOrWhiteSpace($VerifyCorpusDirectory)) {
    [IO.Path]::GetFullPath($VerifyCorpusDirectory)
} else {
    $null
}
if ($null -ne $corpusPath) {
    if (-not (Test-Path -LiteralPath $corpusPath -PathType Container)) {
        throw "Missing materialized corpus: $corpusPath"
    }
    foreach ($record in $selectedRecords) {
        $relative = "$($record.Language)/$($record.Target)/$($record.Path)"
        $materializedFile = Join-Path $corpusPath $relative
        if (-not (Test-Path -LiteralPath $materializedFile -PathType Leaf)) {
            throw "Materialized corpus file is missing: $relative"
        }
        $materializedHash = (
            Get-FileHash -LiteralPath $materializedFile -Algorithm SHA256
        ).Hash.ToLowerInvariant()
        if ($materializedHash -ne $record.Sha256) {
            throw "Materialized corpus file identity mismatch: $relative"
        }
    }
    $materializedFiles = @(
        Get-ChildItem -LiteralPath $corpusPath -Recurse -File
    )
    if ($materializedFiles.Count -ne $selectedRecords.Count) {
        throw "Materialized corpus contains an unowned file"
    }
    $verifiedPath = $corpusPath
    $runnerEnvironment = Get-RunnerEnvironment -WorkspacePath $corpusPath
}
if ($null -eq $runnerEnvironment -or
    (Get-JsonSha256 -Value $runnerEnvironment) -ne
        (Get-JsonSha256 -Value $manifest.runner.environment)) {
    throw "Current runner environment does not match the frozen environment"
}

$measuredCandidate = $null
$premeasurementFullPatchHash = $null
if ($PrepareMeasurement) {
    $currentCandidateIdentity = Get-CurrentMeasuredCandidate
    $measuredCandidate = $currentCandidateIdentity.candidate
    $premeasurementFullPatchHash = $currentCandidateIdentity.full_patch_sha256
}

[pscustomobject]@{
    targets = $manifest.targets.Count
    available_files = $allRecords.Count
    available_physical_lines = (
        $allRecords | Measure-Object PhysicalLines -Sum
    ).Sum
    parseability_excluded_files = $excludedPaths.Count
    parseability_admitted_files = $admittedRecords.Count
    corpus_files = $selectedRecords.Count
    corpus_physical_lines = (
        $selectedRecords | Measure-Object PhysicalLines -Sum
    ).Sum
    corpus_digest = $aggregateDigest
    inventory_sha256 = $inventoryHash
    runner_environment = $runnerEnvironment
    measured_candidate = $measuredCandidate
    premeasurement_full_patch_sha256 = $premeasurementFullPatchHash
    release_evidence = $verifiedReleaseEvidence
    materialized_at = if ($BuildCorpus) { $outputPath } else { $null }
    verified_at = $verifiedPath
} | ConvertTo-Json -Depth 20
