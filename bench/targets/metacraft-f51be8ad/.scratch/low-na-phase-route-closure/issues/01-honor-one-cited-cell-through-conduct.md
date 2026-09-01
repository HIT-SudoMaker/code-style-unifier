# 01 — Honor one cited cell through conduct

**Type:** implementation

**Status:** wontfix

**Superseded by:** [Metalens Sonnet convergence](../../metalens-sonnet-convergence/spec.md).

**Blocked by:** none.

## Outcome

A propagation-phase brief may cite one physical period and one atom height.
Those facts survive compilation, admission, fake-solver evidence, matching,
Field formation, and Result replay without being replaced by a generated
sampling value or synthetic advice.

The Johansen 2024 circular-pillar example is the tracer bullet.

## What to build

- Add optional `cell_period_nm` and `atom_height_nm` constraints to the brief.
  The compiled design resolves one required physical period while retaining
  the unfloored sampling ceiling separately as a canonical `Decimal`.
- Validate an explicit integer period against the unfloored ceiling. Use
  `floor_10nm(sampling ceiling)` only as the absent-period default.
- Let an explicit height form the singleton height domain even when it lies
  outside the route's default height prior. Request height advice only when
  the brief leaves height open.
- Introduce one discriminated height basis: `brief constraint` or
  `height advice`. Remove the assumption that every HeightChoice, CellChoice,
  and Result owns an advice reference.
- Keep an explicit propagation height behind the admitted phase envelope and
  its certified exclusions; forecasts and advice cannot replace it.
- Use the physical period, not the sampling ceiling, for aperture placement,
  aperture-intent validation, unit-cell construction, evidence identity, and
  provenance.
- Preserve the current ADR 0007 period derivation when no explicit period is
  supplied.
- Make later values cite the admitted height choice rather than copying its
  domain and optional advice references.
- Carry the cited circular-pillar shape through the existing propagation
  route; do not create a paper-specific workflow.

## TDD seam

Begin at `conduct` with the Johansen brief and deterministic fake capacity and
solver evidence, deliberately supplying no height adviser response. The first
failing test must show the cited period, height, or height basis being lost or
replaced. Lower-level tests may then sharpen validation and provenance.

## Acceptance

- The Johansen example completes independent 8-, 12-, and 16-state fake
  conducts.
- Every admitted document and replayed Result reports the cited physical
  period and height.
- A sampling ceiling of 857.5 nm accepts an explicit 857 nm period, derives an
  850 nm default when omitted, and returns a typed `height_domain` refusal for
  an explicit 858 nm period without a binary-float comparison or solver
  dispatch.
- An absent period still follows the established default derivation.
- An explicit height outside the default route prior can be admitted after
  physical validation.
- An absent height still enters height advice; an explicit height does not.
- Existing advice-based propagation and geometric briefs still complete fake
  conduct and retain their exact advice provenance.
- Result and CellChoice output never fabricate an advice record for a brief
  constraint.
- Malformed explicit values fail brief validation; well-formed but
  inapplicable constraints become typed findings before solver dispatch.
- The Rust tree is byte-for-byte untouched.
- Focused tests, architecture tests, Pyright, and CSU on touched files pass.

## Do not add

- A new Rust state or `period choice` state.
- Nullable advice references scattered through downstream result types.
- A Johansen workflow, parser, or public type.
- Live Lumerical execution.
- A material catalogue.
- Large-na, optimization, or achromatic behavior.
