# Three-competitor source archive

This directory records the lawful, durable source inventory used to compare
MetaCraft with three agentic metasurface systems. It is **research context, not
scientific Authority**: a manifest entry can establish which bytes or official
locator were inspected, but it cannot admit a scientific claim into a study.

The machine-checked record is [`manifest.json`](manifest.json). Bibliographic
metadata remains in the deduplicated
[`../2026-08-15-wayfinder-agentic-metasurface-and-achromatic-materials.bib`](../2026-08-15-wayfinder-agentic-metasurface-and-achromatic-materials.bib).

## Identity and status rules

Article identity uses a DOI when one has been assigned and otherwise the
version-independent arXiv identifier. arXiv versions are recorded on artifacts,
not treated as new articles. The manifest deliberately contains exactly these
three identities:

1. `doi:10.1002/lpor.71739` — *A Self-Evolving Agentic Framework for
   Metasurface Inverse Design*;
2. `doi:10.1126/sciadv.adx8006` — *A multi-agentic framework for real-time,
   autonomous freeform metasurface design* (MetaChat);
3. `arxiv:2605.22647` — *Agentic metasurface design with self-correcting
   language-model systems* (MetaDesigner).

Each source set has distinct `article`, `supporting_information`, `code`,
`data`, and `weights` entries. Their statuses mean:

- `retained_local`: durable bytes under `reference/` are content-addressed;
- `linked_only`: an official locator is retained intentionally without copying
  the artifact, with the reason recorded;
- `typed_missing`: an expected original is absent from the durable archive;
  the absence is evidence and must not be silently filled by a derived or
  temporary file;
- `not_applicable`: the paper does not define that artifact class.

Public readability is not a redistribution licence. In particular, the local
MetaChat source tree has no `LICENSE`, `COPYING`, or `NOTICE` file, so its
redistribution status is recorded as `not_established` despite its public
GitHub origin.

## Content addressing

Files use SHA-256 over their exact bytes. A retained directory uses this
canonical tree representation:

```text
relative/path<TAB>byte-size<TAB>lowercase-file-sha256
```

Lines are sorted by POSIX relative path, joined by LF with no trailing LF, and
then hashed with SHA-256. `byte_size` is the sum of admitted file sizes.
`.git/`, `.DS_Store`, `__pycache__/`, `*.pyc`, and `*.pyo` are excluded. The
Git commit is recorded separately as source version metadata. Temporary
downloads, paper-card renders/extractions, runtime reports, bytecode caches,
and run projections are never durable source artifacts.

## Current durable boundary (2026-08-15)

| Source set | Article | Supporting information | Code | Data | Weights |
| --- | --- | --- | --- | --- | --- |
| Self-Evolving | retained publisher PDF | typed missing behind the explicit SI gate | official repository linked only | complete paper/OOD suite typed missing | not applicable |
| MetaChat | typed missing locally; DOI/arXiv recorded | typed missing behind the SI gate | retained at commit `e66deddbc96e4fe3e78837e069c44a4d15cf558c` | official Stanford record linked only | official Zenodo record linked only |
| MetaDesigner | typed missing; temporary arXiv v2 copy explicitly excluded | no distinct SI original located | typed missing | typed missing | typed missing |

The two retained artifacts are the user-provided Self-Evolving PDF and the
existing MetaChat repository. They are preserved in place; this archive does
not rename, replace, or repackage them. The MetaDesigner PDF observed under
`.codex_tmp/` is not promoted into `reference/`. It remains the third article
original to archive after the user confirms the full-text/SI acquisition
choice. MetaChat's article PDF is also not yet present in the durable archive.

