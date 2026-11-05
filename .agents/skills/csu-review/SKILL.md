---
name: csu-review
description: Audit Python, Rust, C, and C++ source contracts with CSU, prepare missing Authority, interpret existing CSU terminals, or carry out authorized evidence-based remediation and Project Fact registration.
license: MIT
metadata:
  author: HIT-SudoMaker
---

# CSU Review

Pin the requested source scope and capture one CSU Terminal. Target source remains
READ_ONLY during review.

Read the [Review contract](references/contract.md) completely. Resolve the project
root, scope, Authority and executable from caller and repository context. Missing
Authority follows [Preparation](references/preparation.md); continue authorized
read-only orientation and return its setup blocker.

Read [Federation](references/federation.md) only when another review artifact or
co-invoked skill is an input. Read [Remediation](references/remediation.md) only for
explicitly authorized repair or Project Fact registration.

Return Terminal, Disposition, Completion, finding and blocked counts, Seal or error,
evidence location and one next action. Repair remains later work.
