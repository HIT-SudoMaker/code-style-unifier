# 09 — Ratchet the Sonnet architecture

Type: implementation and non-live verification

Status: resolved (2026-07-28)

Blocked by: tickets 05A through 08.

## Outcome

The accepted architecture becomes easier to preserve than to violate.
Documentation, imports, names, tests, and public Interfaces tell one story.

## What to build

- Complete a responsibility-led production naming audit without mechanical
  long-name churn.
- Keep noun types, verb operations, paired word order, and natural scientific
  names across touched ownership seams.
- Remove residual `route_*`, `*_operation`, manager/handler/processor,
  public mathematical shorthand, strategy-as-route, and provider-native
  vocabulary where those names still encode the retired architecture.
- Keep accurate short nouns and narrow mathematical locals unchanged.
- Remove dead compatibility exports, shallow forwarding Modules, obsolete
  tests, speculative future fixtures, and unused implementation paths exposed
  by tickets 01–08.
- Update `CONTEXT.md`, `SCIENCE.md`, `DEVELOPMENT.md`, relevant ADR links, and
  package documentation to the implemented tree and mental order.
- Repair dead local Markdown links left by deleted architecture. Preserve a
  historical path or ADR number as explicit provenance text when no current
  target exists; never invent a replacement document or rewrite the research
  conclusion.
- Add architecture ratchets for:
  - unchanged Rust source and protocol;
  - aim-local metalens language;
  - cross-aim Field without metalens focus values;
  - no dotted route identities or compiler-derived schemas;
  - inward advice dependencies;
  - narrow Lumerical exports and hidden test seams;
  - no speculative future proofs;
  - no old import aliases or schema readers.
- Replace tests of retired shallow Modules with tests at the deep Interface.
- Run the complete non-live suite and record exact results in this ticket.

## TDD seam

Architecture tests inspect public exports, dependency direction, schema
ownership, forbidden production identifiers, and Rust immutability. Behavioral
tests continue to assert scientific outcomes rather than source spelling.

## Acceptance

- The complete non-live suite passes with live network and solver tests
  explicitly deselected.
- Pyright reports zero errors and zero warnings.
- Every touched file has zero CSU hard violations; remaining lower-severity
  findings are reported rather than hidden.
- No test case imports another test-case file.
- No broad test recomputes compiler, fake solver, three quantizations, Field,
  Result, and replay merely to check one local fact.
- Canonical examples compile without launching an adviser, solver, or Torch
  calculation unless that test explicitly owns the corresponding seam.
- Documentation and source use `geometric phase`; PB terminology remains only
  in physics explanation and citations.
- Every local Markdown link resolves. References to deleted historical paths
  are visibly historical provenance, not links that pretend the target still
  exists.
- `git diff -- rust` is empty.
- The ticket records the exact baseline commit and verification commands for
  ticket 10.

## Do not add

Do not weaken a hard seam for test convenience, silence CSU findings by broad
suppression, rewrite unrelated prose, or run the four full live briefs.

## Closure record

Baseline commit:

`743efbb13963cf70209e52648c1da748f95873c3`

Focused architecture verification:

```powershell
C:\Users\Administrator\miniforge3\envs\research_env\python.exe -m pytest -q -p no:cacheprovider tests/architecture --tb=short
```

Result: `42 passed in 4.72s`.

Focused behavioral verification covered the adviser, standard studies,
shared-field seam, metalens aperture/focus/result, canonical compilation and
recorded qualification boundary, and narrow Lumerical ownership.

Result: `83 passed in 13.88s`. The final Field and solver-evidence slice also
passed `35` focused tests in `12.70s`.

Complete non-live verification:

```powershell
C:\Users\Administrator\miniforge3\envs\research_env\python.exe -m pytest -q --tb=short -p no:cacheprovider -m "not integration and not lumerical_live and not advice_live and not lumerical_delivery"
```

Result: `364 passed, 15 deselected in 257.93s (0:04:17)`.

Static verification:

```powershell
C:\Users\Administrator\miniforge3\envs\research_env\python.exe -m pyright
.\csu\bin\csu.exe check <each-touched-production-file> --format json --output .csu/ticket09-one.json --no-history
git diff -- rust
```

Results:

- Pyright: `0 errors, 0 warnings, 0 informations`.
- CSU: 20 touched production files, `0 hard_violation`,
  `0 soft_friction`, and 1,379 non-blocking `under_review` findings retained
  for later calibration rather than hidden or opportunistically rewritten.
- Rust diff and status: empty.
- Tracked local Markdown links: zero unresolved.
- Independent Spec review: PASS, no remaining finding.
- Independent Standards review: PASS, `0 hard`.
- Independent main-agent architecture recheck: `42 passed in 4.78s`.
