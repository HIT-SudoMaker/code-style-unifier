# Two-case periodic-response pilot

Status: complete

## Purpose

Run the two simplest complete propagation-cell libraries before any aperture
or field work.  Preserve the already admitted blind-brief choices and gather
native Lumerical complex-transmission evidence over every legal lateral value
on the brief's fabrication grid.

## Cases

- `mcclung-2024-low-na-propagation`: period 430 nm, height 650 nm,
  circular-pillar diameter 90--340 nm in 10 nm steps (26 responses).
- `arbabi-2015-high-na-propagation`: period 800 nm, height 900 nm,
  circular-pillar diameter 120--680 nm in 10 nm steps (57 responses).

These period and height values are restored from their existing Authority
roots.  Published values remain external benchmark context and do not seed a
new choice.

## Execution order

1. Qualify the configured Lumerical installation and positive capacity.
2. Prepare a fresh McClung root and gather its complete 26-response batch.
3. Inspect completeness, reference planes, finite complex response, useful
   power, and phase coverage before opening the Arbabi batch.
4. Prepare and run Arbabi only after the McClung seam is sound.

## Stop conditions

Stop on typed product unavailability, incomplete work, mismatched world
reference planes, non-finite response, invalid power, or an unexpected fault.
Do not add aperture formation, field propagation, focus evaluation, automatic
optimization, or a PB Cartesian sweep to this pilot.

## Result

Both finite grids completed through the same parameterized harness path and
replay from their admitted Authority evidence without another native solve.

- McClung observed 26/26 responses and delivered 8-, 12-, and 16-level phase
  sets.  Its response phase covering arc is 5.5718032758534433 rad.
- Arbabi observed 57/57 responses and delivered 8- and 12-level phase sets.
  Its response phase covering arc is 5.6402509406535266 rad.  The 16-level
  request is explicitly refused as `cell_library_coverage_inadequate`.

The first Arbabi run reproduced a deterministic 540 nm failure at a normalized
power of 1.0270489507746696.  Its native FDTD status was 1: the solve reached
the 1000 fs maximum before autoshutoff.  A fresh-session replay returned the
same value, ruling out session reuse.  With mesh accuracy fixed at 4 and only
the maximum simulation time raised to 2000 fs, native status became 2 and the
power converged to 0.9335635888647187.  Production keeps the strict [0, 1]
power gate and now gives resonant cells the longer maximum time.

Logs show that some large-diameter tail cells still reach the maximum time.
They are retained as measured responses, not hidden:

- McClung has 16 autoshutoff and 10 full-time cells.  Direct 1000-to-2000 fs
  comparison over all 26 cells changed power by at most 0.0003704459238831337
  and phase by at most 0.00032663059805254635 rad.
- Arbabi has 44 autoshutoff and 13 full-time cells.  None of those 13 cells is
  selected by the delivered 8- or 12-level sets.  A conservative 650 nm
  2000-to-4000 fs check changed power by 0.1571% and phase by 0.002854 rad.

The retained `*-1000fs-diagnostic-root` directories preserve the before/after
evidence that motivated the numerical-template change.  The `*-live-root`
directories and `*-response-summary.json` files are the current acceptance
artifacts.

## Nominal vector-ASM pilot

The Arbabi high-NA route advanced through the canonical local chain to an
admitted pointwise field, then propagated one deliberately bounded plane at
the nominal 25 um focal distance. This first sanity check preceded the
bounded focal survey below; it did not run the direct-Debye comparison.

- lattice: 123 by 123 periods with 11,669 occupied sites;
- formed transverse field: 2952 by 2952 samples at 33.333 nm spacing;
- device: qualified `cuda:0` vector angular spectrum realization;
- all Cartesian output components finite;
- input/output longitudinal power: 9.051944007434927e-12 W on both planes;
- peak offset from the geometric centre: 23.570 nm;
- half-maximum widths: 1.267 um horizontally and 0.800 um vertically;
- longitudinal electric-intensity fraction: 0.4716243.

The exact machine-readable result is
`acceptance/arbabi-nominal-vector-asm-summary.json`.  This closes the nominal
plane numerical sanity check, not focal bracketing or paper-metric agreement.

## Vector focal survey

The same admitted Arbabi field was reused without another periodic solve.
The qualified CUDA vector-ASM realization searched `0.8f`--`1.2f` on 17
coarse planes and locally refined the neighbours of its interior maximum.
The 31 distinct observations use the maximum of the summed Cartesian
intensity at one sample, not a sum of component maxima from different
locations.

- expected and observed focus: 25.000 um; focal shift: 0;
- smallest refined axial step: 78.125 nm;
- bracketed depth of focus: 2.5069 um;
- interpolated half-maximum widths: 1.2361 um horizontally and 0.8173 um
  vertically;
- peak offset from the geometric centre: 23.570 nm;
- Airy-bucket fraction of propagated aperture power: 0.56275;
- input/output longitudinal Poynting power error: 0;
- CUDA survey time after field restoration: 6.149 s.

The exact machine-readable result is
`acceptance/arbabi-focus-survey-summary.json`. It is a complete bracketed
focus under the production focus evaluator. The bucket fraction is relative
to the already formed aperture field; it is not an end-to-end illumination
efficiency or a paper comparison. Direct-Debye and published-reference
agreement remain separate evidence.

## Numerical-time closure

The diagnostic's fixed `2000 fs` maximum has been replaced by the bounded
policy accepted in ADR 0025. Each periodic construction now derives an
ordinary maximum from its complete FDTD span, admitted material indices,
wavelength, and ordinary-method guards. Native autoshutoff may finish early;
status `1` permits exactly one doubled extension, after which the consumed
response—including the sampled near field when present—must be stable or the
work is explicitly refused.

Every attempt retains its project, execution, native status, terminal decay
level, threshold, and actual end time. Accepted closure is recorded in the
work construction; an exhausted ladder records a numerical refusal without a
false observation. No caller-selected solver-time knob or open-ended tuning
loop was added. The existing `*-live-root` artifacts remain evidence of the
earlier fixed-time pilot; fresh Native acceptance of ADR 0025 produces new run
identity rather than rewriting them.

The bounded Native qualification retained under
`acceptance/time-budget-native-qualification/` executed exactly three 400 nm
fixtures. All three ended in the ordinary `1000 fs` tier by native status `2`
at 303.17 fs, 424.54 fs, and 506.46 fs, with terminal autoshutoff levels below
`1e-5`. The machine-readable digest is
`acceptance/time-budget-native-qualification-summary.json`.
