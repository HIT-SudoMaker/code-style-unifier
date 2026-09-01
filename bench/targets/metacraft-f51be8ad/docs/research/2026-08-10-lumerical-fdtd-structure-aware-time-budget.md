---
record_type: research_record
date: 2026-08-10
status: research_finding
authority_level: none
current_capability: false
scope: lumerical_fdtd_periodic_response_time_budget
implemented_by: docs/adr/0025-let-geometry-budget-time-and-native-decay-close-it.md
---

# Structure-aware time budgets for Lumerical periodic FDTD responses

## Question and boundary

Should MetaCraft derive the FDTD `simulation time` from the vertical extent of
its periodic `grating_s_params` construction, so that light has time to cross
the complete native group?

This record uses only first-party Ansys Lumerical documentation for product
behaviour. It proposes a MetaCraft planning policy but neither accepts an ADR
nor changes production code. It applies to the existing periodic transmission
and polarization response templates; an explicitly high-Q or resonant study
remains a separate numerical method.

## Conclusion first

The structure length should determine a **causal lower bound**, but one optical
transit through the analysis group is not a convergence condition. The relevant
volume is the complete FDTD simulation region, not only the
`grating_s_params` container. A valid time budget must cover three independent
clocks:

```text
source injection
    + propagation and early round trips
    + structure-dependent energy decay
```

