# ChromatixNext scientific-foundation audit

**Snapshot date:** 2026-07-25
**Status:** Historical and superseded

This path is retained as a tombstone for the 2026-07-25 audit. It is not
current project truth and must not be used to reopen decisions that have since
been closed. The complete original snapshot remains available in Git:

```text
git show 8a18e04:docs/research/chromatix-next-scientific-foundation-audit.md
```

## Current authority

Use these sources, in order, for the current scientific and architectural
contract:

1. `CONTEXT.md` for the domain model and admitted scientific semantics;
2. `MISSION.md` for the product boundary;
3. `docs/architecture.md` and accepted ADRs for architecture;
4. production code and executable tests for implemented behaviour.

## Resolution of the snapshot findings

- Optical-path semantics and unequal-reference coherent combination are
  defined in `CONTEXT.md`.
- `VectorAngularSpectrum` and `AplanaticFocus` are implemented production
  components.
- Meta Inference derives compatibility through real `forward` execution on
  the `meta` device; the former `FieldDescription`/`describe` twin is retired.
- The unconsumed `DescriptionCache` is removed.

Ongoing scientific capability planning belongs in the active issue tracker,
not in this historical snapshot.
