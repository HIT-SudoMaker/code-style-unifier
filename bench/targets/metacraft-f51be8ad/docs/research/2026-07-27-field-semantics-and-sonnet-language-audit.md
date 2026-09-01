# Field semantics and Sonnet language audit

## Question

MetaCraft currently calls its low-na array a scalar field and lets that
approximation leak into task, capability, evidence, and function names. Can
one field value carry polarization and vector meaning without creating
parallel `Scalar*` and `Vector*` type trees, and which nearby names currently
misstate their responsibility?

This record is a source audit and design comparison. It establishes no
external scientific fact.

## Source observations

The current implementation reveals five concrete mismatches.

1. `field/angular_spectrum.py` exposes `FieldPlane`, but the value contains
   one anonymous two-dimensional complex array. Polarization, component basis,
   medium, coordinate frame, and source evidence are absent.
2. `_local/propagation.py::propagate_scalar_field` and
   `_local/geometric.py::propagate_channel_fields` do not propagate. They form
   aperture-plane arrays and serialize them.
3. Both focus operations reconstruct those arrays from the aperture and
   propagate again. Route conclusion repeats parts of the same calculation,
   so admitted field and focus evidence are not the sole inputs to
   interpretation.
4. `PhaseMethod` names a control strategy while `relationships.Method` names
   an evidence-establishing method. `CellPolicy` combines sampling, stack,
   fabrication, mesh, and monitor-construction facts.
5. Scientific identifiers still contain local mathematical shorthand such as
   `kx`, `ky`, `kz`, `na`, bare `x` and `y` result fields, and asymmetric
   Jones-response names.

The Authority already stores opaque bytes under exact media types. A field
manifest may therefore cite immutable binary component objects without a Rust
protocol change.

## Compared designs

### Prefix tree

One class family for scalar fields and another for vector fields makes the
approximation part of every downstream type name. Focus, survey, plane, pupil,
and evidence values then fork even when their responsibilities are otherwise
identical. This design was rejected.

### Envelope or electromagnetic content

One `Field` may contain either a complex envelope with a polarization profile
or explicit electromagnetic components. This keeps a small current
construction but creates two internal representations and requires conversion
rules before low-na and large-na results can be compared.

### Component field

One `Field` carries one sampled physical fact:

- one wavelength;
- one surface and coordinate frame;
- one locally uniform medium;
- one explicit component basis;
- electric component arrays;
- optional magnetic component arrays;
- exact source references.

Transverse linear, circular, Cartesian, and sphere-tangent bases state which
components exist. No `is_vector` Boolean is stored. A propagated field carries
no global polarization label; local polarization is derived from its complex
components. The brief separately retains the incident polarization condition.

This design was selected. It has one representation, makes PB converted and
retained roles an interpretation of physical handedness components, and
allows vector angular spectrum and Debye--Wolf calculations to consume the
same field language without pretending that they share one input surface or
method.

One field remains single-wavelength. A future achromatic proof composes exact
fields at several wavelengths instead of silently broadcasting one grid,
medium, or component array across a spectral axis.

## Selected mental order

The current metalens proof refines to:

`aperture -> field -> focal region -> focus -> result`

The corresponding operations are:

`form -> propagate -> evaluate -> conclude`

- `form_aperture_field` combines aperture states, response channels, and the
  incident condition into one field fact.
- `propagate_field` consumes one field through the realization already chosen
  by the compiled task and records a focal-region survey.
- `evaluate_focus` consumes that survey without propagating again.
- `conclude` interprets admitted evidence without rebuilding any prior fact.

Scalar or vector approximation remains explicit in method applicability,
realization identity, qualification, and result provenance. It does not name
the field value.

## Sonnet language findings

The following are semantic corrections, not cosmetic rewrites:

- `PhaseMethod` / `phase_method` -> `ControlStrategy` /
  `control_strategy`;
- aperture regime remains independent from control strategy;
- `CellPolicy` is removed and its facts move to their scientific or product
  owners;
- `HeightDomain.route` names the compiled route, never the control strategy;
- receipt reconstruction uses `restore`, while propagation uses `propagate`
  and scientific synthesis uses `form` or `synthesize`;
- the grating response's phase-plane declaration is `phase_planes`, not an
  Authority-like `phase_reference`;
- solver construction inputs do not reuse the scientific `Cell` name;
- a logical processor is not named `Cpu`;
- a native-execution Boolean cannot also summarize fixture advice provenance.

Natural production identifiers expand local shorthand:

- `wave_number_x`, `wave_number_y`, `wave_number_z`;
- `numerical_aperture`;
- `position_x_m`, `position_y_m`;
- `x_half_maximum`, `y_half_maximum`, `depth_of_focus`;
- `output_y_from_input_x`;
- `minimum_fit_frequency_hz`, `maximum_fit_frequency_hz`;
- `real_part`, `imaginary_part`.

Units and established technology nouns remain concise. Native solver property
strings remain exact inside the Adapter and are translated immediately.
Short, accurate domain nouns such as `Field`, `Cell`, `Aperture`, `Lane`,
`Brief`, `Study`, `Method`, `Route`, `Proof`, and `Binding` are retained.

## Implementation consequences

- Field components and aperture index maps become immutable binary authority
  objects; small canonical documents cite them by exact reference.
- Public evidence schemas migrate atomically with their decoders and tests.
- The low-na propagation and geometric proofs retain distinct scientific
  meanings while sharing the component-field implementation.
- Architecture tests reject the retired vocabulary and protect the frozen
  Rust boundary.
- No registry, plugin system, generic workflow, GUI layer, or speculative
  optimizer is introduced.
