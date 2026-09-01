# Let two real harness profiles meet one acceptance seam

**Parent map:** [Harness-native Sonnet hardening](../map.md)

**Label:** `wayfinder:prototype`

**Assignee:** Codex

**Status:** resolved (2026-08-09)

**Blocked by:** [Let sealed evidence retire its repair code](03-let-sealed-evidence-retire-its-repair-code.md)

## Question

Once historical repair execution is absent, where should the acceptance-only
seam place Codex and Claude Code capsule layout, environment, argv/stdin,
event-shape validation, access extraction, command grammar, and explanation so
that each real external harness has locality while the shared four-case matrix,
redaction, sealing, and reporting keep leverage?

Compare materially different Interfaces and use recorded-event test Adapters.
Do not introduce a production harness Adapter, copy the canonical skill, or
prepare Reasonix/Pi support.

## Resolution

Adopt a closed union of two concrete, acceptance-only profiles. The profile
seam has exactly the two external conventions that exist today:

```python
HarnessAcceptanceProfile = CodexAcceptanceProfile | ClaudeAcceptanceProfile

ACCEPTANCE_PROFILES: tuple[HarnessAcceptanceProfile, ...] = (
    CodexAcceptanceProfile(),
    ClaudeAcceptanceProfile(),
)
```

This is a fixed composition root, not a `Protocol`, registry, discovery
mechanism, plugin Interface, or promise that a third harness can be added by
configuration. `CodexAcceptanceProfile` and `ClaudeAcceptanceProfile` remain
under `tests/`; production must neither import them nor grow an equivalent
harness Adapter.

### Confirmed seam

The current acceptance support passes a `harness: str` through several shallow
Interfaces and then recovers the same distinction repeatedly:

- `prepare_capsule` chooses native skill layout and Claude-only settings;
- `harness_environment` chooses home/authentication variables;
- separate Codex and Claude argument functions choose argv and prompt channel;
- `audit_transcript`, event-shape validation, access extraction, and command
  parsing switch between two native event dialects;
- runner preflight repeats executable/help/required-flag tables;
- `run_matrix` chooses arguments and stdin again;
- `_explanation` chooses the harness's final-message convention.

Those differences all describe one true external dependency: the selected
harness convention. They belong together. The blind case matrix, scientific
inspection, confinement policy, redaction, classification, sealing, and
post-hoc reporting do not vary by that convention and must stay shared.

The concrete profiles expose only three behaviors and a literal name:

```python
@dataclass(frozen=True)
class HarnessPreflight:
    version: str
    missing_flags: tuple[str, ...]


@dataclass(frozen=True)
class HarnessInvocation:
    argv: tuple[str, ...]
    cwd: Path
    environment: Mapping[str, str]
    stdin: str | None


@dataclass(frozen=True)
class PreparedHarnessRun:
    capsule: PreparedCapsule
    invocation: HarnessInvocation


@dataclass(frozen=True)
class HarnessObservation:
    event_count: int
    accesses: tuple[HarnessAccess, ...]
    violations: tuple[str, ...]
    explanation: str


class CodexAcceptanceProfile:
    name: Literal["codex"]

    def preflight(self, capture: CaptureCommand) -> HarnessPreflight: ...
    def prepare(self, request: CapsuleRequest) -> PreparedHarnessRun: ...
    def observe(self, transcript: bytes) -> HarnessObservation: ...


class ClaudeAcceptanceProfile:
    name: Literal["claude"]

    def preflight(self, capture: CaptureCommand) -> HarnessPreflight: ...
    def prepare(self, request: CapsuleRequest) -> PreparedHarnessRun: ...
    def observe(self, transcript: bytes) -> HarnessObservation: ...
```

`CapsuleRequest` supplies the fresh root, case name, repository root, required
Python executable, inherited environment, and shared opening prompt. It is an
in-memory input value, not a durable schema. The runner never looks up a
profile by string; it iterates `ACCEPTANCE_PROFILES` and passes the same value
through preflight, preparation, execution, and observation.

`prepare` first delegates common blind-fixture and application-root work to a
shared private helper, then adds the profile's native overlay and returns the
complete invocation. Each profile owns its destination for the one canonical
`skills/metacraft-design/SKILL.md`; temporary capsule materialization must be
byte-identical to that source and must not create a second repository copy or
behavior source.

