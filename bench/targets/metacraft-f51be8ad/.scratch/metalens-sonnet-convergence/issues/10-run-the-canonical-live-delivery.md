# 10 — Run the canonical live delivery

Type: live verification

Status: wontfix

Superseded by:
[Run the canonical live delivery](../../sonnet-performance-and-reliability/issues/06-run-the-canonical-live-delivery.md).

Blocked by: ticket 09 and explicit human approval of the live flags.

## Outcome

The four canonical briefs are exercised against the installed Lumerical
product only after the architecture is green. Every outcome is real,
replayable, and scientifically honest.

## What to verify

1. Enable `advice_live` with `METACRAFT_RUN_ADVICE_LIVE=1`. Verify that one
   intentionally incomplete wording returns exact questions and opens no
   downstream scientific work, while one complete canonical brief crosses
   the configured OpenAI-compatible Adviser seam successfully. Record
   provider, endpoint identity, model, request identity, response identity,
   and outcome without reading or printing the API key.
2. Enable the `lumerical_live` marker explicitly. Use
   `METACRAFT_RUN_LUMERICAL_SMOKE=1` for inspection,
   `METACRAFT_RUN_LUMERICAL_SOLVE=1` for the bounded native solve, and
   `METACRAFT_RUN_LUMERICAL_DELIVERY=1` only for the four-brief delivery.
3. Run one bounded smoke that checks installation, version, licenses,
   solver-native material sampling, automatic lanes, one reusable session,
   one work record, and one admitted observation.
4. Inspect the smoke artifacts before opening a full sweep.
5. Run the Johansen-inspired circular propagation brief through the configured
   Adviser and Lumerical Adapter.
6. Run the Pi-inspired square propagation brief through the same seams.
7. Run the Khorasaninejad-inspired rectangular geometric brief through the
   same seams.
8. Run the Yang-inspired elliptical geometric brief through the same seams.
9. Reopen authority and replay every completed Result or waiting Study with
   Adviser, Lumerical, and Torch disabled.
10. Record wall time, observed license limits, lane count, session count,
   candidate/solve counts, solver version, artifact roots, Results, Findings,
   and replay identities under this ticket.

## Successful scientific target

- Johansen and Pi each return independent 8-, 12-, and 16-state propagation
  Results.
- Khorasaninejad and Yang each return one continuous-orientation geometric
  Result.
- A fully closed matrix therefore contains eight Results.

This target is not permission to change a brief. A real run may instead
return a replayable waiting Study when advice, solver evidence, phase
coverage, focus bracketing, or another declared claim remains unresolved.

## Acceptance

- The bounded smoke passes before any full sweep begins.
- Qualification confirms the configured Lumerical 2025 R2 (`25v2`)
  installation, or stops before every solve with an exact version finding.
- The incomplete wording asks for missing facts and launches no solver work;
  the complete brief receives real, recorded provider outcomes.
- Every launched solve was admitted under observed workstation and license
  capacity.
- No caller supplied workers, sessions, CPU sets, or memory placement.
- Every completed Result cites native Lumerical evidence and the admitted
  Torch realization.
- Every waiting Study retains exact Findings and useful diagnostics.
- Replay repeats no consultation, solve, or propagation.
- No brief, physical rule, threshold, padding factor, device policy, or
  method was changed during verification.
- Rust remains unchanged.

## Stop rule

This ticket performs no opportunistic code repair. On a product, numerical,
or scientific defect, preserve the run and open one new focused issue against
the responsible Module. Do not patch around the defect inside the live
verification session.

## Live attempt one — stopped (2026-07-28)

The user explicitly approved the documented live flags. Preflight collected
15 live tests and confirmed the advice configuration without reading or
printing its API key.

The targeted advice gate ran with `METACRAFT_RUN_ADVICE_LIVE=1` and stopped
after `1 failed in 23.60s`. The configured provider was
`openai_compatible`, endpoint identity was
`https://api.deepseek.com/v1/chat/completions`, and the configured model was
`deepseek-v4-flash`.

For the wording labelled complete, both provider attempts returned
`status=received`, `complete=False`, no provider failure, and
`needs=("dimension_step_nm",)`. Inspection confirmed that the wording omitted
that fact even though the typed fixture supplied it separately. The
intentionally incomplete wording did not run because the test stopped at this
contradiction. `WordingReview` also lacked the request and response identity
fields required by this ticket.

Lumerical preflight stopped before installation, version, license, material,
session, or solve observation. One legacy local key was mechanically renamed
from `LUMERICAL_SILICA_MATERIAL` to `LUMERICAL_MATERIAL_SILICA` with its value
unchanged. Reparse then found the remaining legacy key
`LUMERICAL_SILICON_NITRIDE_MATERIAL`; no second migration or product probe was
performed.

