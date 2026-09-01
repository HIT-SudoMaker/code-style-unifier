# Sonnet baseline convergence

Status: resolved (2026-07-30)

## Problem Statement

MetaCraft has reached a successful architectural baseline: authority and
science are separated, the production Python import graph is acyclic, the
compiler and runner have distinct responsibilities, scientific evidence is
replayable, and the non-live verification suite is green. The architecture
review scores that baseline at 92/100. The next problem is therefore not a
system rewrite. It is convergence.

Several local seams still make the repository harder to read and maintain than
the architecture deserves. One private Rust conflict is encoded as text before
the authority interprets it. Expected material absence is also classified from
exception strings in the local application even though material selection,
solver verification, and scientific refusal have distinct domain meanings.
Production Python names are individually reasonable but do not yet apply one
strict, repository-wide Sonnet naming contract to values, predicates, modules,
and files. Presentation work, historical renderings, QA artifacts, and
pre-reorganization copies remain mixed into the code workspace as untracked
files. Finally, obsolete local branches, attached worktrees, loose Git objects,
and the lack of a remote backup leave repository cleanup unfinished.

The four concrete canonical briefs and their paper-comparison cases are also
defined inside the installable production package even though they are example
inputs rather than reusable MetaCraft capability. The repository-root examples
currently wrap those installed values instead of owning them. That direction
would make the next brief-validation phase test examples that production code
appears to own.

The user wants one balanced closure: preserve the successful architecture and
all durable identities, make the few weak seams explicit, rename Python
production code by domain intent, give report work its own repository, archive
historical material with exact hashes, and retain rather than rebuild the code
repository's history.

## Solution

Converge the current baseline in five deliberately bounded movements.

First, lock the public Rust authority contract with high-level characterization
tests and validate one private semantic-error slice. The ledger-head conflict
will carry a private Rust meaning from its source until the outer boundary
encodes the existing public string. The stable `Authority` class and its
`check`, `view`, `fetch`, and `decide` operations remain unchanged. The
existing `is_finding()` classification remains unchanged because its finding
set accurately expresses which admission failures become stable rejected
decisions.

Second, replace material-related exception-text inspection with one deep,
Python-owned material-binding operation. It returns either an established
material binding or a typed material-binding refusal. It hides deterministic
material selection, admission, solver-native verification, sampling, and exact
reference closure while the local application retains ownership of translating
the outcome into available science or an honest waiting finding. Unexpected
defects continue to raise directly.

Third, move the four concrete canonical briefs, their paper-comparison truth,
case factories, and delivery selection into the repository-root example layer.
The reusable `MetalensBrief` domain type remains in production science, but the
installable package contains no canonical example values. Canonical brief bytes
and identities remain unchanged.

Fourth, apply one Sonnet naming contract to production Python in reviewable,
green batches. Names will follow domain ownership and natural language:
modules and files use accurate nouns, types use accurate noun phrases,
operations use verb phrases, Boolean values state their polarity, and
predicates read naturally. Wide names and duplicated context are removed.
Canonical serialized keys, schema identifiers, content hashes, replay bytes,
and exact external product strings remain stable through explicit boundary
mapping.

Fifth, establish a sibling report repository. Active narrative, evidence,
figures, drafts, templates, and deliverables move into a clear report-owned
structure. Large active office artifacts use Git LFS. Historical
pre-reorganization work and QA snapshots live in an ignored archive whose
manifest records relative identities, byte sizes, and SHA-256 hashes. Exact
duplicates and non-unique editor backups may be removed only after their
retained equivalents and hashes have been verified.

Sixth, seal both repositories and create the MetaCraft Next phase archive.
Before deleting obsolete code branches or
worktrees, create and hash a complete Git bundle because no remote currently
protects the local history. Preserve the code repository and its commits,
remove only merged or patch-equivalent refs and stale worktrees, commit an
intentional baseline, run a release native build and import smoke test, and
record the implementation commit, report commit, four canonical brief
identities, and verification results in a tracked closure record. Create one
immutable annotated stage tag without moving the existing code tag, then record
the final tagged commits, verified repository bundles, and retained report LFS
payload archive in the ignored archive manifest.
Run ordinary Git object maintenance and leave both repositories clean. Live
brief validation begins from that tagged baseline in a separate phase.

