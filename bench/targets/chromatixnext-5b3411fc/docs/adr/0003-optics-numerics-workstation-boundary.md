# The optics / _numerics / workstation.py seams

**Status:** Accepted

**Partial supersession:** the "exposes only `Workstation` and `Precision`"
public-imports claim in the Public imports subsection is partially superseded
by `0008-active-polarization-foundation.md` re: the actual top-level public exports
(`Workstation` and `install_state`; `Precision` was already removed by
`0005-fixed-double-scientific-core.md`). The hosted-load behaviour that
ADR-0003 did not constrain in the Workstation Host Claim paragraph is
partially superseded by `0006-state-installation-and-immutable-hosting.md`
(implemented by Tickets 07 and 08 of the final-seal initiative). The rest
of ADR-0003 remains in force, and it remains the implemented truth at
baseline `92a69d9`.

**Partial supersession:** the tensor-storage lifetime model in the One-way
dependency subsection below enumerates "final Physical Values" as the
retained run-result category that enters the conservative Memory Estimate
(alongside operator inputs and results, aliases, disposable temporaries,
non-persistent caches, and autograd-saved storage). The implicit "no retained
intermediate" reading of that category — that only final Physical Values are
retained as run results — is partially superseded by
`0011-assembly-topology-contract.md` (Accepted — implemented present truth,
converged by the sonnet-assembly-topology-closure initiative) re: the
implemented Authored Exposure semantics. Under ADR-0011 an Authored Exposure
may name a topologically intermediate output and is retained through run
completion as a final Named Output, so the conservative Memory Estimate must
account for that retained lifetime rather than treating the non-consuming
readout as free; one Tensor storage still contributes only once when several
Named Outputs alias it. Only the "final Physical Values only" reading of the
retained run-result category is narrowed; the memory-tracing architecture, the
`real model peak <= meta conservative peak` safety relation, the Assembly
ownership of topology and authored exposures (not memory estimation), and the
rest of ADR-0003 stay in force. The older "final Physical Values" wording
below stays in place as the bannered frozen record, not unbannered present
truth.

## Context

The legacy source tree separated `science`, `optics`, `assembly`,
`simulator`, `workstation`, and evidence packages, but did not enforce the
separation (historical ADR 0225 noted that operation-local execution modules
under `optics/` imported simulator strategy abstractions, while simulator
preflight code imported admission manifest types). The result was weak
ownership, duplicate concepts across overlapping packages, and names that did
not follow the project's paired domain language.

The refactor collapses the production package to exactly three seams
with one enforced dependency direction.

## Decision

### Three production seams only

The installed package contains exactly:

1. **`chromatix_next/optics/`** — the sole scientific base. It owns the flat
   Physical Value modules (`field.py`, `intensity.py`, `grid.py`,
   `spectrum.py`, `medium.py`, `polarization.py`), the `assembly.py`
   authoring layer, the private `_role_contract.py` validation module, and the
   five singular Optical Role packages (`source`,
   `element`, `propagation`, `combination`, `detection`).
2. **`chromatix_next/_numerics/`** — private PyTorch reference kernels and
   safe numerical caches. It is private; nothing under `_numerics` is part of
   the public API.
3. **`chromatix_next/workstation.py`** — the single execution-seam file.
   It owns platform, device, `Precision`, memory, placement decisions, run
   randomness, execution, populated Named Outputs, and Run Record. Its
   cohesive private support lives in two root modules. `_execution_memory.py`
   traces tensor-storage lifetimes across meta and real replay.
   `_ownership.py` is the second private root support: it owns the host
   ownership registry, weak references, locks, the Windows CUDA singleton,
   claim/release/assert operations, and the atomic preflight-placement-commit
   protocol. Workstation owns platform, device, and precision policy and how
   a module tree is placed; ownership mechanics, registry state, and their
   locks stay inside `_ownership.py` and do not leak across the seam.
   Neither module is a fourth public seam.

No other production package exists. The banned legacy package names
`core`, `science`, `simulator`, `runtime`, `workflow`, `optimization`,
`experiment`, `registry`, `utils`, `measurement` (as a role), `emission`
(fluorescence), and `evaluation` (as a layer) are excluded.

### One-way dependency

The only allowed dependency direction is:

```
workstation.py  ->  optics  ->  _numerics
```

- `_numerics` imports nothing from `optics` or `workstation`.
- `optics` imports nothing from `workstation`.
- `workstation.py` may import from both, as the top of the chain.

Physical Value modules never depend on Component modules; Components depend
on Physical Values. Tests, Examples, and release tooling may consume the
production package; production modules never import them.

Physical Value modules own no shared Component base or resource policy.
Spectrum and Source Polarization State are immutable physical inputs. An
Optical Field carries only Polarization Representation; its Jones components
live in the envelope and are never duplicated as field metadata. Assembly
first asks each Component owner to revalidate mutable physical state, then
evaluates real Component `forward` methods through the sole isolated sandbox
in `optics/_meta_inference.py`; root execution support reuses that sandbox
from above, while optics never imports root execution policy. There is no
Field Description or handwritten memory twin. Fixed tensors used by a
Component are Buffers, user Parameters preserve identity, and every public
physical value rejects non-finite state at its owning interface.

The Component-owned `_output_grid_for` seam is the only narrow exception to
meta-only allocation. During that call, an exception- and thread-local guard
permits single-element real grid metadata so continuous coordinates are
checked by the same resolver as execution. Arrays and field-scale real
storage remain forbidden; no Field Description or grid twin is introduced.