Ansys defines `simulation time` as a maximum duration. Early shutoff may end the
run sooner when the energy remaining in the simulation volume reaches the
configured threshold. Solver status `1` means that this maximum was reached;
status `2` means that autoshutoff ended the run; status `3` means divergence.
[FDTD solver object](https://optics.ansys.com/hc/en-us/articles/360034382534-FDTD-solver-Simulation-Object)

The compact policy is therefore:

> Geometry plans the cap; solver state validates the decay.

It is not:

> One group transit proves completion.

## What the official product documentation establishes

### Maximum simulation time and autoshutoff are different controls

`simulation time` is an upper bound, while `AUTO SHUTOFF MIN` is the normal
energy-decay termination criterion. The latter compares total energy remaining
in the simulation volume with the maximum injected energy. `AUTO SHUTOFF MAX`
belongs to divergence checking and must not be interpreted as a convergence
target. The solver exposes both status and the autoshutoff-level history as
results.
[FDTD solver object](https://optics.ansys.com/hc/en-us/articles/360034382534-FDTD-solver-Simulation-Object)

Consequently, a generous cap does not force every ordinary cell to run for that
entire duration: a decayed cell should stop early. Conversely, setting a short
cap because a wave can geometrically reach a monitor can truncate the time
signal before the energy has left the solver.

### A single-frequency result still begins with a finite pulse

FDTD uses a time-domain pulse even when steady-state or single-frequency results
are requested. Its pulse duration and offset depend on the source spectrum and
time-domain settings; making a pulse narrower in frequency makes it longer in
time and can require a longer overall simulation.
[Changing the source bandwidth](https://optics.ansys.com/hc/en-us/articles/360034383094-Changing-the-source-bandwidth-in-FDTD-and-MODE)

The source clock therefore cannot be reconstructed from geometry alone. For the
internally constructed `grating_s_params` source, a reliable planner must use
native setup/read-back of its effective pulse settings or time signal rather
than inventing a pulse duration from the requested wavelength.

### Propagation length matters, but so do material delay and return paths

The official metamaterial example says that changing wavelength may require a
changed simulation time, and explicitly names simulation span and resonances as
additional factors. It recommends checking a time monitor to ensure that the
source has injected its pulse and that the fields have decayed.
[Metamaterial parameter extraction](https://optics.ansys.com/hc/en-us/articles/360042097393-Metamaterial-parameter-extraction-Smith)

The causal travel time is therefore an optical/group-delay path, not simply
`length / c`. A conservative one-dimensional estimate is

\[
t_{\mathrm{cross}} = \sum_i \frac{n_{g,i}\,\Delta z_i}{c},
\]

where the segments cover the complete FDTD region and `n_g` denotes group
index over each segment. The estimate must allow the source-to-structure path,
transmission to the downstream absorber, and reflection back to the upstream
absorber. Physical interfaces and resonant cells can add round trips. The
`grating_s_params` monitors require propagating fields and use near-field
grating projection; reaching the T plane once does not prove that the DFT time
signal is complete.
[Metamaterial S-parameter extraction](https://optics.ansys.com/hc/en-us/articles/360042095873-Metamaterial-S-parameter-extraction)

### Resonant lifetime can dominate geometric transit

Ansys states that high-Q structures trap light for many round trips and require
longer simulations; frequency-domain monitor results are wrong when fields have
not decayed before the time signal is truncated.
[Ring-resonator parameter extraction](https://optics.ansys.com/hc/en-us/articles/360042800213-Ring-resonator-getting-started-Final-parameter-extraction)

For an exponentially decaying mode, Ansys's field-amplitude correction contains
the factor `exp(-omega * t / (2Q))`. The corresponding stored energy decays as
`exp(-omega * t / Q)`. If a conservative Q bound is known, the time required for
that energy to fall to a fraction `eta` is approximately

\[
t_Q(\eta) \approx \frac{Q_{\max}}{\omega_{\min}}
                  \ln\!\left(\frac{1}{\eta}\right).
\]

[Correcting field amplitudes for high-Q cavities](https://optics.ansys.com/hc/en-us/articles/360041611674-Correcting-field-amplitudes-for-high-Q-cavities)

No finite geometric-length rule can bound an unknown Q. Ansys also warns that
early shutoff may trigger too early for a weakly excited, narrow high-Q mode;
its photonic-crystal cavity workflow disables early shutoff for that reason.
[Photonic-crystal cavity](https://optics.ansys.com/hc/en-us/articles/360041567754-Photonic-crystal-cavity)

### Solver status is necessary evidence, but not universal proof

For ordinary passive transmission work, Ansys recommends increasing simulation
time when status is `1` until status is `2`. Residual energy from a truncated run
can create spectral ripples and even normalized transmission above one. If the
problem persists after autoshutoff, the threshold may also need to be reduced.
[Transmission results greater than one](https://optics.ansys.com/hc/en-us/articles/12614264530323-Transmission-Results-Greater-Than-One)

Status `2` is therefore the cleanest termination signal for MetaCraft's current
non-high-Q periodic responses, not an unconditional guarantee for every future
resonant method. Status `1` is not sufficient evidence by itself, but a bounded
time-extension comparison can still demonstrate that the target observable has
converged even when weak stored energy remains. The configured threshold,
termination status and response convergence all belong in the recorded
numerical contract.

## MetaCraft implications at the time of research

[ADR 0017](../adr/0017-let-one-periodic-layout-place-every-reference-plane.md)
already gives one owner to the world-coordinate layout. In the current template,
the `grating_s_params` group ends at the transmission plane while the FDTD region
continues another 100 nm to its upper absorbing boundary. A time planner must
therefore consume the `PeriodicConstruction.layout` FDTD bounds, not infer time
from the analysis-group span.

The implementation examined by this research had two evidence gaps:

1. `_PeriodicTemplate.simulation_time_fs` is a universal `2000 fs`, independent
   of layout, source pulse and response mechanism.
2. `Session.result(...)` writes the logical string `"complete"` instead of
   returning native FDTD status, autoshutoff level, actual simulated duration and
   threshold. Downstream validation can therefore reject non-finite power, but it
   cannot distinguish native status `1` from status `2`.

These observations do not invalidate the completed benchmark runs. They explain
why `2000 fs` is only a reproducible provisional cap, not yet a structure-aware
time contract.

The scale comparison is instructive. The approved FDTD layouts span `2000 nm`
for the 405/650 nm McClung cell and `2800 nm` for the 1550/900 nm Arbabi cell.
One vacuum transit is only about `6.7 fs` and `9.3 fs`, respectively. Material
group delay increases those values, but a one-transit rule remains far below the
observed `1000--2000 fs` decay behaviour of the difficult Arbabi cell. Geometry
is a floor; stored energy is the tail.

The retained Arbabi 540 nm diagnostic also exposes the internally generated
source clock. Native read-back gives a `10.24 fs` pulse length, a `29.03 fs`
offset and a time signal ending at `58.06 fs`. The `1000 fs` run nevertheless
ended with native status `1` and an autoshutoff level near `9.94e-4`; the
`2000 fs` run ended by autoshutoff at about `1712 fs` with a level near
`9.88e-6`. The extra time is therefore decay time, not source injection or one
geometrical crossing.

## Proposed MetaCraft policy

### 1. One immutable time-budget value

Add no independent `fs helper` and no solver-wide timing manager. The periodic
template should form one immutable `PeriodicTimeBudget` beside its immutable
layout:

```text
source_end_fs
crossing_time_fs
resonance_decay_fs | unknown
maximum_time_fs
autoshutoff_threshold
extension_count
```

The construction manifest records the value; the Session only translates and
reads it back. Planning remains pure, native state remains in the Adapter, and
the observation reports what actually stopped the run.

### 2. Structure-aware initial cap

For the current ordinary periodic response route, use this planning candidate:

\[
t_{\mathrm{geom}} = t_{\mathrm{source,end}} + 4t_{\mathrm{cross}},
\]

\[
t_{\mathrm{cap},0} = \operatorname{ceil}_{100\,\mathrm{fs}}
\left[
\max\left(
t_{\mathrm{profile}},
t_{\mathrm{geom}},
t_{\mathrm{source,end}} + t_Q(\eta)
\right)
\right].
\]

`4 * t_cross` is a MetaCraft engineering margin for direct clearance and early
round trips; it is not an Ansys constant and must be natively characterized.
`t_profile` is a versioned starting cap for one declared response profile, not
a hidden universal constant. Until that characterization is accepted, the
existing `2000 fs` can remain the conservative profile seed. A known Q supplies
the third term; an unknown or explicitly high-Q structure cannot manufacture a
Q bound and must use the staged result below.

This formula makes physical extent, wavelength-dependent source duration and
known resonant burden explicit without pretending that geometry predicts all
decay.

### 3. One bounded feedback step

The numerical outcome closes the plan deterministically:

| native outcome | MetaCraft action |
| --- | --- |
| status `2`, finite response, conservation checks pass | accept and record actual shutdown evidence |
| status `1` | retry once with `ceil100(2 * t_cap,0)` or a predeclared equivalent extension |
| second status `1`, target observables converge within declared tolerances and physical gates pass | accept as `converged_by_extension` and record the residual-energy warning |
| second status `1`, target observables do not converge | return typed `time_budget_exhausted`; require an explicit resonant/convergence study |
| status `3` | return divergence fault; do not lengthen time blindly |
| status `2` but ripples, `T > 1`, or unstable comparison | tighten the declared autoshutoff threshold and run a bounded convergence check |

There is no open-ended per-cell tuning loop. The complete study owns one initial
policy; exceptional cells may consume its one declared extension and record that
fact in the run. A future resonant phase route should own a distinct Q/frequency-
resolution contract rather than silently deepening this ordinary periodic one.

## Trade-off and decision input

Using only one transit would be fast and explainable, but physically insufficient.
Keeping `2000 fs` forever is reproducible, but hides why the value is safe and
cannot scale to longer wavelengths, larger cells or future microwave structures.
A full adaptive convergence sweep would be robust, but it would turn a bounded
cell library into an uncontrolled experiment.

The staged policy keeps the middle path: length sets a visible floor, pulse and Q
complete the budget, autoshutoff ends cheap cells early, and one typed extension
contains exceptional cells.

## Subsequent decision

[ADR 0025](../adr/0025-let-geometry-budget-time-and-native-decay-close-it.md)
accepted the bounded ladder. It refined the proposal by using a reviewed
`100 fs` source-injection guard, rather than making generated-source timing a
second construction owner, and by requiring full sampled-field convergence
whenever reference-surface capability feeds downstream assembly. The Adapter
now records FDTD status, autoshutoff threshold and terminal level, and actual
end time for every ordinary or extended attempt. Representative fresh Native
execution remains an acceptance check on the implementation, not authority for
the numerical policy.
