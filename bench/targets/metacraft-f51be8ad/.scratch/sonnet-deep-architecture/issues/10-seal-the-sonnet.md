# 10 - Seal the Sonnet

Type: implementation

Status: resolved (2026-08-05)

Blocked by: none.

Readiness: all dependency tickets are resolved and Ticket 09's redacted
five-solve receipt independently validates. Separate owner authorization is
still required before writing the closure report or creating a commit.

## Outcome

Close the architecture with deterministic evidence only.

Verify the exact installed interfaces, scientific behavior, dependency
direction, import cost, deletion of the replaced lifecycle, external benchmark
ownership, frozen Rust source, release wheel, and the tracked native receipt
record from Ticket 09. Verify accepted ADR 0018 and record one closure report.

This ticket does not run Adviser, product discovery, native solves, or artifact
recovery. If a deterministic gate exposes an implementation defect, reopen the
ticket that owns it rather than repairing architecture during the seal.

## Scope

Add or finalize architecture ratchets for:

- root `metacraft` exports exactly `Authority`, `compile_study`, and `conduct`;
- `Authority` still exposes exactly `check`, `view`, `fetch`, and `decide`;
- `metacraft.field` exports exactly the six shared vocabulary values;
- raw rectilinear reference-surface geometry and qualified uniform batch
  formation remain specialized Field submodules and add no root export;
- the session and Adapter contain no uniform-spacing gate, interpolation, or
  reference-surface fallback;
- the existing `ProjectExecution` is persisted before observation, while no
  observation-failure schema or sidecar exists and execution alone never
  becomes work, receipt, evidence, recovery, or lifecycle authority;
- root and field imports do not load Torch or Lumerical;
- `conduct` compiles before claiming one fresh application root, opens one
  aim-specific `MetalensEvidenceAdapter` exactly once, and rejects existing or
  partial roots before opening evidence;
- `Study` owns canonical encoding and strict restoration;
- production has one compile/conduct lifecycle;
- production Result contains no external benchmark meaning;
- `examples/metalens_benchmark_cases.py` owns the four published cases;
- production never imports `examples`;
- Lumerical imports no metalens control strategy or project comparison;
- runtime imports form a DAG without an allowlist;
- cross-module private lifecycle imports are absent;
- deleted lifecycle files, names, aliases, and schemas are absent;
- current benchmark-case, benchmark-comparison, and focal-field-comparison
  schema identifiers are exact and strict;
- the wheel excludes examples, tests, `.scratch`, and generated artifacts;
- Rust source and protocol values match the fixed point.

Add `.scratch/sonnet-deep-architecture/CLOSURE-REPORT.md`.

Verify that [ADR 0018](../../../docs/adr/0018-let-one-sonnet-baseline-tell-one-truth.md)
agrees with the implementation it already governs:

- the breaking Python cutover;
- create-only application-root support and one aim-specific evidence opening;
- `Study` as sole scientific state;
- `AuthoritySession` as sole revision policy;
- `WorkExecution` as sole work life;
- two-question metalens consultation;
- one periodic-response seam;
- scientific Result separated from external benchmark comparison;
- the exact root and field interfaces;
- unchanged Rust authority.

The closure report records:

- implementation commit;
- focused seam tests from Tickets 01 through 09;
- complete non-live test count;
- Pyright outcome;
- CSU outcome;
- runtime DAG and import-surface checks;
- Rust source identity, format, lint, and test outcomes;
- release wheel name, size, and SHA-256;
- isolated import-smoke outcome;
- Ticket 09 canary-record identity and its five-solve summary;
- final repository status.

Do not reopen the Native application root from Ticket 09. Verify only its tracked,
redacted record and content hash.

### Pre-seal prerequisites

Ticket 10's evidence prerequisites are ready:

- Tickets 06, 07, 08, 08.5, 08.6, 08.7, and 09 are resolved under the
  dependency graph;
- Ticket 09's redacted `NATIVE-RECEIPT.json` independently validates as a
  strict five-solve record with SHA-256
  `5bf6e2170b82f077cfd313ed28c4c9268f773a1e857a4b92a838fbdd68b05416`;
- CSU reports zero blocking finding; Ticket 06 owns the enumerated 84 baseline
  blockers and Ticket 07 owns the remaining 69, so this seal owns none;
- `MethodUnavailable`, `AimUnavailable`, `_validate_successor`, the replaced
  lifecycle, and all compatibility carriers are absent from implementation;
