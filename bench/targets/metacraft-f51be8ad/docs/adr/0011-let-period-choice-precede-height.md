# 0011 — Let period choice precede height

Status: accepted

A metalens cell period is a scientific choice with its own physical domain and
basis; it is not an incidental field of the later height domain. MetaCraft
therefore compiles `PeriodDomain → PeriodChoice` before
`HeightDomain → HeightChoice`. An explicit brief period and one exact period
advice are the two possible bases. These are immutable Python scientific
values, not new mutable workflow or Rust authority states.

The sampling ceiling, order ceiling, strict 10 nm period limit, and unchanged
accept-or-refuse behavior remain governed by ADR 0009. This decision
supersedes ADR 0008's height-domain ownership and “no PeriodChoice” clauses
and refines ADR 0009's period-to-height sequencing. It is grounded in the
[zeroth-order period rule](../research/2026-07-26-zeroth-order-period-rule.md).
