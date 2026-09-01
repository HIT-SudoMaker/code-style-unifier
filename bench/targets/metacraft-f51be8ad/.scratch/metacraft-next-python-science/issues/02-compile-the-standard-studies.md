# 02 — Compile the standard studies

**What to build:** A researcher can submit either approved 400 nm metalens brief and receive one deterministic typed design and study whose proof obligations, ready tasks, and unresolved facts follow from evidence rather than a workflow position.

**Blocked by:** 01 — Cross the authority boundary.

**Status:** wontfix

**Superseded by:** [Four-brief delivery tickets 02, 05, and 06](../../four-brief-metalens-delivery/spec.md).

- [x] Briefs preserve original wording, explicit declarations, and omissions.
- [x] `metalens-propagation-400nm-na030` compiles the accepted 660 nm period and propagation evidence topology.
- [x] `metalens-geometric-400nm-na030` compiles the accepted geometric evidence topology and explicit handedness.
- [x] Identical typed inputs produce identical studies and canonical bytes.
- [x] The compiler is pure and does not import the authority adapter, LLM client, solver, runner, or filesystem.
- [x] Unsupported large-na, multi-wavelength, missing-route, and fabrication-inconsistent briefs fail or remain unresolved honestly.
