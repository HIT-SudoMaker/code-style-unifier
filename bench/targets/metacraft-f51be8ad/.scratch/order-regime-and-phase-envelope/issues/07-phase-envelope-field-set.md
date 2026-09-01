# 07 — Fix the PhaseEnvelope and HeightReach field set

**Type:** `wayfinder:prototype`

**Blocked by:** 05, 06 (06 resolved 2026-07-26; waiting on 05)

**Status:** resolved (2026-07-26)

## Question

What does the envelope actually return, judged by reading a filled-in example
rather than a schema?

Build a throwaway prototype that emits a real `PhaseEnvelope` for the 355 nm and
400 nm briefs under the corrected period, then read it and decide:

- Does `HeightReach` need the span triple (`minimum_phase_span`,
  `maximum_phase_span`, `required_phase_span`) once the verdict comes from the
  shared coverage predicate rather than from a span comparison? A span a human
  can read is worth keeping even if it is not the rule.
- Where do the sampling-density facts live — a coarsest predicted step against
  the permitted step, per quantization, or one worst case?
- Is the fabricable diameter grid part of the reach, or already carried by the
  domain?
- Does `ruled_out: bool` carry a reason code beside it, and is
  `not applicable` a third state rather than a flag?
- What does `OpticalContrast` hold — material samples with provenance, not bare
  numbers — and does it name the ambient medium explicitly?
- All values are `Decimal` or formatted strings; `canonical.py:40` rejects
  `float`. Does the document round-trip byte-identically?

Link the prototype from this ticket. Do not merge it.

## Resolution (2026-07-26)

Field set fixed by reading the filled prototype, then tightened after the
owner's Sonnet challenge exposed the one true duplication:

- `PhaseEnvelope { brief_identity, source_references, bound_checks, reaches }`
  — the source references contain only the exact admitted inputs. One global
  `bound_checks` block records the certified endpoint and ordering checks:
  ceiling closes to the pillar index at d -> P; floor closes to the ambient
  index at d -> 0; floor remains below ceiling over the whole grid. The block
  is not repeated per height.
- `HeightReach`:
  - grid facts: height, minimum/maximum feature, lateral step, candidate
    count;
  - `bounded_reasoning`, one block: floor index at the minimum feature,
    ceiling index at the maximum feature with its polarization, rigorous
    turns ceiling — not expanded per quantization (the rule only asks for
    one full turn);
  - `forecast`, one block: model spans, the steepest adjacent step as an
    optional field that is absent when undefined (single candidate),
    per-level budgets, and the non-authorizing annotation
    `forecast insufficient`;
  - `applicability`, one block: single-mode cutoff diameter, affected count
    and fraction — retained even when empty, because the emptiness is a
    proof, not a default;
  - `standings` — the one per-quantization table {levels, standing,
    deciding tier, reason}, merging the prototype's parallel
    arithmetic-verdict and overall-standing lists.
- Every value is a formatted decimal string; the document reads in the
  mental order facts -> bounds -> forecast -> standings.
- Prototype artifacts were throwaway and are not durable provenance:
  `envelope-prototype-355.json`, `envelope-prototype-400.json`,
  `envelope-prototype-summary.md`, `envelope-prototype-build.py` in the
  session scratchpad. Ticket 30 replaces them with one independent derivation
  and two reviewed golden fixtures at implementation time.
