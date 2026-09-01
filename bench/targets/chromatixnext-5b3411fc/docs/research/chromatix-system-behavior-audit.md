# Chromatix 0.4/0.6 system-behaviour audit

Status: primary-source audit for the scientific-coverage wayfinder

## Question and scope

This audit asks what *physical and system behaviour* Chromatix 0.4.0 and
0.6.0 actually provide, rather than how many public names they export. It is
intended to support the decision in **Freeze the scientific coverage
boundary**. It does not propose a new public interface or authorize
implementation.

The frozen upstream sources are:

- tag `0.4.0`, commit
  `727d7a39e9a0054cfe3a102440fcf931d31fd11a`;
- tag `0.6.0`, commit
  `d24bdf0022835bb8ce1cdcc6aeafbc7fcb39daee`.

All upstream citations below use the form `tag:path:lines` or
`tag:notebook:cell`. The source, tests, examples and notebooks in the local
`reference/chromatix` clone are the primary evidence. ChromatixNext ownership
is interpreted using `CONTEXT.md`, ADR-0001 through ADR-0004, and the current
production source. The paper is not needed to infer code behaviour where the
tagged implementation itself owns the fact.

## Executive finding

Chromatix has only three library-level system classes in both releases:
`OpticalSystem`, `Microscope`, and `Optical4FSystemPSF`
(`0.4.0:src/chromatix/systems/__init__.py`;
`0.6.0:src/chromatix/systems/__init__.py`). None has a direct test in either
tag. CGH, DMD holography, Holoscope, Fourier ptychography, Gabor holography,
and aberration fitting are notebook-defined research workflows, not reusable
library systems.

The durable scientific behaviour is therefore below the upstream `systems`
package:

1. strong sampled-field semantics;
2. named sources and optical actions;
3. separately selected propagation methods;
4. scalar and polarized sample interactions;
5. intensity formation, pixel integration/resampling, convolutional imaging
   and noise;
6. ordinary differentiable composition used by Examples.

ChromatixNext should cover those stable behaviours while rejecting the
untyped sequential `OpticalSystem`, the method-switching `Propagate`, the
duplicate functional/element surfaces, and notebook-specific workflow types.
The upstream `Microscope` is useful as a behaviour decomposition, but not as a
class to copy. Its assumptions must be made explicit before its steps can be
reassembled from ChromatixNext Physical Values, Optical Components, an
Assembly, and an Example.

Experimental Modified Born and fluorescence are not part of the first
complete scientific gate. Both remain possible future solver slices, each
requiring an independent physical design and Component Evidence.

## The three upstream system objects

### OpticalSystem is an unchecked unary sequence

Both releases execute the first callable with all supplied positional and
keyword arguments, then feed its result through every remaining callable as a
single positional argument:

```text
first(*args, **kwargs)
  -> second(field)
  -> third(field)
  -> ...
  -> final value
```

The first callable may create a `Field`; every middle callable is merely
assumed to accept and return a `Field`; the final callable may return an
array. There is no empty-sequence check, port declaration, topology check,
branch, merge, named output, field-compatibility check, or enforcement that an
array-returning callable is last
(`0.4.0:src/chromatix/systems/optical_system.py:11-36`;
`0.6.0:src/chromatix/systems/optical_system.py:11-39`).

The 0.4 implementation is a compact Flax module; 0.6 is an explicitly
initialized Equinox module. The dataflow behaviour is otherwise unchanged.
The migration is execution-framework work, not a new physical system model.

ChromatixNext already has the better ownership:

- direct Component Calls express a simple physical reading order;
- a frozen Assembly owns branched, merged or multi-output topology;
- `describe(...)` and Assembly Check reject invalid whole paths before field
  allocation;
- Named Outputs close the path explicitly.

Accordingly, upstream `OpticalSystem` belongs to **reject**, not parity work.
Its useful behaviour is already divided between direct calls and Assembly
(`CONTEXT.md`, “Optical Composition” and “Assembly”; ADR-0002).

### Microscope is a shift-invariant incoherent image-formation pipeline

`Microscope` does not coherently propagate through a sample. It assumes a
planewise spatially invariant intensity PSF and models fully incoherent
imaging by convolving the sample with that PSF. Version 0.6 states this
limitation explicitly
(`0.6.0:src/chromatix/systems/microscopes.py:20-33`).

Its full call chain is:

