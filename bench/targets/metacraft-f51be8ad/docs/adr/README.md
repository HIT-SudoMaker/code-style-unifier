# Architecture decision index

This index is navigation only. Each ADR owns its decision, status, amendment,
and supersession language. Do not infer current architecture from file order
alone; use the accepted decisions together with `CONTEXT.md`, `DESIGN.md`,
`SCIENCE.md`, and `DEVELOPMENT.md`.

## Current accepted decisions

| ADR | Decision | Relationship note |
| --- | --- | --- |
| [0001](0001-separate-authority-from-science.md) | Separate authority from science | foundational |
| [0002](0002-compile-studies-from-evidence.md) | Compile studies from evidence | runner wording superseded by ADR 0018 |
| [0003](0003-gate-external-solvers-with-local-facts.md) | Gate external solvers with local facts | amended by ADR 0016; dispatch wording superseded by ADR 0018 |
| [0004](0004-compile-proofs-from-claims-and-methods.md) | Compile proofs from claims and methods | amended by ADR 0006; runner wording superseded by ADR 0018 |
| [0006](0006-represent-fields-by-components-not-approximations.md) | Represent fields by components | amends ADR 0004 proof wording |
| [0008](0008-honor-explicit-cell-constraints-before-advice.md) | Honor explicit cell constraints before advice | period clauses superseded by ADR 0009; height ownership by ADR 0011 |
| [0009](0009-keep-g0-only-metalens-proofs-in-the-zeroth-order-domain.md) | Keep G0-only proofs in the zeroth-order domain | supersedes ADRs 0005 and 0007 |
| [0010](0010-let-each-aim-own-its-scientific-language.md) | Let each aim own its scientific language | supersedes obsolete route-identity clauses |
| [0011](0011-let-period-choice-precede-height.md) | Let period choice precede height | supersedes ADR 0008 height ownership |
| [0012](0012-audit-the-history-reuse-the-proof.md) | Audit the history, reuse the proof | historical-proof discipline |
| [0013](0013-let-each-periodic-response-prove-itself.md) | Let each periodic response prove itself | amended by ADR 0015 and operationally narrowed by ADR 0019 |
| [0014](0014-let-dependencies-flow-without-return.md) | Let dependencies flow without return | runtime DAG and composition direction |
| [0015](0015-let-reference-surfaces-prove-their-own-response.md) | Let reference surfaces prove their own response | amends ADR 0013; clarified by ADR 0019 |
| [0016](0016-let-materials-choose-and-solvers-verify.md) | Let materials choose and solvers verify | amends ADR 0003 material ownership |
| [0017](0017-let-one-periodic-layout-place-every-reference-plane.md) | Let one periodic layout place every reference plane | sole vertical-layout owner |
| [0018](0018-let-one-sonnet-baseline-tell-one-truth.md) | Let one Sonnet baseline tell one truth | current ownership, naming, stop rule, and evidence-reading benchmark contract |
| [0019](0019-form-uniform-fields-from-rectilinear-reference-surfaces.md) | Form uniform fields from rectilinear reference surfaces | preserves ADR 0017; clarifies ADR 0015 |
| [0020](0020-let-benchmark-truth-explain-without-directing.md) | Let benchmark truth explain without directing | supersedes only ADR 0018's concrete benchmark shape |
| [0021](0021-let-harnesses-answer-grounded-consultations.md) | Let harnesses answer grounded consultations | supersedes only ADR 0003's general `.env` credential clause and the named ADR 0018 clauses |
| [0022](0022-let-sampling-bound-the-period-and-order-bound-the-proof.md) | Let sampling bound the period and order bound the proof | supersedes only ADR 0009's period-legality clauses; preserves its no-G0-overclaim rule |
| [0023](0023-let-mcclung-complete-the-four-case-frame.md) | Let McClung complete the four-case frame | supersedes only ADR 0020's Yun-specific active-case clauses |
| [0024](0024-let-one-cell-study-own-bounded-response-work.md) | Let one cell study own bounded response work | refines ADR 0011; closes the planning/evidence seam |
| [0025](0025-let-geometry-budget-time-and-native-decay-close-it.md) | Let geometry budget time and native decay close it | preserves ADR 0017; closes bounded periodic numerical time |
| [0026](0026-let-propagation-and-aplanatic-reference-meet-in-comparison.md) | Let propagation and aplanatic reference meet in comparison | refines ADR 0006; keeps one conduct life and distinct physical roles |
| [0027](0027-let-labels-select-examples-and-content-identify-science.md) | Let labels select examples and content identify science | separates external catalogue labels from canonical scientific identity |
| [0028](0028-let-continuous-compensation-compose-pb-and-spectral-response.md) | Let continuous compensation compose PB and spectral response | preserves the two control strategies while adding one continuous-band metalens Method |

## Superseded decisions

| ADR | Superseded by |
| --- | --- |
| [0005](0005-derive-the-cell-period-from-the-zeroth-order-condition.md) | ADR 0009 |
| [0007](0007-report-order-risk-without-capping-the-cell-period.md) | ADR 0009 |

ADR 0018 supersedes only the obsolete operational clauses it names. It does
not erase the scientific or authority meaning of ADRs 0001 through 0017.
ADR 0020 preserves ADR 0018's external benchmark ownership and supersedes only
its concrete benchmark-shape clauses.
ADR 0021 preserves ADR 0018's single conduct lifecycle and, when implemented,
supersedes only its embedded-adviser, active-callback, and absolute no-reopen
clauses. It also supersedes only ADR 0003's reservation of `.env` for LLM/API
credentials; ADR 0003's product-owned solver environment and gating remain.