## User Stories

1. As a MetaCraft maintainer, I want the successful architecture preserved, so
   that cleanup does not become an unnecessary rewrite.
2. As a MetaCraft maintainer, I want the architecture assessed against explicit
   criteria, so that future changes start from evidence rather than taste.
3. As a Python caller, I want the stable `Authority` surface to remain
   unchanged, so that authority access does not require migration.
4. As a workspace owner, I want canonical decisions and replay results to stay
   byte-for-byte stable, so that existing workspaces remain trustworthy.
5. As a Rust maintainer, I want a ledger-head conflict to retain semantic
   identity internally, so that core control flow does not parse its own
   formatted text.
6. As a Rust maintainer, I want public error text encoded only at the outer
   boundary, so that private meaning and public compatibility remain separate.
7. As a Rust maintainer, I want the semantic-error experiment to remain one
   narrow vertical slice, so that validation cannot quietly become a broad
   error-framework rewrite.
8. As an authority maintainer, I want the accepted finding classifier preserved,
   so that accurate rejected-decision behavior is not disturbed without a
   concrete problem.
9. As a scientist, I want missing material registration to be distinct from a
   missing solver-native material, so that a waiting study tells me what fact
   is absent.
10. As a scientist, I want uncovered wavelength support to remain a distinct
    material refusal, so that I can correct the actual scientific input.
11. As an application maintainer, I want expected material absence represented
    as typed data, so that reason text can change without breaking control
    flow.
12. As an application maintainer, I want unexpected material defects to raise
    directly, so that malformed catalogues and invalid solver read-back are
    never disguised as ordinary waiting.
13. As a material-library maintainer, I want project selection to remain
    separate from solver verification, so that registrations do not pretend to
    be observations.
14. As a replay consumer, I want material bindings to retain exact admitted
    references, so that replay never reopens the mutable project catalogue.
15. As a code reader, I want one concept to use one word, so that I can follow
    a responsibility across modules without translating synonyms.
16. As a code reader, I want types to be accurate nouns and operations to be
    clear verbs, so that declarations explain their intent before I inspect
    their bodies.
17. As a code reader, I want Boolean values to state their polarity, so that
    conditions are readable without mentally negating ambiguous names.
18. As a code reader, I want predicate callables to read as natural domain
    statements, so that the code remains concise without mechanical prefixes.
19. As a maintainer, I want broad names such as manager, helper, utils, data,
    and info excluded from production ownership, so that abstractions state
    what they actually own.
20. As a maintainer, I want repeated surrounding context removed from local
    names, so that names remain short without becoming vague.
21. As a maintainer, I want Python renames delivered in bounded batches, so
    that each architectural region remains reviewable.
22. As a maintainer, I want deliberate breaking Python renames without
    compatibility aliases, so that the repository converges on one language
    instead of preserving duplicate vocabulary.
23. As a workspace owner, I want serialized identity mapped explicitly across
    Python renames, so that code clarity does not change durable meaning.
24. As a future aim implementer, I want generic modules to remain independent
    of metalens consumers, so that naming work cannot reintroduce dependency
    cycles.
25. As a report author, I want presentation work owned by a sibling report
    repository, so that code and communication have distinct responsibilities.
26. As a report author, I want narrative, evidence, figures, drafts, templates,
    and deliverables separated, so that each artifact has a clear lifecycle.
27. As a report author, I want the upcoming group-meeting deck treated as a
    draft until approved, so that work in progress is not mistaken for a final
    deliverable.
28. As a report maintainer, I want large active binary documents stored through
    Git LFS, so that report history remains practical.
29. As an archivist, I want historical copies preserved by exact hash and
    relative identity, so that cleanup remains auditable.
30. As an archivist, I want exact duplicates deleted only after verification,
    so that deduplication cannot lose unique work.
31. As a code maintainer, I want active local planning records retained in the
    code tracker, so that cleanup does not erase unresolved decisions.
