# Issue tracker: Local Markdown

Issues and specs for this repository live as Markdown files under `.scratch/`.

## Conventions

- One feature lives in one `.scratch/<feature-slug>/` directory.
- Its specification is `.scratch/<feature-slug>/spec.md`.
- Implementation issues are separate files under `.scratch/<feature-slug>/issues/`, numbered from `01`.
- A `Status:` line near the top records the ticket's current state.
- An open ticket uses one of the five canonical triage roles documented in
  `triage-labels.md`.
- A closed local decision uses `resolved (YYYY-MM-DD)`. `resolved` is a
  lifecycle value, not a sixth triage role.
- Conversation history, when needed, is appended under `## Comments`.

## Publishing

When a skill says to publish to the issue tracker, create or update the corresponding feature directory under `.scratch/`. Local tracker documents are planning records; they do not become product or document authority merely by existing.
