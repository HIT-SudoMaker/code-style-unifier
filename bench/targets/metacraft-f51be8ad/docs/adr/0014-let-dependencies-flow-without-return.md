# 0014 — Let dependencies flow without return

Status: accepted

## Context

Three production Python dependencies pointed from a generic value back to one
of its consumers. `Study` imported the metalens design that already extended
its generic `Design`; generic relationships selected the metalens
relationship that already used their values; and the pure workstation model
observed Windows even though the Windows Adapter already consumed its layout.
Function-local imports delayed these edges, but did not remove them. The
runtime import graph therefore contained three strongly connected components.

The compiler also mixed explicit aim selection, metalens interpretation, and
aim-neutral Study formation in one file. Generic Study and conduct values
named three concrete advice records, so adding another aim would have changed
shared vocabulary before it supplied any new science.

## Decision

The production Python runtime import graph is a directed acyclic graph. Every
runtime import, including one inside a function, participates. Only imports
guarded by `TYPE_CHECKING` are absent at runtime and excluded. One architecture
test discovers the graph statically, uses no allowlist, and reports every
strongly connected component with its internal source edges.

Compiler ownership follows one direction:

```text
science.compile
    public compile_study and explicit aim composition
        ↓
science.metalens.compiler
    metalens validation, design, advice, and relationship interpretation
        ↓
science.compiler
    aim-neutral proof, task, evidence, and Study formation
```

`science.relationships` owns only `Method` and `Relationship` values. The
composition root selects an aim; no value Module selects its consumer.

`Study` stores a tuple of structural `Advice`. Design, period, and height
consultations satisfy that Interface without inheritance, conversion, or
registration. Concrete advice interpretation remains aim-owned.

`Study` exposes only its generic `design`. Metalens owns the one strict
`metalens_design(study)` narrowing operation. The former `.metalens`
convenience property is removed without an alias.

`workstation.model.plan` requires explicit `Demand` and `Host` facts. The
package-level `workstation.plan` remains the composition seam: it observes
Windows only when the caller did not supply a Host, then invokes the pure
planner.

## Consequences

- Generic values import no aim or platform consumer; all three baseline
  strongly connected components disappear.
- A future aim adds one explicit composition branch and its own compiler. It
  does not alter Study vocabulary or a generic selector.
- Public `compile_study` and package-level `workstation.plan` retain their
  meaning while internal module paths and `Study.metalens` deliberately
  change.
- Canonical brief, design, proof, task, evidence, Study, and result bytes do
  not change.
- No registry, plugin discovery, compiler hierarchy, dependency container,
  compatibility alias, or workflow framework is introduced.