1. Call an injected `system_psf(microscope, *args, **kwargs)`.
2. Accept either a complex `Field` or an array already interpreted as PSF
   intensity.
3. If it is a `Field`, reduce it to intensity. This sums polarization and
   applies spectral density according to the field type. If it is an array,
   no physical type distinguishes intensity from another real array.
4. Infer the simulated PSF spacing. For a `Field`, assume identical
   rectangular spacing at every wavelength and use one central/first
   wavelength spacing. For an array, derive spacing from sensor shape and the
   unpadded PSF shape.
5. Infer the unpadded shape from `padding_ratio`, centre-crop the intensity
   PSF, then optionally multiply it by a sigmoid taper.
6. Resample the processed PSF to sensor sampling.
7. Fourier-convolve sample and PSF over selected axes.
8. Send the image through the sensor without a second resampling; the sensor
   may sum an axis or devices and then add shot noise.

The 0.4 implementation is at
`0.4.0:src/chromatix/systems/microscopes.py:87-173`; the clearer 0.6 form is at
`0.6.0:src/chromatix/systems/microscopes.py:190-297`.

This pipeline carries several important scientific assumptions and limits:

- It is an incoherent intensity model, not a general coherent microscope.
- The PSF is planewise shift invariant. Space-variant systems are not
  represented by the convolution.
- Multiple wavelengths are reduced to intensity before convolution, but PSF
  resampling assumes their spacings are equal. The source contains an explicit
  warning about this
  (`0.6.0:src/chromatix/systems/microscopes.py:248-252`).
- A raw array is silently assumed to be intensity, and its spacing is inferred
  rather than carried by a Physical Value
  (`0.6.0:src/chromatix/systems/microscopes.py:211-219,253-260`).
- Crop and taper change the PSF but are not followed by an explicit PSF
  normalization. `padding_ratio` is converted through integer truncation, so
  odd sizes need deliberate validation rather than copied arithmetic
  (`0.6.0:src/chromatix/systems/microscopes.py:241-268`).
- In 0.6, `convolution_axes=(-2,-1)` means independent 2D plane convolution;
  `(-3,-2,-1)` requests a 3D convolution. The choice is supplied as array
  axes, not a named physical imaging model
  (`0.6.0:src/chromatix/systems/microscopes.py:78-86,290-292`).
- Sensor noise treats image values directly as Poisson means. There is no
  exposure time, quantum efficiency, photon-energy conversion, read noise,
  dark current or saturation model. Exact Poisson forward values use a
  Gaussian surrogate derivative and are always cast to float32
  (`0.6.0:src/chromatix/ops/noise.py:38-68`).
- The 0.6 `BasicSensor` constructor path intends to require a random key when
  noise is enabled, but the expression `key is not None, ("...")` is a tuple,
  not an assertion. The later random split fails indirectly instead of the
  owning physical concept reporting the invalid state
  (`0.6.0:src/chromatix/elements/sensors.py:96-105`).
- Resampling either sum-pools integer blocks or interpolates and divides by
  the scale product, apparently intending count/flux preservation. The sensor
  test checks shapes and repeated-call equality, not conservation
  (`0.6.0:src/chromatix/ops/resample.py:11-74`;
  `0.6.0:tests/test_sensors.py:8-49`).
- Resampling terminology also drifts: documentation advertises
  `"pooling"` while dispatch checks for `"pool"`. This is an interface defect,
  not a second physical method
  (`0.6.0:src/chromatix/ops/resample.py:77-126`).

The Holoscope notebook exposes the same steps without the wrapper: objective
point-source PSF, phase mask, Fourier lens, intensity, centre crop, taper,
sum-downsampling, per-plane convolution, depth sum, then Poisson noise
(`0.6.0:docs/examples/holoscope.ipynb:cells 12,16,23,31`). It then repeats the
workflow with `Microscope` and `Optical4FSystemPSF`
(`0.6.0:docs/examples/holoscope.ipynb:cells 35-37`). This is evidence that the
system class is a convenience composition, not a new optical law.

ChromatixNext should therefore not create a generic `Microscope` role. Its
steps divide as follows:

