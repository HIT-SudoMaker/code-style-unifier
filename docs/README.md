# CSU Documentation

The documentation has one path from rule to evidence. Each concern has one
owner so that maintenance does not create competing specifications.

## Read in this order

1. [Coding Standards](coding_standards.md) — normative Python, Rust, C, and C++
   source rules.
2. [Design](design.md) — why CSU uses one stateless lifecycle, dual observation,
   compact closure, and deterministic terminals.
3. [AI Review Protocol](AI-REVIEW-PROTOCOL.md) — how an agent interprets and
   repairs evidence without evasion.
4. [Test Contract Map](TEST-CONTRACT-MAP.md) — which public-seam test owns each
   behavior.
5. [Core fixtures](fixtures/core/README.md) — four-language examples, self-check
   evidence, and the frozen performance workload.
6. [Primary sources](sources.md) — language and implementation references that
   bound project choices.

The executable self-review Authority is
[authority/csu-self/authority.json](authority/csu-self/authority.json);
it instantiates the Coding Standards and does not redefine them.

## Maintenance rule

Change rule meaning in the Coding Standards first. Change architectural
reasoning in Design. Change executable evidence only after those owners agree.
Research notes, temporary tickets, generated reviews, and superseded designs do
not belong in the maintained documentation tree.
