# Angular-spectrum evanescent support

Status: supporting analysis accepted by ADR 0107

## Question

Should ChromatixNext always discard evanescent spatial frequencies in Angular Spectrum Propagation, always retain them, or expose distinct scientific contracts?

## Physical distinction

For the time convention `exp(-i angular_frequency time)`, a scalar field prescribed on one transverse plane in a homogeneous medium has the angular-spectrum continuation

```text
field(x, y, separation)
  = inverse_fourier[
      spectrum(k_x, k_y)
      exp(i longitudinal_wave_number separation)
    ]

longitudinal_wave_number
  = sqrt(medium_wave_number^2 - k_x^2 - k_y^2)
```

The outgoing branch has nonnegative real and imaginary parts.

- When `k_x^2 + k_y^2 <= medium_wave_number^2`, the longitudinal wave number is real. The transfer factor has unit magnitude and describes a propagating, or radiative, plane-wave component.
- When `k_x^2 + k_y^2 > medium_wave_number^2`, the longitudinal wave number is imaginary. For positive separation into the selected outgoing half-space, the transfer magnitude is `exp(-decay_rate separation)`.

Evanescent components are therefore part of the angular-spectrum representation of fields near subwavelength sources and interfaces; they are not merely numerical error. Dipole-radiation analysis explicitly separates travelling and evanescent components and shows the latter decaying away from the source plane. [Foley and Arnoldus, 2003](https://doi.org/10.1364/FIO.2003.WPP4)

This does not mean that every high discrete spatial frequency in an arbitrary sampled scalar array is a physically established evanescent field. Its interpretation depends on the boundary field, half-space, medium, polarization model, and sampling. Homogeneous Angular Spectrum Propagation transports an already defined boundary spectrum; it does not solve the material interface or aperture that generated that spectrum.

## Forward continuation is not inverse propagation

For one evanescent component with decay rate `decay_rate > 0`, forward continuation over positive separation has singular value

```text
forward_gain = exp(-decay_rate separation)
```

The algebraic inverse would multiply by

```text
inverse_gain = exp(+decay_rate separation)
```

and therefore amplifies measurement noise and floating-point error exponentially. Published inverse-diffraction analysis identifies this divergence and the need for regularization, with a direct trade-off against recovered super-resolution. [Nieto-Vesperinas, 2004](https://doi.org/10.1364/JOSAA.21.000491) Boundary-condition analysis likewise treats wave backpropagation, phase conjugation, and time reversal as related but non-identical constructions rather than one signed-distance shortcut. [Liu and Waag, 1997](https://doi.org/10.1109/58.585184)

Changing the longitudinal branch so that evanescent components decay on both sides of a source plane is a valid outgoing-half-space construction, but it is not the inverse of the positive-separation operator. A signed parameter cannot express both meanings without ambiguity.

## Numerical consequences for the locked precisions

The local Python 3.12 research environment reports PyTorch `2.12.0+cu130`, float32 maximum `3.40282e38`, and float64 maximum `1.79769e308`. Consequently:

| Storage | Approximate exponential overflow | Approximate smallest-normal decay |
| --- | ---: | ---: |
| `complex64` components | `exp(88.7)` | `exp(-87.3)` |
| `complex128` components | `exp(709.8)` | `exp(-708.4)` |

Subnormal representation extends decay slightly, but it is not a scientific stability guarantee and may differ in effective behaviour across execution targets. More importantly, inverse reconstruction becomes noise-dominated long before arithmetic overflow. `complex128` postpones floating-point failure; it does not cure the ill-posed inverse.

Forward outgoing continuation is numerically bounded, but high-spatial-frequency amplitudes and their input-field gradients vanish exponentially with separation. Gradients with respect to wavelength, refractive index, or another parameter that moves a discrete sample across the propagating/evanescent cutoff also require a separately fixed-support or range-stable Gradient Contract.

## Sampling and band limiting are separate questions

The physical light-cone boundary

```text
k_x^2 + k_y^2 = medium_wave_number^2
```

separates propagating and evanescent components. It is not the same as an alias-safe numerical band limit. A numerical angular-spectrum method may need to discard additional *propagating* frequencies because its sampled transfer function, finite computational window, propagation distance, or shifted destination window cannot represent them without aliasing. Matsushima and Shimobaba show that ordinary sampled ASM can produce severe errors and introduce a distance- and sampling-dependent band limit to control them. [Matsushima and Shimobaba, 2009](https://doi.org/10.1364/OE.17.019662)

ChromatixNext must therefore derive two named supports and take their justified intersection:

1. **Physical Longitudinal Support** determines whether the selected scientific contract admits radiative components only or radiative plus outgoing evanescent components.
2. **Alias-Safe Numerical Support** determines which admitted components the finite sampled calculation can propagate within its Qualification Envelope.

A single `bandlimit` or `remove_evanescent` boolean cannot represent both decisions.

## What upstream Chromatix 0.4.0 and 0.6.0 do

Both audited tags expose `remove_evanescent=False` on `asm_propagate`. Their transfer-kernel calculation:

1. computes a complex square root when evanescent removal is disabled;
2. uses the absolute propagation distance in the phase;
3. conjugates the complete transfer value for negative distance.

For a propagating component this conjugates its phase. For an evanescent component the positive-distance transfer value is real exponential decay, so conjugation leaves the same decay. Negative distance is therefore an outgoing/decaying continuation on the other side, not the algebraic inverse advertised by a generic signed-distance interpretation. Both tags also hard-code `complex64` in that complex square root even when a wider precision is requested. See the retained [upstream propagation source](../../reference/chromatix/src/chromatix/functional/propagation.py) and its limited [propagation tests](../../reference/chromatix/tests/test_propagate.py).

The upstream test for `remove_evanescent=True` verifies a radiative-only forward/backward round trip. The default evanescent-retaining path has an aperture-intensity comparison but no evanescent analytic case, half-space contract, negative-distance inverse test, cutoff-gradient test, or precision-range test.

## Scalar and vector scope

Retaining evanescent samples in a scalar Helmholtz transfer factor does not establish full electromagnetic near-field support. Near subwavelength apertures and material interfaces, longitudinal field components, transversality, polarization coupling, and boundary conditions can materially affect the result. Recent full-vector ASM work explicitly distinguishes a pseudo-vector approach that independently applies scalar propagation to stored components from an electromagnetic construction that enforces vector projection and interface behaviour. [Song, He, and Yuan, 2025](https://doi.org/10.1088/2515-7647/ae0384)

The current ChromatixNext implementation stores only a scalar `PolarizationContract` and applies one scalar transfer kernel. It can presently qualify scalar homogeneous-medium continuation only. A future Cartesian vector Optical Field needs an independently qualified vector Angular Spectrum operation; it must not inherit a scalar near-field claim automatically.

## Options

### Always discard

Advantages:

- bounded, unit-modulus transfer on retained modes;
- meaningful radiative forward/backward round trips;
- suitable for most macroscopic free-space Fourier-optics workflows;
- simple gradients and energy invariants.

Costs:

- not a complete outgoing scalar half-space continuation;
- loses genuine near-field content from subwavelength sources and interfaces;
- can change short-step multislice behaviour;
- prevents future near-field research without an API break.

### Always retain

Advantages:

- represents the complete sampled outgoing scalar half-space spectrum when the boundary field is physically valid;
- preserves a path toward near-field and subwavelength workflows;
- remains bounded for positive outward separation.

Costs:

- signed negative distance becomes physically ambiguous;
- users may mistake decaying-on-both-sides continuation for an inverse;
- scalar component-wise propagation may overstate electromagnetic validity;
- cutoff, underflow, gradient, and sampling requirements differ materially from ordinary radiative propagation.

### Separate explicit contracts

Advantages:

- retains generality without lying about invertibility or vector physics;
- permits narrow, evidence-backed qualification envelopes;
- keeps inverse reconstruction and its regularization out of forward propagation;
- allows the planner to estimate decay range and memory without changing scientific meaning.

Cost:

- requires two explicit scientific contracts and separate evidence.

## Recommendation

Keep one **Angular Spectrum Propagation** family, but admit two independently qualified scientific contracts:

1. **Radiative Angular Spectrum Propagation**
   - admits propagating components only;
   - may use signed axial displacement under a declared plane orientation;
   - qualifies radiative forward/backward equivalence;
   - is the ordinary workstation Fourier-optics contract.
2. **Outgoing Near-Field Angular Spectrum Propagation**
   - admits both radiative and evanescent components already present in a valid scalar boundary field;
   - uses a nonnegative `plane_separation` plus an explicit destination half-space, never an ambiguous signed distance;
   - applies the outgoing/decaying branch;
   - reports the physical cutoff, alias-safe support, maximum decay exponent, underflow risk, and retained support during Preflight;
   - initially qualifies input-field gradients only and only for scalar homogeneous media;
   - requires analytic single-mode decay cases, direct Rayleigh-Sommerfeld or Weyl references, distance refinement, both precisions, and CPU/CUDA parity.

Create a future **Angular Spectrum Reconstruction** capability outside forward propagation for inverse use. It must name a regularization and noise/data model; raw exponential inversion is rejected.

This split is more general than always discarding evanescent content and more reliable than upstream's boolean. It also leaves room for later vector near-field propagation and material-interface scattering without allowing a scalar FFT kernel to claim those domains prematurely.
