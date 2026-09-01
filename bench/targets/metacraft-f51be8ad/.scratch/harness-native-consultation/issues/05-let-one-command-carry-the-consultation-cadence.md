# 05 - Let one command carry the consultation cadence

**What to build:** Add one narrow local command Adapter that translates
canonical brief and consultation documents to the resumed conduct Interface so
Codex and Claude Code can use MetaCraft without importing Python internals.

**Blocked by:** 04 - Let one application root resume one conduct life.

**Status:** resolved (2026-08-09; final review corrected)

- [x] Install one `metacraft conduct` operation mirroring public `conduct`, with
      exact paths `--brief BRIEF.json --application-root RUN --material-library
      MATERIALS.toml`, optional `--lumerical-environment LUMERICAL.env`, and
      optional `--answer ANSWER.json`. Add no prepare/submit lifecycle,
      `--project-root`, positional alias, or environment-driven command choice.
- [x] Every typed ConductOutcome, including InvalidBrief, UnsupportedAim,
      ConsultationRequired, WaitingStudies, and CompletedResults, exits `0` and
      writes exactly `{"schema":"metacraft.command.conduct_outcome",
      "outcome":"...","value":{...}}` as canonical JSON to stdout. Outcome is
      exactly `invalid_brief`, `unsupported_aim`, `consultation_required`,
      `waiting_studies`, or `completed_results`.
- [x] Malformed CLI, brief, answer, or document input exits `2`, leaves stdout
      empty, and writes exactly `{"schema":"metacraft.command.input_failure",
      "reason":"..."}` with a stable reason to stderr.
      Unexpected Authority, storage, and implementation exceptions stay
      uncaught nonzero failures and are never translated into science.
- [x] Without an answer, the operation starts or resumes the exact application
      and may emit its current request. With an answer it validates that answer
      and advances to the next ConductOutcome. Repetition without an answer is
      idempotent.
- [x] Compose the current Lumerical evidence Adapter only from the explicit
      material-library and optional Lumerical-environment paths. Reuse their
      existing formats; add no project manifest, provider configuration, hidden
      web access, dynamic imports, harness detection, registry, dependency
      container, or generic command framework.
- [x] When the Lumerical environment path is absent, pass no evidence Adapter
      and rely on the public honest-waiting contract; never construct a test
      fake, search an implicit project root, or begin Native work.
- [x] Keep every physical rule and schema validation inside its owning science
      Module. The Adapter may translate values and failures but may not repair,
      rank, default, or reinterpret an answer.
- [x] Refuse to print secrets or persist raw agent transcripts. Retain only the
      accepted scientific answer and declared source locators.
- [x] Test the installed command through subprocess boundaries on Windows using
      the mandated `research_env` interpreter and paths containing spaces.
- [x] Preserve direct Python `conduct` use; the command is an Adapter, not a
      second product lifecycle.
- [x] Update command and conduct usage in `DEVELOPMENT.md` in the same change as
      implementation and subprocess tests.

## Verification boundary

Use deterministic temporary application roots and exact structured inputs.
Assert stdout bytes, stderr discipline, exit meanings, no partial writes, and
equivalence with direct conduct outcomes. Do not run Codex, Claude Code,
network research, Native Lumerical, or benchmark comparisons yet.

## Comments

Implemented one installed `metacraft` launcher and one thin `command.py`
Adapter. Fixed-order envelopes keep `schema` first and omit a trailing newline;
nested outcome values use the project's canonical encoding. Input decoding and
typed consultation-answer rejection are the only translated failures. The
required material library is validated on every invocation, while Lumerical
evidence is composed only from an explicit environment file with no inherited
product settings. Subprocess coverage uses the mandated research environment,
including the installed Windows launcher and paths containing spaces.

Verification: all 9 command boundary tests pass, including the refreshed
installed launcher. The 71-test scoped command, conduct, brief, and material
boundary and 73 architecture tests pass. Pyright reports zero errors and
warnings for the command Module, and `git diff --check` passes.

Review correction: command envelopes now cross stdout and stderr as explicit
UTF-8 bytes, independent of `PYTHONIOENCODING`. Argparse abbreviation is
disabled and duplicate singleton options fail closed. Exact byte tests cover
all five ConductOutcome variants, noncanonical brief and answer refusal, and
equality between direct-conduct encoding and installed command output.
Correction verification: 76 scoped command, conduct, brief, and material tests
and 73 architecture tests pass. Pyright reports zero errors and warnings for
the command Module, and `git diff --check` passes.

Final review correction: Authority's `Document.from_bytes` now validates the
decoded top level as a Mapping before key comparison. JSON `null`, arrays, and
strings therefore share the stable `document_shape_invalid` owner error; the
command translates each malformed answer to the exact stderr-only
`answer_document_invalid` input failure.
Final verification: 215 focused Authority decoder and command tests and 73
architecture tests pass. Pyright reports zero errors and warnings across the
Authority decoder and command Module, and `git diff --check` passes.