- the architecture fixed point is the literal commit `40f2127`;
- every pre-existing dirty-worktree path has an explicit disposition and no
  unrelated user change would be included in a closure commit.

The owner must separately authorize implementation and local commit creation
before this ticket writes a closure report or commit. Planning approval
does not grant that authority.

### Commit semantics

The closure report's `implementation commit` is the immutable commit that
contains the complete implementation of Tickets 06 through 09, including 08.5,
and all deterministic production repairs, immediately before Ticket 10 adds
`CLOSURE-REPORT.md`. Record that commit hash as data; do not describe a
dirty worktree or the future closure commit as the implementation commit.

After every deterministic gate passes against that implementation commit,
add only the closure report and any predeclared non-production ratchet required
by this ticket. Create the closure commit, repeat the clean
status and fixed-point checks, and record both hashes without self-referential
wording. If the approved commit strategy differs, stop and obtain an explicit
replacement before proceeding.

## TDD seam

Write any missing ratchet before final verification. The deterministic test
surface must prove:

1. exact root interface;
2. exact field interface;
3. cheap root and field imports;
4. pure compile outcomes;
5. fresh-root conduct atomicity and deterministic outcomes through recorded
   Adapters, with no existing-root second call;
6. strict Study, checkpoint, and Result restoration;
7. external benchmark-case dependency direction;
8. one Authority session and one work life;
9. one periodic-response method through both Adapters;
10. absence of every deleted lifecycle path and symbol;
11. runtime DAG without an exception list;
12. built-wheel contents and installed Authority behavior;
13. unchanged Rust source.
14. zero unexpected skipped test cases in the explicitly selected non-live
    suite;
15. one exact wheel inventory with one native extension and no forbidden
    source or generated path.

Ratchets may inspect source imports, declared exports, paths, and frozen
identities. They must not lock private class layout, function-body text,
callback order, line counts, or internal file size.

## Acceptance

- Every deterministic Python test passes with zero unexpected skip.
- Pyright reports zero errors, warnings, and information.
- CSU reports zero blocking finding.
- CSU ownership is already closed by Tickets 06 and 07; this seal modifies no
  production source to repair a finding.
- Runtime imports are acyclic without an allowlist.
- Root and field imports satisfy their exact interfaces and loaded-module
  constraints.
- Production contains no external benchmark facts or `examples` dependency.
- The replaced local lifecycle, compatibility readers, and forwarding aliases
  are absent.
- Rust has an empty fixed-point diff; format, strict lint, tests, and source
  manifest all pass.
- One release wheel builds.
- The wheel contains exactly one `_authority` extension and no examples,
  tests, `.scratch`, or generated artifacts.
- An isolated target install imports the package, creates a fresh Authority
  workspace, and exercises `check`, `view`, `fetch`, and `decide`.
- Accepted ADR 0018 and the closure report agree with implemented behavior.
- Ticket 09's tracked record states exactly five native solves and passes its
  redaction checks.
- `git diff --check` passes and the repository is clean after the closure
  commit.
- The implementation and closure commit identities follow the frozen
  two-point semantics above and were created only under explicit owner
  authorization.

## Verification

Use only:

```text
C:\Users\Administrator\miniforge3\envs\research_env\python.exe
```

Run the complete deterministic Python suite:

```powershell
$projectPython = 'C:\Users\Administrator\miniforge3\envs\research_env\python.exe'
$sealRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("metacraft-sonnet-" + [guid]::NewGuid().ToString("N"))
$wheelDirectory = New-Item -ItemType Directory -Path (Join-Path $sealRoot "wheel")
$isolatedTarget = New-Item -ItemType Directory -Path (Join-Path $sealRoot "installed")
$testReport = Join-Path $sealRoot "pytest.xml"

& $projectPython -m pytest -q --tb=short -p no:cacheprovider --strict-markers `
  --junitxml $testReport `
  -m "not integration and not advice_live and not lumerical_live and not lumerical_delivery and not lumerical_canary"

& $projectPython -c "import sys, xml.etree.ElementTree as ET; root=ET.parse(sys.argv[1]); skipped=[(case.get('classname',''), case.get('name',''), child.get('message','')) for case in root.findall('.//testcase') for child in case.findall('skipped')]; unexpected=[item for item in skipped if not (item[0].endswith('workstation.test_workstation') and item[2].endswith('host has no complete workstation lane'))]; assert not unexpected, unexpected; print({'skipped': skipped})" $testReport

& $projectPython -m pyright

.\csu\bin\csu.exe check src\metacraft --format json --output .csu\sonnet-closure.json --no-history
```

