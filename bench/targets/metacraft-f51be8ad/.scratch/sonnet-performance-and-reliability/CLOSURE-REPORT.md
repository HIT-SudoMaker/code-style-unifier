# Closure report — Sonnet performance and reliability convergence

Ticket 05 — Let the architecture close without residue.

Branch: `ticket/05-architecture-closes-without-residue` (based at `6337676`).
Python: `C:\Users\Administrator\miniforge3\envs\research_env\python.exe`.
Native extension: `<worktree>/src/metacraft_next/_authority.cp312-win_amd64.pyd`.
All test runs use `PYTHONPATH=<worktree>/src`.

This is the historical closure snapshot integrated at `ca90c27`. The later
terminal convergence is recorded separately under
`../sonnet-terminal-convergence/`.

This report is durable evidence beside [spec.md](spec.md). It does not infer
success from any prior agent ledger; every count below was produced by the
recorded command on the committed tree.

## What converged

### (A) Field-internals ratchet tightened; the private reach removed

`src/metacraft_next/science/metalens/focus_evidence.py` reached storage helpers
(`ARRAY_DTYPE`, `ARRAY_ORDER`, `require_raw_media`, `require_references`,
`require_storage`, `resolve_component_references`, `restore_components`)
directly from the PRIVATE `...field._storage` via a level-3 relative import.

Chosen fix (the brief's preferred option): route `focus_evidence.py` through
the field package's intended seam. `src/metacraft_next/field/evidence.py`
already imported every one of those names from `_storage` for its own use, so
`focus_evidence.py` now imports them from `...field.evidence` instead. No
cycle is introduced (field.evidence depends only on `field._storage`,
`field.sample`, and `authority`), and field's PUBLIC `__all__` is unchanged:
the helpers stay field-internal and are reached by explicit name, not through
star-export. After this change NO science (or any non-field) module imports
`field._storage`; the only importer of `_storage` is `field/evidence.py`
itself, inside the field package.

The ratchet `test_only_local_evidence_admission_crosses_the_field_internals`
(in `tests/architecture/test_sonnet_architecture.py`) was rewritten:

- detection moved into `_field_internal_module(node)`, which catches every
  relative level `>= 2` into `field.<sub>` plus absolute
  `metacraft_next.field.<sub>` forms (the previous `level == 2` predicate
  omitted level-3 reaches entirely);
- the allowlist now names EVERY legitimate seam importer exactly:
  `_local/application.py:field.evidence`, `science/metalens/aperture.py:field.sample`,
  `science/metalens/focus_evidence.py:field.evidence`,
  `science/metalens/focus_evidence.py:field.sample`, and
  `science/metalens/result.py:field.evidence`. Tightening surfaced these four
  additional legitimate public-seam crossings that the level-2 ratchet had been
  blind to; they are named rather than silently allowed;
- a new `test_a_synthetic_forbidden_field_storage_importer_is_caught` proves a
  new level-3 `from ...field._storage import ...` reach is detected and is not
  in the allowed-module set.

Decision rationale: the brief sketched the tightening as surfacing "ONE real
reach" (the `field._storage` defect). Tightening the COMPREHENSIVE ratchet (all
`field.<sub>`) also surfaces four pre-existing legitimate public-seam crossings
(`field.sample`/`field.evidence`) that the level-2 ratchet had missed. Rather
than narrow the watch to `field._*` only (which would have lost the existing
seam coverage and understated the true crossing surface), the comprehensive
form was kept and every legitimate importer is named exactly. This satisfies
the spec's "name every allowed private importer exactly" and "Tests do not
claim a seam is closed while omitting a relative-import level."

### (B) Orphaned geometric observation decoder deleted

`src/metacraft_next/solvers/lumerical_fdtd/evidence.py` contained
`_decode_geometric_observation`, dead because the live geometric decode path
uses `GeometricBasisObservation.from_mapping`. A repository-wide audit
(`src/`, `tests/`, `rust/`) found ZERO callers of `_decode_geometric_observation`.

Deleted (all EXCLUSIVELY orphaned by the decoder's removal — each was verified
to have no surviving caller in production or tests):

- `_decode_geometric_observation`;
- `_complex_value`, `_geometric_candidate`, `_polarized_channel`,
  `_execution_record` (called only from the dead decoder; the like-named
  `_geometric_candidate` in `sweep.py` is a separate, still-used function);
