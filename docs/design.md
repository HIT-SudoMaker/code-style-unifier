# CSU Design

This document owns the architectural reasoning behind CSU. The Coding Standards
define what source should mean; this document defines how CSU can judge that
meaning simply, quickly, and without manufacturing certainty.

## 1. Decision

CSU is one stateless Rust reviewer with one public lifecycle:

```text
compile Authority
  -> admit one frozen Snapshot
  -> capture each file once
  -> observe bytes and structure
  -> judge enabled rules
  -> close every required Fact Family
  -> seal one Terminal
  -> project read-only output
```

Byte/line observation handles physical source facts. A pinned Tree-sitter
grammar handles declaration ownership and attachment facts. These are two
observation tracks inside one File Review, not two parsers and not two review
engines.

The design spends precision only where the source can prove it. A missing fact
becomes Incomplete. A semantic ambiguity becomes Review Required. Neither can
be converted to Clean by a fallback.

## 2. Priorities

The priorities are ordered:

1. A correct terminal is more important than a more detailed terminal.
2. One obvious lifecycle is more important than extension machinery.
3. Cold one-shot speed is more important than cross-run reuse.
4. Native language forms are more important than artificial cross-language
   symmetry.
5. Evidence size must follow files and Fact Families, not every possible rule
   claim multiplied by every declaration.

This order is intentional. CSU may conservatively return Incomplete where a
larger analyzer could recover more detail, but it must not return a confident
answer from guessed ownership.

## 3. What earlier approaches taught us

### Line-only scanning

A line scanner is fast and excellent for newlines, trailing text, visual width,
literal tokens, and characters inside a structurally supplied range. It cannot
reliably prove that a Python string is the first statement of a function suite,
that Rust documentation attaches to one item, or that a C++ comment owns a
particular declaration. Adding indentation and keyword heuristics would create
a second, incomplete parser.

### Structure-only scanning

A structural parser establishes declaration kinds, scopes, receivers, and
documentation attachment. Using it for every physical fact increases traversal
work and obscures simple byte evidence. It also does not remove language
limits: C and C++ preprocessing, build configuration, and public reachability
still require project Authority.

### Rich receipt graphs

Materializing every Claim × Subject × Demand relation makes evidence look
formal while multiplying memory, serialization, and ownership rules. Most of
those objects restate one of three facts: a family was not required, completed
with a count, or blocked for a reason. The larger model increases the number of
ways a review can remain half closed.

### Incremental caches

A cache requires content identity, invalidation, dependency tracking, schema
migration, partial-result trust, and recovery after interrupted writes. A
one-shot 200,000-line review already fits the performance budget, so this
complexity has no current owner. Digests bind evidence; they do not authorize
reuse.

## 4. The public seam

The library exposes one deep module:

```rust
pub struct WorkspaceReviewer { /* immutable compiled Authority */ }

impl WorkspaceReviewer {
    pub fn compile(
        authority: AuthorityInput,
    ) -> Result<Self, ReviewRejection>;

    pub fn review(
        &self,
        input: ReviewInput,
    ) -> ReviewTerminal;
}
```

Callers learn Authority admission, Review input, terminal semantics, and
performance characteristics. Parsers, language adapters, Fact rows, judgment
operators, and closure storage remain private. Tests cross the same seam as the
CLI.

The module is deep because deleting it would spread four-language parsing,
completion, ordering, and sealing into every caller. Internal helpers that only
forward data without owning an invariant should be folded back into their
owner.

## 5. Authority is compiled before source access

Authority is project-owned executable data. It declares the enabled rule
families, language projections, grades, messages, public surfaces, identifier
vocabulary, unit suffixes, and presentation order.

Compilation must reject missing language projections, unknown operators,
duplicate identities, invalid registries, or absent capabilities before any
target file is read. After compilation, review uses typed rows and closed
operator kinds; it does not interpret regexes, scripts, callbacks, native
plugins, or a general rule language.

This places combinatorial rule configuration outside the hot path while keeping
semantic ownership in one visible input. Expanding vocabulary is an Authority
change. Adding a new kind of source fact is an implementation change and must
cross the public test seam.

## 6. One File Review

Each admitted file follows a finite transaction:

1. Capture its bytes once.
2. Build one line index and perform one byte sweep.
3. Parse structurally at most once when an enabled family needs structure.
4. Convert parser-owned nodes into small owned facts.
5. Apply closed judgments to those facts.
6. Close every required file/family cell.
7. Release the syntax tree, cursors, and source buffer.

Tree-sitter nodes, borrowed slices, and parser state cannot escape this
transaction. The two observation tracks share byte offsets and the same source
capture.

### Byte/line track

This track owns physical lines, offsets, literal characters, and text inside
ranges already established by structure. It does not infer declarations from
keywords, indentation, braces, or neighboring comments.

### Structural track

This track owns declaration kind, scope, source order, receiver roles,
documentation attachment, and dependency constructs. It does not reread files
or implement physical-text rules through a second traversal when a byte check
is sufficient.

## 7. Four parallel language profiles

Python, Rust, C, and C++ share rule intent, not invented syntax. Every enabled
rule family has one explicit projection per language:

