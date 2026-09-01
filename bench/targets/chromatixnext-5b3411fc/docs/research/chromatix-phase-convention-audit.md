# Chromatix 0.4.0 and 0.6.0 phase-convention audit

## Question

Can Chromatix 0.4.0 or 0.6.0 be treated as a phase-consistent reference for coherent systems that mix propagation families, lenses, phase elements, and field addition?

## Scope and source identity

This audit reads the official Chromatix source at the immutable tags retained in `reference/chromatix`:

- `0.4.0`: commit [`727d7a39e9a0054cfe3a102440fcf931d31fd11a`](https://github.com/chromatix-team/chromatix/tree/727d7a39e9a0054cfe3a102440fcf931d31fd11a)
- `0.6.0`: commit [`d24bdf0022835bb8ce1cdcc6aeafbc7fcb39daee`](https://github.com/chromatix-team/chromatix/tree/d24bdf0022835bb8ce1cdcc6aeafbc7fcb39daee)

Claims below distinguish observable implementation facts from physical conclusions that still require independent qualification. Upstream behaviour is evidence, not scientific authority.

## Conclusion

Neither version is a sufficient phase reference for a mixed-family coherent simulator. Both can reproduce useful intensity behaviour inside their tested regimes, but they use different spatially uniform phase conventions across Angular Spectrum, Fresnel, Scalable Angular Spectrum, ordinary focal-plane, and high-numerical-aperture paths. Their `Field` values carry no axial optical path or phase reference with which to reconcile those conventions, and direct field addition performs no reference alignment.

Version 0.6.0 substantially reshapes the field and spectrum types, array layout, documentation, and typing, but it does not establish a common carrier-path contract. ChromatixNext should therefore reconstruct justified relative-field calculations while replacing the phase-reference architecture, not copy either release's tensors as universally coherent truth.

## Governing factorization

Under the ChromatixNext time convention `Re{E exp(-i omega t)}`, homogeneous scalar propagation over signed displacement `d` has the exact radiative transfer

`H_AS = exp(i d sqrt((2 pi n / wavelength)^2 - k_transverse^2))`.

At zero transverse frequency this is `exp(i 2 pi n d / wavelength)`. Factoring that common carrier gives

`H_AS = exp(i 2 pi n d / wavelength) * exp(i d (k_longitudinal - 2 pi n / wavelength))`.

The paraxial residual becomes

`H_Fresnel,residual = exp(-i pi wavelength d |spatial_frequency|^2 / n)`.

This is the basis for separating ChromatixNext's **Reference Path Effect** from its **Field Envelope Effect**. A constant diffraction-integral phase such as `-i` remains part of the Field Envelope Effect unless an independently justified physical path model says otherwise.

## Source findings

### Field state and coherent addition

Chromatix 0.4.0 stores complex samples, spacing, spectrum, spectral density, and transverse origin, but no axial position, accumulated optical path, coherence domain, or phase-reference state. Its `Field.__add__` directly adds `u` arrays. [0.4.0 field state](https://github.com/chromatix-team/chromatix/blob/727d7a39e9a0054cfe3a102440fcf931d31fd11a/src/chromatix/field.py#L19-L89) [0.4.0 field addition](https://github.com/chromatix-team/chromatix/blob/727d7a39e9a0054cfe3a102440fcf931d31fd11a/src/chromatix/field.py#L299-L305)

Chromatix 0.6.0 changes `Field` to an Equinox hierarchy and stores `u`, `dx`, transverse `origin`, and `spectrum`, but still has no axial optical-path reference. Direct addition again adds `u` arrays; the source contains TODOs for even field-type and shape checks. [0.6.0 field state](https://github.com/chromatix-team/chromatix/blob/d24bdf0022835bb8ce1cdcc6aeafbc7fcb39daee/src/chromatix/core/field.py#L42-L142) [0.6.0 field addition](https://github.com/chromatix-team/chromatix/blob/d24bdf0022835bb8ce1cdcc6aeafbc7fcb39daee/src/chromatix/core/field.py#L448-L465)

Neither tag contains a dedicated beam-splitter or coherent-combination primitive. Users can create those calculations with raw field arithmetic, but the library cannot prove that the operands share a plane, coherence relationship, polarization convention, or carrier reference.

### Angular Spectrum Propagation

Both versions compute a phase proportional to `abs(z) * n / wavelength * delay` and conjugate the transfer for negative `z`. For a normal propagating plane wave, `delay=1`, so the tensor receives the complete carrier factor `exp(i 2 pi n z / wavelength)`. [0.4.0 ASM kernel](https://github.com/chromatix-team/chromatix/blob/727d7a39e9a0054cfe3a102440fcf931d31fd11a/src/chromatix/functional/propagation.py#L476-L545) [0.6.0 ASM kernel](https://github.com/chromatix-team/chromatix/blob/d24bdf0022835bb8ce1cdcc6aeafbc7fcb39daee/src/chromatix/functional/propagation.py#L498-L579)

The `remove_evanescent=True` branch does not remove evanescent spectral samples. It clamps a negative longitudinal-square value to zero, obtains `delay=0`, and then evaluates a unit-magnitude transfer `exp(i * 0)=1` when no other filter removes that sample. This conflicts with the option name and documentation in both releases. The ordinary `False` branch forces the square root through `complex64`, which also prevents this kernel from serving as a `complex128` scientific reference.

The negative-distance conjugation reverses radiative phase. For evanescent samples it preserves decay rather than forming an exponentially growing algebraic inverse. That behaviour may be useful as an outgoing continuation, but it is not one operation with a single forward/inverse meaning. ChromatixNext's separate Scalar Angular Spectrum Propagation, Outgoing Near-Field Angular Spectrum Propagation, and future Angular Spectrum Reconstruction contracts are therefore justified.

### Fresnel transfer propagation

Both releases implement the Fresnel transfer phase as

`-pi * (wavelength / n) * z * |spatial_frequency - tilt|^2`.

The zero-frequency transfer is exactly one, so the tensor omits `exp(i 2 pi n z / wavelength)`. The relative paraxial transfer is useful, but it is expressed under a different carrier convention from the ASM tensor. [0.4.0 Fresnel transfer kernel](https://github.com/chromatix-team/chromatix/blob/727d7a39e9a0054cfe3a102440fcf931d31fd11a/src/chromatix/functional/propagation.py#L452-L473) [0.6.0 Fresnel transfer kernel](https://github.com/chromatix-team/chromatix/blob/d24bdf0022835bb8ce1cdcc6aeafbc7fcb39daee/src/chromatix/functional/propagation.py#L465-L495)

This is not intrinsically wrong for a Field Envelope. It becomes unsafe because the `Field` type does not say that the common carrier was factored out, while ASM returns a tensor in which it was retained.

### Single-transform Fresnel and Scalable Angular Spectrum

In both versions `optical_fft` supplies a forward `-1j` normalization factor, while `transform_propagate` immediately multiplies the returned field by `1j`. The two factors cancel. The method also omits the common carrier. Thus its spatially uniform phase convention differs not only from full-carrier ASM but also from a Fresnel transfer representation that retains the conventional diffraction-integral `-i` in the envelope. [0.4.0 transform propagation](https://github.com/chromatix-team/chromatix/blob/727d7a39e9a0054cfe3a102440fcf931d31fd11a/src/chromatix/functional/propagation.py#L35-L83) [0.4.0 optical FFT](https://github.com/chromatix-team/chromatix/blob/727d7a39e9a0054cfe3a102440fcf931d31fd11a/src/chromatix/functional/convenience.py#L9-L53) [0.6.0 transform propagation](https://github.com/chromatix-team/chromatix/blob/d24bdf0022835bb8ce1cdcc6aeafbc7fcb39daee/src/chromatix/functional/propagation.py#L34-L82) [0.6.0 optical FFT](https://github.com/chromatix-team/chromatix/blob/d24bdf0022835bb8ce1cdcc6aeafbc7fcb39daee/src/chromatix/functional/convenience.py#L9-L65)

The SAS precompensation uses the difference between exact and Fresnel longitudinal factors, `H_AS - H_Fr`, so their common `1` cancels; SAS then calls the same single-transform Fresnel path. SAS therefore inherits that path's carrier and scalar-phase convention rather than the full ASM convention. [0.4.0 SAS path](https://github.com/chromatix-team/chromatix/blob/727d7a39e9a0054cfe3a102440fcf931d31fd11a/src/chromatix/functional/propagation.py#L86-L169) [0.6.0 SAS path](https://github.com/chromatix-team/chromatix/blob/d24bdf0022835bb8ce1cdcc6aeafbc7fcb39daee/src/chromatix/functional/propagation.py#L85-L166)

The `skip_initial_phase` and `skip_final_phase` booleans allow callers to remove physical chirp factors without creating a separately named and qualified scientific operation. ChromatixNext should reject these as public scientific switches.

### Lenses and far-field paths

The ordinary thin-lens operation in both releases applies only the relative quadratic phase `-pi n r^2 / (wavelength f)`. This is appropriate for an ideal lens model that makes no claim about centre thickness or material delay; it must not be interpreted as the complete interferometric phase of a physical lens. [0.4.0 lenses](https://github.com/chromatix-team/chromatix/blob/727d7a39e9a0054cfe3a102440fcf931d31fd11a/src/chromatix/functional/lenses.py#L37-L61) [0.6.0 lenses](https://github.com/chromatix-team/chromatix/blob/d24bdf0022835bb8ce1cdcc6aeafbc7fcb39daee/src/chromatix/functional/lenses.py#L37-L62)

There is no independently named Fraunhofer propagation primitive in either tag. Ordinary `ff_lens` delegates to `optical_fft`, which omits the path carrier. The high-NA focal path instead includes `exp(i k s_z f)`; its on-axis value contains `exp(i k f)`. The scalar/focal and high-NA paths therefore cannot be assumed to share one carrier convention. [0.4.0 focal paths](https://github.com/chromatix-team/chromatix/blob/727d7a39e9a0054cfe3a102440fcf931d31fd11a/src/chromatix/functional/lenses.py#L64-L158) [0.6.0 focal paths](https://github.com/chromatix-team/chromatix/blob/d24bdf0022835bb8ce1cdcc6aeafbc7fcb39daee/src/chromatix/functional/lenses.py#L65-L154)

The Collins/ray-transfer path contains relative input, transfer, and output quadratic phases but no explicit common optical path through the represented system. A ray-transfer matrix alone does not determine that missing path; ChromatixNext must not infer it from the matrix. [0.4.0 ray transfer](https://github.com/chromatix-team/chromatix/blob/727d7a39e9a0054cfe3a102440fcf931d31fd11a/src/chromatix/functional/rays.py#L57-L85) [0.6.0 ray transfer](https://github.com/chromatix-team/chromatix/blob/d24bdf0022835bb8ce1cdcc6aeafbc7fcb39daee/src/chromatix/functional/rays.py#L102-L154)

### Phase and material elements

Chromatix 0.4.0 optionally scales a supplied phase by the first spectral wavelength divided by each wavelength. Chromatix 0.6.0 moves the same rule into `Spectrum.spectral_modulation`; `central_wavelength` is still defined as element zero even though spectra may otherwise be authored in any order. [0.4.0 spectral phase scaling](https://github.com/chromatix-team/chromatix/blob/727d7a39e9a0054cfe3a102440fcf931d31fd11a/src/chromatix/functional/phase_masks.py#L30-L86) [0.6.0 spectral phase scaling](https://github.com/chromatix-team/chromatix/blob/d24bdf0022835bb8ce1cdcc6aeafbc7fcb39daee/src/chromatix/functional/phase_masks.py#L29-L124) [0.6.0 central wavelength](https://github.com/chromatix-team/chromatix/blob/d24bdf0022835bb8ce1cdcc6aeafbc7fcb39daee/src/chromatix/core/spectrum.py#L87-L103)

This encodes two different physical models behind `spectrally_modulate`: a phase map at an assumed first-channel reference wavelength and a wavelength-independent dimensionless phase. ChromatixNext's separate Optical Path Modulation, Common Phase Modulation, and explicit Reference Phase Map conversion should be retained.

Thin-sample operations apply refractive-index change `dn`, not the complete background index. That is a relative sample effect and can preserve the reference when background-medium propagation is separately declared. A uniform or long baseline thickness must not be guessed from a sampled map. [0.4.0 thin samples](https://github.com/chromatix-team/chromatix/blob/727d7a39e9a0054cfe3a102440fcf931d31fd11a/src/chromatix/functional/samples.py#L21-L101) [0.6.0 thin samples](https://github.com/chromatix-team/chromatix/blob/d24bdf0022835bb8ce1cdcc6aeafbc7fcb39daee/src/chromatix/functional/samples.py#L29-L132)

The retarder implementation factors its eigenphase pair symmetrically with `exp(-i eta/2)`. It models relative retardance rather than a physical plate's mean material delay. This is a legitimate idealized Field Envelope Effect, but a physical birefringent-plate model needs a separately declared Reference Path Effect. [0.4.0 retarder](https://github.com/chromatix-team/chromatix/blob/727d7a39e9a0054cfe3a102440fcf931d31fd11a/src/chromatix/functional/polarizers.py#L160-L181) [0.6.0 retarder](https://github.com/chromatix-team/chromatix/blob/d24bdf0022835bb8ce1cdcc6aeafbc7fcb39daee/src/chromatix/functional/polarizers.py#L168-L192)

### Polarization handedness mapping

Both upstream tags construct their value named `left_circular` with transverse
components equivalent to `(Ex, Ey) = (1, +i) / sqrt(2)`, and their value named
`right_circular` with `(Ex, Ey) = (1, -i) / sqrt(2)`. ChromatixNext freezes the
explicit time dependence `Re{E exp(-i omega t)}` and canonical `(Ex, Ey, Ez)`
component order. For propagation along `+z`, it therefore names
`(1, -i, 0) / sqrt(2)` left-circular and `(1, +i, 0) / sqrt(2)`
right-circular.

The migration mapping is consequently name-reversing:

| Upstream constructor | Explicit upstream transverse vector | ChromatixNext value |
| --- | --- | --- |
| `left_circular()` | `(1, +i) / sqrt(2)` | `Polarization.right_circular()` |
| `right_circular()` | `(1, -i) / sqrt(2)` | `Polarization.left_circular()` |

This table maps explicit vectors rather than treating handedness words as
scientific evidence. ChromatixNext provides no compatibility alias: source
migration must choose the value whose Jones vector preserves the intended
time evolution. Ordinary tests independently advance both public states by a
quarter period, and the mutation gate proves that reversing either the time
convention or the handedness is detected.

### Frequency and support contracts

Both plane-wave generators apply `exp(i * kykx dot position)`, which gives `kykx` angular-wavevector units. The propagation kernels directly subtract the same parameter from the ordinary spatial-frequency grid in cycles per length. Version 0.6.0 explicitly distinguishes `f_grid` from `k_grid=2 pi f_grid`, making the unit conflict visible while retaining the subtraction from `f_grid`. [0.4.0 plane wave](https://github.com/chromatix-team/chromatix/blob/727d7a39e9a0054cfe3a102440fcf931d31fd11a/src/chromatix/functional/sources.py#L152-L205) [0.6.0 plane wave](https://github.com/chromatix-team/chromatix/blob/d24bdf0022835bb8ce1cdcc6aeafbc7fcb39daee/src/chromatix/functional/sources.py#L212-L293) [0.6.0 frequency grids](https://github.com/chromatix-team/chromatix/blob/d24bdf0022835bb8ce1cdcc6aeafbc7fcb39daee/src/chromatix/core/field.py#L185-L218)

The 0.6.0 padding calculators accept no refractive index and use vacuum wavelength where the main propagation kernel uses `wavelength/n`. Its ASM band-limit calculation likewise does not consistently expose the medium wavelength. This is a confirmed internal contract inconsistency for `n != 1`; the direction and size of the resulting support error require independent formula-based qualification rather than an assertion from code inspection alone. [0.6.0 padding calculations](https://github.com/chromatix-team/chromatix/blob/d24bdf0022835bb8ce1cdcc6aeafbc7fcb39daee/src/chromatix/functional/propagation.py#L582-L655)

### Test evidence

The propagation tests construct an analytic Fresnel field containing `exp(i 2 pi n z / wavelength)` but compare only its intensity with numerical results. Forward/backward checks compare one method with its own inverse convention. The tests do not compare complex phase between ASM and Fresnel, between transform and transfer Fresnel, or across unequal interferometer paths. [0.4.0 propagation tests](https://github.com/chromatix-team/chromatix/blob/727d7a39e9a0054cfe3a102440fcf931d31fd11a/tests/test_propagate.py) [0.6.0 propagation tests](https://github.com/chromatix-team/chromatix/blob/d24bdf0022835bb8ce1cdcc6aeafbc7fcb39daee/tests/test_propagate.py)

These tests support intensity reconstruction within their examples. They do not qualify the library's cross-family coherent phase.

## ChromatixNext reconstruction decision

| Upstream behaviour | Treatment | Reason |
| --- | --- | --- |
| ASM relative longitudinal phase | Preserve after independent derivation | It represents the scalar Helmholtz angular-spectrum relation. |
| ASM full carrier inside the tensor | Reshape | Move the uniform path into Optical Path Reference and retain only residual phase in Field Envelope. |
| Fresnel transfer residual phase | Preserve after validity qualification | It is the paraxial envelope transfer under an explicit carrier factorization. |
| Fresnel transform normalization and constant phase | Re-derive | Do not copy the `1j` cancellation without a declared complete formula and phase-sensitive evidence. |
| SAS relative precompensation | Preserve only through the SAS paper and independent evidence | It must inherit the same reference/envelope factorization as other propagation families. |
| `remove_evanescent` boolean | Reject | Replace with separately qualified radiative and outgoing near-field capabilities. |
| `skip_initial_phase` / `skip_final_phase` | Reject | They remove physical factors through unqualified implementation switches. |
| Raw `kykx` | Reject | Use strong Propagation Direction or Transverse Phase Gradient values with explicit units. |
| First-wavelength phase scaling | Reject | Use Optical Path Modulation or explicit Reference Phase Map conversion. |
| Ideal thin-lens quadratic phase | Preserve as relative-only model | It has zero Reference Path Effect unless physical thickness is separately modeled. |
| Raw Field addition | Reject | Use Coherent Combination with coherence checks and Reference Alignment. |
| Upstream complex outputs | Retain as Upstream Observations only | They document release behaviour but cannot establish scientific phase truth. |

The implemented base field contract now makes that factorization explicit.
`OpticalPathReference` contains one finite SI-metre length per Spectrum entry;
`OpticalField` requires the reference count to match the Spectrum count.
Sources initialize it to zero. Homogeneous Angular Spectrum
propagation applies `exp(i d (kz - k))` to the envelope and adds
`n(wavelength) * d` to the reference. Reconstructing
`envelope * exp(i 2 pi reference / wavelength)` therefore recovers the complete
complex Angular Spectrum field. Signed distance and dispersive media follow the
same rule; destination translation and Propagation Exterior leave the reference
unchanged. For a trainable distance, the per-spectrum reference length stays a
graph-bearing zero-dimensional real Tensor rather than a Python-float snapshot,
so autograd covers both the residual envelope and the factored uniform carrier;
the carrier gradient is observable through coherent recombination of unequal
references, not through the intensity of an isolated single field.

## Required Component Evidence

No propagation, phase, lens, or coherent-combination Component should be
public using intensity-only evidence. Its Component Evidence must include,
where applicable:

1. zero-transverse-frequency carrier/reference advancement;
2. analytic complex residual phase at multiple admitted spatial frequencies;
3. complex-field agreement between exact and approximate families inside a quantified overlap regime after Reference Alignment;
4. unequal-arm interference at zero, quarter-, and half-wavelength Optical Path Difference;
5. long common paths with sub-wavelength Anchor differences and differentiable Adjustment differences;
6. true removal of radiatively forbidden support and independently qualified outgoing evanescent decay;
7. medium-index, wavelength, direction, shifted-grid, and non-square-grid cases;
8. `complex64` and `complex128` forward and independent gradient evidence;
9. consistency across both supported Precisions and every claimed native
   execution path.

## Architectural consequence

The audit supports the accepted ChromatixNext rule that every field-transforming
Optical Component updates the Field Envelope and Optical Path Reference as one
physical action. This rule is not cosmetic metadata: it is the missing
scientific seam that prevents individually useful upstream kernels from
becoming mutually inconsistent when assembled into a coherent optical path.
