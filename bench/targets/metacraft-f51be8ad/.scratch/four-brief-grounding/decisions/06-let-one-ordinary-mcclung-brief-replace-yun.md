# Let one ordinary McClung brief replace Yun

Label: `wayfinder:grilling`

Status: resolved (2026-08-09)

## Question

How should the low-NA propagation benchmark replace Yun without presenting a
paper reproduction, proliferating geometry templates, or adding an
`adapted brief` identity?

## Resolution

The current catalogue replaces Yun with one ordinary McClung-grounded
`MetalensBenchmarkCase`. Its blind brief is compact and workstation-scaled:

```text
name: low-na-propagation-550nm
aim: metalens
objectives: focus
wavelength: 550 nm
numerical aperture: 0.20
focal length: 200 um
incident polarization: x-linear
control strategy: propagation phase
meta atom: circular silicon-nitride pillar
substrate: fused silica
aspect limit: 8
dimension step: 10 nm
solver preference: lumerical_fdtd
budget: workstation
aperture: omitted
cell period: omitted
atom height: omitted
```

The compiler receives exactly this compact brief. The published reference
alone owns the paper's 6 mm aperture, 14.7 mm focal length, 430 nm triangular
lattice, 650 nm height, hexagonal cross-section, dimensions, and reported
efficiencies. The benchmark alignment records the exact relationship between
each brief fact and each paper fact, but neither the case nor the brief carries
an `adapted` label.

Existing closed Yun research, tickets, transcripts, and closure records remain
historical evidence. The current `yun.py`, catalogue membership, active case
tests, current qualification road, and Yun-specific current-policy clauses
leave the active baseline in one atomic cutover. This resolution supersedes
only the active Yun disposition in
`Let target-near briefs declare material adaptations`; it preserves that
decision's material-truth and no-silent-substitution rules.

## Consequences

- The four cases remain ordinary external benchmarks rather than claimed
  reproductions.
- Production gains no triangular-lattice or hexagonal-meta-atom template.
- The low-NA propagation brief has source-grounded period and height context
  without receiving either answer in advance.
- Historical truth is preserved without keeping Yun in the current catalogue.
