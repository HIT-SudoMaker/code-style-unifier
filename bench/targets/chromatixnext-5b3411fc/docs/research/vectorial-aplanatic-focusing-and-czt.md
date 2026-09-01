# Vectorial aplanatic focusing and CZT

**Date:** 2026-07-27
**Status:** implemented and qualified research record

## Question and verdict

This record explains how ChromatixNext implements high-numerical-aperture
focusing without exposing a numerical algorithm as optical physics or
enlarging the current field model prematurely.

The implemented physical slice is one paired action:

```python
aplanatic_focus(...)
AplanaticFocus(...)
```

It consumes a transverse exit-pupil `OpticalField` and returns one focal-plane
`OpticalField` with explicit `(Ex, Ey, Ez)` content. It fixes the objective's
`maximum_convergence_angle` and accepts only `RELATIVE` normalization.
`chromatix_next._numerics` owns the production CZT behind the existing
`optics -> _numerics` dependency. The direct angular quadrature and
Fourier-Bessel are test evidence outside the production dependency. There is
no public algorithm selector and no new volume Physical Value in this slice.

## Primary scientific evidence

Richards and Wolf derive the electromagnetic field near the focus of an
aplanatic imaging system, including electric and magnetic vectors,
polarization, energy densities, and the Poynting vector. This is the physical
foundation for the proposed action, not a scalar angular-spectrum calculation
followed by reconstruction of one longitudinal component.
[Richards and Wolf, 1959](https://doi.org/10.1098/rspa.1959.0200)

Leutenegger et al. evaluate the vectorial Debye integral with an FFT over the
focal region, then generalize it with the chirp z-transform (CZT) for a
flexible sampling grid and further speedup. Their stated result includes
amplitude, phase, and polarization for an arbitrary paraxial input field under
the validity conditions of the Debye representation.
[Leutenegger et al., 2006](https://pubmed.ncbi.nlm.nih.gov/19529543/)
([DOI](https://doi.org/10.1364/OE.14.011277))

Hu et al. likewise express scalar and vector diffraction as Fourier-type
calculations and use Bluestein's method for selectable regions of interest and
sample counts.
[Hu et al., 2020](https://www.nature.com/articles/s41377-020-00362-z)
That paper must not be cited as the origin of the high-NA CZT method:
Shao and Urbach show that its core approach was already published by
Leutenegger et al. in 2006, and clarify that Bluestein's convolution identity
is the enabling step in the CZT algorithm.
[Shao and Urbach, 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC7797477/)

Sherif and Török give a Bessel and circular prolate-spheroidal eigenfunction
representation of the Debye diffraction integral. This supports a structured
radial or angular-mode acceleration, but not a general claim that every
two-dimensional pupil is radial.
[Sherif and Török, 2005](https://doi.org/10.1080/09500340512331309084)

The scientific and numerical lineage is therefore:

```text
Richards-Wolf aplanatic vector integral
    -> direct angular quadrature reference
    -> Fourier representation
    -> FFT or CZT evaluation
```

CZT changes how the same Fourier-type integral is evaluated. It does not
create a different propagation law or repair an invalid pupil-to-reference-
sphere mapping.

## CZT is not the radial reduction

For a general pupil, the aplanatic vector integral is a two-dimensional
angular/Fourier integral. A separable two-dimensional CZT evaluates that
integral on a selected uniform focal-plane region without requiring the
input-determined FFT output grid.

For an axisymmetric pupil, or after an explicit low-azimuthal-mode expansion,
the azimuthal integral can instead be performed analytically. The remaining
one-dimensional radial integrals contain ordinary Bessel kernels
`J_m`; this is a Fourier-Bessel/Hankel reduction. It is not:

- the CZT;
- a Bessel-beam model;
- radial polarization;
- radial parameterization of a device design.

Both CZT and Fourier-Bessel are possible numerical implementations of the same
Richards-Wolf physical action. Only an explicit truncation of azimuthal modes
changes the scientific approximation and would need to be visible to a
caller.

Even a circularly symmetric pupil amplitude is not automatically an
order-zero scalar problem. A uniformly x-polarized aplanatic field contains
the familiar `J0`, `J1`, and `J2` terms after azimuthal integration; its
cross-polarized `Ey` component is generally nonzero away from the optical
axis. An implementation that keeps only `J0`, or reconstructs only `Ez` after
a scalar propagation, changes the physics.

Vector angular-spectrum propagation is a separate physical action. It
propagates a known complex vector field from one plane to another. Aplanatic
focusing instead maps an exit-pupil field through the sine-condition
reference sphere of an ideal objective. The two actions may both use FFT or
CZT internally, but they are not interchangeable backends and neither may be
an automatic fallback for the other.

The MetaCraft archive contains no recoverable implementation of the formerly
named radial-achromatic, Bessel, or full-array Debye path. Its exhaustive Git
provenance found only orchestration shells, metric names, and deferred
requirements; the correct result is negative evidence, not a lost algorithm
to copy. See:

- [Debye-Wolf numerical heritage recovery](../../../../Year2026_Project_MetaCraft/code/docs/research/2026-07-15-debye-wolf-numerical-heritage-recovery.md);
- [large-NA method boundaries](../../../../Year2026_Project_MetaCraft/code/docs/research/2026-07-27-large-na-propagation-metalens-method-boundaries.md);
- [field-semantics audit](../../../../Year2026_Project_MetaCraft/code/docs/research/2026-07-27-field-semantics-and-sonnet-language-audit.md).

## What upstream Chromatix actually implements

The retained upstream repository is checked out at tag `0.4.0`; tag `0.6.0`
is also locally addressable. The relevant immutable source locations are:

| Tag | Tagged source path | Finding |
| --- | --- | --- |
| `0.4.0` | `src/chromatix/functional/lenses.py` | `high_na_ff_lens` branches over scalar/vector fields, maps Cartesian pupil components, applies a `1/sz` defocus factor, and calls `zoomed_fft`. |
| `0.4.0` | `src/chromatix/field.py` | `cartesian_to_spherical` returns a bare array rather than a strong field value. |
| `0.4.0` | `src/chromatix/utils/czt.py` | one- and multi-dimensional CZT use Bluestein convolution through JAX FFT. |
| `0.6.0` | `src/chromatix/functional/lenses.py` | retains the same high-NA action, single-wavelength/square-field warnings, and zoomed transform. |
| `0.6.0` | `src/chromatix/core/field.py` | retains the Cartesian-to-spherical array conversion after the field refactor. |
| `0.6.0` | `src/chromatix/utils/czt.py` | retains the public numerical CZT utility. |

These sources are reproducible with, for example:

```powershell
git -C reference/chromatix show 0.4.0:src/chromatix/functional/lenses.py
git -C reference/chromatix show 0.6.0:src/chromatix/functional/lenses.py
```

The local `0.4.0` copies are directly readable at
[lenses.py](../../reference/chromatix/src/chromatix/functional/lenses.py),
[field.py](../../reference/chromatix/src/chromatix/field.py), and
[czt.py](../../reference/chromatix/src/chromatix/utils/czt.py).

Useful lessons are the explicit single-wavelength limitation, vector pupil
mapping, and zoomed focal sampling. ChromatixNext should not copy the bare
`n`, `NA`, `output_shape`, `output_dx`, scalar/vector branching, bare
reference-sphere array, or public numerical-transform surface. Those mix
field meaning, objective physics, destination geometry, and numerical
implementation.

## Implemented ChromatixNext foundation

The completed base supplies:

- `OpticalField` fixes the layout
  `[batch..., spectrum, polarization, height, width]`;
- `PolarizationRepresentation.FULL` already means three explicit components;
- `SpatialGrid` already expresses a shifted and scaled focal-plane destination;
- Spectrum, Medium, Precision, Source Lineage, and Optical Path Reference are
  strong field-owned values;
- the dependency direction is already
  `workstation.py -> optics -> _numerics`;
- Assembly meta inference and Workstation memory tracing execute the real
  module path;
- `vector_angular_spectrum` / `VectorAngularSpectrum` implement radiative
  vector plane propagation;
- `aplanatic_focus` / `AplanaticFocus` implement the one-plane ideal
  objective map and explicitly change `TRANSVERSE` to `FULL`;
- private separable Bluestein CZT evaluates the production focal transform;
- direct angular quadrature and Fourier-Bessel references independently check
  the same physical action.

The remaining boundaries are deliberate: general vector POWER/Poynting flux,
focal volumes, trainable hard geometry, nonuniform sampling, and a public
algorithm selector are not claimed. These exclusions do not weaken the
implemented one-plane relative-field action.

## Three interface shapes considered

### Public objective and reference-sphere field

```text
IdealObjective -> ReferenceSphereField -> DebyeFocus
```

This is physically explicit but currently shallow. There is only one planned
producer and one consumer, so callers would have to learn sphere sampling,
apodization, tangent bases, and integration measure without gaining a
replaceable public seam. It should be reconsidered only when a second real
producer or consumer exists.

### New focal-volume value

```text
RichardsWolfFocus -> FocalField(depth, height, width)
```

This preserves an axial coordinate correctly but expands the closed Physical
Value set, Assembly outputs, Detection, Optical Path Reference, and memory
contracts before a system case requires a volume. Hiding depth in a batch axis
would be worse, but a new volume value is still premature for the first slice.

### Hybrid plane action — selected

One deep physical module hides the reference sphere and its numerical
realizations while returning the existing plane field:

```python
def aplanatic_focus(
    field: OpticalField,
    *,
    focal_length: float | torch.Tensor,
    maximum_convergence_angle: float | torch.Tensor,
    axial_distance_from_focus: float | torch.Tensor,
    destination_grid: SpatialGrid,
) -> OpticalField:
    ...


class AplanaticFocus(torch.nn.Module):
    ...
```

Its invariants are:

- input is a transverse exit-pupil field in the same homogeneous image-space
  Medium as the focus;
- output is one focal plane with explicit `(Ex, Ey, Ez)` components;
- `maximum_convergence_angle` is a fixed, finite geometric value, with
  `0 < angle < pi / 2`; it is not a trainable hard-aperture parameter;
- wavelength-resolved numerical aperture is derived as
  `n(wavelength) * sin(maximum_convergence_angle)`, so immersion `NA > 1` is
  legal and never clipped;
- all spectral components share the fixed focal length and convergence
  geometry, which is an ideal achromatic-objective contract rather than a
  claim that a real objective has no wavelength-dependent focal shift or
  aberration;
- the Abbe sine condition, one aplanatic apodization convention, polarization
  transport, phase convention, and path-reference convention are fixed by the
  action;
- the output Optical Path Reference carries the uniform propagation carrier
  to the selected focal plane, while the envelope retains only the
  angle-dependent residual axial phase;
- the first qualified slice accepts only `RELATIVE` normalization;
- no scalar fallback, automatic physical-method substitution, or public
  `algorithm`, `backend`, `use_czt`, or `radial` selector exists.

The public name describes the physical system. Exact Richards-Wolf provenance
belongs in its documentation and evidence; CZT belongs only in the
implementation.

The formal implementation contract is frozen by the Vector Angular Spectrum
Propagation entry in `CONTEXT.md` and the closure decisions in `docs/adr/`.
It supersedes the earlier interface sketch in this research record. In
particular, axial distance is explicit rather than defaulted, geometry tensors
are fixed, and only axial distance is a claimed trainable physical parameter.

The frozen Cartesian convention uses the laboratory components `(Ex, Ey, Ez)`,
pupil coordinates `(y_p, x_p)`, the sine condition
`rho = focal_length * sin(theta)`, and the energy-preserving
`sqrt(cos(theta))` apodization. The direct evidence owns the full global phase,
prefactor `-i k focal_length / (2 pi)`, solid-angle Jacobian, and polarization
map. The full phase includes the common focal-length carrier. Production uses
the algebraically equivalent residual axial phase and advances Optical Path
Reference by
`n(wavelength) * (focal_length + axial_distance_from_focus)`. The objective
baseline is therefore explicit rather than discarded or left to a caller.

The private one-axis CZT is also fixed exactly as:

```text
Y[m] = sum(
    X[n] * exp(i * n * (starting_phase + m * phase_step)),
    n = 0 .. N - 1,
)
```

It is unnormalised. `starting_phase = 0`, `phase_step = -2 pi / N`, and
`M = N` recover the FFT convention. The production implementation uses
separable Bluestein convolution and never materializes the direct matrix.

## PyTorch feasibility and one local blocker

PyTorch officially supports native `complex64`/`complex128` tensors, complex
autograd, and FFT operations on native complex tensors.
[Complex tensors](https://docs.pytorch.org/docs/stable/complex_numbers.html)
[torch.fft](https://docs.pytorch.org/docs/stable/fft.html)
This is sufficient for a differentiable CZT assembled from chirp
multiplication, FFT convolution, and cropping on CPU or CUDA.

The official [`torch.special`](https://docs.pytorch.org/docs/stable/special.html)
surface includes ordinary `bessel_j0` and `bessel_j1`, but local operator
coverage must be tested rather than inferred from their presence. On
2026-07-27, the required project interpreter reported:

```text
torch 2.12.0+cu130
bessel_j0 RuntimeError: output does not require grad and has no grad_fn
bessel_j1 RuntimeError: output does not require grad and has no grad_fn
fft_gradient tensor([1., 4.], dtype=torch.float64)
```

This is a local environment diagnostic, not a claim about every future
PyTorch release. It means a trainable Fourier-Bessel path cannot currently
delegate directly to `torch.special.bessel_j0/j1` and retain the project's
gradient claim. Such a path needs a separately qualified recurrence, custom
autograd implementation, or later operator support. It should not block the
general CZT route.

Fixed Bessel tables can still preserve gradients with respect to pupil
amplitudes or phases through the subsequent contraction. The missing gradient
is through the Bessel argument itself, so trainable focal geometry, numerical
aperture, or sample coordinates must not be claimed on that implementation.

## Implemented production and evidence ownership

- **Production: separable Bluestein CZT.** Private
  `chromatix_next._numerics` evaluates the authored uniform focal-plane region
  without a dense transform matrix. It supports ordinary PyTorch autograd,
  both paired Precisions, CPU, and available Windows CUDA.
- **Evidence: direct angular quadrature.** Test-side two-dimensional
  Richards-Wolf integration independently owns the global phase, prefactor,
  solid-angle Jacobian, polarization map, and convergence comparison. It never
  imports production Numerical Support.
- **Evidence: Fourier-Bessel.** Test-side axisymmetric reduction retains the
  required `J0`, `J1`, and `J2` content. Fixed Bessel tables check the
  production field while making no gradient claim through Bessel arguments.

The public action is bounded to a uniform sampled transverse pupil, one
uniform destination plane, fixed objective geometry, RELATIVE normalization,
and a homogeneous wavelength-dispersive Medium. Qualified gradients are the
input envelope and axial distance from focus. Both Precisions and available
Windows CUDA use the same public interfaces and PyTorch equations. No Linux
execution result is claimed.

## Open Poynting and volume questions

For a general nonparaxial vector superposition, axial power flow is determined
by the time-averaged Poynting vector, not universally by
`|Ex|^2 + |Ey|^2 + |Ez|^2`. Richards and Wolf explicitly treat both electric
and magnetic fields and the Poynting vector. ChromatixNext must therefore
reject `POWER` input for this first action instead of relabeling electric-field
magnitude as watts per square metre. A later power claim requires magnetic
field semantics or an independently qualified Poynting-flux observation.

Likewise, a focal volume must not masquerade as a batch of planes. It should be
designed only when a real consumer justifies a new Physical Value with an
explicit axial grid, per-plane carrier reference, Detection semantics, and
Assembly/Workstation traversal. Neither open question blocks the honest
one-plane, relative-field aplanatic focusing slice.