The JUnit audit makes unexpected skips an executable gate rather than a manual
reading of terminal output. The sole accepted deterministic environmental
skip is an exact `host has no complete workstation lane` result from
`tests/workstation/test_workstation.py`; record its case names in the closure
report. Ticket 09 already proves the required live lane separately. Any other
skip requires reopening its owning ticket; do not broaden this frozen rule.

Run Rust verification without editing Rust:

```powershell
git diff --exit-code 40f2127 -- rust
cargo fmt --manifest-path rust/Cargo.toml --all -- --check
cargo clippy --manifest-path rust/Cargo.toml --workspace --all-targets -- -D warnings
cargo test --manifest-path rust/Cargo.toml --workspace --all-targets

& $projectPython -m pytest -q -p no:cacheprovider `
  tests/architecture/test_scientific_boundary.py::test_rust_tree_matches_the_committed_source_manifest
```

Build the release wheel:

```powershell
& $projectPython -m maturin build `
  --manifest-path rust/Cargo.toml `
  --release `
  --locked `
  --interpreter $projectPython `
  --out $wheelDirectory.FullName

$builtWheels = @(Get-ChildItem -LiteralPath $wheelDirectory.FullName -Filter *.whl -File)
if ($builtWheels.Count -ne 1) { throw "expected_exactly_one_wheel" }
$builtWheel = $builtWheels[0].FullName

& $projectPython -c "import sys, zipfile; names=zipfile.ZipFile(sys.argv[1]).namelist(); native=[name for name in names if name.startswith('metacraft/_authority') and name.endswith(('.pyd','.so'))]; forbidden=('examples/','tests/','.scratch/','.csu/','rust/target/','__pycache__/'); assert len(native)==1, native; assert not any(any(part in name for part in forbidden) or name.endswith(('.pyc','.pyo')) for name in names), names; print(len(names), native[0])" $builtWheel
```

Install it with:

```powershell
& $projectPython -m pip install `
  --no-index `
  --no-deps `
  --target $isolatedTarget.FullName `
  $builtWheel
```

Set `$smokeWorkspace = Join-Path $sealRoot "authority-smoke"`; do not create
that leaf. Run Python with `-I`, insert only `$isolatedTarget.FullName` into
`sys.path`, and
assert:

- root `__all__` is exact;
- one native `_authority` module loads;
- `Authority` has the four verbs;
- a fresh workspace passes `check`;
- `view` reports the root revision;
- one canonical document can be decided, fetched, and matched by reference.

Use the installed package's `metacraft.authority.Document`, `Proposal`, and
`Revision` values for the smoke proposal. Require an admitted decision, fetch
its `body_reference`, compare the fetched canonical document, and run
`Authority.check()` again after the write. The smoke must import no source-tree
module; record `metacraft.__file__` and `_authority.__file__` relative to the
isolated target in the closure report.

Run that exact smoke as:

```powershell
$smokeWorkspace = Join-Path $sealRoot "authority-smoke"

@'
from pathlib import Path
import sys

installed = Path(sys.argv[1]).resolve()
workspace = Path(sys.argv[2]).resolve()
assert not workspace.exists()
sys.path.insert(0, str(installed))

import metacraft
import metacraft._authority as native_authority
from metacraft import Authority
from metacraft.authority import Document, Proposal, Revision

assert metacraft.__all__ == ["Authority", "compile_study", "conduct"]
assert Path(metacraft.__file__).resolve().is_relative_to(installed)
assert Path(native_authority.__file__).resolve().is_relative_to(installed)
assert {name for name in ("check", "view", "fetch", "decide") if hasattr(Authority, name)} == {"check", "view", "fetch", "decide"}

authority = Authority(workspace)
assert authority.check().is_workspace_valid
assert authority.view().revision == Revision.root()
document = Document("metacraft.seal.smoke", {"verified": True})
decision = authority.decide(Proposal.record(document), at=Revision.root())
assert decision.admitted and decision.body_reference is not None
assert Document.from_bytes(authority.fetch(decision.body_reference)) == document
assert authority.check().is_workspace_valid
print(Path(metacraft.__file__).resolve().relative_to(installed))
print(Path(native_authority.__file__).resolve().relative_to(installed))
'@ | & $projectPython -I - $isolatedTarget.FullName $smokeWorkspace
```

Finally run:

```powershell
git diff --check
git status --short
```

The complete suite explicitly deselects every live marker. No live
availability is required or permitted.

## Stop and report

Stop and report if:

