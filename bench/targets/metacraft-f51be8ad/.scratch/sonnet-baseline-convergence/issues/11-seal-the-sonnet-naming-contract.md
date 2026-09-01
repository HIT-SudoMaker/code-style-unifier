# 11 — Seal the Sonnet naming contract

**What to build:** An executable repository ratchet and final migration pass
that leave production Python with one intention-revealing vocabulary and no
durable-identity drift.

**Blocked by:** 08 — Let metalens realization and conclusion speak one
language; 10 — Let local composition close the new language.

**Status:** resolved (2026-07-30)

- [ ] Production modules and files use concise domain nouns and language-native
      casing; types use precise nouns; functions and methods use verb phrases.
- [ ] Production Boolean fields, parameters, and reviewed locals use `is`,
      `has`, `can`, or `should`, while natural predicate callables remain
      readable domain propositions.
- [ ] Meaningless numbering, pinyin, unclear abbreviations, duplicated context,
      and broad names such as data, info, manager, helper, and utils are absent.
- [ ] Architecture tests prove the stable Authority surface, allowed dependency
      direction, runtime import DAG, external-example direction, and frozen
      durable identities.
- [ ] The naming ratchet distinguishes source identifiers from mathematical
      equations, units, protocol keys, and exact native product strings.
- [ ] No migration allowlist, compatibility alias, duplicated module, or stale
      old-name import remains.
- [ ] Static type checking reports no errors or warnings and the code
      sustainability audit has no blocking finding.
- [ ] Every focused non-live test group affected by the naming migration passes.
- [ ] The architecture score is reassessed and no reviewed category regresses
      below the pre-change baseline.