| Behaviour | ChromatixNext ownership |
| --- | --- |
| Point-source PSF generation | Source plus Propagation/Element Components |
| Field-to-intensity reduction | Detection |
| PSF crop and taper | explicit imaging preparation; likely private Numerical Support behind a named physical action |
| Pixel integration/resampling | Detection, with sampling and conservation semantics fixed first |
| Shift-invariant intensity convolution | reusable incoherent image-formation behaviour; requires strong sample/PSF value semantics before placement is final |
| Depth or spectral integration | Detection |
| Noise and quantization | Detection when a physical sensor contract exists; otherwise Example |
| A complete fluorescence microscope | Assembly plus Example |

The unresolved item is not a class name. It is whether sample emission,
intensity PSF and detected image need additional strong Physical Values.
That decision must precede implementation of reusable incoherent imaging.
The audit recommends admitting the narrow physical behaviour

```text
image(x, y) = sum_over_planes(sample_intensity_plane * psf_intensity_plane)
```

to the first complete scope, while keeping fluorescence emission outside it.
Admission means the strong input/output semantics must be fixed; it does not
mean admitting the upstream `Microscope` class.

### Optical4FSystemPSF is a three-action PSF recipe

Version 0.6 performs:

1. enlarge the simulation shape using the parent microscope padding ratio;
2. derive Fourier-plane spacing
   `f_tube * wavelength / (n * height * output_spacing)`;
3. generate the field after an objective for a point source defocused by `z`,
   including the objective focal length and NA;
4. apply a 2D phase map in radians;
5. apply an `f-f` Fourier lens with the tube-lens focal length;
6. return the complex `Field`, leaving intensity formation, crop, taper and
   resampling to `Microscope`.

The implementation and spacing formula are at
`0.6.0:src/chromatix/systems/microscopes.py:300-365`. The corresponding
objective source, phase action and lens are independent library behaviours
(`0.6.0:src/chromatix/functional/sources.py:122`;
`0.6.0:src/chromatix/functional/phase_masks.py:29`;
`0.6.0:src/chromatix/functional/lenses.py:64`).

Version 0.4 uses the same three-action recipe through `OpticalSystem`, but has
no separate tube-lens focal length: it uses `microscope.f` both in the
required-spacing formula and in `FFLens`
(`0.4.0:src/chromatix/systems/microscopes.py:176-236`). Version 0.6 adds
mandatory `f_tube`, separating objective and tube-lens focal lengths. This is
a real physical correction/extension, not merely an Equinox migration.

The 0.6 source-distributed `examples/parallel_imaging.py` was not updated for
that required argument: both constructors omit `f_tube`
(`0.6.0:examples/parallel_imaging.py:22-35,62-78`, compared with
`0.6.0:src/chromatix/systems/microscopes.py:322-332`). This static mismatch is
additional evidence that upstream examples and systems were not under one
release gate.

ChromatixNext should express this recipe as an Assembly/Example made from an
Objective Point Source, phase/optical-path action, Fourier-lens propagation
and Intensity Detection. It should not copy `Optical4FSystemPSF` as a special
system class.

## What the sixteen notebooks actually demonstrate

Both tags contain the same sixteen files under `docs/examples/`, although
many were rewritten from Flax elements to Equinox or direct functions in
0.6. They fall into four groups.

### Stable numerical and physical demonstrations

| Notebook | Behaviour | Correct ownership | Primary evidence |
| --- | --- | --- | --- |
| `bandlimited_angular_spectrum.ipynb` | BLAS and off-axis propagation | Propagation plus Example | `0.6.0:docs/examples/bandlimited_angular_spectrum.ipynb:cells 5,7,11,13` |
| `off_axis_propagation.ipynb` | carrier and shifted destination window | Propagation plus Destination Grid; Example | `0.6.0:docs/examples/off_axis_propagation.ipynb:cells 1,3,5,7,9` |
| `rescaled_propagation.ipynb` | scaled/shifted propagation, CZT and runtime comparison | Propagation methods; CZT in private Numerical Support; Example | `0.6.0:docs/examples/rescaled_propagation.ipynb:cells 4,6,13,15,17,19-20` |
| `sas.ipynb` | SAS versus Fresnel-transform and padded ASM | separate Propagation; Example | `0.6.0:docs/examples/sas.ipynb:cells 3,6,8,10` |
| `gabor_hologram.ipynb` | forward/back propagation of inline hologram and method suitability | Propagation plus Example | `0.6.0:docs/examples/gabor_hologram.ipynb:cells 3,9,11,13` |
| `highNA_PSF.ipynb` | scalar and vectorial high-NA focusing | vector Physical Value and high-NA Propagation; Example | `0.6.0:docs/examples/highNA_PSF.ipynb:cells 4,8` |
| `polarized_multislice.ipynb` | birefringent vector multislice | Sample solver; Example | `0.6.0:docs/examples/polarized_multislice.ipynb:cells 3,5,7` |

