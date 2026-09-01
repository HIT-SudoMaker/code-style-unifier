# Handoff to Codex — metalens-sonnet-convergence (tickets 05A–10)

> **Superseded (2026-07-29).** This handoff is historical evidence of the
> prior metalens-sonnet-convergence effort. The active implementation road is
> now [`../authority-and-science-sonnet-closure/spec.md`](../authority-and-science-sonnet-closure/spec.md),
> whose tickets 01–09 are committed on `main`. Read what follows as the
> superseded plan, not current guidance.

Status: tickets 01–05 are implemented and committed on `main`, but independent
review found ownership, reference, and test-hygiene gaps. Ticket 05A repairs
those gaps before Codex continues with tickets 06–10.

This is a **deletion-style convergence** of an already-complete earlier
implementation into the Sonnet architecture defined by
`spec.md` + ADR 0010 + ADR 0011. The working tree at baseline `addc3e5` was a
full, green implementation of the *prior* architecture. Tickets refactor and
narrow it, reusing existing capability — they do not rebuild it.

## Execution model (follow exactly)

One subagent per ticket, in this order, blocked by the spec's edges:

```
05A (conformance repair)
  → 06 (Field/focus)
  → 07 (Lumerical)
  → 08 (Result/replay + retire routes)
  → 09 (ratchet)
  → 10 (human-enabled live delivery)
```

Per ticket:
1. Dispatch a subagent with the ticket file, the spec, ADR 0010/0011, the
   audit gaps below, and a **strict scope boundary** (do not absorb later
   tickets' work — the spec's "Delivery discipline" forbids it).
2. The subagent implements TDD (red → green), must NOT `git commit`.
3. Main agent **independently verifies** before committing:
   - full non-live suite via the research_env python (see Environment)
   - `pyright` → 0 errors, 0 warnings
   - `git diff -- rust` → empty
   - structural/boundary grep checks (see each ticket below)
   - **0 skipped** tests (the suite must have `0 skipped`; `15 deselected` is
     the live-marker baseline). Investigate any `skipped`.
4. Commit one ticket per commit with a message naming the ticket, the change,
   the scope boundary respected, and the verification numbers.

### Anti-patterns observed in earlier subagents (tell yours to avoid)
- **Do not `git stash` to compare baselines** — it perturbs pytest marker
  counts and produces phantom `skipped`/deselected noise. Use
  `git show <commit>:<path>` to read historical file content.
- **Run the FULL non-live suite, not a focused slice**, before reporting done.
- Do not let `.serena/` or `tests/science/unused/workspace.*` get staged; the
  ticket-04 commit accidentally included `.serena/project.yml`. Ticket 09
  should add `.serena/` to `.gitignore` and `git rm --cached` it.
- Run the repository CSU binary on every touched production file and require
  zero hard violations. Do not substitute Pyright or architecture tests for
  this gate.

## Environment

- Repo root: `E:/Year2026_Project_MetaCraft/code`
- Python: **always** `C:/Users/Administrator/miniforge3/envs/research_env/python.exe`
  (Python 3.12; pytest 9.0.3, torch 2.12, pyright 1.1.411). base python has no
  pytest; terasense_env is 3.10 (too old).
- Non-live suite: `PY=...research_env/python.exe && "$PY" -m pytest -q --tb=short -p no:cacheprovider`
  (pyproject addopts already deselect integration/lumerical_live/advice_live).
- Typecheck: `"$PY" -m pyright`
- Rust extension `src/metacraft_next/_authority.cp312-win_amd64.pyd` is prebuilt;
  never trigger a maturin rebuild. `git diff -- rust` must stay empty.

## Progress so far

| Ticket | Wave | commit | non-live tests | skip/deselect |
|---|---|---|---|---|
| baseline | — | `addc3e5` | 295 | 15 deselected |
| 01 metalens owns intent | 1 | `29e213a` | 304 | 0 skip / 15 desel |
| 02 proof/task identity | 1 | `070c0d7` | 313 | 0 skip / 15 desel |
| 03 period before height | 2 | `fc9e5e9` | 317 | 0 skip / 15 desel |
| 04 adviser inward | 2 | `590bace` | 318 | 0 skip / 15 desel |
| 05 aperture | 3 | `c5e18fb` | 326 | 0 skip / 15 desel |

