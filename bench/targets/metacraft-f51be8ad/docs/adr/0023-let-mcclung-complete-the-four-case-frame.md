# 0023 - Let McClung complete the four-case frame
Status: accepted

Implementation status: implemented (2026-08-09)

Supersedes only the Yun-specific case, aspect-limit, and unresolved-period
clauses under “Preserve honest blindness” in
[ADR 0020 - Let benchmark truth explain without directing](0020-let-benchmark-truth-explain-without-directing.md).
ADR 0020's external benchmark ownership, fixed comparison contract, blindness,
and no-silent-substitution rules remain accepted.

## Research basis

The primary-source facts and evidence limits are recorded in
[McClung visible-metalens benchmark facts](../research/2026-08-09-mcclung-visible-metalens-benchmark.md).

## Context

The four-case catalogue spans propagation and geometric phase at low and high
NA. Its former low-NA propagation case could not source-join a published period
to the selected height, which made period and height comparison structurally
weak. Keeping it current would preserve a historical choice rather than a
balanced benchmark frame.

McClung et al. publish one 550 nm, NA 0.2 silicon-nitride platform with a joined
430 nm period, 650 nm nominal height, and explicit lateral geometry. Their
device is millimetre scale and uses a hexagonal triangular-lattice platform;
the benchmark needs a compact workstation design, not a reproduction mode.

## Decision

The sole current low-NA propagation case is
`mcclung-2024-low-na-propagation`. Its blind `MetalensBrief` declares 550 nm,
NA 0.20, 200 µm focal length, x-linear incidence, propagation phase, circular
silicon-nitride pillars on fused silica, aspect limit 8, a 10 nm dimension
step, `lumerical_fdtd`, and workstation budget. Aperture, cell period, and atom
height remain honest omissions.

The external `PublishedReference` alone owns the paper's 6 mm aperture,
14.7 mm focal length, 430 nm triangular-lattice period, 650 nm nominal height,
hexagonal post geometry, lateral dimensions, and efficiency meanings. The
alignment records focal length and shape as adapted, polarization and process
limits as independent, and paper geometry as withheld. No `adapted brief`
identity, compatibility alias, reproduction mode, or second catalogue exists.

The blind material families bind through the existing reviewed registrations:
silicon nitride selects `Si3N4 (Silicon Nitride) - Luke`, and fused silica
selects `SiO2 (Glass) - Palik`. The benchmark adds no material alias or optical
record.

Current catalogue membership, strict restoration, harness case lists, and
active tests change together. The retired Yun identity may appear only in one
negative assertion proving that selection rejects it. Historical Yun Research
Records, ADRs, tickets, transcripts, and closure records remain unchanged.

## Consequences

The catalogue now has one stable propagation/geometric by low/high-NA frame:
McClung, Yang, Arbabi, and Khorasaninejad. Paper facts can diagnose a completed
result without seeding period or height advice, and efficiency remains context
rather than a hidden threshold.

Production science, benchmark schemas, material registrations, conduct,
Authority, and Result types do not change. No triangular-lattice template,
hexagonal-post template, lattice abstraction, solver run, or compatibility
path is introduced.

The resolved decision record and implementation ticket are
[Four-brief grounding decision 06](../../.scratch/four-brief-grounding/decisions/06-let-one-ordinary-mcclung-brief-replace-yun.md)
and
[Four-brief baseline ticket 02](../../.scratch/four-brief-baseline/issues/02-let-mcclung-complete-the-four-case-frame.md).