These notebooks call library primitives but are not library systems. Their
tagged sources are the correspondingly named files under
`0.6.0:docs/examples/`. The high-NA kernel itself explicitly assumes one
wavelength and a square input
(`0.6.0:src/chromatix/functional/lenses.py:98-156`); those limits must not be
lost behind a general-sounding name.

### Research workflows built in notebooks

| Notebook | Custom workflow | Correct ownership | Primary evidence |
| --- | --- | --- | --- |
| `cgh.ipynb` | train a phase map through plane wave, phase action, Fourier lens, multi-depth Fresnel transfer | Example-owned optimization | `0.6.0:docs/examples/cgh.ipynb:cells 7,21,27-28` |
| `dmd.ipynb` | train a binarized amplitude mask followed by ASM | Example-owned optimization | `0.6.0:docs/examples/dmd.ipynb:cells 10,13-14` |
| `fourier_ptychography.ipynb` | tilted illuminations, complex thin sample, two-lens relay, intensity loss and reconstruction | Example-owned inverse workflow | `0.6.0:docs/examples/fourier_ptychography.ipynb:cells 9,13,21` |
| `holoscope.ipynb` | 3D incoherent image formation with engineered PSF | Assembly plus Example | `0.6.0:docs/examples/holoscope.ipynb:cells 12,16,23,31,35-37` |
| `seidel_fitting.ipynb` | fit Seidel coefficients from noisy PSFs | Example-owned inverse workflow | `0.6.0:docs/examples/seidel_fitting.ipynb:cells 6,8,10,14` |
| `zernike_fitting.ipynb` | fit Zernike coefficients from noisy PSFs | Example-owned inverse workflow | `0.6.0:docs/examples/zernike_fitting.ipynb:cells 4,6,8,12` |

For example, the 0.6 CGH notebook defines its own `CGH(eqx.Module)` and its
own loss/update loop (`0.6.0:docs/examples/cgh.ipynb:cells 7,21,27-28`).
Fourier ptychography defines `tilted_illumination_system`, a loss, optimizer
and nested acquisition loop in the notebook
(`0.6.0:docs/examples/fourier_ptychography.ipynb:cells 9,21`). These are
exactly the Example-owned workflows established by ADR-0004, not missing
production roles.

The migration history reinforces that conclusion. The 0.4 CGH and DMD
notebooks used `OpticalSystem` and Flax elements, whereas 0.6 rewrites them as
custom Equinox modules with direct functional calls
(`0.4.0:docs/examples/cgh.ipynb`; `0.6.0:docs/examples/cgh.ipynb`;
`0.4.0:docs/examples/dmd.ipynb`; `0.6.0:docs/examples/dmd.ipynb`). Their
physics survives while their system wrapper changes.

### Data-only demonstrations

`filaments.ipynb` and `pollen.ipynb` generate and plot synthetic volumes.
They do not define an optical system. They belong to Example data preparation,
not the installed scientific base
(`0.6.0:docs/examples/filaments.ipynb:cells 3-4`;
`0.6.0:docs/examples/pollen.ipynb:cells 3-4`).

### Experimental solver demonstration

`modified_born.ipynb` imports the experimental MBS `Sample`, `Source` and
`solve`, constructs complex permittivity and absorbing boundaries, builds a
vector current source and solves for a vector field
(`0.6.0:docs/examples/modified_born.ipynb:cells 0-5`;
`0.6.0:src/chromatix/experimental/modified_born_series/solver.py`).
It is not integrated with the ordinary Field, Component or system path. It
remains a separately staged solver. Its own README lists unresolved coordinate
ordering, tensorial permittivity, Chromatix Field input/output, inverse design,
and chiral/magnetic terms
(`0.6.0:src/chromatix/experimental/modified_born_series/README.md`).

## Behaviour changes from 0.4 to 0.6

The largest change is the Field and execution model, not an expansion of the
system catalog:

- Flax modules and explicit trainable wrappers become Equinox modules and
  ordinary array leaves. `OpticalSystem` keeps the same unchecked sequence.
