# Issue tracker: Local Markdown

Issues and specs for this repository live as Markdown files under `.scratch/`,
a gitignored local working area: they are not tracked repository structure
(see `.gitignore`), so each clone maintains its own local copy rather than
sharing specs through version control.

## Conventions

- One feature uses one directory: `.scratch/<feature-slug>/`.
- Its specification is `.scratch/<feature-slug>/spec.md`.
- Its implementation tickets are separate files under
  `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01` in
  dependency order.
- Each ticket records `Status:` near the top using a role from
  `triage-labels.md`.
- Each ticket records `Resolution:` separately. `open` means acceptance
  remains outstanding; `completed` means every acceptance criterion has
  passed. Triage status and implementation resolution never substitute for
  one another.
- Comments and conversation history are appended under `## Comments`.

When a skill says to publish a specification or issue, it creates the
corresponding local file. When a skill says to fetch one, it reads the path or
issue number supplied by the user.

## Blocking and frontier

Each ticket records `Blocked by:`. A ticket is on the frontier when it is
`ready-for-agent`, its `Resolution` is `open`, and every listed blocker has
`Resolution: completed`. If several tickets are on the frontier, the lowest
ticket number is selected first.