After 05, `science/metalens/` owns: brief, design, relationship, period,
height, material, propagation_envelope, period_advice, height_advice,
aperture (new in 05).

## Remaining tickets — audit gaps + scope boundaries

### Ticket 05A — Let each fact have one owner
Spec issue file: `issues/05a-let-each-fact-have-one-owner.md`. Ready now.
It repairs only verified gaps left by tickets 01–05:
- one schema owner beside each value and decoder;
- one authoritative ScientificTask identity;
- exact PeriodDomain and PeriodChoice references through advice and height;
- one complete Aperture owner with vectorized propagation and geometric
  placement;
- one admitted library exercised at 8/12/16 states;
- temporary test workspaces that leave Git status unchanged.

It must not absorb Field/focus, Lumerical, Result/replay, route retirement,
repository-wide naming, or live work.

### Ticket 06 — Let field travel and focus speak once (wave 3)
Spec issue file: `issues/06-let-field-travel-and-focus-speak-once.md`. Blocked
by 05A.
Audit status before convergence: **partial**. Known state after 05:
- `field/__init__.py` still exports metalens focus values (`FocalRegion`,
  `FocusResult`, `HalfMaximum`, `FocusConvergence`, `evaluate_focus`) — these
  must move to metalens; `field/` keeps only reusable `Field` + component
  manifest.
- Angular-spectrum implementation must deepen behind one small Interface that
  owns qualification, spectrum preparation, memory budgeting, component
  propagation, axial survey, local refinement. Callers/tests must not import
  private preparation/batching/refinement.
- Preserve bound Torch realization (CUDA when admitted, Torch CPU otherwise,
  float64/complex128, two-times padding, recorded transform/evanescent
  conventions). No production FFT path on NumPy or four-times padding.
- `evaluate_focus` is the sole owner of focus search, x/y half-max widths,
  depth, transmission, concentration, completeness, applicable leakage. Complete
  `Focus` only when all closing facts bracketed; else admit `FocusSurvey` +
  typed `Finding`. Remove every calculation from `conclude` (including
  geometric retained power/leakage).
- **Boundary**: do not retire `science/routes/` (08); do not change identity
  (02); do not do Lumerical (07). Field evidence already at
  `field/evidence.py` with `FIELD_SCHEMA`/`FOCAL_REGION_SCHEMA`.
- TDD seam: qualify+propagate linear-basis Field; two circular components one
  prepared spectrum each; complete Focus; unbracketed FocusSurvey+Finding;
  applicable Leakage; conclude with Torch+propagation disabled.

### Ticket 07 — Let Lumerical contain one work life (wave 4)
Spec issue file: `issues/07-let-lumerical-contain-one-work-life.md`. Blocked
by 05A.
Audit status: **partial**. Known gaps:
- Rename/deepen product probe to `InstallationProbe`; declare every operation
  dispatch performs (replace `getattr` sniffing in `dispatch.py`).
- Delete dormant `DirectEngine` (`adapter.py`) and its tests.
- `WorkstationExecution` sole production path; hide session creation behind
  `SessionPool` returning `SessionLease`, one private `open_session`.
- Remove public `SessionFactory`, caller-supplied execution/session pairs
  (`open_sweep(execution, session_factory)`, `LumericalSweep.__init__`
  execution/session_factory params), exported fakes.
- `work_identity`/`session_identity`/`lane_identity` independent; reopen session
  on a lane creates new session identity.
- Introduce `WorkRecord` as sole owner of the standard artifact manifest;
  deepen `RunDirectory` so sweep code stops handwriting filenames
  (`sweep.py` before.fsp/after.fsp/construction.json/execution.json/observation.json/solver.log).
- Shrink `lumerical_fdtd.__all__` to the real caller Interface
  (InstallationProbe, WorkstationExecution, SessionPool, SessionLease,
  WorkRecord, RunStore, RunDirectory).
- Preserve physical policy: 4 distinct physical cores, no SMT, one locality
  cell, 16 GiB/lane; caller supplies no worker count.