- The old `field.py` is replaced by a `core` package with `Field` subclasses,
  `Spectrum`, scalar/vector and mono/chromatic distinctions
  (`0.6.0:src/chromatix/core/base.py`;
  `0.6.0:src/chromatix/core/field.py`;
  `0.6.0:src/chromatix/core/spectrum.py`).
- Spectrum construction normalizes density to sum to one
  (`0.6.0:src/chromatix/core/spectrum.py:25-42`). ChromatixNext deliberately
  retains explicit reduction weights without hidden normalization
  (`CONTEXT.md`, “Spectrum”); upstream numerical outputs must therefore be
  compared under matched weights, not copied blindly.
- The meaning of the old `k_grid` changes: 0.6 names cycles-per-distance
  `f_grid` and reserves `k_grid` for angular spatial frequency
  (`0.6.0:src/chromatix/core/field.py`, `f_grid` and `k_grid` properties).
- `Microscope` gains explicit convolution axes and supports clearer 2D versus
  3D convolution selection; its sensor gets an explicit PRNG key.
- `Optical4FSystemPSF` gains the separate mandatory `f_tube`.
- The CGH example corrects its default focal-length scale from `200` to
  `200e3` in its stated micrometre units, while the DMD example changes its
  propagation from Fresnel transfer to ASM
  (`0.4.0:docs/examples/cgh.ipynb`;
  `0.6.0:docs/examples/cgh.ipynb`;
  `0.4.0:docs/examples/dmd.ipynb`;
  `0.6.0:docs/examples/dmd.ipynb`). These are changes in example physics,
  further reason not to define parity by notebook output alone.
- 0.6 adds explicit sample element classes for clear and multislice samples
  and renames the vector solver to
  `polarized_multislice_thick_sample`, while keeping an alias
  (`0.6.0:src/chromatix/functional/samples.py:444-556`).
- 0.6 adds tests for `jit`/`vmap` preservation of Field metadata, which are
  JAX transformation guarantees rather than additional optics
  (`0.6.0:tests/test_jax_transforms.py:9-72`).

The stable physical clusters remain substantially the same. This argues for
selective behaviour migration, not version-specific surface parity.

## What upstream tests actually establish

### Stronger evidence

- Fresnel transform, Fresnel transfer, ASM and BLAS intensities are compared
  independently with the analytic square-aperture Fresnel solution at two
  rectangular/square shapes and multiple padding choices. The relative
  squared error threshold is 2%
  (`0.6.0:tests/test_propagate.py:17-193`).
- Transform propagation and radiative ASM without evanescent terms are
  propagated forward and backward and compared as complex fields, which
  checks phase as well as magnitude in those cases
  (`0.6.0:tests/test_propagate.py:53-57,127-149`).
- CZT is compared with JAX DFT/IDFT and SciPy CZT
  (`0.6.0:tests/test_czt.py`).
- Thin scalar sample tests independently check identity, a half-cycle phase
  reversal and `1/e` amplitude attenuation
  (`0.6.0:tests/test_samples.py:9-46`).
- Source tests check requested integrated power and tensor shape for scalar,
  vector, spectral, point and objective-point fields
  (`0.6.0:tests/test_sources.py:10-79`).
- Fourier convolution is compared with SciPy in 2D and 3D, with and without
  fast FFT shapes (`0.6.0:tests/test_convolution.py:8-53`).

### Missing or weak evidence

- There are no direct tests of `OpticalSystem`, `Microscope`, or
  `Optical4FSystemPSF` in either release.
- No test differentiates through a system or an optical primitive. Notebook
  optimization demonstrates that selected paths run, but is not gradient
  evidence with an independent finite-difference or analytic reference.
- Propagation methods share the same analytic *intensity* target, but are not
  compared for complex phase across methods. SAS has no inverse check.
- Most lenses, high-NA focusing, microlens arrays, thick plano-convex lenses,
  polarized multislice, fluorescence and MBS have no direct unit test.
- The multislice absorption test is explicitly skipped with “The math doesn't
  make sense here,” leaving attenuation through a thick stack unverified
  (`0.6.0:tests/test_samples.py:68-82`).
- The sensor test primarily establishes shapes and equality between Field and
  intensity inputs. It does not test pixel-integrated energy, sampling
  coordinates, interpolation error, expected Poisson statistics, dtype, or
  gradients (`0.6.0:tests/test_sensors.py:8-49`).