32. As a code maintainer, I want obsolete branches removed only when merged or
    patch-equivalent, so that unique history is not discarded.
33. As a code maintainer, I want a complete bundle before ref cleanup, so that
    the repository can be recovered despite having no remote.
34. As a code maintainer, I want stale worktrees and loose objects cleaned
    normally, so that Git reflects the current project rather than abandoned
    experiments.
35. As a maintainer, I want non-live Python, typing, architecture, Rust, replay,
    and contract tests green at closure, so that “clean” means verified as well
    as tidy.
36. As a maintainer, I want live solver and adviser work excluded from this
    convergence, so that external availability cannot obscure repository
    quality.
37. As a package consumer, I want reusable brief types but no embedded
    canonical example briefs, so that the installed package provides capability
    rather than project test inputs.
38. As an example author, I want the four concrete briefs owned by the
    repository-root example layer, so that they can evolve as explicit inputs
    without becoming production defaults.
39. As a brief-validation maintainer, I want each external example brief to
    retain its exact canonical identity during relocation, so that the next test
    phase starts from the already-reviewed inputs.
40. As an architecture maintainer, I want production code forbidden from
    importing the external example layer, so that dependency direction remains
    one-way from examples into MetaCraft.
41. As a release maintainer, I want a native release build and installed import
    smoke test, so that the phase archive proves more than source-level tests.
42. As a future brief tester, I want a closure record naming the exact code,
    report, brief, and archive identities, so that every live result can cite
    the baseline it exercised.
43. As a repository owner, I want an immutable annotated stage tag, so that the
    end of MetaCraft Next convergence and the start of brief validation are
    unambiguous.
44. As a report owner, I want the new repository's LFS payloads preserved
    independently of a remote, so that a valid Git pointer can never outlive
    its only local binary object.

## Implementation Decisions

- The current authority/science separation, immutable study model, runner
  boundary, directed acyclic Python dependency graph, and deep scientific
  modules remain the architectural baseline.
- The work follows the progression `Rust validation -> material outcome ->
  external examples -> Python naming -> report separation -> phase archive`.
- Rust work begins with an external-behavior characterization of the stable
  authority seam, followed by one private ledger-head-conflict vertical slice.
- The Rust semantic value is constructed where the conflict becomes known,
  matched by meaning inside authority, and formatted only at the public
  language boundary.
- The `Authority` type, its four public operations, protocol schemas, canonical
  JSON, persisted workspace representation, decision findings, and replay
  behavior remain unchanged.
- `is_finding()` and its accepted finding set remain unchanged. This
  specification does not attempt to type every Rust failure.
- The Rust experiment has a stop condition: if the one semantic slice requires
  a cross-crate error hierarchy or widespread migration, implementation stops
  and records the failed assumption instead of widening scope.
- Material binding becomes one deep application operation that returns either
  `EstablishedMaterialBinding` or `MaterialBindingRefusal`.
- `MaterialBindingRefusal` distinguishes absent registration, absent native
  material, and uncovered wavelength. These are expected outcomes, not faults.
- Material selection remains owned by the project material library. Native
  existence and wavelength-specific sampling remain owned by the qualified
  solver adapter. The application composes them without moving scientific
  meaning into Rust.
- The local application remains the sole translator from a typed material
  refusal to available science and a waiting finding.
- The material operation does not introduce a generic solver port, exception
  hierarchy, service container, registry framework, or compatibility layer.
- `MetalensBrief` and the other reusable brief vocabulary remain production
  science. Concrete canonical brief instances are inputs and do not.
- The four concrete canonical briefs, paper-comparison values, case factories,
  and delivery selection are owned by the repository-root example layer, which
  depends on the installed package. Production code never imports that layer.
- The installable package no longer exposes an examples subpackage or canonical
  case factories. No compatibility module remains.
- Moving the examples preserves each canonical brief document byte-for-byte,
  including its content identity. This ticket changes ownership, not scientific
  content.
- Offline example inspection and selection remain available from a source
  checkout. Live adviser and solver execution remain explicit opt-in example
  operations.
