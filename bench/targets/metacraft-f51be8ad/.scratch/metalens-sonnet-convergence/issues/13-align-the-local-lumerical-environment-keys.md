# 13 — Align the local Lumerical environment keys

Type: deployment repair

Status: resolved (2026-07-28)

Blocked by: ticket 10 live attempt one.

## Outcome

The local `.env.lumerical` uses the current provider-neutral material key
vocabulary without changing any configured material value.

## Evidence

The first Ticket 10 preflight found two legacy keys before any product probe:

- `LUMERICAL_SILICA_MATERIAL`, already migrated mechanically to
  `LUMERICAL_MATERIAL_SILICA`;
- `LUMERICAL_SILICON_NITRIDE_MATERIAL`, still requiring migration to
  `LUMERICAL_MATERIAL_SILICON_NITRIDE`.

A key-only audit found no other legacy material key. No configured value was
printed.

## What to repair

- Rename the remaining legacy key only when the old key occurs exactly once
  and the new key is absent.
- Preserve its value, encoding, line ending, and every unrelated setting.
- Reparse the file and report only key names, booleans, and non-secret product
  facts.
- Do not commit the local environment file.

## Acceptance

- The old key is absent and the new key occurs once.
- `read_lumerical_environment` accepts the file.
- No value or secret appears in output or source control.

## Verification

- `LUMERICAL_SILICON_NITRIDE_MATERIAL` occurred exactly once and
  `LUMERICAL_MATERIAL_SILICON_NITRIDE` was absent before migration.
- The byte-preserving mechanical migration left the old key absent, the new
  key present exactly once, and every value, line ending, and unrelated byte
  unchanged.
- `read_lumerical_environment` parsed the migrated file successfully with the
  required research environment Python interpreter.
- `LUMERICAL_FDTD_PATH`, `LUMERICAL_PYTHON_API_PATH`, and
  `LUMERICAL_LICENSE_UTILITY_PATH` each name an existing file; the license
  server is configured.
- No environment value or secret was printed. No installation probe, license
  inspection, native session, or solver execution was started.
- The local `.env.lumerical` remains outside source control and was not
  committed.
