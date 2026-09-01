# 08 — Rework the advice seam so the adviser reads the envelope

**Type:** `wayfinder:grilling`

**Blocked by:** 07 — resolved 2026-07-26 independent of the exact field set;
only the advice prompt's envelope rendering follows 07's final shape.

**Status:** resolved (2026-07-26)

## Question

How does height advice move behind the envelope without loosening the checks
that currently bind it?

- `_derive_height_domain` (`application.py:237-262`) admits the domain and
  consults the adviser in one operation. The envelope must sit between them, so
  the consultation moves. Where to — its own operation, or the tail of
  `estimate_phase_envelope`?
- `compile.py:179-183` hardcodes `consultations` onto the `height_choice`
  obligation alone. Does that stay, generalise, or move?
- `choose_height` (`height.py:213`) asserts
  `ready[0].consultations == (advice_reference,)` and rebuilds the expected
  domain document byte-for-byte at `:199-204`. Both need the envelope folded in
  without weakening them.
- `HeightAdvice` must now cite brief, domain, and envelope. Does
  `HeightAdvice.domain_reference` become a tuple of source references, or gain a
  sibling field?
- The prompt in `adviser.py:458 _height_prompt` gains the envelope. What does a
  ruled-out height look like to the model, and what happens when it recommends
  one anyway — a finding asking for a new recommendation, never a silent
  substitution?
- `_geometric()` keeps `choose_height` on `("height_domain",)`. Confirm the
  adviser signature change does not force a fake envelope onto that route.

## Resolution (2026-07-26)

**Consultation becomes the first firing of `choose_height`.**

- When the height-choice task is ready and no advice exists, the operation
  consults — the adviser reads the brief, the admitted domain, and the
  admitted envelope — admits the advice, and returns. The study recompiles;
  `compile.py`'s existing consultations binding attaches the advice
  reference; the next firing validates and chooses. Every advance
  establishes exactly one fact; no operation does two things.
- `derive_height_domain` sheds its consultation — its current second job —
  and becomes single-purpose.
- `HeightAdvice` gains `envelope_reference`; `choose_height`'s staleness
  discipline extends to it: advice must cite the exact admitted domain and
  envelope.
- Adviser signature: `recommend_height(brief, domain, envelope)`; the
  geometric route passes no envelope — the consultation reads what exists,
  and no fake envelope is forced onto that route.
- A recommendation naming a ruled-out height produces a typed finding
  (`height_advice_ruled_out`) requesting a fresh recommendation — never a
  silent substitution.
- The `consultations` hardcode on the `height_choice` obligation stays:
  height choice remains the only consulted obligation.

**Amended 2026-07-26 (post-review):** the two-firing mechanism is
superseded — "choose" must always choose. The compiler emits an advice
finding; the application seam performs the consultation and recompiles;
`choose_height` keeps exactly one meaning. Everything else in this
resolution stands. Ticket 22 carries the revised contract; the exact Adviser
Interface and route-specific envelope invariant live in
[The height-advice grounds Interface](25-height-advice-grounds-interface.md).
