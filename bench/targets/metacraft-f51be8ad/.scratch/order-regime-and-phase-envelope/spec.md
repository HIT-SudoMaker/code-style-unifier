# Order regime and phase envelope

Status: superseded by ../metalens-sonnet-convergence/spec.md

This spec remains an audit record. The map
(`.scratch/order-regime-and-phase-envelope/map.md`) is the audit archive of
the decisions behind it; implementation tickets are 18-23 and 31-33.

## Problem Statement

The 355 nm propagation sweep ran at a 630 nm period — the Nyquist sampling
bound — inside the multi-order regime: nine propagating transmitted orders,
zeroth-order power down to 0.37%. Ticket 17 verified the extraction path
bit-for-bit, so the recorded phase truly is the G0 coefficient of a
multi-order field. That coefficient is valid for its declared channel, but it
cannot stand for the complete transmitted field or total efficiency. The
compiler cannot classify this risk alone because it needs an evidence-backed
refractive index.

Two further costs surfaced while diagnosing this. Every sweep pays two
Lumerical session round-trips per candidate (~38 s of a ~100 s budget), and
nothing before the sweep can say that a height is hopeless, so a doomed
configuration burns a full sweep before refusing.

## Solution

Three layers. Seventeen closed decision tickets and ADRs 0005 and 0007 stand
behind them; ADR 0007 supersedes only ADR 0005's hard period cap. The seven
post-review tightenings below are contract, not commentary.

**Layer 1 — order-aware evidence.** Solver-native refractive indices are
sampled at qualification (`getindex` over a registered wavelength grid,
recorded with fit targets and the `|getfdtdindex - getindex|` residual
together with the exact `(fmin, fmax)` span the residual was computed
under) into a separate admitted document citing the solver binding. The
reference chain is replayable from authority alone after any restart:

`solver binding <- material sample <- material binding <- height domain`

The height domain gains `requires material_binding` on both metalens routes
and owns the only physical cell period: the floored `sampling ceiling`
(Nyquist). It derives the `order ceiling` (`lambda/(n_sub+NA)`) from the
material sample only to classify the `order regime` (ADR 0007).
`multi order` produces the non-blocking `higher orders possible` caution; it
never shrinks the period or refuses work. **Period ownership is exclusive:**
the compiler's field is renamed
`sampling_ceiling_nm`; the height choice carries the physical period; every
downstream consumer — cell construction, sweeps, results — reads the period
from the choice or the domain, never from the compiler ceiling, and an
architecture test forbids the ceiling from reaching solver construction.
An empty fabrication domain remains a finding on an unfinished study, never
an exception; it is not an order-regime refusal.

**Layer 2 — the phase envelope.** A pure-Python, zero-solver forecast in
`science/routes/propagation_envelope.py`, one public verb:
`estimate_phase_envelope(domain, contrast) -> PhaseEnvelope`. Its evidence
semantics are narrow by construction: **it closes only the claim that the
envelope has been established; it never closes periodic transmission, cell
library, or phase set, and it never claims coverage.** Three verdict tiers:
arithmetic exclusion (hard, per quantization); bounded exclusion (hard,
currently only from the elementary material interval
`ambient index <= axial index <= pillar index`); and model estimates that
report numbers but never verdicts. Primary-source review recorded in
`docs/research/2026-07-26-phase-envelope-certified-roots.md` found exact
HE11 and Rytov equations but no published proof that they bound the real
two-dimensional periodic pillar array. They therefore remain named forecast
models, not hard bounds. Ordinary floating-point special functions are not
certified numerics either. Until both gaps are closed, the deliberately loose
material interval is the only bounded-exclusion authority. The
coverage predicate it applies is the production predicate, extracted whole
into the shared phase module — forecast and judgement share one law.
`PhaseEnvelope.source_references` contains references only. One global
`bound_checks` block records the certified endpoint and ordering checks with
their supporting values; it is never repeated per height. A missing, failed,
or uncertified check permits reported numbers but forbids a bounded-exclusion
verdict.

Advice sits behind the envelope with one meaning per verb: the compiler
emits an advice finding when the height-choice obligation is ready without
bound advice; the application seam answers the finding — consults the
adviser with the brief, the admitted domain, and the admitted envelope,
admits the advice, and recompiles; `choose_height` always and only chooses,
deterministically. A recommendation naming a ruled-out height yields the
finding `height_advice_ruled_out`, never a silent substitution.
The Adviser Interface remains one verb:
`recommend_height(brief, domain, *, envelope: PhaseEnvelope | None = None)`.
Propagation requires the exact admitted envelope; geometric requires no
envelope and rejects one if supplied.

**Layer 3 — throughput.** The Lumerical Adapter may keep one hidden product
session across build, engine solve, and result load only when the workstation
owns that process tree's placement, containment, and memory accounting for its
complete lifetime. Otherwise the established two-session lifecycle remains.
No GUI Module or GUI-specific Interface enters the architecture;
`lumerical_gui` remains only a native licence-feature name. Ticket 09 measured
separate 500-seat licence pools (`lumerical_gui` / `lumerical_solve`), but
licence independence never creates a workstation exception. Project bytes are
unchanged. The run manifest carries the physical period, order regime, and
any non-blocking caution as the factual record; directory names may echo them
for readability only.

The quantizations become independently satisfiable, and the lateral step
becomes a period-hooked fabrication granularity. **Benchmark expectations,
not acceptance answers:** arithmetic tests guarantee candidate counts only;
synthetic fixtures prove the independent-quantization algorithm; whether a
real phase set forms is decided by live FDTD evidence. The recorded
expectations — 355 nm propagation delivers 8/12 and refuses 16; 355 nm
geometric feasible (the geometric showcase); 400 nm propagation delivers
all three; 400 nm geometric feasible — are benchmarks to compare against,
never targets to tune toward. No brief changes.

## Standing constraints

- Rust is frozen; everything lands behind the four authority verbs.
- The envelope starts no external process.
- `canonical.py` rejects floats — every emitted number is a Decimal or a
  formatted string.
- Sonnet standard with CSU as the lower bound: every touched file leaves
  `csu check` with zero hard violations, including pre-existing ones.
  Repo-wide cleanup is out of scope.
- Terminology per the revised `CONTEXT.md`; avoided: `single order`,
  `admissible period`, `n_eff`.
- Any future HE11 or Rytov forecast fixture must be independently derived,
  reviewed, and non-authorizing. It may not silently replace the material
  interval used by the hard tier.

## Phases and tickets

Phase 1, evidence core: tickets 18, 19.
Phase 2, coverage law: ticket 20 (after 19).
Phase 3, phase envelope: tickets 21, 22 (after 18-20).
Phase 4, throughput and run legibility: ticket 23. Manifest work is
independent; session reuse remains conditional on the workstation contract.

Phase 5, propagation closure: ticket 31 carries the brief's circular or
square atom through construction and readback; ticket 32 proves one standard
propagation brief from compilation through the admitted focus result.

Phase 6, external validation: ticket 33 compares primary papers and proposes
one exact reproduction brief for human review. A paper validates this
architecture; it does not redefine the core rules.

Each ticket is one vertical slice through the public authority seam, with
live Lumerical checks separately marked, and no task advancing until its
evidence is admitted. The shared acceptance grammar is
`exact source -> decide -> reopen -> recompile -> one consequence`; only the
temporary workspace path is shared. Admission, replay, and interpretation
remain visible in each ticket's test body rather than hidden behind a seam
harness.