- The Sonnet naming contract is normative for production Python:
  one concept uses one domain word; module and file names are concise
  snake-case nouns; type names are precise PascalCase nouns; functions and
  methods are snake-case verb phrases; Boolean fields, variables, and
  parameters begin with `is`, `has`, `can`, or `should`; predicates may use a
  natural domain verb when that reads more clearly.
- Ambiguous predicates such as generic completion, freshness, or admission
  terms are renamed to state the subject and meaning. Already natural domain
  predicates are not mechanically lengthened.
- Names avoid meaningless numbering, version labels, pinyin, unexplained
  abbreviations, duplicated context, and broad owners such as data, info,
  manager, helper, or utils.
- Public Python subpackage types, operations, parameters, modules, and files
  may change without compatibility aliases. Renames are delivered in
  architectural batches rather than one opaque repository-wide edit.
- Durable serialized names do not follow Python renames automatically.
  Boundary mappings preserve canonical keys, schema identifiers, references,
  content hashes, fixtures, and replay bytes.
- The root authority API and its four verbs are excluded from naming changes.
- The production dependency graph remains acyclic, with dependencies flowing
  from composition through aim-owned science toward generic values rather
  than back from values to consumers.
- Report work becomes an independent sibling Git repository with explicit
  ownership for narrative, evidence, figures, drafts, templates,
  deliverables, and ignored archives.
- The current upcoming meeting deck remains a draft until human approval.
- Active office documents and packaged binary deliverables use Git LFS.
  Text, structured metadata, vector sources, and report-building scripts use
  ordinary Git.
- Historical presentation cleanup material and section QA snapshots are
  retained in the ignored report archive with a versioned hash manifest.
- The previously audited figure package may be removed from the code
  workspace only after its retained package is reverified byte-for-byte.
  Editor backups may be removed only when they contain no unique content.
- The active four-brief decision map remains in the code repository and is not
  merged into this implementation specification.
- The code repository is preserved. It is not reinitialized.
- Before destructive ref cleanup, complete Git bundles for both repositories
  are written to the archive and recorded in the archive manifest.
- Only merged, patch-equivalent, or otherwise verified-obsolete local branches
  and worktrees are removed. Ordinary Git maintenance then packs reachable
  history and prunes unreachable loose objects according to normal safety.
- Phase closure performs a native release build and an import smoke test against
  the built package. The smoke test also proves that production packaging
  excludes the external canonical examples.
- The tracked closure record names the implementation commit, report commit,
  four canonical brief content identities, Rust source-manifest state,
  verification commands and results, and the planned disposition of local refs
  and artifacts. The ignored archive manifest, written after tagging and
  bundling, names the final tagged commits and verified bundle hashes without
  creating a self-referential commit.
- Matching immutable annotated stage tags mark the pre-brief-validation
  baseline in both repositories. The existing code tag is retained at its
  current object and is never moved.
- Because ordinary Git bundles do not contain Git LFS payloads, the archive
  separately retains and hashes every LFS object reachable from the tagged
  report commit.
- Changes are committed in coherent movements so that Rust semantics,
  material behavior, example ownership, Python vocabulary, report ownership,
  and final repository closure remain independently reviewable.

## Testing Decisions

- Tests observe behavior at the highest stable seam. For Rust authority work,
  that seam is the public Python `Authority` surface together with the existing
  Rust authority interface tests.
- Authority characterization covers public exception text, admitted and
  rejected decisions, canonical JSON, exact references, revision mismatch,
  integrity checks, and replay. Tests assert public results rather than the
  layout of private error types.
- The semantic Rust slice is accepted only when the ledger-head conflict no
  longer depends on string-prefix classification inside authority and all
  existing public outputs remain identical.
- Existing tests of stable authority findings remain prior art for
  `is_finding()`. No new test asserts its private implementation.
- Material behavior is tested primarily through `conduct` and compilation:
  each expected material absence produces the same honest waiting meaning,
  successful binding closes over exact admitted references, and unexpected
  defects propagate.
- Narrow material-library and solver-adapter tests may supplement the
  application seam when they prove source-specific selection or native
  verification behavior that cannot be observed precisely through `conduct`.
