# 06 — Let the binding propagate and let incomplete focus wait

**Type:** implementation

**Status:** wontfix

**Superseded by:** [Metalens Sonnet convergence](../../metalens-sonnet-convergence/spec.md).

**Blocked by:** ticket 01.

## Outcome

The compiled task binding owns how a Field is realized and propagated.
Science callers provide a Field, not an optional algorithm switch. A sampled
focus window that does not contain the complete focus remains a waiting
Study, never a contradictory Result.

## What to build

- Remove optional propagation convention or algorithm arguments from the
  public Field propagation interface.
- At the local application seam, verify that the ready task names the
  composition-time qualified angular-spectrum binding before invoking that
  concrete realization. Record the binding and realization in focal-region
  provenance.
- Keep scalar angular-spectrum behavior unchanged for the current low-na
  routes.
- Prepare one source spectrum per component and propagate requested axial
  distances through bounded vectorized batches. Preserve the adaptive survey
  and local-refinement order while removing plane-by-plane inverse-transform
  calls; keep the batch bound private to the qualified realization.
- Admit an edge-clipped or otherwise incomplete focus survey as a diagnostic
  record, not as the task's expected `focus` document.
- Add the Python finding kind `incomplete`; return a `focus` finding whose
  need is `focus_incomplete` and whose record references include the
  diagnostic.
- Extend a finding with immutable diagnostic record references. Accept a
  reported `incomplete` finding only for a known proof claim, with at least one
  admitted record; retain the existing duplicate-claim rejection.
- Prevent incomplete focus evidence from closing the proof or constructing a
  Result.
- Keep the requested `[0.8f, 1.2f]` observation window fixed; do not silently
  expand and retry it.

## TDD seam

Begin at the public Field/evaluation seam with one complete focus and one
edge-clipped focus. The failing assertions should expose both leaked algorithm
choice and contradictory Result construction.

## Acceptance

- Public callers cannot pass a propagation convention or algorithm name.
- The qualified angular-spectrum binding is accepted and a mismatched binding
  cannot dispatch through the same operation.
- A structural test proves one source FFT per component and one inverse
  transform per axial batch, with numerical equivalence to reviewed
  single-plane fixtures and no wall-clock threshold.
- Complete focus still reports the established focal metrics.
- Incomplete focus produces durable diagnostics and a waiting Study, with no
  exception during Result construction because no Result is attempted.
- Unknown-claim, duplicate, or reference-free incomplete findings are
  rejected before task dispatch.
- Authority reopen preserves the realization and waiting reason.
- The public return remains `Study | tuple[Result, ...]`; no mixed outcome
  carrier is introduced.
- Focused tests, architecture tests, Pyright, and CSU on touched files pass.

## Do not add

- Vector angular spectrum, Debye--Wolf, or optimizer implementations.
- Automatic focus-window enlargement.
- A new Rust state or protocol field.
- A public propagation protocol or runtime method registry for one concrete
  realization.
- A caller-supplied batch size, plane worker count, or performance threshold.
- Route-specific Field APIs.
