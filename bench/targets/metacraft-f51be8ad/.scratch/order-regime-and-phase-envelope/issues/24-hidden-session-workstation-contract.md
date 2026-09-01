# The hidden session's workstation contract

**Type:** `wayfinder:grilling`

**Status:** resolved (2026-07-26)

**Assignee:** Codex

**Parent:** [Order regime and phase envelope](../map.md)

**Blocked by:** None — on the frontier.

## Question

May the Lumerical adapter keep one hidden GUI session alive across an engine
solve when that process tree sits outside the workstation lane and its memory
is merely recorded?

The accepted workstation contract gives Python one place for physical-core
placement, process containment, and memory admission. Ticket
[Session reuse and run legibility](23-session-reuse-and-run-legibility.md)
currently creates an exception: roughly 240 MiB remains outside the lane while
the contained engine runs. Settle whether session reuse must bring that session
under workstation placement and accounting, or must remain disabled when the
adapter cannot do so. Also settle whether this changes capacity evidence or
only the lane implementation.

Recommended answer: no unguarded exception. Session reuse ships only when the
workstation owns the hidden session's placement and memory accounting;
otherwise the adapter retains the existing two-session lifecycle.

## Resolution

**No GUI concept enters the architecture, and no hidden product process earns
an exception from the workstation contract.**

- `lumerical_gui` remains only the native licence-feature name. A
  `hide=True` Lumerical session is product machinery inside the Adapter, not a
  public GUI Module or scientific concept.
- Per-candidate session reuse may ship only when the workstation owns that
  hidden process tree's placement, containment, and memory accounting for its
  complete lifetime.
- If the Adapter cannot satisfy that Interface, it keeps the established
  two-session lifecycle. Recording an unguarded resident-set size is not
  admission.
- This does not change Rust capacity semantics. Any necessary placement work
  remains in Python's workstation implementation and the Lumerical Adapter.

Owner confirmation: “是的，我们不需要设计GUI。”