The isolated meta execution and the later real execution share one weak
tensor-storage lifetime tracer in `_execution_memory.py`. Public factories,
operator inputs and results, input-factory values, aliases, disposable
temporaries, non-persistent caches, final Physical Values, and autograd-saved
storage enter that one model. Tensor wrappers are weakly observed, so tracing
does not turn the whole calculation into a cumulative allocation sum.
Nested mappings and dataclasses are traversed without retaining their tensors.
Registered Parameter and Buffer views are deduplicated by storage identity,
excluded from the dynamic trace, and added once. Explicit real-device requests
are rejected before a meta factory runs except for the bounded
`_output_grid_for` metadata phase described above.

`Workstation.run` is the sole public replay boundary. A frozen Assembly is a
convenience input translated to the same private replay request as a
module-level calculation; Assembly has no public `forward`. It remains a
PyTorch Module only to register the authored component and parameter tree.
Its frozen connections, exposures, and execution steps name Components rather
than retaining instances or Python identities. Assembly Check and Workstation
meta/real replay consume that same private fact through one private Assembly
replay implementation.

Meta values cannot read physical cache keys, and existing scientific caches
deliberately miss on meta rather than inventing values. Therefore the safety
relation is `real model peak <= meta conservative peak`, not unconditional
byte equality: a representative cold calculation proves equality, while a
warm real cache may prove a strictly smaller peak. A real peak above the meta
peak is rejected. Names, Physical Value types, carrier shapes and dtypes are
equal across replay, and each stage independently enforces its required
device. This is a deterministic tensor-storage model, not a claim of equality
with CUDA workspaces, allocator fragmentation, or driver memory.

`Workstation.run` has one replay engine. A module-level calculation is
injected with an explicitly hosted Module root and a replayable
`inputs(device, precision)` factory. Closures, callable objects, captured or
runtime-created Modules, and real allocations outside the bounded
`_output_grid_for` metadata phase are rejected during meta preflight. Frozen
Assembly remains a convenience input but resolves to the same private replay
request; Assembly owns topology and authored exposures, not memory estimation.
Workstation creates Named Outputs only after a successful real replay. Meta
and real randomness use separately reconstructed named generators from the
same root seed; `Workstation.generator` exposes the same derivation without
touching global random state.

### Public imports

The top-level `chromatix_next/__init__.py` exposes only `Workstation` and
`Precision`. Physical Values and `Assembly` come from `chromatix_next.optics`;
every Component comes from its singular role package. There is no duplicate
re-export, no public registry, no dynamic name lookup, and no compatibility
alias.

### Propagation geometry and execution choice

Destination Grid is one explicit Spatial Grid, not an aligned/shifted wrapper
hierarchy and never a propagation-method selector. A propagation Component
accepts the requested geometry, executes only the scale, shift, orientation,
and sampling it scientifically supports, and rejects the rest without
substitution. Later scaled or transformed methods reuse the same geometry
language.

The implemented Propagation surface names each physical action explicitly:
`scalar_angular_spectrum` / `ScalarAngularSpectrum`,
`vector_angular_spectrum` / `VectorAngularSpectrum`, and
`aplanatic_focus` / `AplanaticFocus`, alongside the distinct Fresnel
Transform. Scalar and vector plane propagation are not interchangeable with
the aplanatic objective map. Aplanatic Focus alone owns its private separable
Bluestein CZT production support. Direct angular quadrature and
Fourier-Bessel constructions remain test evidence outside production; no
public transform, backend, or automatic method selector is introduced.

Workstation is created only through explicit CPU and CUDA factories. There is
no direct public device constructor, automatic discovery, fallback, or
hypothetical implementation-support hook.

Workstation Host claims the complete PyTorch module tree rooted at an
independent Component or frozen Assembly. A read-only ownership preflight first
validates that the tree is wholly unhosted, then placement and ownership commit
atomically. Repeating the same complete root on the same Workstation is
idempotent; a partially hosted tree or any ownership by another Workstation is
rejected without mutation. Ownership is stored in a Workstation-side weak-key
registry rather than in researcher module dictionaries. The owning Workstation
may explicitly release the original root without moving its state; deep copies
and serialized copies therefore carry no stale claim. Every run revalidates
complete-tree ownership and every returned Physical Value tensor against its
placement contract. The decision kept floating and complex Parameter/Buffer
state, Field Envelope, Intensity, and Spatial Grid on the selected paired
Precision, while dynamic Tensor Optical Path References use `float64` on that
same device. This precise accumulator did not introduce a second Precision
selector or widen all module state. Run Record names the implementation,
device, and selected Field/numerical-kernel Precision, not the invariant
Optical Path accumulator dtype.

Windows permits one live CUDA Workstation in a process. Linux may hold
independent Workstations for different local CUDA devices, but a single run
never splits tensors across devices.

## Consequences

- There is no governance layer, no second runtime, and no evidence package
  inside production source.
- Later propagation, vector, scattering, compiled, native CUDA, and multi-GPU
  work extend one appropriate module without forcing circular imports or
  copying scientific rules across execution adapters.

> **Superseded reading order.** An earlier version of this section prescribed
> navigation "from execution seam to Physical Values to optical actions to
> Assembly to hosting to run." That sequence is not a consequence of the
> three-seam decision and is no longer active truth. Cognitive order is owned
> by `CONTEXT.md`; dependency direction and researcher execution order are
> owned by `docs/architecture.md`. The three are kept distinct, and no reading
> path loops from Workstation through physics back to Workstation.

## Superseded history

Historical ADRs 0097, 0225, and 0227 established the one-way dependency
intent inside the legacy tree. Their lessons are recorded in `docs/history.md`.
