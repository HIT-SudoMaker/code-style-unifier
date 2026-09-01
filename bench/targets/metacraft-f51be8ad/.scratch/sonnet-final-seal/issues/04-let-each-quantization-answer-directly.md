# Let each quantization answer directly

Type: implementation

Status: resolved (2026-07-29)

Blocked by:
[Let advice own one identity](03-let-advice-own-one-identity.md).

## Outcome

Each 8-, 12-, or 16-level propagation quantization returns either one complete
phase set or one explicit refusal. Ordinary scientific refusal is no longer
classified from exception text.

## Scope

1. Replace private `_form_phase_set` with `_attempt_phase_set`.
2. Return `PhaseSet | QuantizationRefusal`.
3. Return reason `cell_library_insufficient` when fewer candidates exist than
   one requested level count.
4. Return reason `cell_library_coverage_inadequate` when the admitted phase
   responses cannot cover one uniform level set.
5. Keep `levels`, `available_cells`, and `required_cells` as separate refusal
   facts.
6. Remove embedded `:<levels>` suffixes from refusal reasons.
7. Make `assess_phase_sets` collect returned phase sets and refusals without
   catching or parsing ordinary `ValueError`.
8. Preserve the independent 8-, 12-, and 16-attempt order.
9. Preserve `form_phase_sets` as the successful-phase-set projection.
10. Preserve direct faults for invalid phase selection, malformed responses,
    impossible assignments, and implementation drift.
11. Preserve complete formation reporting and branch formation.
12. Update `SCIENCE.md` with the explicit answer model.

## Acceptance

- A qualifying library forms distinct 8-, 12-, and 16-level phase sets.
- Candidate shortage returns a typed refusal.
- Coverage shortage returns a typed refusal.
- Neither ordinary refusal is produced by catching or parsing exception text.
- Refusal reason and arithmetic facts are separate.
- A mixed formation returns all successful phase sets and every refused
  quantization.
- Only successful phase sets become branches.
- Formation report retains every refusal.
- Invalid internal state still raises directly.
- No geometric-phase quantization is introduced.
- Rust is untouched.

## Focused verification

Run only focused tests or exact nodes covering:

- successful 8/12/16 formation;
- insufficient candidate count;
- inadequate cyclic coverage;
- mixed successful and refused formation;
- direct invariant faults;
- branch formation report.

Also run:

- local Pyright for touched Python scope;
- CSU for touched production files;
- `git diff --check`;
- `git diff -- rust`.

Do not run the complete science suite, complete architecture suite, live
solver, canonical briefs, Torch delivery, or Rust tests.

## Stop and report

Stop if an ordinary refusal needs a third accepted reason, if refusal requires
changing the 8/12/16 policy, if formation report bytes must be migrated, or if
the change reaches geometric-phase science.

## Do not add

Do not add a refusal exception hierarchy, enum registry, new quantization,
geometric phase levels, optimizer, fallback phase set, compatibility reason,
live execution, or Rust change.