`observe` decodes every nonblank JSONL line through the profile's strict native
dialect. It owns native event-shape validation, access extraction, outer
command grammar, and final explanation selection. It returns normalized facts;
the shared audit applies capsule confinement and allowed-answer-name policy.
The small parser for the one canonical `metacraft conduct` command may remain a
shared primitive used by both profiles, but neither profile may delegate its
native shell/tool envelope to a new harness switch.

### Ownership after the change

| Concern | Codex profile | Claude profile | Shared runner/support |
| --- | --- | --- | --- |
| Native capsule overlay | `.agents/skills/...` | `.claude/skills/...`, settings, empty MCP | blind fixtures, application root, canonical skill source |
| Environment | Codex home/auth additions | Claude config/auth additions | reviewed runtime allowlist and filtering rule |
| Invocation | strict `codex exec`, prompt on stdin | strict `claude`, prompt in argv | process timeout and capture |
| Transcript dialect | Codex thread/turn/item events | Claude system/assistant/user/result blocks | JSONL framing and normalized audit values |
| Command/explanation | PowerShell envelope and final agent message | tool-use envelope and final result | canonical `metacraft conduct` primitive and fallback wording |
| Acceptance lifecycle | none | none | fixed 2x4 order, raw/redacted parity, inspect, classify, retain, hash, seal, report |

Profiles cannot choose cases, retry a run, classify science, redact evidence,
write a manifest, seal a root, or generate post-hoc claims. Granting any of
those operations would create a second acceptance lifecycle and forfeit the
shared leverage this seam is meant to preserve.

### Invariants and error ownership

- Both profiles complete preflight before the evidence root is created and
  before any paid or stateful attempt. A missing executable, failed version or
  help command, missing required flag, or missing installed launcher is one
  direct preflight failure containing facts for both profiles.
- Capsule roots are fresh. A layout collision, invalid native destination, or
  missing canonical skill is a direct setup failure, not a transcript
  violation and not a synthetic harness outcome.
- The shared environment allowlist remains closed. A profile may add only its
  reviewed home/config and authentication names; it cannot pass arbitrary
  inherited variables through.
- Every nonblank transcript line is either a valid event in that profile's
  native dialect or an audit violation. Malformed, unknown, case-changed, and
  incomplete event shapes fail closed rather than being ignored.
- Rejected tools, commands, paths, and answer names are recorded as audit
  violations. Normalized paths are still judged by the one shared confinement
  policy.
- Timeout and nonzero exit remain captured process facts for shared acceptance
  classification. A profile/parser implementation fault propagates directly;
  it must not be mislabeled as an external confinement or scientific result.
- The tuple has exactly two members with unique literal names. No unknown-name
  fallback, placeholder profile, or `else means Claude` behavior survives.

### Caller and recorded-event Adapter

The intended caller is deliberately linear:

```python
preflights = [profile.preflight(_capture) for profile in ACCEPTANCE_PROFILES]
require_preflight(preflights)

for slot, case_name in fixed_runs(CASE_NAMES, ACCEPTANCE_PROFILES):
    prepared = profile.prepare(CapsuleRequest(...))
    capture = execute(prepared.invocation)
    raw = profile.observe(capture.stdout)
    raw_audit = audit_observation(raw, capsule=prepared.capsule.root)
    redacted = redact_transcript(capture.stdout, ...)
    retained = profile.observe(redacted)
    retained_audit = audit_observation(retained, capsule=prepared.capsule.root)
    require_same_audit_result(raw_audit, retained_audit)
    # shared inspect -> classify -> retain -> hash -> seal -> report
```

Keep process substitution as one private callable argument on `run_matrix`;
do not add a public execution port:

```python
ExecuteHarness = Callable[[HarnessInvocation], ProcessCapture]

def run_matrix(..., execute: ExecuteHarness = _run_once) -> None: ...
```

The live callable invokes the real subprocess. A test-only
`RecordedHarnessExecution` Adapter returns fixed Codex or Claude stdout,
stderr, exit, and timeout facts keyed by the prepared run. When a full matrix
fixture needs an answer file, the Adapter may reproduce only the recorded
answer bytes inside that fresh temporary capsule. It does not parse or
normalize events and never writes the sealed retained evidence root, so live
and recorded executions cross the same `profile.observe` and shared audit
path.

Use small recordings from both real harness dialects, not hand-normalized
surrogate events. Tests may derive malformed/unknown/case-changed/escape cases
from those recordings, but the original valid event shapes must remain visible
as fixtures.