- `_mapping`, `_boolean`, `_integer` (every call site of these three lived
  inside the dead block; the parallel helpers in `aperture.py`,
  `propagation_phase.py`, `sweep.py`, and `template/periodic.py` are separate
  module-local functions and were not touched);
- orphaned imports `from decimal import Decimal`,
  `from ...science.metalens.aperture import Ellipse, Rectangle`,
  `from .adapter import ExecutionRecord`, and the names `ComplexValue`,
  `GeometricObservation`, `PolarizedChannel` from the `.sweep` import block.

No test exercised the dead decoder; no test was removed. A new architecture
ratchet `test_the_geometric_observation_decoder_is_retired` scans production
for the retired function names so the decoder cannot return.

### (C) Stale tests with non-canonical hashes fixed

Ticket 02 made `Reference.from_mapping` / `_require_hash` reject any hash that
is not `sha256:` + 64 lowercase hex. Several tests fabricated references with
`content_hash=f"sha256:{name}"` / `metadata_content_hash=f"sha256:metadata-{name}"`
(non-canonical), which survived direct construction but failed any round-trip
through `from_mapping`.

Every such helper was made to emit a canonical hash derived deterministically
from the name (`hashlib.sha256(name.encode()).hexdigest()`). TEST-ONLY changes;
ticket 02's strict decoder was not weakened. Files touched:

- `tests/advice/test_adviser.py`, `tests/lumerical_fixtures.py`,
  `tests/science/test_aperture.py`, `tests/science/test_geometric_cell_choice.py`,
  `tests/science/test_geometric_phase_sets.py`, `tests/science/test_height_choice.py`,
  `tests/science/test_metalens_aperture.py`, `tests/science/test_propagation_phase_sets.py`,
  `tests/science/test_standard_studies.py`, `tests/solvers/test_geometric_sweep.py`,
  `tests/solvers/test_lumerical_dispatch_gather.py`, `tests/solvers/test_ticket07_work_life.py`
  (each gained a local `_reference_hash` helper);
- `tests/derivations/phase_envelope.py`, `tests/science/test_propagation_envelope.py`,
  `tests/solvers/test_propagation_evidence.py` (envelope/candidate-shaped
  fabrications);
- `tests/solvers/test_lumerical_material_sample.py` (positional
  `Reference("sha256:binding", ...)` literal → canonical).

`tests/authority/test_strict_decoding.py` and
`tests/authority/test_view_values.py::test_from_mapping_rejects_malformed_nested_entries`
intentionally use malformed hashes to prove rejection; they were left intact.

### Verified prior-closure mechanics (not restructured)

- Common metalens proof tail / schema ownership: the existing
  `test_one_production_module_owns_each_schema_literal` ratchet still holds
  (one owner per `*_SCHEMA`); no duplicate proof-tail declaration appears.
- Binary component mapping / storage descriptors: `field/_storage.py` remains
  the single private owner; `tests/field/test_shared_field_storage.py` passes;
  no non-field module imports `field._storage`.
- Shared-context validation on replay (ticket 03):
  `_local/replay.py::_validate_shared_context` is in place and exercised.
- Field and FocalRegion keep distinct public schemas (`FIELD_SCHEMA` vs
  `FOCAL_REGION_SCHEMA`) and distinct restore paths.

### Planning records reconciled

- `.scratch/authority-and-science-sonnet-closure/spec.md` — Status: superseded
  by `../sonnet-performance-and-reliability/spec.md` (tickets 01–09 implemented
  2026-07-29).
- `.scratch/authority-and-science-sonnet-closure/map.md` — "Road completed
  (2026-07-29): tickets 01–09 were implemented…".
- `.scratch/metalens-sonnet-convergence/issues/10-run-the-canonical-live-delivery.md`
  — Status: wontfix, superseded by ticket 06.

This effort's Tickets 01–05 are resolved at `f3efe39`, `cfb42b5`, `dd5bff7`,
`6337676`, and `aa30da2`/`ca90c27`. Ticket 06 remains `ready-for-human`,
blocked by explicit approval of the live flags.

The terminal closure reconciled these lifecycle lines with the implemented
Git history; no live state was inferred from the non-live baseline.

## Gates (real commands and counts)

Worktree root for every command: `E:/Year2026_Project_MetaCraft/code/.worktrees/ticket-05`.
Python interpreter: `C:\Users\Administrator\miniforge3\envs\research_env\python.exe`.

