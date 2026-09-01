# The durable source of the golden envelope fixture

**Type:** `wayfinder:grilling`

**Status:** resolved (2026-07-26)

**Assignee:** Codex

**Parent:** [Order regime and phase envelope](../map.md)

**Blocked by:** [What the phase envelope records as checks](26-phase-envelope-checks.md)

## Question

What independent artifact supplies the golden `PhaseEnvelope` bytes?

The resolved field-set ticket names two JSON files and a prototype script in a
session scratchpad, but none is present in the repository. Generating expected
bytes from the production implementation would make the golden test
self-confirming. Decide which independently reviewed artifact is committed and
where it lives.

Recommended answer: regenerate the two envelopes with a small independent
derivation, review them once, and preserve the accepted JSON under
`tests/fixtures/`; production code must never generate its own expected bytes.

## Resolution (2026-07-26)

Accepted by the owner in its tightened Sonnet form:

```text
tests/
├── derivations/
│   └── phase_envelope.py
└── fixtures/
    └── phase_envelope/
        ├── propagation_355_nm.json
        └── propagation_400_nm.json
```

- The durable order is `derive -> review -> preserve -> compare`.
- `tests/derivations/phase_envelope.py` independently declares the two inputs,
  numerical precision, conservative rounding, bound checks, standings, and
  canonical JSON encoding. It imports nothing from `metacraft_next`.
- The derivation proposes candidate bytes; human review accepts them; the
  fixtures remember the accepted public contract.
- `test_phase_envelope_matches_reviewed_bytes` reads the two fixtures and
  compares exact canonical bytes. It never runs or imports the derivation.
- Fixtures freeze public document meaning: brief identity, source references,
  bound checks, height reaches, standings, absent-field semantics, and
  canonical bytes. They do not freeze iterations, intermediate variables,
  internal names, logs, timing, live FDTD results, or advice.
- There is no automatic golden-update command. An intentional schema or
  scientific change updates the independent derivation first, then replaces
  fixtures only after review of the exact JSON diff.
- `reference` is not used as a directory name because it is already a precise
  Authority-domain term.
- Neither derivation nor fixture is scientific evidence or system authority:
  Research Records explain, ADRs decide, derivations calculate, review
  accepts, fixtures remember, and tests guard.