- **Boundary**: do not retire routes (08); existing templates/mesh/offsets/solve
  behavior scientifically unchanged.

### Ticket 08 — Let Result close and replay exact evidence (wave 5)
Spec issue file: `issues/08-let-result-close-and-replay-exact-evidence.md`.
Blocked by 05A, 06, and 07. **This ticket retires `science/routes/`.**
Audit status: **partial**. Known gaps:
- Keep generic `ResultClosure` in shared science; move metalens conclusion
  values under `science/metalens/`. Retain distinct `PropagationResult` /
  `GeometricResult`. Both through single schema `metacraft.science.metalens.result`.
- Result document stores only conclusion, exact fabrication output, evaluation
  refs, closure ref, origin, replay provenance. Read aim/objectives/strategy/
  regime/proof from cited closure — no second copy. Remove the `"route"` key
  still present in `propagation_result.py`/`geometric_result.py`.
- `conclude` = pure closure validation + immutable assembly. Currently
  `geometric_result.py` computes leakage/power inside conclude — remove; consume
  admitted leakage evidence. `propagation_result.py` calls `assess_phase_sets`
  inside conclude — review.
- Implement Result **replay**: byte-identical conclusion docs from authority
  objects without Adviser/Lumerical/Torch/device/FFT.
- **Retire `science/routes/` package** entirely; remove `interpret` operations
  (`conduct.py`, `_local/application.py`, `_local/propagation.py`,
  `_local/geometric.py`) and `*_operation` suffixes; use common metalens verbs
  `assign_aperture`, `form_field`, `propagate_field`, `evaluate_focus`,
  `conclude`. Delete old Result schema readers and route-shaped replay caches.
- Note: routes/ is down to 6 files after ticket 03 (propagation_envelope moved
  out). `interpret` + `*_operation` are in `_local/*.py`.

### Ticket 09 — Ratchet the Sonnet architecture (wave 5)
Spec issue file: `issues/09-ratchet-the-sonnet-architecture.md`. Blocked by
05A–08.
Audit status: **partial**. Known gaps:
- Responsibility-led naming audit (no `route_*`, `*_operation`,
  manager/handler/processor, public math shorthand, strategy-as-route,
  provider-native vocab where it encodes retired architecture). Keep accurate
  short nouns.
- Remove dead compatibility exports, shallow forwarding modules, obsolete
  tests, speculative future fixtures, unused paths exposed by 01–08.
- Update `CONTEXT.md`, `SCIENCE.md`, `DEVELOPMENT.md`, ADR links to the
  implemented tree.
- Repair dead local Markdown links; preserve historical paths as provenance
  text where no current target exists; never invent a replacement doc.
- Add architecture ratchets for: unchanged Rust; aim-local metalens language;
  cross-aim Field without metalens focus values; no dotted route identities /
  compiler-derived schemas; inward advice deps; narrow Lumerical exports /
  hidden test seams; no speculative future proofs; no old import aliases /
  schema readers.
- Replace tests of retired shallow modules with tests at the deep Interface.
- **Record in this ticket** the exact baseline commit, the final non-live
  passed count, and the verification commands for ticket 10.
- Also: add `.serena/` (and `.spec-workflow/` is already ignored) to
  `.gitignore` + `git rm --cached .serena/`; verify `tests/science/unused/`
  marker handling.
- Final gate (spec): complete non-live suite; one explicitly enabled live
  Adviser check; one bounded native Lumerical smoke; four canonical live briefs
  only with explicit human approval; replay every completed/waiting outcome.

## Ticket 10 — ready-for-human
Live canonical delivery. The user's request to complete tickets 05A–10
authorizes entry only after ticket 09 records a green non-live baseline.
The ticket's staged live flags and stop rule still govern execution.

## Key guardrails (spec "Delivery discipline") — stop and report if a ticket would:
- change Rust; conflict with an admitted ADR; need a compatibility shim;
- pass only by changing brief physics/numerical policy; need a new registry /
  generic framework / public test seam; leave a live solver run incomplete /
  unavailable / scientifically unresolved.