- Lens tests check an inverse intensity or power relation and a nonzero centre,
  not an independent complex PSF or focal-phase reference
  (`0.6.0:tests/test_lenses.py:6-44`).
- There is no release test for the source examples; the missing `f_tube` in
  the 0.6 parallel imaging script confirms this gap.

Existence in a tagged source tree is therefore insufficient for
ChromatixNext. Every retained behaviour still needs the four Component
Evidence layers required by `CONTEXT.md`.

## Complete ownership map

### Recommended ChromatixNext placement

This table is the compact placement decision for system-level parity. It
classifies upstream behaviour by the ChromatixNext seam that should own it;
it is deliberately not a list of upstream classes to reproduce.

| Placement | Upstream behaviour | Recommended ChromatixNext treatment | Reason |
| --- | --- | --- | --- |
| Existing Assembly / Example | Unary optical sequences; 4f PSF recipes; CGH, DMD, Fourier ptychography, Gabor holography, Holoscope and aberration fitting | Use direct Component Calls for a short linear path, frozen Assembly for topology and named outputs, and ordinary Python Examples for acquisition, loss and optimization | These workflows add composition and study policy, not a new optical law. `OpticalSystem` is only an unchecked callable loop (`0.6.0:src/chromatix/systems/optical_system.py:11-39`). |
| Add atomic Optical module | Missing named sources; phase/amplitude/polarization actions; high-NA focusing; Fresnel, BLAS, SAS and scaled/off-axis propagation; thin and multislice sample interactions | Add separately named, strongly typed Optical Components in physical reading order. Keep FFT, CZT, padding and kernels behind private Numerical Support | These are reusable field transformations with independent applicability ranges and scientific evidence. The example chains above consume them directly. |
| Add non-optical scientific module | Planewise shift-invariant incoherent image formation; finite-pixel integration/resampling; explicitly scoped detection statistics | Add one narrow image-formation module operating on strongly typed sample-intensity and PSF-intensity values, followed by Detection. Do not let it generate a PSF, own an optical path or infer physical meaning from a raw array | The stable law is intensity convolution and plane reduction, not a generic microscope object (`0.6.0:src/chromatix/systems/microscopes.py:190-297`). |
| Independent future solver | Modified Born electromagnetic scattering; fluorescence emission and transport | Design each as a separate complete solver slice after its material, source, boundary, spectrum and observation semantics are frozen | Upstream MBS is explicitly experimental and not integrated with ordinary Field semantics (`0.6.0:src/chromatix/experimental/modified_born_series/README.md`). Fluorescence is not merely an incoherent-convolution flag. |
| Explicitly reject copying | `OpticalSystem`; the `Microscope` god object; special-case `Optical4FSystemPSF`; method-switching `Propagate`; duplicate functional/element interfaces; JAX/Flax/Equinox state machinery and `pmap`-specific reductions | Preserve only independently named physical behaviours. Do not add compatibility wrappers, method selectors or framework-shaped public seams | Copying these interfaces would reproduce upstream coupling and release drift without adding scientific coverage. The missing required `f_tube` in the 0.6 parallel example is direct evidence of that drift (`0.6.0:examples/parallel_imaging.py:22-35,62-78`). |

