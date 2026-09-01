# 12 — Give active report work one repository

**What to build:** An independent sibling report repository whose active
narrative, evidence, figures, drafts, templates, and deliverables have explicit
ownership and reproducible binary handling.

**Blocked by:** 02 — Let one Rust conflict keep its meaning until the boundary.

**Status:** resolved (2026-07-30)

- [ ] The sibling report directory is initialized exactly once as an
      independent Git repository and is not nested inside or linked as a
      submodule of the code repository.
- [ ] Its root explains the ownership and lifecycle of narrative, evidence,
      figures, drafts, templates, deliverables, and ignored archive content.
- [ ] Active curated presentation material moves from the code workspace with a
      source-to-destination inventory and byte-level verification.
- [ ] The upcoming group-meeting deck remains a draft until explicit human
      approval promotes it to a deliverable.
- [ ] Active PPTX, DOCX, XLSX, and packaged binary deliverables use Git LFS;
      text, CSV, JSON, SVG, DrawIO, and build scripts use ordinary Git.
- [ ] Git LFS is initialized and its tracked patterns and object presence are
      verifiable locally.
- [ ] Active office packages can be structurally opened after migration.
- [ ] The report repository has one intentional baseline commit and a clean
      status excluding its declared archive.
- [ ] The code workspace no longer contains active presentation ownership.
