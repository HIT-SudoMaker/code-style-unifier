# 05A — Let each fact have one owner

Type: repair implementation

Status: resolved (2026-07-28)

Blocked by: tickets 01 through 05.

## Outcome

The first five convergence tickets leave one authoritative representation for
each scientific fact. Advice cites the domain it answers, downstream choices
cite the exact admitted facts they consume, Aperture owns one complete
placement, and the non-live suite leaves the repository unchanged.

## What to repair

- Keep metalens aim ownership and refusal behavior established by ticket 01.
- Place each stable scientific schema beside the value and decoder that own
  it. Remove schema aliases from relationship and shared Result Modules.
- Give `ScientificTask` one authoritative identity representation. Do not
  retain parallel identity fields or free-form copies that can disagree.
- Make `PeriodAdvice` cite the exact `PeriodDomain` it answers.
- Let the period Module own period-limit validation once. Compiler and Adviser
  call that Interface instead of restating the physical rule.
- Derive `HeightDomain` only from the exact admitted `PeriodChoice` in the
  current Study. Cite that choice without copying its period basis.
- Make `Aperture` own the complete circular placement: paired coordinates,
  occupied mask, continuous target phase, stable state identities, spacing,
  radius, and assignment facts.
- Keep propagation assignment finite, deterministic, cyclic at `0 == 2π`,
  and vectorized. Keep geometric assignment continuous from one admitted Cell
  and vectorized without manufactured phase levels.
- Validate that geometric CellChoice and Orientations references belong
  together before an Aperture can be formed.
- Narrow the metalens package Interface to scientific values and operations
  callers genuinely need.
- Replace the fixed test workspace with per-test temporary workspaces. Remove
  tracked generated database, marker, and lock artifacts.

## TDD seam

Through existing public scientific Interfaces:

1. one task identity cannot disagree with its brief or design identity;
2. one PeriodAdvice answers one exact PeriodDomain;
3. one HeightDomain accepts the current admitted PeriodChoice and rejects a
   stale or foreign choice;
4. one admitted propagation library forms 8-, 12-, and 16-state Apertures
   across the cyclic phase seam;
5. one admitted geometric CellChoice and its Orientations form one continuous
   Aperture, while mismatched references are rejected;
6. serialized Aperture evidence restores coordinates, mask, target phase, and
   placement without recomputation;
7. the complete non-live suite starts and ends with the same Git status.

Tests observe these behaviors through public Interfaces. They do not assert
private helper names, duplicate production arithmetic, or mock internal
scientific Modules.

## Acceptance

- Each stable schema has one owner beside its value and decoder.
- `ScientificTask` has one authoritative identity representation.
- Period advice cites its exact period domain.
- Period validation has one implementation in the period Module.
- Height derivation validates the exact admitted period choice in the current
  Study and carries no copied period basis.
- Aperture is the sole owner of its complete lattice and placement evidence;
  no second public lattice value divides that ownership.
- Propagation matching remains deterministic and cyclic; geometric placement
  remains continuous and both use vectorized identity placement.
- The same admitted propagation library forms the 8-, 12-, and 16-state test
  Apertures.
- The metalens public Interface contains no implementation-only state,
  response, or construction helpers.
- Tests use isolated temporary workspaces. No generated workspace artifact is
  tracked or changed by a test run.
- Focused identity, period, height, aperture, and architecture tests pass.
- The complete non-live suite passes with zero skipped tests and leaves
  `git status --short` unchanged.
- Pyright reports zero errors and zero warnings.
- Every touched production file has zero CSU hard violations.
- `git diff -- rust` is empty.

## Scope boundary

Do not move Field or focus values (ticket 06), change Lumerical work life
(ticket 07), retire `science/routes/` or implement Result replay (ticket 08),
perform the repository-wide naming and documentation ratchet (ticket 09), or
run a live adviser or solver (ticket 10).

## Verification

- Focused public-seam review: 112 passed.
- Complete non-live suite: 337 passed, 15 live tests deselected, zero skipped.
- The complete suite left `git status --short` unchanged.
- Pyright: zero errors and zero warnings.
- CSU: 22 touched production files, zero hard violations.
- Rust diff: empty.
- Independent Spec and Standards re-reviews: passed.

## Do not add

Do not add compatibility aliases, schema registries, identity managers,
generic assignment strategies, public test seams, a second lattice owner, or
new scientific policy.