| Upstream behaviour cluster | ChromatixNext placement | First complete gate |
| --- | --- | --- |
| Spectrum, polarization, grid, medium, field normalization | Physical Values | yes; extend only where new invariants require it |
| Plane, Gaussian, point, objective-point, imported field | Source | yes |
| Amplitude and phase/optical-path actions; interpolated SLM behaviour | Element | yes |
| Circular, square, rectangular, Gaussian, super-Gaussian and Tukey apertures | Element or exact profile owned by an Element | yes |
| Ideal lens; Seidel/Zernike; prism, gratings, axicon; polarizers and retarders | Element | yes |
| Microlens arrays and thick plano-convex actions | Element or explicit small Assembly, after decomposition | yes, after core lens/propagation |
| Fresnel transform, Fresnel transfer, radiative ASM, BLAS, SAS, scaled/CZT and shifted/off-axis propagation | separately named Propagation Components | yes |
| FFT, CZT, zoomed FFT, convolution, padding, crop, taper, grids, propagator construction and paraxial ray-transfer calculations | private Numerical Support | yes when required by an admitted behaviour |
| Raw arbitrary `KernelPropagate` | reject as public methodless propagation; kernel application remains private | no |
| Thin scalar and Jones sample interactions | Sample-oriented Element | yes |
| Scalar multislice and polarized multislice | Sample solver slice | yes |
| Intensity, finite-pixel integration/resampling, physically named reductions | Detection | yes |
| Shot noise, approximate noise, quantization | Detection only after units/statistics/gradient claim are explicit; otherwise Example | yes for a narrow, evidenced sensor model |
| Shift-invariant incoherent PSF convolution | requires a strong sample/PSF observation decision; then Detection/Assembly | yes for the microscope Example closure |
| `OpticalSystem` and method-switching `Propagate` | reject | no |
| CGH, DMD, Fourier ptychography, Gabor holography, Holoscope, Seidel/Zernike fitting | Assembly plus Example-owned workflow | yes as teaching closure, not production roles |
| Filament and pollen generators | Example data preparation | optional |
| Modified Born series | separately staged advanced solver | no |
| Fluorescent multislice/emission | separately staged emission solver | no |
| JAX `jit`/`vmap`/`pmap`, Flax/Equinox state, multi-device reductions | reject for this Windows PyTorch scope | no |

## Recommended dependency-closed scientific waves

These are decision waves, not implementation interfaces.

### Wave 1 — close field, vector and observation semantics

Freeze vector/high-NA meaning, spectral and polarization reductions, strong
sample/PSF observation values, and which quantities Detection is allowed to
consume and produce. This wave prevents sensor and microscope convenience
from forcing untyped arrays back into the core.

### Wave 2 — complete sources and local optical actions

Add Gaussian, point, objective-point and imported sources; then phase/SLM,
remaining pupil profiles, polarization actions, aberrations, prism/grating/
axicon and lens-derived actions. Each action must preserve the canonical field
axes and carry an explicit applicability range.

### Wave 3 — complete the propagation family

Add separately named Fresnel transform, Fresnel transfer, BLAS and SAS
Components, followed by scaled/CZT and shifted/off-axis methods using the
existing Destination Grid language. Keep FFT/CZT/padding/kernels private.
Never restore an upstream `method=` selector or automatic method fallback.

### Wave 4 — complete deterministic samples

Establish the common material/volume semantics, then thin scalar, Jones thin,
scalar multislice and polarized multislice in that order. High-NA vector
semantics from Wave 1 and propagation support from Wave 3 are prerequisites.

### Wave 5 — complete detection and incoherent imaging

Establish finite-pixel integration, resampling, reductions and one narrow
sensor-noise contract. Then compose a shift-invariant incoherent PSF imaging
path. Validate PSF normalization, sampling coordinates, conservation, 2D
plane versus 3D convolution, statistics and gradients explicitly; do not
inherit the upstream raw-array assumptions.

### Wave 6 — close with executable research Examples

Publish ordinary Python Examples for propagation comparison, high-NA PSF,
polarized multislice, CGH/DMD, Fourier ptychography, Gabor holography,
Holoscope and aberration fitting. Their optimization remains ordinary
PyTorch in the Example, as required by ADR-0004. Example smoke tests exercise
the public researcher path but do not replace Component Evidence.

### Later independent slices

Modified Born and fluorescence remain outside the first completion gate.
Modified Born needs a complete vector material/source/boundary/solver design.
Fluorescence needs explicit emission, incoherence, spectrum, randomness and
observation semantics. Neither should be smuggled into Wave 4 or Wave 5 as an
extra boolean or raw tensor path.

## Boundary recommendation

The first complete ChromatixNext scientific release should mean:

> All stable, independently verifiable physical behaviour clusters needed to
> build the tagged Chromatix propagation, focusing, deterministic sample,
> sensor and research-system Examples are present under ChromatixNext's
> Physical Value, Component, Assembly, Numerical Support and Example
> ownership rules.

It should explicitly *not* mean:

- public-symbol or import parity;
- copying upstream systems, workflows or method selectors;
- accepting raw arrays where physical meaning is required;
- treating a notebook result as Component Evidence;
- completing experimental MBS or fluorescence;
- Linux, multi-GPU, JAX transformation or JAX performance coverage.

This boundary preserves the scientific content that made the upstream
examples possible while keeping the ChromatixNext core compact, typed,
composable and independently evidential.