```text
Supported(contract) | NotApplicable(reason) | NeedsAuthority(capability)
```

Python documentation is a suite-first string expression. Rust documentation is
an attached outer documentation form. C and C++ documentation is a
project-recognized adjacent block whose public owner must be declared. Likewise
`import`, `use`, `#include`, and C++ module `import` remain separate structural
subjects.

C and C++ do not become equivalent because their surface text resembles each
other. Header language, preprocessing assumptions, declaration identity, and
public ownership must come from Authority when syntax alone cannot prove them.

## 8. Compact closure

Completion uses a fixed cell for each admitted file and Fact Family:

```text
NotRequired
Complete(observed_subject_count)
Blocked(reason)
```

There is no successful Pending state. `Complete(0)` means the family was
observed and no subject existed; absence of a cell is an internal failure.
Required/executed masks prove that every selected operator ran. Findings and
blockers are sparse, while family state remains dense and bounded.

The storage bound is therefore:

```text
O(file × fixed family count + blockers + findings)
```

rather than the product of claims, subjects, and demands. Closure is a
construction property, not a convention checked by a final boolean.

## 9. Terminal algebra

`ReviewTerminal` has three shapes:

```text
Rejected(ReviewRejection)
Failed(ReviewFailure)
Sealed(SealedReview)
```

A Sealed review derives its Disposition without configuration:

| Evidence | Disposition |
|---|---|
| Complete and zero Findings | Clean |
| Complete and one or more Findings | Findings |
| Any Blocked required family | Incomplete |
| Invalid Authority or request before admission | Rejected |
| Broken internal invariant after admission | Failed |

The Seal commits to Authority identity, Snapshot identity, scope, family states,
counts, Findings, Completion, schema version, and canonical ordering. It excludes
absolute paths, clocks, thread order, UI layout, and output destinations.

Human and JSON output are projections of the same Terminal. A renderer or file
write failure cannot change a semantic result.

## 10. Damaged syntax

CSU does not require target code to compile. Tree-sitter can produce a tree that
contains `ERROR` or `MISSING` nodes, and byte/line facts may still be valid.

For Direct Source, structural damage produces a source-anchored parseability
Finding and blocks every structure-dependent family for that file. Independent
physical facts remain available. External Source records the obstruction
without assigning a project-rule violation.

The first release blocks at file/family granularity instead of building a range
contamination graph. This can be conservative, but it keeps one evidence store
and prevents recovered syntax from silently authorizing Clean.

## 11. Anti-evasion

The governed declaration remains the Review Subject throughout repair. A
Finding is not closed by replacing a documentation carrier with an ordinary
comment, deleting or renaming the declaration, shrinking scope, weakening
Authority, adding an exclusion, or accepting Incomplete.

Public callables require the language profile’s arguments, returns, and
failures roles. Internal callables require a concise summary in the native
carrier. This makes “comment instead of docstring” observable in all four
languages while avoiding public-contract verbosity inside private code.

## 12. Performance and size

Product Rust has a hard ceiling of 20,000 physical lines. Tests, fixtures, and
frozen third-party corpora are reported separately and cannot carry production
logic.

The release workload is a fresh-process, no-cache review of exactly 200,000
physical lines across the four languages. Its p95 must remain below ten seconds
and 30 identical runs must produce one projection digest. From the 2.0 baseline
forward, a semantically identical candidate must also remain within 1.5× p95
and 2× peak RSS.

Parallel execution may be introduced only behind the same interface and only if
canonical output, one-capture/one-parse counts, and memory bounds remain
unchanged. Concurrency is an implementation choice, never Seal semantics.

## 13. Verification strategy

The highest-value fixture is:

```text
WorkspaceReviewer::compile(in-memory Authority)
  -> review(in-memory four-language DocumentSet)
  -> ReviewTerminal + Seal
```

A compact matrix proves valid carriers, ordinary-comment evasions, missing
public roles, short candidate symbols, and damaged syntax in all four languages.
Focused tests exist only for genuinely different semantic branches. CSU then
reviews its own product source with its self Authority; Clean requires zero
Findings and zero Blocked families.

The frozen real-project corpus proves throughput and exposes unsupported
language shapes. It is not a Clean example project and cannot be edited to
improve the score.

## 14. Release design

GitHub Actions builds on native Windows, Linux x86-64, Linux ARM64, macOS Intel,
and macOS Apple Silicon runners. The release job starts only after every package
exists, computes SHA-256 checksums, waits for the next five-minute clock
boundary, and publishes one GitHub Release.

Packaging logic stays in the workflow because it is release orchestration, not
product behavior. The repository does not maintain a second local packaging
program.

## 15. Change discipline

Stop and revisit this design if a proposed feature needs any of the following:

- a second rule source or dynamic rule execution;
- a public parser or language-adapter interface;
- repeated file reads or repeated full structural parses;
- cached state that influences a later Review;
- target-specific suppression;
- configurable Clean, Completion, or grade semantics;
- a rich per-claim receipt graph;
- cross-language inference without a native profile;
- product Rust beyond 20,000 lines.

A new rule should normally be typed Authority data over existing facts. A new
fact capability is a vertical change through Authority admission, observation,
closure, Terminal evidence, and one public-seam test.
