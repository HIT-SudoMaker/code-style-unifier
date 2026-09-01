# Python scientific compilation

Status: superseded by ../metalens-sonnet-convergence/spec.md

## Problem

MetaCraft needs a small Python scientist behind the frozen Rust authority. It must preserve a user's brief, accept optional LLM advice without trusting it, compile the evidence still required, gather that evidence through qualified implementations, and return only conclusions whose exact closure Rust admitted.

The former Python runtime encoded workflow positions and duplicated lifecycle state. The replacement must be organized by scientific meaning and must allow future aims, routes, solvers, materials, and optimizers to remain Python-only changes.

## Current capability

The first complete capability is a single-wavelength, low-na metalens through either propagation phase or geometric phase. Periodic vector unit-cell responses come from a qualified Lumerical FDTD binding. Finite-aperture evaluation uses a qualified scalar angular-spectrum implementation in Python.

Two small standard briefs freeze the first tracer:

- `metalens-propagation-400nm-na030`: 400 nm, na 0.30, focal length 30 um, x-linear input, circular silicon-nitride posts on silica, solver-native materials, fabrication aspect limit 8, compact budget.
- `metalens-geometric-400nm-na030`: the same optical target with right circular input and rectangular silicon-nitride fins through geometric phase.

The exact Lumerical material names are binding facts discovered and recorded from the configured installation. They are not guessed in the brief.

## Scientific order

`brief → advice → design → study → task → evidence → result`

- A brief contains immutable user wording, typed declarations, and honest omissions.
- Advice is a received, unavailable, or invalid consultation record. It never becomes user fact or authority.
- A design resolves aim, objectives, operating conditions, constraints, allowed control strategies and capabilities, and budget.
- A study is the pure compiled route and proof snapshot for exact admitted inputs.
- A task is one fully bound operation with exact prerequisites, expected evidence, implementation, and capacity scope.
- An observation becomes evidence only after Python validates its scientific form and Rust admits it.
- A result is pure evaluation of a complete admitted evidence closure.

No mutable workflow position, task status, retry ledger, or scientific authority exists in Python.

## Scientific language

The public scientific language is `brief → study → result`.

- Aim and objectives belong to the brief.
- Route and proof belong to the study.
- Claim and method are internal compiler language.
- Task and binding are execution language.
- Permit and receipt remain Rust authority language.

An aim declares terminal claims. A registered method establishes one claim
from exact prerequisite claims and evidence under explicit applicability
conditions. The compiler composes these relations into a deterministic proof;
it does not select a prewritten route package.

The compiler exposes no public rule, graph, registry, plugin, reflection,
dynamic-discovery, or AI-planning Interface. Aim modules do not own an
end-to-end process, and method modules do not collect briefs, run workers,
admit facts, or return route results.

## Frozen authority boundary

The private native dependency is `metacraft_next._authority.Authority`. One Python adapter preserves the constructor and the four verbs `check`, `view`, `fetch`, and `decide`, while translating protocol values to typed Python values.

Scientific modules do not import the native extension, encode proposals, parse raw decisions, rebase revisions, or maintain a second authority view. Rust source is unchanged by this feature.

## Compilation rules

Compilation is pure for validated brief, validated advice, policy, admitted evidence, and registered capabilities. Identical inputs produce identical typed studies and canonical bytes.

A declared applicable control strategy is honored. A sole applicable
claim–method proof may be determined. When several proofs remain applicable,
advice may explain a choice but the compiler preserves the unresolved decision
until the user or deterministic policy supplies it.

The two current routes are golden proof relationships compiled through the
same seam:

- propagation phase closes `focus ← scalar field ← aperture ← phase set ← fixed-height cell library ← periodic complex transmission ← material and height evidence`;
- geometric phase closes `focus ← converted and retained fields ← channel apertures ← analytic orientations ← one anisotropic cell ← Jones response and polarization convention ← material and height evidence`.

Propagation matching uses one canonical phase circle on `[0, 2π)`, treats
`0 ≡ 2π`, and uses cyclic distance. The geometric proof gathers its x and y
responses sequentially beneath one permit, then derives orientation states
analytically without orientation-specific FDTD tasks.

Their matching projection is intentionally shared:

- `phase.value`
- `power.useful`
- `power.leakage`

Raw route evidence remains distinct. Geometric evidence retains:

- `linear.from_x.along_x`
- `linear.from_x.along_y`
- `linear.from_y.along_x`
- `linear.from_y.along_y`
- `circular.converted`
- `circular.retained`

Future relationship fixtures must prove that the same compiler can form:

- large-na metalens focus claims through vector, Debye, pointwise, or
  optimization methods;
- holographic reconstruction, fidelity, efficiency, and crosstalk claims;
- quasi-bic resonance, Q, symmetry, radiation-channel, eigenmode, and
  driven-spectrum claims without phase, aperture, or focus requirements;
- frequency-selective reflection, transmission, absorption, bandwidth, angle,
  and polarization claims without entering an imaging proof.

These fixtures declare relationships only. Their solver implementations remain
out of scope, and adding them must leave Rust unchanged.

## Standard geometry policy

For the current metalens slice:

