# Project documentation

The documentation set has one active route. A document remains only when it
controls current research, architecture, reproducibility, planning, or source
provenance that has not yet been absorbed elsewhere.

## Read in order

1. [`restoration/README.md`](restoration/README.md) — the short entrance to the
   active intelligent-front-end design and four-day closure plan.
2. [`restoration-research-design.md`](restoration-research-design.md) — the
   canonical long-form background, theory, experimental programme, comparison
   policy, and data-readiness audit.
3. [`data-and-layers-architecture.md`](data-and-layers-architecture.md) —
   frozen data stages, flat optical layers, and experiment-owned composition.
4. [`project-baseline.md`](project-baseline.md) — Fixed Measurement, Adaptive
   Measurement, protected evidence, and scientific gates.
5. [`wayfinder/restoration-map.md`](wayfinder/restoration-map.md) — unresolved
   implementation decisions and evidence tickets.

`CONTEXT.md` at the repository root is the canonical terminology ledger. Root
`AGENTS.md` and colocated Module `README.md` files remain beside the code they
govern.

## Decisions

The active ADRs are:

- [`ADR-0015`](adr/0015-freeze-reusable-data-stages-and-flat-optical-layers.md)
  — freeze reusable data and optical building blocks;
- [`ADR-0016`](adr/0016-target-quasi-static-prescan-and-hold-microscopy.md)
  — target quasi-static calibration and held correction;
- [`ADR-0017`](adr/0017-separate-input-amplitude-and-fourier-phase-slm-roles.md)
  — keep the two physical SLM roles distinct;
- [`ADR-0018`](adr/0018-retire-fixed-measurement-and-reset-on-adaptive-optics.md)
  — retire Fixed Restoration as the active research architecture;
- [`ADR-0019`](adr/0019-share-restoration-foundations-and-separate-experiment-protocols.md)
  — share stable physical Interfaces while separating experiment protocols;
- [`ADR-0020`](adr/0020-adopt-a-fixed-reference-correctability-aware-intelligent-front-end.md)
  — adopt fixed mechanical delay, reference-on science, and selective
  `correct / probe / abstain` control.

## Prompts and research provenance

Canonical prompts live under [`prompts/`](prompts/). The completed external
audit used
[`restoration-research-prompt.md`](prompts/restoration-research-prompt.md)
together with
[`restoration-foundations.md`](research/restoration-foundations.md). The
classification of active supporting notes and superseded narrative provenance
lives in [`research/README.md`](research/README.md).

- [`restoration-audit-package.zip`](restoration-audit-package.zip) is the
  immutable GPT Pro delivery.
- [`restoration-bibliography.bib`](restoration-bibliography.bib) is provisional
  and still requires item-level metadata verification before manuscript use.

## Documentation rule

- One active baseline.
- One terminology ledger.
- One active research-design document per candidate method.
- One architecture document per stable code seam.
- One canonical prompt per active task.
- ADRs only for durable decisions.
- Dated research documents only when their evidence remains active.
- Historical narrative is clearly marked as provenance, never left to compete
  with the active design.
- Project tooling, including Nature skills and the ignored
  `refresh_workspace.py` archival script, is not research evidence and must not
  be removed by documentation cleanup.
