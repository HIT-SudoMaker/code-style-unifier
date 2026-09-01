# Map — Make authority swift and science exact

**Label:** `wayfinder:map`

**Status:** road completed (2026-07-29)

## Destination

One reviewed canonical specification and six implementation tickets that make
MetaCraft's existing architecture fast under long authority histories, exact
at every Python and solver seam, and complete across every propagation branch
without widening the frozen public lifecycle.

The road completed on local `main` at `ca90c27`. Tickets 01–05 were integrated
without running a live adviser, Lumerical solve, or canonical brief; Ticket 06
remains the separate human gate.

## Notes

- Canonical language comes from `CONTEXT.md`; system boundaries come from
  `DESIGN.md`, `AUTHORITY.md`, `SCIENCE.md`, `DEVELOPMENT.md`, and the ADRs.
- Sonnet means balanced ownership, paired language, one-way dependencies,
  natural names, deep Modules, and the smallest truthful Interface. It does
  not name a model.
- Rust changes first and closes completely before Python implementation
  begins.
- The public authority Interface remains exactly
  `check -> view -> fetch -> decide`.
- The implementation road is [the canonical specification](spec.md) followed
  by the six tickets under `issues/`.
- Focused tests run per ticket. The complete non-live suite runs once at
  closure. Live delivery remains an explicit human gate.

## Decisions so far

- [Let authority remember what it has proved](issues/01-let-authority-remember-what-it-has-proved.md)
  — one full audit establishes a private verified authority state; stable
  `view` and `decide` reuse that proof, while any external generation change
  forces another full audit.
- [Let the Python view reject what Rust did not say](issues/02-let-the-python-view-reject-what-rust-did-not-say.md)
  — the Python Adapter decodes exact protocol values without coercion or
  compatibility repair.
- [Let every branch return with its siblings](issues/03-let-every-branch-return-with-its-siblings.md)
  — `conduct` owns and records the complete delivered frontier after every
  transition; operations return facts and do not checkpoint partial knowledge.
- [Let each periodic response prove itself](issues/04-let-each-periodic-response-prove-itself.md)
  — periodic transmission and periodic polarization are independent,
  route-neutral capabilities backed by their own execution fixtures.
- [Let the architecture close without residue](issues/05-let-the-architecture-close-without-residue.md)
  — shared meanings become single implementations, architecture ratchets tell
  the truth, dead paths disappear, and planning status agrees with Git.
- [Run the canonical live delivery](issues/06-run-the-canonical-live-delivery.md)
  — live smoke and four-brief delivery remain human-enabled only after the
  repaired non-live baseline is green.

## Not yet specified

Nothing. The design tree is closed and the implementation road is fully
specified.

## Out of scope

- A content-addressed projection tree, ledger delta migration, Merkle or
  Patricia storage, or another authority storage format. Those may offer a
  deeper asymptotic redesign, but they require a separate Rust-first effort.
- Any new public authority verb, Python workflow Interface, mutable task
  status, background health service, retry database, solver registry, or
  compatibility layer.
- Large-NA methods, optimization, holographic synthesis, quasi-BIC,
  frequency-selective-surface implementation, CST, COMSOL, RCWA, or GUI work.
- Changes to briefs, physical thresholds, Torch device policy, two-times
  padding, workstation lane policy, scientific matching, or result metrics.
- Running live adviser calls, native Lumerical qualification, solver sweeps,
  or the four canonical briefs during implementation.
