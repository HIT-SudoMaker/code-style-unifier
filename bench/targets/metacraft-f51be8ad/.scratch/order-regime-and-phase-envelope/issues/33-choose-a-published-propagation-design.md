# 33 — Choose a published propagation design

**Type:** research (spec phase 6)

**Status:** wontfix

**Superseded by:** [Metalens Sonnet convergence ticket 10](../../metalens-sonnet-convergence/issues/10-run-the-canonical-live-delivery.md).

**Blocked by:** ticket 32.

**What to build:** Compare two or three primary, top-journal propagation-phase
metalens papers and recommend one design that the current low-na architecture
can reproduce without adding large-na, achromatic, vector-field, or optimizer
capabilities. Prefer a single wavelength, disclosed materials and geometry,
a recoverable unit-cell period and height, a stated aperture and focal
length, and published focal-width or efficiency data suitable for comparison.

Record the search and selection as a Research Record. Translate the selected
paper into one proposed exact brief and list every expected comparison
quantity, but keep missing facts explicit. Stop at human review: the paper
may validate MetaCraft, but it may not silently revise the period law,
fabrication policy, phase coverage law, or Authority protocol.

**Acceptance:**

- The Research Record cites primary sources and explains why each candidate
  is reproducible or unsuitable.
- The recommended paper fits the implemented low-na propagation route.
- The proposed brief separates paper facts, derived values, local execution
  facts, and honest omissions.
- Existing compact standard briefs remain as regression contracts; the paper
  brief is an external-validation example, not a replacement oracle.
- No solver run and no core-rule change occurs in this ticket.

Decisions: ticket 32; spec phase 6.

## Comments

### 2026-07-26 — research complete; awaiting user review

Recorded the primary-source comparison in
`docs/research/2026-07-26-published-low-na-propagation-metalens-selection.md`.

The recommendation is the 500 µm focal-length device target from Zhan et al.
(2016), explicitly as an **adapted reproduction**:

- retain the paper's 633 nm target, 112 µm aperture, low NA, circular
  silicon-nitride pillars, quartz/silica substrate, and propagation phase;
- let MetaCraft retain ownership of the admitted physical period, one advised
  height, the fabrication boundary, and independent 8/12/16 phase sets;
- use the eight-state result as the primary comparison without claiming it is
  the paper's six-state/443 nm layout.

No production code, test, core rule, standard brief, or solver state changed.
No solver was started. Human review is required before adding an external
validation example or conducting the design.
