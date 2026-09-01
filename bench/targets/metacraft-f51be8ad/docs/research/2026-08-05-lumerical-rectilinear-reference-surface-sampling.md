# Lumerical rectilinear reference-surface sampling

Date: 2026-08-05

## Question

Does the installed Lumerical FDTD product return one fixed uniform transverse
grid for every internal `grating_s_params` transmission surface when the
solver uses automatic non-uniform meshing and the monitor uses
`specified position` spatial interpolation?

## Redacted product evidence

One authorized fresh Native gate retained two distinct classes of sampled
reference surface. This record deliberately omits absolute paths, machine
identity, license configuration, raw field values, and full coordinate
arrays.

- The qualification reference surface contained a 43 by 43 closed transverse
  grid. Both coordinate axes were strictly increasing and uniformly spaced.
- Each candidate basis observation contained the same 36 by 33 closed
  transverse grid shape. Both coordinate axes were strictly increasing, but
  their successive coordinate differences were non-uniform.
- The candidate endpoint samples closed the periodic seam. Non-uniform
  interior spacing, rather than a missing or unordered coordinate, was the
  contradiction with MetaCraft's former uniform-spacing gate.
- The qualification and candidate observations came from different physical
  constructions. Their different grids are therefore evidence that automatic
  meshing may change transverse sampling with the construction even when the
  declared period and reference plane are unchanged.

The statements above are array facts only. They do not publish the arrays and
do not publish the arrays.

## Read-only numerical qualification

The approved numerical study opened the existing failed gate root's retained
`after.fsp` files read-only. It performed zero Native solves and did not reuse,
resume, or mutate that root. Both the from-x and from-y observations had a
400 nm period, a closed 36 by 33 grid, and an exactly matching periodic seam.
Across both observations, successive x steps ranged from 10.476 nm to 15 nm;
successive y steps ranged from 10.577 nm to 14.711 nm.

The accepted realization is `periodic_rectilinear_bilinear_v1`:

- one 24 by 24 half-open uniform target grid for the complete compatible
  batch;
- separable periodic bilinear interpolation;
- maximum batch size 256;
- no extrapolation and no amplitude or power normalization;
- raw round-trip relative L2 error at most `0.0081`;
- normalized maximum error at most `0.0093`;
- relative power-proxy change from the 20 by 20 grid to the 24 by 24 grid at
  most `0.0006`.

The earlier 64 by 64 candidate contract did not close system resources: high-
NA delivery crossed the already qualified 1 GiB vector-field guard. The 24 by
24 target has a 16.67 nm step at 400 nm period, the same scale as the Native
grid's largest 15 nm step, and all five delivery tests across the four cases
passed under the bounded resource contract.

The read-only measurements passed all three limits:

| Input basis | Raw round-trip relative L2 | Normalized maximum | 20→24 power-proxy change |
|---|---:|---:|---:|
| from-x | 0.00798322 | 0.00926499 | 0.000571006 |
| from-y | 0.00789876 | 0.00811822 | 0.000236897 |

These measurements qualify the fixed numerical contract against the retained
candidate evidence. Ticket 08.6 subsequently resolved its deterministic
production implementation. Neither the measurements nor that resolution
authorize reuse of the failed Native root.

## Product documentation

Ansys documents FDTD's default automatic mesh as a graded Cartesian mesh whose
cell sizes can vary with position, wavelength, material properties, and
geometry. Mesh accuracy 4 is a target of 18 points per wavelength, not a
promise of one global transverse step or one fixed point count.

Ansys also documents `specified position` as the Yee-field interpolation
choice that records fields at the monitor position. It does not state that the
monitor's transverse coordinates become uniformly spaced. Frequency-domain
monitor downsampling samples grid points; it does not regularize them.

`getresult(..., "E")` returns a rectilinear dataset. Its `x`, `y`, and `z`
parameters are the sampled position vectors, and the field-array dimensions
correspond to their lengths. Those returned coordinate vectors are therefore
the product fact; a caller must not reconstruct them from span and shape.

Primary references:

- [FDTD solver mesh settings](https://optics.ansys.com/hc/en-us/articles/360034382534-FDTD-solver-Simulation-Object)
- [Understanding the non-uniform mesh in FDTD](https://optics.ansys.com/hc/en-us/articles/360034382634-Understanding-the-non-uniform-mesh-in-FDTD)
- [Frequency-domain monitor](https://optics.ansys.com/hc/en-us/articles/360034902393-Frequency-domain-monitor-Simulation-object)
- [Introduction to Lumerical datasets](https://optics.ansys.com/hc/en-us/articles/360034409554-Introduction-to-Lumerical-datasets)
- [getresult script command](https://optics.ansys.com/hc/en-us/articles/360034409854-getresult-Script-command)
- [Accessing simulation results through the Python API](https://optics.ansys.com/hc/en-us/articles/39744236202771-Accessing-Simulation-Results-Python-API)
- [interp script command](https://optics.ansys.com/hc/en-us/articles/360034925893-interp-Script-command)
- [Mesh override](https://optics.ansys.com/hc/en-us/articles/360034901833-Mesh-override-Simulation-Object)

## Finding

A strict uniform-spacing requirement is not a valid Native-observation
invariant. A finite, strictly ordered rectilinear surface may be a valid
observation even when its axes are non-uniform, non-square, or sampled at
different densities. Uniform sampling is instead an applicability requirement
of MetaCraft's current FFT-based field propagation.

The product Adapter must retain the actual coordinate vectors and validate
their structural and physical context without pretending they are uniform.
Any transformation into the existing uniform `Field` is a separate numerical
formation. It must operate on a complete compatible batch, preserve exact
source evidence, and carry its own qualification.

## Remaining non-decisions

This record does not select a GPU implementation or a future direct
non-uniform/NUFFT realization. Neither is required by the accepted fixed
contract, and neither may appear as a hidden fallback.

## Decision input

[ADR 0019](../adr/0019-form-uniform-fields-from-rectilinear-reference-surfaces.md)
records the resulting architecture decision. It leaves ADR 0017's substrate,
vertical layout, world-coordinate, and exact transmission-plane decisions
unchanged.
