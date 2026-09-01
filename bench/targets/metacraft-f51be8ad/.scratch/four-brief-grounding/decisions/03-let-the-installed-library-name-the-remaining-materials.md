# Let the installed library name the remaining materials

Label: `wayfinder:task`

Status: resolved (2026-08-08)

## Question

Which exact native records in the installed Lumerical 25v2 material database
represent `hydrogenated amorphous silicon`, `silicon`, and
`amorphous titanium dioxide`, and do their tabulated bands cover the canonical
brief wavelengths that request them?

The task is read-only. It may inspect material existence and sampled bands,
but it must not create, import, modify, sweep, or solve any structure.

## Resolution

Read-only inspection of the installed Lumerical 25v2 default database found:

- `Si (Silicon) - Palik` exists and its isotropic sampled table covers both
  850 nm and 1550 nm.
- No exact default record exists for hydrogenated amorphous silicon. It must
  remain unregistered until a reviewed custom or imported dataset is chosen.
- `TiO2 (Titanium Dioxide) - Siefke` exists, covers 532 nm, and derives from
  an experimentally characterized TiO2 film deposited by ALD at 100 C. It is
  the closest installed process match for the amorphous ALD TiO2 benchmark.
- The Kischkat record does not cover 532 nm, while the Devore record describes
  anisotropic rutile and is not an amorphous-film substitute.

The inspection opened one hidden empty FDTD session, performed no project
load, material mutation, structure construction, save, or solve, and closed
the session normally.