- Example-boundary tests import the four cases only from the external example
  layer, prove that production modules do not import or package that layer, and
  compare all four canonical brief bytes and identities before and after the
  move.
- Offline example tests prove inspection, named selection, stable delivery
  order, and serialization without opening an adviser, solver, workstation, or
  Authority.
- Naming batches run the affected behavioral tests and static type checking.
  Architecture tests enforce the runtime import DAG, allowed package
  direction, stable public authority surface, frozen durable identities, and
  completion of the naming migration.
- A repository naming audit checks production Python identifiers against the
  Sonnet contract without treating mathematical notation inside equations or
  exact external product strings as production vocabulary.
- Report migration is tested by comparing the source inventory with the
  destination manifest, verifying byte counts and SHA-256 hashes, opening or
  structurally inspecting active office packages, and confirming Git LFS
  tracking for selected binary classes.
- Git cleanup is accepted only after the bundle verifies, the intended commits
  and tags remain reachable, obsolete refs have recorded disposition, and both
  repositories report an intentional clean status.
- Final code verification includes the complete non-live Python test suite,
  static type checking, architecture tests, Rust formatting, Rust linting,
  Rust tests, a release native build, an import smoke test against the built
  package, canonical replay fixtures, and public contract characterization.
- Phase-archive verification proves that the tracked closure record and ignored
  archive manifest jointly match both repository heads, all four example brief
  identities, both verified Git bundles, the reachable report LFS payload
  archive, and the immutable annotated stage tags.
- Existing successful baselines provide prior art: the non-live Python suite,
  architecture-boundary tests, authority-interface tests, verified-state
  tests, and Rust workspace tests.
- Tests requiring a live Lumerical installation, external adviser, live
  qualification, or solver delivery are not closure gates for this work.
- All project Python commands use the repository-mandated research environment
  interpreter.

## Out of Scope

- A broad Rust error hierarchy, a conversion of every `Result<_, String>`, or
  any modification to `is_finding()` and its finding set.
- New Rust authority verbs, science-specific Rust concepts, protocol fields,
  schema identifiers, persistence formats, or workspace migrations.
- A redesign of field, focal-region, angular-spectrum, direct-Debye, sweep, or
  result mechanics without a separate evidence-backed problem.
- Changes to scientific claims, proof relationships, selection laws, canonical
  brief meaning, or existing result semantics.
- Live Lumerical material discovery, native sweeps, external solver execution,
  adviser calls, or canonical four-brief delivery.
- Fuzzy material matching, solver-material substitution, automatic aliases, a
  universal material registry, or a generic solver framework.
- Compatibility aliases for renamed Python production APIs.
- Re-encoding persisted identities merely to follow source-code names.
- Keeping concrete canonical briefs, paper-comparison cases, or delivery
  factories inside the installable production package.
- Changing the wording, wavelength, material families, control strategy,
  geometry intent, comparison truth, or canonical bytes of the four briefs
  while relocating them.
- Editing or rewriting the scientific content of presentation materials.
- Committing the large historical report archive directly to Git or Git LFS.
- Reinitializing the code repository, squashing its history, deleting unique
  commits, or requiring a remote service.
- Treating local tracker records as product or document authority.
- Executing the four live brief validations as part of phase archival; they
  begin from the archived baseline in the next phase.

## Further Notes

The architecture review found no production import cycle, no need to split the
large sweep or result modules merely because of line count, and no evidence
that a framework-level rewrite would improve the current system. The preferred
shape is therefore “small seam, strong contract; broad vocabulary, bounded
batches; external examples, exact archive, clean close.”

“External example” means external to the installable production package, not
external to the source repository. The root example layer remains versioned
beside the code so its canonical inputs and executable entry points can be
reviewed and reproduced, while dependency direction always points from examples
into MetaCraft.

This specification follows the durable authority and science language in the
domain glossary and the accepted decisions separating authority from science,
reusing verified authority state, preserving an acyclic dependency graph,
typing expected adapter absence, and separating project material selection
from solver-native verification. No new research record or ADR is required:
the work applies existing decisions rather than establishing new scientific or
system-wide policy.
