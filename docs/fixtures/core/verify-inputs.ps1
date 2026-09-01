[CmdletBinding()]
param(
    [switch]$BuildCorpus,
    [string]$OutputDirectory,
    [string]$VerifyCorpusDirectory
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($BuildCorpus -and
    -not [string]::IsNullOrWhiteSpace($VerifyCorpusDirectory)) {
    throw "Use either -BuildCorpus or -VerifyCorpusDirectory"
}

function Get-Sha256Text {
    param([Parameter(Mandatory)][string]$Text)

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
        $rootPrefix = [IO.Path]::GetFullPath($targetRoot).TrimEnd("\", "/") + "\"
        $fullPath = [IO.Path]::GetFullPath($file.FullName)
        if (-not $fullPath.StartsWith(
            $rootPrefix,
            [StringComparison]::OrdinalIgnoreCase
        )) {
            throw "Target file escaped frozen root: $fullPath"
        }
        $relativePath = $fullPath.Substring($rootPrefix.Length).Replace("\", "/")
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
$fixtureManifestPath = Join-Path $fixtureRoot "fixture-manifest.json"
$fixtureManifest = Get-Content -LiteralPath $fixtureManifestPath `
    -Raw -Encoding UTF8 |
    ConvertFrom-Json
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
if ($authority.schema_version -ne 2 -or $authority.families.Count -ne 2) {
    throw "Frozen Authority fixture must contain schema 2 and two families"
}
$requiredLanguages = @("c", "cpp", "python", "rust")
foreach ($familyName in @("identifier", "documentation")) {
    $family = $authority.families |
        Where-Object name -EQ $familyName |
        Select-Object -First 1
    if ($null -eq $family) {
        throw "Frozen Authority fixture is missing family $familyName"
    }
    $projectionNames = @(
        $family.projections.PSObject.Properties.Name |
            Sort-Object
    )
    if (($projectionNames -join ",") -ne
        ($requiredLanguages -join ",")) {
        throw "Family $familyName does not have exactly four projections"
    }
    foreach ($projection in $family.projections.PSObject.Properties) {
        if ($projection.Value -notin @(
            "supported",
            "not_applicable",
            "needs_authority"
        )) {
            throw "Invalid projection state in family $familyName"
        }
    }
}

foreach ($scenario in $fixtureManifest.scenario_contracts.PSObject.Properties.Name) {
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
                "soft_friction",
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
$performanceIdentifier = $performanceAuthority.families |
    Where-Object name -EQ "identifier" |
    Select-Object -First 1
$performanceDocumentation = $performanceAuthority.families |
    Where-Object name -EQ "documentation" |
    Select-Object -First 1
if ($performanceAuthority.schema_version -ne 2 -or
    $performanceAuthority.source_form -ne "external" -or
    $null -eq $performanceIdentifier -or
    $null -eq $performanceDocumentation -or
    @($performanceAuthority.public_callables.PSObject.Properties).Count -ne 0 -or
    @($performanceIdentifier.projections.PSObject.Properties |
        Where-Object Value -NE "supported").Count -ne 0 -or
    @($performanceDocumentation.projections.PSObject.Properties |
        Where-Object Value -NE "not_applicable").Count -ne 0) {
    throw "Performance Authority does not isolate throughput evidence"
}
$targetsRoot = [IO.Path]::GetFullPath(
    (Join-Path $fixtureRoot $manifest.targets_root)
)
$allRecords = [Collections.Generic.List[object]]::new()

foreach ($target in $manifest.targets) {
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
    throw "Frozen workspace inventory identity mismatch"
}

$releaseEvidencePath = Join-Path $fixtureRoot $manifest.release_evidence.path
$releaseEvidenceHash = (
    Get-FileHash -LiteralPath $releaseEvidencePath -Algorithm SHA256
).Hash.ToLowerInvariant()
if ($releaseEvidenceHash -ne $manifest.release_evidence.sha256) {
    throw "Frozen release evidence identity mismatch"
}
$releaseEvidence = Get-Content -LiteralPath $releaseEvidencePath `
    -Raw -Encoding UTF8 | ConvertFrom-Json
$measurements = @($releaseEvidence.measurements)
if ($releaseEvidence.schema_version -ne
        $manifest.release_evidence.schema_version -or
    $releaseEvidence.authority_sha256 -ne $performanceAuthorityHash -or
    $releaseEvidence.corpus_files -ne $selectedRecords.Count -or
    $releaseEvidence.corpus_physical_lines -ne
        $manifest.corpus_200k.physical_lines -or
    $releaseEvidence.corpus_digest -ne $aggregateDigest -or
    $releaseEvidence.inventory_sha256 -ne $inventoryHash -or
    $releaseEvidence.runs -ne $manifest.runner.fresh_process_runs -or
    $releaseEvidence.warmup_runs -ne
        $manifest.runner.warmup_runs_not_measured -or
    $releaseEvidence.p95_elapsed_ms -ge
        $manifest.release_evidence.absolute_p95_budget_ms -or
    -not $releaseEvidence.deterministic_projection -or
    $releaseEvidence.diagnostic_incomplete -or
    @($releaseEvidence.projection_digests).Count -ne 1 -or
    $measurements.Count -ne $releaseEvidence.runs -or
    @($measurements | Where-Object {
        $_.exit_code -ne $manifest.release_evidence.expected_exit_code -or
        $_.terminal -ne $manifest.release_evidence.expected_terminal -or
        $_.disposition -ne
            $manifest.release_evidence.expected_disposition
    }).Count -ne 0) {
    throw "Frozen release evidence does not satisfy its absolute gate"
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
    $inventoryPath = Join-Path $outputPath ".csu-inventory.json"
    [IO.File]::WriteAllText(
        $inventoryPath,
        $inventoryJson,
        [Text.UTF8Encoding]::new($false)
    )
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
    $materializedInventory = Join-Path $corpusPath ".csu-inventory.json"
    if (-not (Test-Path -LiteralPath $materializedInventory -PathType Leaf)) {
        throw "Materialized corpus lacks .csu-inventory.json"
    }
    $materializedInventoryHash = (
        Get-FileHash -LiteralPath $materializedInventory -Algorithm SHA256
    ).Hash.ToLowerInvariant()
    if ($materializedInventoryHash -ne $inventoryHash) {
        throw "Materialized corpus inventory identity mismatch"
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
    if ($materializedFiles.Count -ne $selectedRecords.Count + 1) {
        throw "Materialized corpus contains an unowned file"
    }
    $verifiedPath = $corpusPath
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
    materialized_at = if ($BuildCorpus) { $outputPath } else { $null }
    verified_at = $verifiedPath
} | ConvertTo-Json
