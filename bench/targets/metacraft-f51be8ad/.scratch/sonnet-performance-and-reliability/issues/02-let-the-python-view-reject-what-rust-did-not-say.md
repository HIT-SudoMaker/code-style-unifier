# 02 — Let the Python view reject what Rust did not say

Type: implementation

Status: resolved (2026-07-29)

Blocked by: ticket 01.

## Outcome

The Python authority Adapter accepts exactly the values Rust can emit and
rejects every malformed imitation at the seam. Downstream Python receives
immutable authority values and never repairs native truth.

## Scope

1. Begin with failing decoder tests for wrong schemas, wrong primitive types,
   boolean integers, malformed references, invalid timestamps, and impossible
   permit relationships.
2. Make the Authority view decoder validate the exact top-level and nested
   field sets before constructing any value.
3. Decode Current values, admitted decisions, references, and permits once
   inside the authority Adapter.
4. Require exact strings and exact non-boolean integers. Remove `str`, `int`,
   rounding, defaulting, and fallback coercion from native-view decoding.
5. Validate non-empty revisions, keys, names, media types, and permit scopes;
   accepted hash form; non-negative byte length; and valid RFC3339 expiry.
6. Validate open, consumed, revoked, and expired permit relationships,
   including exact receipt requirements and forbidden combinations.
7. Keep native mappings private to the Adapter. Application, replay,
   scheduling, and science callers consume typed attributes only.
8. Round-trip valid mappings produced by the real Rust extension without
   changing their meaning or bytes.

## Acceptance

- A complete valid Rust view decodes into immutable typed collections.
- Unknown fields, missing fields, wrong containers, and wrong schema fail at
  the Adapter boundary.
- Booleans cannot pass as integer revisions or sizes.
- Empty or malformed reference identities fail before reaching application
  logic.
- Invalid permit state, close reason, expiry, supersession, or receipt
  combinations fail directly.
- No downstream caller parses native view keys or reconstructs references.
- Replay and permit scheduling preserve their existing valid behavior.
- No mapping compatibility property, permissive decoder, or old-shape reader
  remains.
- Rust source, protocol fixtures, and the four native verbs are unchanged by
  this ticket.

## Focused tests

- decode one golden view emitted through the public Python Authority;
- mutate every top-level and nested field independently and require rejection;
- cover integers, booleans, strings, hashes, sizes, timestamps, and all permit
  state relationships;
- replay one record/current chain through typed decisions;
- reserve, consume, revoke, expire, close, and inspect permits through typed
  values;
- scan application and science code for retired raw native-key parsing.

## Verification

- focused authority Adapter and replay tests;
- Pyright with zero errors;
- CSU on every touched production file with zero hard violations;
- architecture tests for the native import boundary;
- an empty Rust production diff;
- `git diff --check`.

## Stop and report

Stop if strict decoding reveals a value the current Rust protocol genuinely
emits but the canonical authority documentation does not define. Resolve that
contract explicitly rather than guessing or coercing.

## Do not add

Do not add a generic deserializer, schema registry, Pydantic dependency,
mapping aliases, compatibility properties, permissive numeric conversion, or
a duplicate Python lifecycle.

## Resolution

Commit `cfb42b5` made the Python authority Adapter decode exact Rust shapes,
relations, and values without coercion. The public authority Interface and
canonical wire values remained unchanged.
