# 11 — Disposition of the voided evidence and its run directories

**Type:** `wayfinder:grilling`

**Status:** resolved (2026-07-26)

**Blocked by:** None — on the frontier.

## Question

The admitted 355 nm receipts describe a diffracting cell and cannot support a
phase library. The ledger is append-only. How is "admitted but scientifically
void" expressed?

- The receipts stay in the ledger forever. Is anything recorded to mark them
  void, or does the changed task identity make them simply unreachable and that
  is enough?
- `recover_propagation_library` (`evidence.py:96`) matches on work identity. Once
  the period changes, the old receipts no longer match — so recovery is already
  silent about them. Is silence honest, or does a human reading the ledger need
  a signpost?
- The run directories under `runs/` hold `before.fsp`, `engine.fsp`, and
  `after.fsp` per candidate with no cleanup logic and no hashes. `engine.fsp` is
  a full binary copy of `before.fsp`, doubling disk per candidate. Do the voided
  runs get deleted, archived, or left?
- `RunStore.open` (`artifacts.py:128`) names runs by timestamp, aim, phase
  method, and brief name. Nothing in the name says which physics generation
  produced it. Is that worth fixing now that a generation boundary exists?
- Is there anything worth extracting from the void sweep before it is retired —
  the exact silica index recovery is already captured in the map's findings.

**Blocked by ticket 17 as of 2026-07-26.** Nothing may be archived or retired
until the raw-field-monitor phase re-read returns. If that check shows the
extraction path rather than the cell is at fault, "void" is the wrong verdict
and this ticket's whole question changes.

*Unblocked later the same day: ticket 17 returned "extraction correct, void
stands" with the extraction validated bit-for-bit. This ticket's question
stands exactly as written — now on the frontier.*

## Resolution (2026-07-26)

**Leave everything in place; make the future legible.**

- The ledger stays untouched — append-only silence plus the changed work
  identity is the mechanism; recovery's silence about non-matching receipts
  is honest.
- The run directories stay exactly as they are: no deletion, no archive, no
  marker files added to history. Ticket 17 was possible only because the
  raw fields were still there — the void generation's projects are
  diagnostic raw material, and its 46 multi-order candidates are the only
  record of that regime.
- Forward legibility: from the next sweep on, the run manifest and
  directory naming record the physical period and the order regime, so a
  reader sees the generation boundary without archaeology. `RunStore`
  naming gains that fact at implementation time.
- Extraction from the void sweep is complete: the exact silica-index
  recovery and ticket 17's global-constant validation are both on the map.

## Comments

### 2026-07-26 — Claude Code, verification pass (position, not resolution)

- Proposed stance: the ledger stays untouched — append-only silence plus
  changed work identity *is* the mechanism — but future runs should become
  legible: record `period_nm` (or the order regime) in the run manifest or
  directory name, since `artifacts.py` names carry only timestamp, aim,
  method, and brief. A generation boundary now exists; a one-line fact per
  run is enough to see it.
- One correction to the ticket text: `engine.fsp` is a byte copy of
  `before.fsp` only at creation (`adapter.py:226`); after the solve it holds
  the raw solved dataset, and `after.fsp` adds the analysis on top. Deleting
  `engine.fsp` discards raw fields that `after.fsp` may supersede — decide
  that explicitly rather than treating it as duplicate disk.
- Prefer archiving the voided generation's run directories over deleting
  them: they are the only record of the diffractive regime and the source of
  the silica-index recovery.
