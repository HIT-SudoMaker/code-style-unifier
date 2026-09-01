# Restoration research provenance

This directory contains source-grounded research notes. It is not a second set
of active architecture decisions. Durable choices are promoted to ADRs and the
canonical design; older narratives remain only when they preserve useful source
audits or reasoning.

## Active supporting notes

- [`interferometric-adaptive-restoration-formula-and-novelty.md`](interferometric-adaptive-restoration-formula-and-novelty.md)
  — detailed relative-transfer, phase-shifting, feasible-set, and novelty
  derivation; its Route A reference-on endpoint is now selected by ADR-0020.
- [`adaptive-unknown-aberration-sensing-principles.md`](adaptive-unknown-aberration-sensing-principles.md)
  — truth-leakage boundary, coherent gauge, low-frame protocols, and kill rules.
- [`2026-08-12-single-shot-hybrid-correction-domain-audit.md`](2026-08-12-single-shot-hybrid-correction-domain-audit.md)
  — primary-source audit of the closest 2026 hybrid sensing/correction work.
- [`restoration-adaptive-optics-literature.md`](restoration-adaptive-optics-literature.md)
  — broader adaptive-optics evidence map.

## Provenance, not decision authority

- [`restoration-flagship-story.md`](restoration-flagship-story.md) records the
  earlier self-verifying/reference-off narrative. ADR-0020 supersedes that
  endpoint and terminology; retain the document only as story-development
  provenance until its still-useful figure logic is fully absorbed.
- [`2026-08-11-restoration-paper-positioning.md`](2026-08-11-restoration-paper-positioning.md)
  and [`2026-07-26_adaptive-restoration-competitive-gap.md`](2026-07-26_adaptive-restoration-competitive-gap.md)
  preserve earlier positioning audits.
- [`restoration-foundations.md`](restoration-foundations.md) is the companion
  brief supplied to the external audit and remains source provenance.

When these provenance files conflict with the current design, follow
[`../adr/0020-adopt-a-fixed-reference-correctability-aware-intelligent-front-end.md`](../adr/0020-adopt-a-fixed-reference-correctability-aware-intelligent-front-end.md)
and [`../restoration/intelligent-front-end.md`](../restoration/intelligent-front-end.md).