### Complete non-live suite

```
PYTHONPATH=<worktree>/src <py> -m pytest -q --tb=short -p no:cacheprovider \
  -m "not integration and not lumerical_live and not advice_live and not lumerical_delivery"
```

Result: **649 passed, 15 deselected, 0 failed, 0 unexpected skips** in 40.09 s.
Exit code 0. (The 15 deselected carry the live markers named above.)

### Pyright

```
<py> -m pyright src/metacraft_next
```

Result: **0 errors, 0 warnings, 0 informations**. Exit code 0.

### CSU on every touched production file

```
csu.exe check <file> --format json --output .csu/ticket05-<name>.json --no-history
```

Files: `src/metacraft_next/science/metalens/focus_evidence.py`,
`src/metacraft_next/solvers/lumerical_fdtd/evidence.py`.

Result: each **exit 0**, zero `blocks:true` findings.

### Architecture ratchets (focused)

```
<py> -m pytest -q -p no:cacheprovider tests/architecture/ tests/field/test_shared_field_storage.py \
  -k "field_internals or forbidden_field_storage or geometric_observation_decoder or \
      periodic_full_wave or string_classified or schema_literal or retired_modules or \
      markdown_link or shared_field or conduct_owns or record_hook"
```

Result: **22 passed**, 49 deselected. Includes: field ratchet (level `>= 2`
with exact allowlist), synthetic forbidden `field._storage` importer, retired
geometric decoder scan, retired `periodic_full_wave_response` name, no
string-classified expected failures, single schema owner, retired modules, the
tracked-Markdown link resolver, shared field storage, and the conduct/record
frontier ownership ratchets.

### Rust source-manifest verification + no-change audit

```
<py> -m pytest -q -p no:cacheprovider -k "rust_tree_matches or rust_source_names"
```

Result: **2 passed** (`test_rust_tree_matches_the_committed_source_manifest`,
`test_rust_source_names_only_authority_concerns`), 662 deselected.

Rust production change after ticket 01:

```
git diff f3efe39..HEAD -- rust
```

Result: **0 lines** (empty). Rust remained frozen at this effort's ticket 01
head `f3efe39`. The later terminal convergence made one final authorised Rust
change at `0c64fce`; production Rust is frozen from that commit onward.

### Tracked Markdown link validation

Covered by `test_every_tracked_local_markdown_link_resolves`
(`tests/architecture/test_ticket09_ratchets.py`), part of the passing full
suite and the focused architecture run.

### `git diff --check`

Result: **exit 0** (clean). Only CRLF→LF normalization notices from Windows
`autocrlf`, which are not whitespace errors.

### Clean-status review

`docs/2026年7月14日组会.pptx` and `docs/presentations/` remain UNTRACKED and
UNTOUCHED (not staged, not modified). No user file was touched by this ticket.

## Files changed

Production (2):

- `src/metacraft_next/science/metalens/focus_evidence.py` — route storage
  helpers through `...field.evidence` instead of the private `...field._storage`.
- `src/metacraft_next/solvers/lumerical_fdtd/evidence.py` — delete the dead
  `_decode_geometric_observation` and its exclusively orphaned helpers and
  imports (−180 lines).

Tests (17):

- `tests/architecture/test_sonnet_architecture.py` — rewrite the field
  ratchet, add the synthetic forbidden-importer test, add the retired-decoder
  scan.
- 14 `_reference(...)`/envelope/material helper files — canonical hashes only.
- (No test was deleted; no test was weakened.)

Total: 19 files changed, 192 insertions(+), 231 deletions(-).

## Self-review

- No common science base class, generic registry, storage framework, PUBLIC
  field-internals Interface, compatibility alias, new result schema, broad
  naming campaign, or live solver test was introduced.
- Field's public `__all__` was not widened; storage helpers stay field-internal.
- No working code was restructured: one import was re-routed to an existing
  seam, dead code was deleted, and tests were repaired to emit canonical hashes.
- Rust is unchanged after ticket 01.
- One coherent commit on the branch.

## Concerns

None blocking. One judgment call worth flagging for the reviewer: the
comprehensive field ratchet (all `field.<sub>` importers) was kept and its
allowlist expanded to five entries rather than narrowing the watch to
`field._*` only; this is the stronger, more truthful form and is documented
above under (A).
