---
record_type: research_record
date: 2026-08-09
status: research_finding
authority_level: none
current_capability: false
---
# McClung visible-metalens benchmark facts

## Question and sources

This record establishes the publication facts that may enter the external
McClung benchmark reference while keeping them out of its blind brief.

Primary sources reviewed on 2026-08-09:

1. Andrew McClung et al., “Visible Metalenses with High Focusing Efficiency
   Fabricated Using Nanoimprint Lithography,” *Advanced Optical Materials* 12,
   2301865 (2024), [publisher record](https://doi.org/10.1002/adom.202301865).
2. The authors' complete public manuscript, including the experimental section
   and supporting figures, [arXiv:2312.13851](https://arxiv.org/abs/2312.13851).

The publisher records first online publication on 21 December 2023 and the
formal volume citation as 2024. The benchmark identity therefore uses 2024.

## Selected reference design

The selected object is the shared 6 mm-diameter, NA 0.2 silicon-nitride
metalens design, not a claim that MetaCraft reproduces either fabrication
route. The Results and discussion text accompanying Figure 2 reports:

| Fact | Published value | Locator |
| --- | --- | --- |
| design wavelength | 550 nm | Figure 2 design discussion |
| numerical aperture | 0.2 | Figure 2 design discussion |
| aperture | circular, 6 mm diameter | Figure 2a and design discussion |
| focal length | 14.7 mm | Figure 2a and design discussion |
| atom and substrate | silicon-nitride nano-posts on fused silica | Figure 2a and design discussion |
| atom height | nominally 650 nm | Figure 2 design discussion |
| cross-section and lattice | hexagonal posts on a triangular lattice | Figure 2a and design discussion |
| lattice constant | 430 nm | Figure 2 design discussion |
| post widths | 100–310 nm | Figure 2 design discussion |
| minimum selected gap | 120 nm | Figure 2 design discussion |
| simulated focusing efficiency | 90.2% | Figure 2 design discussion |

The experimental section says the deposited silicon-nitride film was nominally
about 650 nm and measured as 667 nm. The benchmark height fact uses the design's
reported nominal 650 nm; the measured film thickness remains process context.

The narrowest nominal post has a derived feature aspect ratio of
`650 / 100 = 6.5`. The selected minimum gap has a separate derived depth-to-gap
ratio of `650 / 120 = 5.42`. Neither ratio is a published transferable process
ceiling, so the blind brief's aspect limit 8 remains an independent user input.

## Efficiency meanings and limits

The 90.2% value is the paper's grating-averaging simulation estimate for the
550 nm design. The article does not give a reusable numerical focal bucket for
that estimate, so it is comparison context rather than a signed acceptance
threshold.

Figure 4 reports measured peak focusing efficiencies at 552 nm of `(81 ± 1)%`
for the nanoimprinted lens and `(89 ± 1)%` for the EBL control. For those
measurements, focused power passed through a 40 µm pinhole at the focal plane;
incident power was measured through a 6 mm aperture without the lens and
pinhole. The authors corrected for the fused-silica backside reflection and
the ideal-lens power blocked by the pinhole. These values are valid publication
facts, but they are not the 550 nm simulated design measure and must not be
merged into its one fixed comparison quantity.

The paper publishes focal-spot images, MTFs, a transmittance-versus-width plot,
and local holographic measurements. It does not publish reusable independent
x/y half-maximum widths, focal shift, a complete complex focal-field array, or
an exact field-magnitude transmission table. The plotted phase and
transmittance curves also do not state enough textual numeric detail to invent
exact phase-span or transmission-normalization facts.

## Blind-brief boundary

The blind benchmark brief may contain only the owner-approved workstation
intent: 550 nm, NA 0.20, 200 µm focal length, x-linear incidence, propagation
phase, circular silicon-nitride pillars on fused silica, aspect limit 8, a
10 nm dimension step, `lumerical_fdtd`, and workstation budget. Aperture, cell
period, and atom height remain omitted.

Consequently, focal length and atom shape are adapted relations; polarization,
aspect limit, and dimension step are independent; aperture, period, height, and
lateral geometry are withheld. The paper's geometry, efficiencies, NIL route,
and EBL control remain post-hoc context and never direct consultation.