- `unit_cell_period = floor_to(reference_wavelength / (2 × numerical_aperture), 10 nm)`;
- `grating_x_span = grating_y_span = unit_cell_period`;
- `grating_z_min = -0.5 × reference_wavelength`;
- `grating_z_max = atom_height + 0.5 × reference_wavelength`;
- `reflection_plane_z = grating_z_min + 100 nm`;
- `transmission_plane_z = grating_z_max + 100 nm`;
- substrate height is 2000 nm;
- visible atom-height candidates lie from 500 to 800 nm;
- infrared atom-height candidates lie from 0.5 to 0.6 wavelength on a 50 nm grid;
- `atom_height / smallest_feature ≤ aspect_limit`;
- the conservative lateral domain is `minimum_feature` through `period - minimum_feature`;
- propagation geometry uses a 10 nm lateral step;
- geometric geometry uses a 20 nm step with `length > width`.

For the standard 400 nm, na 0.30, aspect-limit 8 briefs, compilation yields a 660 nm period, 100 nm minimum feature, and 560 nm maximum feature. Height evidence is gathered before a full lateral library; height and lateral candidates are not expanded into an unconditional Cartesian workflow.

## Lumerical binding

### Local workstation

Local process placement is solver-neutral. A shared Python workstation Module
observes Windows processor groups, NUMA nodes, LLC domains, physical cores,
SMT siblings, and node-local memory. It exposes an opaque layout of fixed
lanes:

- one lane contains four distinct physical cores from one locality cell;
- exactly one hardware thread from each core is available to the engine;
- SMT siblings are excluded;
- one Job Object contains the complete process tree under a 16-GiB committed
  memory limit;
- four physical cores and 16 GiB remain outside solver admission for the
  workstation;
- placement and memory are read back before work becomes executable.

The workstation Module knows neither Lumerical nor any scientific route. A
solver Adapter supplies a worker command and owns product discovery, license
facts, native construction, and result parsing. The workstation starts the
worker suspended, binds it to the lane and Job Object, verifies the effective
placement, and resumes it. The Adapter chooses the product entrypoint:
Lumerical uses its direct `fdtd-engine.exe`, while a future product may use an
Adapter-owned worker that opens its API inside the contained process tree.

Python combines the fresh workstation layout with the solver's fresh license
limit, then proposes the resulting capacity to Rust. One lane maps to one
permit and one active worker process tree.

The caller supplies a compiled study, not a worker count. The product dispatch
automatically observes license and workstation facts, admits their tightest
capacity, and executes only the remaining candidates in bounded waves.
Capacity is renewed between waves when stale. Independent sweeps share the
same permit scope and wait for available lanes instead of overbooking or
failing on temporary contention.

The first client is the Lumerical Adapter. A future CST or COMSOL Adapter must
use the same workstation Interface. No common cross-product solver Interface
or CST implementation is introduced in the current slice.

The external solver follows:

`configured → found → versioned → licensed → qualified → available`

Exact executable and Python API paths come from environment configuration. A
binding records the exact product build, API, solver-native material identities,
and qualified templates. It carries no current worker count. A separate
capacity observation records the exact resource and license facts, chooses the
tightest supported bound, and carries an explicit freshness policy.

The Lumerical implementation is a deep package. Only its session boundary touches `lumapi.FDTD`. Product-specific object construction stays inside product-specific templates:

- propagation: circular post first, square post later;
- geometric: rectangular fin first, elliptical fin later.

Both templates use one periodic FDTD region and
`addobject("grating_s_params")`. The group owns its source and reference
planes; MetaCraft creates no standalone source or monitor beside it. The
templates perform construction read-back and save before/after projects,
construction evidence, observation evidence, and logs beneath the workspace
`runs/` directory.

One Rust permit means one Python worker and at most one active solver engine.
A geometric candidate runs the x and y inputs sequentially under that one
permit. One candidate never starts a nested native sweep; independent
candidates and independent sweeps may run concurrently only while shared
permits and lanes remain available.

## Materials and advice

Portable material records may come from a user `txt`/`csv` table or immutable refractiveindex.info source bytes. They retain provenance, units, covered band, canonical optical data, and explicit interpolation, and never extrapolate silently.

Solver-native materials remain confined to their exact qualified binding.

The adviser surface is provider-neutral and configured by base URL, API key, and model. DeepSeek may be one provider but does not name a public module. Default tests use a deterministic fixture; live network consultation is opt-in.

## Evaluation and artifacts

The scalar angular-spectrum evaluator freezes coordinate, sampling, padding, Fourier sign, shifts, normalization, and evanescent treatment. Analytic and convergence fixtures qualify it before a focusing result is returned.

Every run is rooted beneath `runs/` and names UTC time, aim, control strategy,
and a stable run key. Candidate directories use natural geometry names and a
short content identity. Partial valid observations remain reusable after a
failed or interrupted sweep.

## Verification

- Default tests use fake authority, adviser, and solver seams where external installations are not required.
- The native boundary is also exercised against the built extension.
- Live LLM consultation is opt-in. Live Lumerical qualification remains an
  explicit open gate until an installed build and its license/material
  read-backs are available; the offline fixture is not presented as live proof.
- Every vertical slice tests malformed inputs, stale authority revisions, missing evidence, and deterministic replay where applicable.
- The final suite asserts that Rust source and its public protocol remain unchanged.

## Out of scope

- large-na propagation, vector angular spectrum, Debye/Richards–Wolf evaluation, and optimization;
- holographic, frequency-selective, quasi-bic, achromatic, and multi-wavelength implementation;
- CST or COMSOL product Adapters, license checks, native construction,
  execution, observation parsing, or native materials; their future use of the
  shared workstation Interface is already fixed;
- full-device FDTD as a permanent required workflow;
- widening or changing the Rust authority protocol.
