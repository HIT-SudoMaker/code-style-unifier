# 12 — CONTEXT.md terminology revision list

**Type:** `wayfinder:grilling`

**Blocked by:** 03, 04 (both resolved 2026-07-26) — now on the frontier.
New inputs: `order regime` {`zeroth order`, `multi order`}, the
`sampling ceiling` / `order ceiling` pair replacing "admissible period"
(ADR 0005), the solver-native material sample source extension (ticket 04),
and ticket 13's decision that `aspect_limit` deliberately carries both the
pillar and the gap meaning.

**Status:** resolved (2026-07-26)

## Question

`CONTEXT.md` is normative and partly enforced by
`tests/architecture/test_scientific_boundary.py`. Which entries change, and to
what exact wording?

Known pressure points:

- `:41` **height domain** — "It contains no solver observation." A sampled
  refractive index comes from the solver. The sentence was written to keep FDTD
  *device response* out of the domain; material identity is not device response.
  Proposed: "It contains no device-response observation; it may cite the
  solver-native material identity it was derived under." Confirm or replace.
- `:111` **material sample** — currently resolved only "from one material
  record", which `:109` restricts to a local table or a refractiveindex.info
  dataset. A solver-native sample fits neither. Extend the source, keeping
  `:107`'s rule that solver-native identity is valid only inside the named
  binding.
- **order regime** — new entry if ticket 03 adopts the term, written to pair
  with `aperture regime` at `:97`.
- **phase envelope**, **height reach**, **optical contrast** — new entries. Each
  must state what the term is *not*: the envelope is not evidence of coverage.
- Does anything need saying about `CellPolicy.period_nm` being demoted to a
  phase-sampling ceiling while the admissible period lives elsewhere? Two
  periods in one system is a naming hazard.

Check the `__all__` assertions and docstring checks in
`tests/architecture/test_scientific_boundary.py:31-57` for anything the new
public names break.

## Resolution (2026-07-26)

Ratified as drafted (W1-W9) and written into `CONTEXT.md` verbatim:

- **height domain** rewritten — owns the physical period and order regime,
  "no device-response observation", may cite the solver-native identity and
  sample it was derived under.
- New entries: **phase envelope**, **height reach**, **optical contrast**
  (placed after height domain, in mental order); **order regime**,
  **sampling ceiling**, **order ceiling**, **aspect limit** (placed after
  aperture regime). The aspect-limit entry records ticket 13's decision in
  words.
- **material sample** extended with the qualification-time solver-native
  source (ticket 04).
- **Avoided language** gains `single order`, `admissible period`, and
  `n_eff`-style abbreviations, each with its replacement.
- `science.__all__` untouched; no docstring assertions affected — the
  glossary edit introduces no code surface.
- Older "admissible period" prose in this map and its closed tickets stays
  as historical record; the glossary and all new writing use the ceiling
  pair.
