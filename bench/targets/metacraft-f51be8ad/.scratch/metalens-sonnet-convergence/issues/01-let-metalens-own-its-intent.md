# 01 — Let metalens own its intent

Type: implementation

Status: resolved (2026-07-28)

Blocked by: a reviewed baseline checkpoint commit.

## Outcome

Shared science names the lifecycle. Metalens science owns every intent and
applicability term that has meaning only for a focusing metalens.

## What to build

- Introduce `science/metalens/` as the aim-local package.
- Move `MetalensBrief`, its atom/aperture/fabrication intent,
  `MetalensDesign`, `ControlStrategy`, and `ApertureRegime` into that package.
- Keep generic `Brief`, `Design`, `Aim`, claims, methods, route, proof, task,
  and study language in shared science.
- Make `ApertureRegime` a required fact of `MetalensDesign` only.
- Keep the four canonical `Aim` values, but remove speculative holographic,
  quasi-BIC, frequency-selective, and large-na proof fixtures.
- Return `AimUnavailable` when no terminal proof is implemented and
  `MethodUnavailable` when metalens has no applicable method.
- Keep `Finding` inside an existing proof; do not add a method or aim finding
  merely to carry a compilation refusal.
- Move the real low-na metalens relationships under metalens ownership.
- Update `SCIENCE.md`, public exports, and architecture tests to agree with
  ADR 0010 and the accepted glossary.
- Migrate imports atomically and delete the retired paths; add no aliases.

## TDD seam

Begin at the pure compilation Interface:

1. compile one propagation-phase metalens brief;
2. compile one geometric-phase metalens brief;
3. compile one declared but unimplemented aim and receive `AimUnavailable`;
4. compile one large-na metalens request and receive `MethodUnavailable`;
5. prove canonical recompilation is byte-stable.

The two current low-na studies must preserve their scientific proof meaning.

## Acceptance

- `ApertureRegime` is available from metalens science and absent from generic
  `science.__all__`.
- Generic `Design` has no optional aperture-regime field.
- No unimplemented aim owns claims, methods, fake evidence, or a golden proof
  graph.
- Large na remains explicit planned research without a fake Study.
- Current low-na propagation and geometric compilation remains deterministic.
- No `routes` package, solver product, or provider is introduced by this
  ownership change.
- Focused compiler and architecture tests pass.
- Pyright reports zero errors; touched files have zero CSU hard violations.
- `git diff -- rust` is empty.

## Do not add

Do not add empty aim packages, a generic aim registry, an optional-field
universal Design, compatibility imports, or any large-na calculation.
