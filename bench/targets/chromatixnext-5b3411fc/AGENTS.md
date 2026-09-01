# Agent Runtime

Use this Python interpreter for all project Python commands:

`C:\Users\Administrator\miniforge3\envs\research_env\python.exe`

Do not use base Python or temporary `uv run --with ...` environments unless the user explicitly requests it.

## Formatting and architecture gate

Run `tools/check_csu.py` without a path for the authoritative non-Example
source-format and architecture gate. It rejects hard findings and review
findings without owner, rationale, and evidence. Then run:

`isort --check-only src tests tools setup.py --skip tests/package_contract/test_examples.py`

Isort alone owns import ordering. Do not run Black: its compact multiline-call
layout conflicts with the CSU expanded-list contract.

## Agent skills

### Issue tracker

Issues and specs use the local Markdown tracker under `.scratch/`. See
`docs/agents/issue-tracker.md`.

### Triage labels

Use the five canonical triage labels. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repository using root `CONTEXT.md` and `docs/adr/`.
See `docs/agents/domain.md`.
