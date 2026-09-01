# Harness-native Sonnet hardening deterministic closure

Date: 2026-08-09

Status: deterministically closed

## Boundary

This record closes the deterministic implementation described by `spec.md` and
Tickets 09-16. It makes no claim of live harness usability, Native execution,
scientific performance, harness parity, release readiness, or paper
reproduction. No Codex, Claude Code, Lumerical, integration, delivery, canary,
Native, network, paid, or real solver execution was opened by this seal.

## Implementation inventory

The implementation and its deterministic seal contain these 29 files. The
first 28 were present before this closure record was created.

Canonical prose:

- `DESIGN.md`
- `DEVELOPMENT.md`
- `SCIENCE.md`

Production:

- `src/metacraft/science/conduct.py`
- `src/metacraft/science/metalens/_closed_advice.py`
- `src/metacraft/science/metalens/conduct.py`
- `src/metacraft/science/metalens/consultation.py`
- `src/metacraft/science/metalens/evidence.py`
- `src/metacraft/science/metalens/height_advice.py`
- `src/metacraft/science/metalens/period_advice.py`

Tests, acceptance support, recordings, and ratchets:

- `tests/harness_acceptance.py`
- `tests/harness_acceptance_runner.py`
- `tests/acceptance/test_harness_acceptance.py`
- `tests/acceptance/test_harness_campaign.py`
- `tests/acceptance/test_retained_harness_evidence.py`
- `tests/acceptance/fixtures/harness/README.md`
- `tests/acceptance/fixtures/harness/codex-native.jsonl`
- `tests/acceptance/fixtures/harness/claude-native.jsonl`
- `tests/architecture/test_runtime_import_dag.py`
- `tests/architecture/test_sonnet_ratchets.py`
- `tests/command/test_conduct_command.py`
- `tests/science/test_advice_replay.py`
- `tests/science/test_closed_advice.py`
- `tests/science/test_conduct.py`
- `tests/science/test_height_choice.py`
- `tests/science/test_height_consultation.py`
- `tests/science/test_period_consultation.py`
- `tests/science/test_period_height_domain.py`

Seal record:

- `.scratch/harness-sonnet-hardening/closure.md`

## Planning inventory

The following owner-approved planning work is visible in the total worktree
but is not implementation code or canonical product documentation:

- `.scratch/INDEX.md`
- `.scratch/harness-sonnet-hardening/spec.md`
- `.scratch/harness-sonnet-hardening/map.md`
- `.scratch/harness-sonnet-hardening/issues/01-*.md` through
  `.scratch/harness-sonnet-hardening/issues/16-*.md`

The map and index were not edited by Tickets 09-16 or by this seal. Ticket
lifecycle and review comments remain planning provenance.

## Deletion inventory

There are no whole-file deletions. The movement deleted these superseded
execution roads without compatibility wrappers:

- the duplicated `_period_conclusion` and `_height_conclusion` restorers and
  both copies of `_indexed_values`, `_mapping`, `_text`, and `_text_list`;
- the old broad consultation `ValueError` translation scope, while moving the
  sole typed `InvalidMetalensConsultationAnswer` owner from metalens conduct to
  metalens consultation;
- the harness-string support functions `prepare_capsule`,
  `harness_environment`, `codex_arguments`, `claude_arguments`,
  `audit_transcript`, `_event_shape_violation`,
  `_codex_event_shape_violation`, `_collect_event_accesses`,
  `_installed_harness_command`, `_audit_codex_command`, and runner
  `_explanation`;
- the `--correct-audits` and `--correct-retained-evidence` modes, both
  correction writers, `_retained_codex_capsule`, `_retained_claude_capsule`,
  and their correction-only `re` import.

The retained runner methods `preflight`, `run_matrix`, `_run_once`, and
`classify_acceptance` were replaced at their existing ownership seam and are
not counted as deletions.

## Retained evidence identity

Ticket 12 recorded both its before and after snapshot as 42 files with whole-
tree SHA-256
`50145dc009658ce518c52b57fa4ab0c6fbe4628414d8ccaa337f414df67c223b`.
This seal independently recomputed the same count and digest before testing,
and `git diff --exit-code --
.scratch/harness-native-consultation/acceptance/07` returned zero.

