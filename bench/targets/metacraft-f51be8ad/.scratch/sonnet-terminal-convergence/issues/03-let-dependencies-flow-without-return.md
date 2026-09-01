# Let dependencies flow without return

Type: implementation

Status: resolved (2026-07-29)

Blocked by:
[Let Python accept only what Rust can say](02-let-python-accept-only-what-rust-can-say.md).

## Outcome

The production Python runtime import graph is a DAG. Explicit composition
selects concrete aims and platforms; generic science and pure workstation
models never import their consumers.

## Scope

1. First add an architecture test that discovers runtime imports under
   `src/metacraft_next`, including function-local imports, excludes only
   `TYPE_CHECKING`, and reports every strongly connected path.
2. Record ADR 0014, “Let dependencies flow without return”.
3. Arrange compiler ownership as:
   - `science/compile.py`: public `compile_study` and explicit aim composition;
   - `science/compiler.py`: aim-neutral Study formation;
   - `science/metalens/compiler.py`: metalens validation, design, advice, and
     relationship interpretation.
4. Keep `science.relationships` as values only. Remove its reverse aim
   selector.
5. Remove `Study.metalens`. Add the single strict aim-owned narrowing
   `metalens_design(study)` and migrate production callers without an alias.
6. Replace generic unions of design, period, and height advice with one
   structural `Advice` Interface. Concrete interpretation remains metalens
   owned.
7. Make workstation model planning require explicit Host facts.
8. Preserve package-level `workstation.plan`: its outer composition observes
   Windows only when Host is absent, then calls the pure planner.
9. Delete all three baseline strongly connected components:
   - `science.study <-> science.metalens.design`;
   - `science.relationships <-> science.metalens.relationship`;
   - `workstation.model <-> workstation.windows`.

## Acceptance

- Every production runtime SCC has size one with no allowlist.
- `science.study`, `science.compiler`, and `science.conduct` import no
  metalens Module.
- `science.relationships` imports no aim Module.
- `workstation.model` imports no platform Module.
- `compile_study` retains its public call meaning and canonical outputs.
- package-level `workstation.plan` retains observed and supplied-Host
  behaviour.
- PeriodAdvice and HeightAdvice remain aim-local, immutable, and untrusted.
- Future aims require one explicit composition branch, not changes to generic
  Study vocabulary.

## Focused tests

- runtime import DAG with useful cycle output;
- propagation and geometric compile golden values;
- incomplete and unsupported aim behaviour;
- advice ordering and exact reference behaviour;
- strict metalens narrowing;
- workstation planning with explicit Host;
- workstation planning with platform observation patched at the package seam.

## Verification

- focused science, workstation, and architecture tests;
- Pyright;
- touched-file CSU;
- production Rust diff is empty;
- fixed-range `git diff --check`.

## Stop and report

Stop before changing brief physics, public compile meaning, document bytes,
workstation lane policy, or Rust.

## Do not add

Do not add an aim registry, plugin discovery, compiler class hierarchy,
dependency container, compatibility alias for `Study.metalens`, workflow
framework, or empty future-aim package.

## Resolution

Commits `a93d8bc` and `44c493d` made the production runtime import graph a DAG
without an allowlist. Composition selects aims and platforms; generic science
and the pure workstation planner no longer import their consumers. ADR 0014
records the accepted dependency direction.
