# 02 — Let McClung complete the four-case frame

**Parent spec:** [Four-brief grounded baseline](../spec.md)

**Decision source:** [Let one ordinary McClung brief replace Yun](../../four-brief-grounding/decisions/06-let-one-ordinary-mcclung-brief-replace-yun.md)

**Status:** resolved (2026-08-09)

**Blocked by:** Ticket 01

## What to change

Create one primary-source Research Record for McClung et al., *Visible
Metalenses with High Focusing Efficiency Fabricated Using Nanoimprint
Lithography*, DOI `10.1002/adom.202301865`. Verify every admitted publication
fact and source locator before encoding it. Record one focused ADR that
supersedes only the Yun-specific case, aspect-limit, and unresolved-period
clauses of ADR 0020; do not rewrite ADR 0020 or historical Research Records.

Replace `examples/metalens_benchmark/yun.py` with `mcclung.py` in one catalogue
cutover. The ordinary case identity is
`mcclung-2024-low-na-propagation`. Its blind brief is exactly the compact
workstation design fixed by the parent specification: 550 nm, NA 0.20,
200 um focal length, x-linear incidence, propagation phase, circular silicon-
nitride pillars on fused silica, aspect limit 8, 10 nm increment,
`lumerical_fdtd`, with aperture, period, and height omitted.

Keep paper truth external. The `PublishedReference` owns the source-supported
6 mm aperture, 14.7 mm focal length, 430 nm lattice period, 650 nm height,
hexagonal-post/triangular-lattice geometry, reported dimensions, and efficiency
meanings. The fixed comparison frame must explicitly mark unsupported or
incomparable measures; it must not turn efficiency into a pass threshold. Use
the existing alignment variants to state matched, independent, withheld, and
geometry differences. Add no `adapted brief` name, type, flag, or display
label.

Update the sole catalogue, harness blind-case list, domain-naming ratchets,
brief-document tests, propagation fixtures, and case contract tests atomically.
Delete active Yun imports and the Yun-specific active contract test. Preserve
closed Yun ADRs, research, `.scratch` tickets, transcripts, and closure records.

## Acceptance

- The catalogue contains exactly McClung, Yang, Arbabi, and Khorasaninejad in
  the stable propagation/geometric by low/high-NA frame.
- Strict case document restoration accepts McClung and rejects the removed Yun
  identity; no compatibility alias or forwarding import remains.
- McClung material intent binds only to the reviewed Luke silicon-nitride and
  Palik fused-silica registrations.
- The brief document contains no paper period, height, aperture, device-scale
  focal length, lattice, post width, gap, or efficiency leakage.
- Current source/tests contain no Yun identity; historical records remain
  byte-preserved.

## Verification

Run all benchmark example, brief document, propagation contract, harness
fixture, architecture naming, and Markdown-link tests. Do not conduct the four
consultations or delete old run artifacts in this ticket.

## Stop condition

Stop after one atomic catalogue replacement. Do not add a lattice template,
paper reproduction mode, benchmark subclass, material alias, or second case
registry.

## Closure

Implemented as one catalogue cutover under ADR 0023. McClung, Yang, Arbabi,
and Khorasaninejad now form the sole active four-case frame. The retired Yun
identity remains only in one negative restoration assertion; historical Yun
records were not changed. Focused contract, benchmark, brief, propagation,
harness, architecture, and Markdown-link gates passed without running
Lumerical or entering Ticket 03 consultation scope.
