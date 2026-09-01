# 09 - Archive the three competitor source sets

Status: ready-for-agent

Assignee: unassigned

Label: `ready-for-agent`

Blocked by: none

Parent: [Publication freeze](../spec.md)

## Work

Lawfully archive or manifest-link the exact Self-Evolving, MetaChat, and
MetaDesigner primary source sets. Reuse the user's existing `reference/`
material, the official MetaChat repository copy, and the current deduplicated
BibTeX. Add stable names, version/date, DOI/arXiv identity, source locator,
license/redistribution status, file size, and SHA-256.

Article full text and Supporting Information are separate manifest entries.
Download or redistribute only when access and license permit it; otherwise
retain a verified primary locator and checksum only for local files already
provided by the user.

## Acceptance

- Exactly three article identities are unambiguous and deduplicated.
- Every local artifact has a checksum and provenance; every linked-only artifact
  states why it is not copied.
- The manifest distinguishes paper, SI, code, data, and weights.
- No transient `.codex_tmp`, `__pycache__`, `.csu`, or runtime outcome file is
  treated as the durable archive.
- The research record and BibTeX point to the manifest without promoting it to
  scientific Authority.

## Non-goals

No bypass of publisher access controls and no claim that absent code/data does
not exist without a documented search date.
