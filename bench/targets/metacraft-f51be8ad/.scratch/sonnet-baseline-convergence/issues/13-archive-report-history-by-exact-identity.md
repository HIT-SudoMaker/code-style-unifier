# 13 — Archive report history by exact identity

**What to build:** A lossless, ignored report archive whose manifest makes
historical presentation cleanup, QA snapshots, deduplication, and discarded
backups auditable.

**Blocked by:** 12 — Give active report work one repository.

**Status:** resolved (2026-07-30)

- [ ] Historical pre-reorganization presentation material and both section-QA
      collections are placed under the ignored report archive.
- [ ] The archive manifest records normalized relative identity, byte size,
      SHA-256 hash, origin, destination, and disposition for every source item.
- [ ] The existing pre-reorganization hash inventory is reconciled or
      superseded without losing its traceability.
- [ ] The audited figure-package working copy is deleted only after its
      retained ZIP contents are reverified byte-for-byte.
- [ ] Editor backups and other transients are deleted only after proving that
      they contain no unique bytes or meaning.
- [ ] No historical TIFF, QA rendering, or pre-reorganization workspace is
      committed to ordinary Git or Git LFS.
- [ ] Source and destination counts, total bytes, and hashes reconcile before
      any destructive cleanup.
- [ ] The disposition is recorded in the existing cleanup decision trace and
      the code workspace contains no presentation-related untracked residue.
- [ ] Material removed as an exact duplicate is identified explicitly as
      deleted and recoverable from its retained equivalent.