The exact tree recipe resolves `acceptance/07`, recursively selects files,
forms slash-normalized paths relative to that root, records each row as
`path<TAB>byte-size<TAB>lowercase-file-sha256`, sorts by path, joins rows with
LF and no trailing newline, encodes that canonical string as UTF-8 without a
BOM, and hashes those bytes with SHA-256.

The read-only retained verifier passed 7 tests in 8.03 seconds. It opened no
harness and wrote no retained artifact.

## Deterministic verification

Every Python command used:

```text
C:\Users\Administrator\miniforge3\envs\research_env\python.exe
```

Focused Interfaces:

```powershell
& $projectPython -m pytest -q --tb=short -p no:cacheprovider `
  tests/science/test_closed_advice.py `
  tests/science/test_period_consultation.py `
  tests/science/test_height_consultation.py `
  tests/science/test_period_height_domain.py `
  tests/science/test_height_choice.py `
  tests/science/test_advice_replay.py `
  tests/science/test_conduct.py `
  tests/science/test_study_codec.py `
  tests/command/test_conduct_command.py `
  tests/acceptance/test_retained_harness_evidence.py `
  tests/acceptance/test_harness_acceptance.py `
  tests/acceptance/test_harness_campaign.py
```

Result: 272 passed, 0 deselected, 0 skipped in 73.68 seconds.

Full deterministic non-live suite:

```powershell
& $projectPython -m pytest -q --tb=short -p no:cacheprovider `
  -m "not integration and not lumerical_live and not lumerical_delivery and not lumerical_canary"
```

Result: 1,463 passed, 5 intentionally deselected, 0 skipped in 402.55
seconds. The five deselected tests are excluded evidence, not passes.

Full project type check:

```powershell
& $projectPython -m pyright
```

Result: 0 errors, 0 warnings, 0 informations.

Complete architecture suite:

```powershell
& $projectPython -m pytest -q -p no:cacheprovider tests/architecture
```

Result: 118 passed in 17.06 seconds.

Canonical Markdown-link ratchet:

```powershell
& $projectPython -m pytest -q -p no:cacheprovider `
  tests/architecture/test_sonnet_ratchets.py::test_every_versionable_local_markdown_link_resolves
```

Pre-record result: 1 passed in 1.78 seconds. The same canonical entry is run
again after this record is complete; no proxy is used.

Domain naming:

```powershell
& $projectPython -m pytest -q -p no:cacheprovider `
  tests/architecture/test_domain_naming.py
```

Result: 10 passed in 0.96 seconds.

Full CSU source analysis:

```powershell
.\csu\bin\csu.exe check src\metacraft --format json `
  --output .csu\report.json --no-history
```

Result: 4,609 total findings, 0 blocking findings, and 4,609 non-blocking
`under_review` findings. The non-blocking review inventory is retained
honestly and is not described as zero findings. The ignored
`.csu/report.json` is not an implementation artifact.

## Source and scope audit

The private `_closed_advice` Module is imported only by `period_advice.py` and
`height_advice.py`. Production contains no acceptance profile symbol. The
active runner contains no correction flag, correction writer, or retained-
capsule recovery helper. `git diff --diff-filter=D --name-status` reported no
file deletion, and `git diff --check` passed before this record was created.

The implementation diff contains no change under `rust`, `examples`,
`src/metacraft/solvers`, `tests/live`, retained `acceptance/07`, `CONTEXT.md`,
or ADR 0021. No benchmark, Authority, Native, solver, retained artifact, map,
or index change belongs to the implementation.

## Final post-record checks

After this record was created, the canonical Markdown-link entry passed 1 test
in 1.66 seconds, `git diff --check` passed, the excluded implementation scope
remained empty, and the retained tree remained 42 files with SHA-256
`50145dc009658ce518c52b57fa4ab0c6fbe4628414d8ccaa337f414df67c223b`
and an empty Git diff. After the Ticket 16 lifecycle note was completed, the
same canonical Markdown entry passed 1 test in 1.70 seconds; whitespace,
retained identity, excluded scope, and final worktree inventory checks all
passed again.