### Designs compared

Three materially different Interfaces were considered.

1. **Closed concrete profile union (selected).** Each profile hides one whole
   external convention behind `preflight`, `prepare`, and `observe`. The
   Interface is smaller than the variation it hides, related decisions have
   locality, invalid cross-combinations are not representable, and the caller
   preserves one shared lifecycle. Its deliberate cost is a little duplicated
   orchestration inside two concrete implementations; common mechanical work
   should move only into private helpers proven identical by both profiles.

2. **Profile and execution ports.** A `HarnessAcceptanceProfile(Protocol)`
   would expose `capsule_overlay`, `preflight`, `run_plan`, and `observe`, with
   `CapsuleOverlay`, `HarnessRunPlan`, and `HarnessObservation` values. A second
   `HarnessExecution(Protocol)` would have live-subprocess and recorded
   Adapters. This makes every dependency replaceable and gives tests explicit
   ports, but the ports and intermediate values approach the complexity they
   hide. With only two fixed harnesses, the execution port mostly wraps
   `subprocess`, invites registry/discovery work, and splits one convention
   across more lifecycle-shaped Interfaces. It is rejected as overdesigned.

3. **Immutable recipe plus common interpreters.** Two frozen profile records
   would declare executable, native paths, extra files, auth names, version and
   help arguments, required flags, plus launch/event/command callbacks. Generic
   `preflight_profiles`, `prepare_attempt`, and `observe_transcript` functions
   would interpret those records. This is compact and makes the two profiles
   easy to compare as data, but it exposes nearly every implementation concept
   and becomes a shallow callback bag. Expressing event and command dialects as
   pure data would require a new schema/DSL; leaving them as callbacks hides
   concrete behavior indirectly. It becomes attractive only after several
   real, mostly declarative profiles exist, which this ticket explicitly does
   not anticipate.

The selected union has the best depth/locality balance: the stable caller sees
three cohesive behaviors, each concrete profile owns all changes caused by one
external CLI dialect, and the high-value lifecycle remains shared.

### Test deletion and replacement inventory

Replace tests of the shallow helpers with tests of the profile Interface:

- exercise `prepare` for both profiles and assert exact native layout,
  byte-identical canonical skill materialization, reviewed environment, argv,
  cwd, and stdin/argv prompt channel;
- feed one valid recorded stream per profile through `observe`, asserting
  event count, normalized accesses, command acceptance, and final explanation;
- mutate each recording to prove missing, unknown, case-changed, malformed,
  forbidden-command, path-escape, and answer-name violations fail closed;
- keep redaction and placeholder/confinement tests shared by applying them to
  normalized observations from both profiles;
- use the recorded execution Adapter for one complete 2x4 temporary matrix,
  proving fixed ordering, run IDs, raw/redacted audit parity, classification,
  hashes, seal, and reporting without a paid harness turn;
- keep retained-evidence verification read-only. It may parse and hash sealed
  artifacts but must not feed them through a writer or regenerate them as a
  golden master;
- retain one focused runner Interface test showing preflight covers both
  profiles before execution and an existing evidence root is rejected.

After migration, delete the harness-string parameters and the superseded
`codex_arguments`, `claude_arguments`, `harness_environment`, event-shape
switch, mixed access walker, and explanation switch. Do not retain compatibility
wrappers for tests. If the profile seam were then deleted, those seven concern
clusters would have to spread back across capsule preparation, preflight,
runner invocation, auditing, and reporting; it therefore passes the deletion
test.

This decision enforces ADR 0021's existing harness-native, exact-once,
acceptance-only boundary. It creates no production or durable Interface and no
hard-to-reverse scientific meaning, so it requires no ADR amendment.

## Comments

The code evidence and three independent Interface sketches were sufficient to
resolve this prototype without another policy choice. Focused acceptance tests
were green before this planning decision:

```text
10 passed in 9.54s
```

This ticket plans only; it makes no runner, support, fixture, production, skill,
or retained-evidence change. Implementation must follow Ticket 03's deletion
first so historical correction switches are not mistaken for profile behavior,
then make one mechanical migration to the closed tuple and run the focused
acceptance suite plus `git diff --check`.

**Map gist:** Close Codex and Claude Code into two concrete acceptance-only
profiles that own native preparation and observation, while one runner retains
the fixed 2x4 audit, redaction, scientific inspection, seal, and report
lifecycle.
