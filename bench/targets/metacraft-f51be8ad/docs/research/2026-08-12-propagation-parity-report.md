# Propagation parity decision

## Context

MetaCraft currently uses component propagation for low-NA propagation and PB
Results, and electromagnetic propagation for pointwise high-NA Results. This
report asks only whether the latter can naturally replace the former. It does
not compare either propagated field with the independently authored aplanatic
reference.

## Matrix and formulas

The strict common-domain fixture is a 940 nm, 17 x 17 transverse-linear
Gaussian field sampled at 200 nm. Both public propagation seams use
complex128/float64 on the same selected Torch device. Transverse agreement is

`min_c ||E_component - c E_electromagnetic||2 / ||E_component||2`.

The maximum allowed error is `1e-12` on CPU and `2e-12` on available CUDA.
Electromagnetic power conservation uses
`abs(P_input - P_output) / P_input` with the same limits. The executable test
also exercises the current 940 nm / 480 nm cell spacing and a right/left PB
field through the electromagnetic Interface.

On the recorded workstation, the CPU fixture took 0.009506 seconds with
67,671 peak Python-traced bytes. CUDA:0 took 0.195896 seconds with 1,675,776
peak Torch-allocated bytes. These bounded measurements describe this small
fixture only; they are evidence, not a scientific acceptance shortcut.

## Evidence

On the shared linear domain, x and y complex transverse fields agree to the
strict tolerance; electromagnetic input and output longitudinal Poynting power
also agree. CUDA is tested only when Torch reports it available and never falls
back to CPU.

Replacement nevertheless fails two frozen claims:

- 480 nm is greater than half of 940 nm (470 nm), so the electromagnetic seam
  truthfully rejects the current benchmark sampling.
- the PB field uses right/left circular channels and converted/retained power,
  whereas electromagnetic propagation requires transverse-linear input and
  reports absolute longitudinal Poynting power.

These are applicability and measurement-channel differences, not numerical
error that a looser tolerance may excuse. NA alone does not settle them.

## Public focus matrix

A second fixture exercises the existing public `Field -> FocalRegion -> Focus`
seams rather than comparing private arrays. It is a 400 nm ideal lens with a
20 um design focus, an NA 0.5 boundary aperture and 150 nm sampling. The
component evaluator uses its inclusive low-NA boundary; the electromagnetic
evaluator uses the next representable float above 0.5, making the absence of
a shared public applicability point explicit rather than hiding it. Both use
the same 0.8f--1.2f axial survey and effectively identical Airy buckets.
Relative difference is
`abs(component-electromagnetic)/max(abs(component),abs(electromagnetic))`.
The frozen limits are 10% for axial focus, x/y FWHM and DOF, and 1% for the
three normalized power ratios.

On CPU, axial-focus error was zero, x/y FWHM errors were 4.1304862597179755%
and approximately `1.3e-16`, and DOF error was approximately `1.3e-15`.
Transmission error was approximately `3.3e-16`; concentration and
focus-efficiency errors were both approximately 0.0190915422%. CUDA:0
reproduced the same values within floating-point
roundoff. All half-maximum measures were bracketed. The comparable power
claims are normalized transmission, focused/transmitted concentration and
focused/incident efficiency. Absolute component-amplitude power and
longitudinal Poynting power remain explicitly `not_comparable`.

The same executable matrix states the PB basis bridge rather than hiding it:
`Ex=(ER+EL)/sqrt(2)` and `Ey=i(ER-EL)/sqrt(2)`, with the inverse projection
returning both circular channels to absolute error at most `1e-14`. Projection
permits electromagnetic propagation but does not change the meaning of the
retained PB converted/leakage Result. Sampling at exactly 470 nm (`lambda/2`)
passes; the current 480 nm sampling still raises
`vector_field_sampling_unsupported`.

The sequential focus matrix took 0.0922278 seconds and 4,297,499 peak
Python-traced bytes on CPU, passing a 16 MiB budget. CUDA:0 took 0.3895099
seconds and 147,232,256 peak Torch-allocated bytes, passing a 192 MiB budget.
Runtime and memory are observational workstation evidence; executable tests
recompute the scientific matrix and enforce the memory ceilings.

The four recorded low/high-NA propagation/PB journeys are linked to the
independent integration command in the machine decision. That gate recomputes
one root-independent compact scientific Result signature across two fresh
roots per role. The signature is evidence of deterministic closure, not a
replacement for the focus parity matrix and not a clone-local content ref.

## Decision

The verdict is `dual_applicability`. Component propagation retains the current
low-NA and PB roles; electromagnetic propagation retains its qualified
transverse-linear, adequately sampled, absolute-power role. No route, binding,
selector or fallback changes in this ticket, and no migration successor is
proposed.

The machine-readable record is
[2026-08-12-propagation-parity-decision.json](2026-08-12-propagation-parity-decision.json).
Its seal is deliberately `incomplete`: Ticket07 real Codex/Claude acceptance
and both named Native delivery endpoints remain outstanding. This report is a
parity decision, not a terminal seal or candidate manifest.

## Native delivery attempt

The authorized two-endpoint gate ran once on 2026-08-13 and failed both cases
in 5.7721233 seconds before any Lumerical execution. Both requested application
roots were fresh, but their shared parent
`E:/Year2026_Project_MetaCraft/work_project` did not exist. The application
root contract creates only the final root, so both command subprocesses raised
`FileNotFoundError` while creating that root. The result was `2 failed`; no
retry, directory repair, solver run, or weakened assertion followed. Both
Native endpoints therefore remain blocking failures, not unavailable passes.

After the shared parent was created, one separately authorized corrected run
used the same roots and command. It again returned `2 failed`, this time in
7.7912642 seconds. Both cases reached the Lumerical Adapter's observation
boundary and failed with
`lumerical_unavailable:configuration_incomplete`; neither opened a solver
execution. The first failure record remains intact, this corrected attempt has
its own evidence record, and no further retry is authorized. Native delivery
therefore remains an explicit blocker.