No solver, GUI, Torch propagation, delivery sweep, or replay was launched.
Rust and tracked product source remained unchanged. Follow-up tickets 11, 12,
and 13 own the three focused repairs before live attempt two.

## Live attempt two — stopped (2026-07-28)

After tickets 11–13, the targeted advice gate was repeated once from baseline
`f2a40ed`. It stopped after `1 failed, 2 deselected in 22.61s`; no Lumerical
path or product operation was opened.

The canonical request identity was
`sha256:61c152ae6665dafd5eac2a5f33767a054eb2031fcc8e36630b1a59b0b2c3f5d3`.
The first received response had identity
`sha256:b9eac8cf670d381f6e055596ac62b73daefda997f3c379bd5aff2634fa19d80e`
and requested `aim` and `objective`. The retry used the same request identity
but produced response identity
`sha256:5e3ec20bf9db8ad2478ea03131e06643c7802467f5d89965678565bef17b3922`
and requested `aim`, `objective`, and `atom_shape`.

Both outcomes were valid received advice with no provider failure. The live
test failed because it retried until `complete=True`, thereby treating
untrusted Adviser judgement as deterministic acceptance. The intentionally
incomplete wording did not run. No API key, request body, or raw response was
printed.

Ticket 14 owns the live-gate correction. It does not change any canonical
brief, provider prompt, required fact, or compiler rule.

## Live attempt three — advice passed (2026-07-28)

After ticket 14, the targeted advice gate ran once from baseline `565fcd4`.
It passed `1 passed, 5 deselected` in 28.67 seconds (29.122 seconds end to
end). The canonical wording and intentionally incomplete wording each crossed
the configured Adviser seam exactly once. No Lumerical, solver, Torch, or
downstream scientific work was opened.

The canonical request identity was
`sha256:61c152ae6665dafd5eac2a5f33767a054eb2031fcc8e36630b1a59b0b2c3f5d3`;
its received response identity was
`sha256:5f9d1202b49f0289963d77781d395ce7552cb204f109e2e97c2d5cbdbca1d2be`
and it advised that `aim`, `objective`, and `atom_shape` remain unstated.

The intentionally incomplete request identity was
`sha256:d5312ed89134684ae5a6d4b062328be74e3980479094820c8d8ac807938ee139`;
its received response identity was
`sha256:9d352189c8a7dd52bba1af51e8cae7e52c1e8d8e56ccd306eb35425b8d7bc2bb`
and it requested `objective` and `dimension_step_nm`.

Both outcomes used the configured `openai_compatible` provider,
`https://api.deepseek.com/v1/chat/completions` endpoint identity, and
`deepseek-v4-flash` model. No API key, request body, or raw response was
printed. Adviser outcomes were retained as consultation evidence and did not
command or rewrite either typed brief.

## Live attempt three — Lumerical smoke stopped (2026-07-28)

The bounded Lumerical gate ran from baseline `79de8fa` with only installation,
license, material read-back, and one periodic observation selected.
Construction parameterizations, the two-lane 19-candidate sweep, and all four
delivery briefs were excluded. The hidden API was used throughout.

Collection found ten non-delivery live nodes in 2.494 seconds. The selected
short gate ended as `1 passed, 3 skipped` in 143.28 seconds (144.294 seconds
end to end). Installation and the configured `v252` path passed. The first
qualification attempt then failed while building the propagation fixture:

`native_session_failed:LumApiError:"in set, the requested property
'simulation time fs' was not found"`

The live helper translated this product failure into a skip. The material and
periodic-observation nodes consequently repeated the same failed
qualification instead of stopping at the first defect. License qualification,
material read-back, session reuse, work-record closure, and an admitted
observation were not reached.

The known artifact root is `E:\Year2026_Project_MetaCraft\code\runs`. Failure
occurred before solve, `execution.json`, and complete work-record assembly.
The native process exited, the temporary smoke and solve flags were restored
to `0`, and the working tree retained no environment change. Ticket 15 owns
the native property mapping. This ticket keeps the smaller verifier repair:
once product qualification begins, its first defect fails directly instead
of being translated into a skip. No delivery sweep or replay was launched.

## Live attempt four — Lumerical smoke stopped (2026-07-28)

The same four-node bounded gate was repeated with `-x` after the simulation
time repair. Installation passed, then qualification stopped at its first
native construction defect: Lumerical rejected `source offset nm`. The run
ended as `1 passed, 1 failed` in 48.41 seconds. Material read-back, periodic
observation, concurrent sweep, and all four delivery briefs did not run.
Temporary smoke and solve flags were restored; delivery remained disabled.

The session Adapter's focused fake-engine seam reproduced the exact public to
native translation error in seconds. `source_offset_nm` now maps explicitly
to native `source offset`, while the existing nanometre-to-metre conversion
remains unchanged. The regression test and seven directly related
session/periodic tests passed; Pyright and CSU remained clean. No live solver
was started while applying this repair.
