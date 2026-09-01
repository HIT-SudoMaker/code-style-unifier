# ChromatixNext

ChromatixNext is a compact PyTorch optical-simulation base for local
workstations. It keeps physical meaning in strong values, optical actions in
small Components, complete paths in an Assembly, and device ownership in a
Workstation.

The current release supports Python 3.12, PyTorch execution on Windows CPU,
and explicit single-device Windows CUDA. Linux is an architectural target
until it receives its own native verification. There is no automatic device,
memory, or propagation-method fallback.

## Install

```text
python -m pip install .
```

The runtime dependency is PyTorch. Create a Workstation explicitly:

```python
from chromatix_next import Workstation

workstation = Workstation.cpu()
```

## Scientific base

- `chromatix_next.optics` owns Physical Values such as `OpticalField`,
  `Intensity`, `SpatialGrid`, `Spectrum`, `Polarization`, and `Medium`.
- Singular role packages own Source, Element, Propagation, Combination, and
  Detection Components.
- `Assembly` authors one complete path with `include`, `connect`, `expose`,
  and `freeze`.
- `Workstation` hosts one Component or frozen Assembly and returns
  `NamedOutputs` with an immutable `RunRecord`.

All public physical numbers use SI units. The numerical regime is fixed
double: every real floating quantity is `torch.float64` and every complex
quantity is `torch.complex128`. There is no precision selector, no precision
argument on Sources or Workstation factories, and no `RunRecord.precision`
field; explicit `float32`/`complex64` state is rejected at construction and
at the host preflight.

## Learn

The seven executable, paired teaching cases are indexed in
[`examples/README.md`](examples/README.md). Each asks one physical question
through public Optical Interfaces; the branched case uses an Assembly.
Examples are included in the source distribution; the runtime wheel exports
only `chromatix_next`.

The canonical domain language is in [`CONTEXT.md`](CONTEXT.md), and durable
decisions are in [`docs/adr/`](docs/adr/). Upstream snapshots under
`reference/` are read-only scientific references and are never imported by
the runtime.

Chinese: [README.zh-CN.md](README.zh-CN.md)
