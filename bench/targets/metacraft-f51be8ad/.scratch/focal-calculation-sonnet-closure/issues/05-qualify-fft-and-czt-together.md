# Qualify FFT and CZT together

Status: completed

Resolution: completed through independent FFT and CZT qualification documents,
one immutable matched-grid qualification fact, and one joint aplanatic-reference
binding that cites all three facts. Formation prepares one pupil, executes FFT
and CZT on identical natural-grid coordinates, enforces their numerical
agreement, then executes CZT on the requested comparison grid.

Blocked by: 04

Parent: [map](../map.md) · [specification](../spec.md)

## Outcome

One aplanatic-reference binding proves that FFT and CZT each satisfy independent
physical fixtures and agree with each other on identical coordinates. Neither
realization can silently replace the other.

## Implementation

Introduce one immutable joint qualification fact owned beside the aplanatic
formation Module. It cites the exact independent FFT and CZT qualifications,
evaluates both on the FFT natural conjugate grid, and records aligned complex
error plus unit-integral intensity error. Freeze a compact fixture matrix that
covers low/high numerical aperture, linear/circular polarization, selected
device, complex128/float64, common pupil sampling, and exact coordinate identity.
Include transverse center and off-axis samples plus negative, zero and positive
axial offsets; the matrix must exercise the nonzero plane correction introduced
by Ticket 03 rather than only geometric focus.
Both joint errors must be at most `1e-10`; the current CPU/CUDA evidence is near
machine precision, including nonzero axial offsets, so this limit is a
regression fence rather than a physical comparison threshold.

Replace the single-CZT production binding with one joint aplanatic-reference
binding containing both exact realization facts and all qualification
references. Formation uses FFT on its natural grid, CZT on the same grid for
agreement, and CZT on the requested comparison grid. Failure of either
independent or joint qualification leaves the capability unavailable; no
averaging, device switch, single-realization fallback, or exception-text
classification is permitted.

## Acceptance

- Deterministic CPU fixtures pass for the full matrix; native CUDA fixtures run
  when selected and report zero hidden fallback.
- Mutating either realization, coordinate, qualification reference, dtype,
  device, sampling count or agreement value invalidates restoration.
- High-Interface instrumentation proves one shared pupil preparation per
  calculation and both required realization executions; no production counting
  hook is introduced.
- Positive and negative axial-offset joint fixtures preserve sign and agree on
  the same natural-grid coordinates.
- The binding and admitted reference retain independent and joint provenance.
- No production branch selects FFT versus CZT from a string or catches one to
  run the other.
- Focused qualification/formation/Result tests, CPU/CUDA gates, Pyright, CSU,
  dependency and diff gates pass.

## Guardrails

Do not compare FFT and CZT on different coordinates, add a Direct runtime path,
or apply the `1e-10` threshold to VASM-versus-aplanatic physical disagreement.

## Evidence

- TDD first failed because the joint qualification Interface did not exist.
- The frozen CPU matrix contains 12 low/high-NA, linear/circular, negative/zero/
  positive-offset fixtures with center and off-axis samples. Both joint errors
  remain near machine precision and below `1e-10`.
- Binding restoration closes exact FFT, CZT and joint qualification references;
  a single-CZT binding fails closed before formation.
- High-Interface instrumentation proves one pupil preparation, one FFT natural-
  grid execution, one matched-grid CZT execution and one requested-grid CZT
  execution. The sole private production seam is `_aplanatic_reference`.
- Focused field/science/architecture gate: 127 passed. Full Pyright: 0 errors,
  0 warnings. CSU: 0 blocking findings. Dependency and diff checks are clean.
- Native CUDA qualification runs when CUDA is available; this environment did
  not report CUDA availability, so the native fixture remains explicitly
  skipped rather than counted as passed.
- Independent-evidence restoration rejects rehashed large, non-finite and
  negative fixture errors against each named fixture's exact qualification
  limit before aplanatic-reference formation can begin.
- A real Authority missing-object witness is normalized through the typed
  `ReferenceUnresolvable` fault into the stable binding mismatch; unrelated
  Authority `RuntimeError` failures remain visible rather than being hidden.
