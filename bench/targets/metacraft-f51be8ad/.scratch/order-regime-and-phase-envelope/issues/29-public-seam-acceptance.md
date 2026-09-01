# Public-seam acceptance for each implementation ticket

**Type:** `wayfinder:grilling`

**Status:** resolved (2026-07-26)

**Assignee:** Codex

**Parent:** [Order regime and phase envelope](../map.md)

**Blocked by:** None — on the frontier.

## Question

Which public Authority-seam test proves each of
[One coverage law, independent quantizations, period-hooked step](20-one-coverage-law-independent-quantizations.md),
[The propagation envelope module](21-the-propagation-reach-module.md), and
[Session reuse and run legibility](23-session-reuse-and-run-legibility.md)
as a vertical slice?

Their current acceptance lists pure, golden, adapter, and live tests but does
not explicitly prove admission, recompilation, or permit-to-receipt recovery
through the public `Authority` Interface. Decide the smallest seam test each
ticket owns without duplicating the same end-to-end fixture three times.

Recommended answer: share only the workspace fixture and the acceptance
grammar, never a domain-aware seam harness. Each ticket owns one naturally
named test whose body visibly crosses the typed `Authority` Interface.

## Resolution (2026-07-26)

Accepted by the owner in its tightened Sonnet form:

- Shared grammar: `exact source -> decide -> reopen -> recompile -> one
  consequence`.
- Shared facility: a temporary workspace path only. No `SeamHarness`,
  scenario runner, hidden admission helper, or domain-aware fixture.
- The test body visibly performs `Authority(...)`, `decide(...)`, `check()`,
  `view()`, and recompilation or receipt recovery.
- Ticket 20 owns
  `test_admitted_phase_sets_close_only_their_quantization`.
- Ticket 21 owns
  `test_admitted_envelope_reveals_advice_without_closing_response`.
- Ticket 23 owns
  `test_admitted_receipt_survives_replay_without_redispatch`.
- Each test asserts one positive consequence and its nearest negative
  boundary. Pure, Adapter, and marked live tests remain separate.
