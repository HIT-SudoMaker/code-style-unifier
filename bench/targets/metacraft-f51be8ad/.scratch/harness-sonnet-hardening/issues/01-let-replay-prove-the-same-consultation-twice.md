# Let replay prove the same consultation twice

**Parent map:** [Harness-native Sonnet hardening](../map.md)

**Label:** `wayfinder:prototype`

**Status:** resolved (2026-08-09)

**Assignee:** Codex

**Blocked by:** none

## Question

Which internal seam should rederive the exact period or height consultation
request during Study replay, reconstruct the closed answer represented by the
retained advice, revalidate it against current admitted grounds, and prove that
the resulting advice is identical—without changing canonical schemas, adding
stored workflow state, or creating a second lifecycle?

Compare at least three materially different internal designs. Judge them by
Interface depth, locality, dependency direction, stable error ownership, and
whether fresh conduct and replay exercise the same question-owned rules.

## Resolution

Deepen the existing `MetalensEvidence.recompile` Interface. Do not add a replay
entry point, policy class, registry, Adapter, stored request, or compiler
callback. Every retained metalens advice item that enters recompilation must be
proved before `compile_metalens` receives it.

The proof has one ordered path:

1. Restore the retained period and height advice subtrees strictly and reject
   duplicates.
2. Derive each advice document reference, fetch the exact admitted bytes through
   the existing `AuthoritySession`, and require those bytes to equal the Study
   subtree. The Study does not authenticate its own retained advice.
3. Restore the current admitted period or height domain through
   `MetalensEvidence`. Restore the current phase envelope only for propagation
   phase; geometric phase continues to forbid one. Period remains before
   height.
4. Re-form the question-owned request from the current brief, domain, envelope,
   and rules. Because the frozen advice schemas do not retain `research_mode`,
   form the request for every member of the closed `ResearchMode` enum and
   require exactly one request identity to equal the retained identity. Do not
   assume a default and do not migrate an old request.
5. Reconstruct the closed `ConsultationAnswer` represented by the advice.
   Reverse-map a retained recommendation value to its canonical candidate;
   preserve its reason, decisive grounds, external claims, and identities.
   Preserve `EvidenceRequired` exactly and leave the Study waiting without
   asking again.
6. Send that answer through the same existing period- or height-owned acceptance
   rules used by fresh conduct. Require the regenerated advice document bytes to
   equal the retained advice document bytes and pass only the regenerated value
   to compilation.

Replay is deterministic and in-process. It performs no Authority mutation,
network access, harness detection, provider call, or second Study lifecycle.
Current rules govern replay: advice produced under older rules may become stale,
and no compatibility repair is attempted.

Question-owned replay faults remain direct and stable, including distinct
period and height request-stale or advice-mismatch failures. A checkpoint codec
may retain its outer `study_frontier_invalid` ownership only by exception
chaining the direct cause. Replay failure must never delete advice, become a
new consultation request, or be translated into a fresh-answer rejection.

### Designs rejected

- Two explicit period/height policy values made the rules auditable but added a
  shallower Interface and ceremony without another production caller.
- A compiler-first design gave `compiler.py` Authority fetching or a mutually
  exclusive input matrix, weakening locality and inviting a dependency back
  edge.

The chosen design is the deepest of the three: callers keep one recompilation
Interface, storage proof stays with the Module that already owns Authority
access, and scientific validation stays with the Module that owns each
question.

## Comments

- 2026-08-09: Approved with the explicit constraint that the implementation
  remain simple, reliable, harness-native, and Sonnet-shaped.
