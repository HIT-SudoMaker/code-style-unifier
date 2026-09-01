# 22 — Advice behind the envelope

**Type:** implementation (spec phase 3, after 21)

**Status:** wontfix

**Superseded by:** [Metalens Sonnet convergence ticket 04](../../metalens-sonnet-convergence/issues/04-let-one-adviser-answer-grounded-questions.md).

**What to build:** One verb, one meaning (revised after review): when the
height-choice obligation is ready without bound advice, the **compiler
emits an advice finding** on the study; the **application seam answers the
finding** — it consults the adviser with the brief, the admitted domain,
and the admitted envelope, admits the advice, and recompiles; after the
advice reference is bound, `choose_height` fires exactly once and does the
only thing its name says: deterministic selection.
`derive_height_domain` sheds its consultation and becomes single-purpose.
`HeightAdvice` gains `envelope_reference: Reference | None`;
`choose_height`'s staleness discipline extends to it. The Adviser Interface is
`recommend_height(brief, domain, *, envelope: PhaseEnvelope | None = None)`.
Propagation requires the exact admitted envelope and renders its standings
first; geometric requires `None` and reads only the brief and domain. Missing,
stale, or fabricated route grounds are rejected before consultation. A
recommendation naming a ruled-out height produces the typed
finding `height_advice_ruled_out` requesting a fresh recommendation —
never a silent substitution. The `consultations` binding on the
`height_choice` obligation stays as-is.

**Acceptance:**

- Tests show the sequence: study carries the advice finding — the seam
  consults and recompiles — `choose_height` fires once and only chooses;
  each step establishes exactly one fact.
- A ruled-out-recommendation test yields the finding on an unfinished
  study.
- Interface tests reject a missing or stale propagation envelope and reject
  any geometric envelope; geometric consultation succeeds with no envelope
  argument.
- Touched files leave `csu check` with zero hard violations.

Decisions: ticket 08; ticket 05 (standings the adviser reads);
[The height-advice grounds Interface](25-height-advice-grounds-interface.md).