- any deterministic gate fails;
- any unexpected test skips;
- a production implementation change is needed;
- live Adviser, product discovery, native solve, or artifact recovery appears
  necessary;
- Rust has any fixed-point diff;
- a wheel contains examples, tests, `.scratch`, or generated artifacts;
- a deleted lifecycle name or compatibility path remains;
- the closure report would claim evidence not present in tracked outputs;
- the Ticket 09 record contains a secret or absolute user path;
- the worktree cannot be made clean without touching unrelated user work;
- implementation or closure commits are not explicitly authorized or cannot
  follow the frozen two-point semantics.

## Do not add

- production features or scientific thresholds;
- compatibility aliases, readers, or migrations;
- another architecture framework or closure framework;
- a live verification step;
- a second wheel smoke path;
- source-shape ratchets for private implementation;
- packaging of external benchmark cases;
- edits to Rust source or protocol values;
- cleanup of unrelated branches, worktrees, reports, archives, or user files;
- a resolved status before every deterministic gate and closure record are
  complete.

## Comments

### 2026-08-01 - Deterministic pre-seal stopped

- The architecture fixed point is `40f2127`, the commit that admitted this
  specification and its ten tickets. Rust has no diff from that fixed point,
  and the committed Rust source-manifest ratchet passes.
- The required CSU check reports 153 blocking hard violations: 133
  `Core011 public_surface.required_docs`, 11 `Core009 dependency.sorting`,
  eight `Core021 layout.alignment_consistency`, and one
  `Py005 function.annotation_completeness`. These are distributed across
  pre-existing production modules and require reopening their owning tickets;
  the seal must not repair them silently.
- The deleted-lifecycle ratchet is also not yet satisfied:
  `_validate_successor` remains defined and used in
  `science/metalens/checkpoint.py`, although Ticket 07 explicitly retired it.
- Ticket 09 did not produce the required five-solve receipt record. This
  ticket therefore remains `ready-for-agent`; no ADR, closure report, wheel,
  or resolved status was produced.

### 2026-08-01 - Exact seal contract approved

The owner approved this ticket revision, not implementation, native work, or
commit creation. The 153 baseline CSU blockers are now assigned upstream, the
fixed point and every temporary path are explicit, skip and source-manifest
audits are executable, wheel inventory is exact, and implementation/closure
commit semantics are frozen. Ticket 10 remains dependency-blocked until
Ticket 09 supplies its tracked record and the owner separately authorizes the
seal execution and commits.

### 2026-08-04 - ADR ownership moved before the seal

Accepted ADR 0018 now owns the system-wide Sonnet decision before production
implementation. Ticket 10 verifies that decision and writes the closure
report; it does not create a replacement ADR or repair production. Ticket 08.5
and the shared Ticket 06/09 Native evidence gate remain prerequisites. This
planning revision authorizes no implementation, Native work, report, or
commit.

### 2026-08-05 - Deterministic seal closed

The owner authorized the non-production closure after implementation commit
`eb6db2f`. The complete non-live suite passed 1,245 tests with 6 deselected
and 0 skipped; the focused and architecture seams passed 194 and 106 tests;
Pyright reported zero findings; and CSU reported 4,473 findings with zero
blocking. Rust remained diff-clean from `40f2127`; format, strict lint, 18
Cargo tests with 3 ignored, 3 Rust architecture tests, 17 Authority Interface
tests, and the source-manifest ratchet passed.

The release wheel
`metacraft-0.0.0-cp312-cp312-win_amd64.whl` is 1,737,468 bytes with SHA-256
`28a8558f43a17685d2dc53fb5cdbdca27ffca2270e4e09f2c4d9931cce8a68f4`.
Its 105-entry inventory contains exactly one native extension,
`metacraft/_authority.cp312-win_amd64.pyd`; isolated package/native imports
and the fresh Authority smoke passed. Ticket 09's tracked receipt retained
SHA-256 `5bf6e2170b82f077cfd313ed28c4c9268f773a1e857a4b92a838fbdd68b05416`,
the exact `3 + 0 + 2 = 5` solve accounting, identical 38-entry Native and
recovery inventories, two 24 by 24 formations, and zero recovery execution.
Both independent reviews reported no blocking finding.

The closure evidence is recorded in
[CLOSURE-REPORT.md](../CLOSURE-REPORT.md). The implementation checkpoint is
`eb6db2f`; the closure checkpoint is recorded by commit history immediately
after the report, avoiding a self-referential hash. No production, test, or
Rust file was changed and no Native work was rerun for this closure.
