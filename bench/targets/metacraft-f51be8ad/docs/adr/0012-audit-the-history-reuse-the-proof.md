# 0012 — Audit the history, reuse the proof

Status: accepted

## Context

The `Authority` owns generic workspace truth through four verbs — `check`,
`view`, `fetch`, and `decide`. Until this decision, every `view` and `decide`
re-audited the full cumulative ledger history before answering. That cost is
intentional for the integrity path: a workspace must be verified before it is
trusted. But it is unnecessary on the stable common path, where the same handle
asks the same workspace again and nothing durable has changed since the last
complete audit. A ledger of a few thousand events made one `view` take minutes,
which crowds out the scientific work the authority exists to support.

## Decision

The `Authority` keeps exactly one private verified state with two meaningful
forms: `unverified`, and `verified(generation, revision, view)`. A verified
state arises only from one successful complete audit or from one successful
atomic commit performed from the currently verified head.

The hidden operational order separates the two concerns deliberately:

```text
open:   recover -> audit -> remember
check:  audit -> remember -> report
view:   observe -> compare -> refresh if changed -> answer
decide: normalize -> compare -> refresh if changed
        -> guard -> commit -> remember -> answer
```

`check` remains a complete historical audit, unchanged. It is the integrity
gate and it is the only verb a caller uses to demand proof on demand. Opening
an authority performs that same complete audit once and remembers its result.
Audit, generation capture, and replacement of verified state occur during one
workspace-writer lifetime. No cooperating writer can place a commit between
the history that was audited and the generation remembered for that history.
Stable `view` and `decide` observe a cheap durable generation, compare it with
the remembered one, and reuse the verified view only while they agree. The
moment they disagree, the path performs exactly one complete re-audit and
remembers the new result.

## Why complete audit stays explicit and exact

The integrity path is exact because workspace truth is exact. `check` walks
every event, validates the hash chain, verifies every stored object against its
content hash, and replays the projection from the first event. Nothing in this
decision weakens that audit, narrows the objects it covers, or substitutes a
cache for it. The verified state is a memoization of one complete audit, not a
replacement for any audit step.

## Why the stable common path may reuse a verified proof

Once a complete audit has established a view at a specific durable generation,
re-reading every historical row cannot produce a different answer unless durable
storage has changed. The stable path therefore compares a cheap durable
identity — the workspace marker signature, the database file signature, the
ledger head, and the event count — with the remembered generation. While they
agree, the verified view is the same answer the complete audit would produce,
served without the historical scan. `fetch` is unaffected: it remains exact
content-hash verification and never consults the verified state.

## What invalidates the proof

Every cooperative commit and ordinary observable durable change invalidates
the proof and triggers one complete re-audit: another `Authority` committing,
another process writing through the governed workspace, a replaced database,
a moved head, or an observable mutation of a projection, event, object, or
marker. Failure to observe any generation fact also invalidates the in-memory
proof. A failed observation or refresh returns no stale view and leaves the
handle unverified.

The cheap generation is a cache-validity signal, not an adversarial tamper
proof. A deliberate raw-byte rewrite that preserves the database size,
modification time, ledger head, and event count may evade the stable-path
signal. Defending against that attack would require hashing governed storage
on every view and would discard the common-path gain. Explicit `check` remains
the complete integrity operation. Restart reconstructs truth from durable
history because verified state lives only in process memory and is never
persisted.

## Why a persistent projection tree is deferred

A content-addressed persistent projection tree could offer stronger asymptotic
storage behavior across very long histories. It would also require a database
migration, a new persistence format, and a substantial Rust rewrite. The
verified state instead removes the repeated full-history cost from the common
path without changing the schema, the protocol, the public surface, or the
recovery semantic. If a future history grows past the point where one complete
audit at open or restart is too expensive, that decision can be made then,
against a real measurement and without the constraints of this convergence.

## Why no protocol or storage migration is required

The verified state is private authority proof. It introduces no new public
verb, no second authority class, no new ledger field, no protocol byte, no
schema identifier, and no compatibility surface. The ledger schema, the wire
protocol, the canonical fixtures, the projection row, and the four-verb public
Interface are byte-for-byte unchanged. An existing workspace opens against
this implementation with no migration step.
