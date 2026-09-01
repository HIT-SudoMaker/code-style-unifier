# 20 — One coverage law, independent quantizations, period-hooked step

**Type:** implementation (spec phase 2)

**Status:** wontfix

**Superseded by:** [Metalens Sonnet convergence ticket 05](../../metalens-sonnet-convergence/issues/05-let-aperture-arrange-one-metalens-field.md).

**What to build:** Extract the full three-stage coverage predicate into
`science/phase.py`: `uniform_targets(levels)`, `level_tolerance(levels)`,
`covers_uniform_levels(phases, levels)` — per-target existence AND distinct
assignment via a private bipartite matcher. `_form_phase_set` calls it first
and keeps its loss-weighted selection; the post-assignment recheck degrades
to an assertion. The names join `phase.__all__` only. `form_phase_sets`
makes the 8/12/16 quantizations independently satisfiable — deliver what
proves and report the rest. A partial formation is recorded in every
delivered propagation result as one `quantizations` block with `delivered`
and `refused` entries; an all-refused formation remains a typed finding on
the unfinished study. Every refusal payload is arithmetic fact only (counts
and the failed formation reason — no inverse recommendations or adviser
prose).
The lateral step becomes a period-hooked policy: propagation 5 nm below a
300 nm physical period, 10 nm otherwise; geometric 10 nm below 300 nm,
20 nm otherwise.

**Acceptance:**

- Public-seam test
  `test_admitted_phase_sets_close_only_their_quantization` visibly admits the
  synthetic library and successful phase-set documents through typed
  `Authority`, reopens and checks the workspace, then recompiles: only the
  quantizations with admitted phase sets close; partial refusals remain in
  the final result report, while an all-refused formation remains an explicit
  finding.
- Predicate unit tests include an existence-passes-but-matching-fails case;
  Decimal comparison stays `cyclic_distance`-only, and a byte-neutrality
  test proves no admitted document changes from the extraction alone.
- **Benchmark expectations, not acceptance answers:** arithmetic tests
  guarantee candidate counts only; synthetic-response fixtures prove the
  independent-quantization algorithm delivers some quantizations while
  refusing others; whether a real phase set forms is decided by live FDTD
  evidence. The recorded expectations (355 nm propagation: 8/12 plus a
  refused 16; 400 nm propagation: all three) are benchmarks to compare
  against and report on, never targets to tune toward.
- `science.__all__` untouched; touched files leave `csu check` with zero
  hard violations.

Decisions: tickets 06, 10, 14, 16, 29.
