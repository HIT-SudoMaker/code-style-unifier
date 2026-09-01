# 19 — The height domain owns the physical period and order regime

**Type:** implementation (spec phase 1)

**Status:** wontfix

**Superseded by:** [Metalens Sonnet convergence ticket 03](../../metalens-sonnet-convergence/issues/03-let-period-choose-before-height.md) and ADR 0011.

**What to build:** `derive_height_domain` gains `requires material_binding`
on both metalens routes, and `material_binding` cites the exact admitted
sample document, so the chain
`solver binding <- material sample <- material binding <- height domain`
replays from authority alone after a restart. `HeightDomain` derives and
retains: the physical `period_nm` = floored sampling ceiling, the
`order_regime`, the diagnostic `order_ceiling_nm`, and the substrate sample
value with its reference (ADR 0007). A `multi order` classification produces
the non-blocking `higher orders possible` caution; it neither caps the period
nor refuses a sweep. **Period ownership is
exclusive:** the compiler's field is renamed `sampling_ceiling_nm` — the
name `period_nm` exists only on the domain and the choice; `HeightChoice`
carries the physical period; every downstream consumer (cell construction,
sweeps, results) reads the period from the choice or domain, never from
the compiler ceiling; an architecture test forbids the ceiling from
reaching solver construction. Feature bounds are computed per height (`height.py` stays the
only rule); the compiler's max-height `minimum_feature` and its
`fabrication_domain_empty` raise retire. A genuinely empty fabrication domain
lands as a fabrication finding on an unfinished study, carrying the sampled
index and per-height feature bounds and candidate counts.
`choose_height`'s byte-exact rebuild discipline extends over the new fields.

**Acceptance:**

- Byte-exact domain rebuild tests cover the new fields and non-blocking
  caution.
- The 355/400 briefs use physical periods 630/660 nm under sampled indices,
  classify them as `multi order`, and continue through `conduct`.
- Run manifests and results retain `higher orders possible` with the exact
  height-domain source reference.
- Old-generation receipts stay unreachable (changed work identity) — no
  ledger mutation.
- The architecture test proving no solver-construction module reads the
  compiler ceiling is in place and failing-before/passing-after.
- Architecture tests updated for the new fields; touched files leave
  `csu check` with zero hard violations.

Decisions: tickets 03, 13, 15; ADRs 0005 and 0007; charted plan-A wiring.
