# Pre-brief-validation baseline closure

Date: 2026-07-30

Status: resolved (2026-07-30). Tickets 14 and 15 are both recorded as
resolved; this tracked report remains the verified closure evidence.

## Verified heads

- Final implementation commit before this closure record:
  `2ecb8d40e468b52585b00b80505fc07da6533adf`.
- Independent report repository commit:
  `4c7340206eb139a909a254296988d8beda11f5e5`.
- The commit containing this record is intentionally not named here. The
  matching annotated stage tags and their exact commits are recorded after
  tagging in the ignored phase-archive manifest, avoiding a self-reference.

No live Adviser call, Lumerical discovery, native solve, sweep, delivery, or
four-brief delivery run was used for this closure.

## Canonical external cases

The concrete cases live only under the repository-root `examples/` layer.
Their brief order, UTF-8 byte lengths, and SHA-256 identities are:

| Case | Brief bytes | Brief SHA-256 | Case bytes | Case SHA-256 |
| --- | ---: | --- | ---: | --- |
| `yun_2025_low_na_propagation` | 933 | `706313191c2254508e10b17e284d97509698339644da08ad0679e11a78cd820c` | 2,208 | `e9e678c3cd38462b64f40acdcd198ac3e00cb95aebbc8d16f0e092bd700605fc` |
| `yang_2018_low_na_geometric` | 951 | `8c2e18c7363bf728713c0e689aee3da8d8e19c26240c921714e7b386929b11f6` | 2,448 | `4407dbcfc76738516d300466a737e2ee7da69d314d969a3862ef6a0a1acc2093` |
| `arbabi_2015_high_na_propagation` | 941 | `e99eb4b5b3a357f5913e744f9c134a27425584023ba5aaa1f72dfdc8c55f24d7` | 2,259 | `360553751591bb5ba534c2da05a10d167365fd087e807ce23906d227e3a8de0f` |
| `khorasaninejad_2016_high_na_geometric` | 915 | `b6ccb65148cadc815fdbe9d829f1619a4a531761b0ce73385ecbd00e28393d4d` | 2,500 | `c5961926434f225e803aae19deaa8fd824d1259283a43a93d9388af3e90b802e` |

Offline selection, serialization, round-trip, and stable ordering are covered
by the example and architecture ratchets. Production neither imports nor
packages the external example layer.

## Verification

Every project Python command used
`C:\Users\Administrator\miniforge3\envs\research_env\python.exe`.

### Python and architecture

```powershell
C:\Users\Administrator\miniforge3\envs\research_env\python.exe -m pytest -q --tb=short -p no:cacheprovider -m "not integration and not lumerical_live and not advice_live and not lumerical_delivery"
```

Result: `989 passed, 15 deselected in 116.70s`. This complete non-live suite
was run once.

```powershell
C:\Users\Administrator\miniforge3\envs\research_env\python.exe -m pyright
```

Result: `0 errors, 0 warnings, 0 informations`.

The complete suite includes the runtime DAG, Authority surface, dependency
direction, external-example direction, naming ratchet, frozen identities, and
replay architecture tests. A post-review focused run of the affected naming,
compiler, fast-Debye, and pointwise seams passed `78` tests. A final exact
Authority/scientific-identity/replay/four-case-identity run passed `19` tests.

### Code sustainability audit

```powershell
.\csu\bin\csu.exe check src\metacraft_next --format json --output .csu\sonnet-closure.json --no-history
```

Result: `4,140` findings, all `under_review`, all with `blocks=false`;
`0` blocking findings. The JSON output is 2,186,741 bytes with SHA-256
`e0b8367b1d5e1a790e766ac74dfa07de26e129199f4695b159eb2a58fc18abe8`.
No finding was suppressed to obtain this result.

### Rust and source manifest

```powershell
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace --all-targets
```

Result: formatting and strict Clippy passed; Rust tests passed
`18 + 3 + 17`, with three release scale diagnostics intentionally ignored.

`rust/SOURCE_MANIFEST.json` governs 14 paths, is 1,470 bytes, and has SHA-256
`f3fceefe1aa5964545795c09c7056d9e0b093669fc77aa0381bb17ceb2641be3`.
It was regenerated with `rust/sync_source_manifest.py` after the final Rust
review fix, and its architecture guard passed in the complete suite.

### Native release package

```powershell
C:\Users\Administrator\miniforge3\envs\research_env\python.exe -m maturin build --release --locked --interpreter C:\Users\Administrator\miniforge3\envs\research_env\python.exe --out <temporary-wheel-directory>
```

Result: one CPython 3.12 Windows x64 wheel,
`metacraft-0.0.0-cp312-cp312-win_amd64.whl`, 1,706,492 bytes, SHA-256
`9d8e573ee8783dffc42229a45125ba039a6c2dc4a6793046f7daf7d997664c1d`.
Its 92 archive entries contain exactly one `_authority` `.pyd` and no path
component named `examples`.

The wheel was installed with `pip --no-index --no-deps --target` into an
isolated directory. Python `-I` then imported both the package and native
extension from that directory, verified root `__all__ == ["Authority"]`,
verified the four public callables `check`, `view`, `fetch`, and `decide`,
created a workspace, passed `check().is_workspace_valid`, and returned the
frozen empty revision value `"root"`. An initial display-only smoke assertion
used `"r0"`; inspecting the typed value showed the established spelling is
`"root"`, and the corrected assertion passed without rebuilding the wheel.

### Report repository and archive

- Tracked active inventory: 28 files, 12,703,951 bytes, all destination sizes
  and SHA-256 values exact; every code source path is absent.
- Git LFS: six active binary files are exact pointers with present local
  objects; `git lfs fsck` passed.
- Package structure: six PPTX/DOCX/XLSX/ZIP files passed ZIP CRC checks; every
  Office package contains `[Content_Types].xml`.
- Ignored archive manifest: 229 source dispositions, 190,027,459 bytes, all
  source paths absent and all retained hashes exact. Manifest SHA-256:
  `5a9442d449823dc51b7817976de64466109b1418e3bf82ddd97b9a5fb6b73488`.
- Pre-reorganization reconciliation: 75 identities and 76 retained
  destinations exact. Reconciliation SHA-256:
  `bd48e02e8ceaf66d50e4218228edfb4b7beb28ad79ab9e5fa4691fdc975ab039`.
- Both repositories were clean before writing this tracked record; the report
  archive remains intentionally ignored.

## Independent review

The review fixed point was
`dab8b575fca70569f3969e972766353d26cf2df3`.

- Spec review initially found two P2 issues: workspace-owned Rust formatting
  and an unclosed cleanup decision trace. Both were fixed; the repeat review
  passed tickets 01-13 with no finding.
- Standards review initially found three functional issues: the `close_study`
  vocabulary, bitwise Boolean-ratchet coverage, and the same unused Rust
  conversion. All were fixed; the repeat review found no functional issue.
- One non-blocking judgement-call smell remains: two architecture test files
  each retain small source-reading AST helpers. Their rules no longer duplicate
  or diverge, so no test framework layer was introduced solely to remove that
  repetition.

## Architecture reassessment

The earlier review persisted only its total `92/100`, not category scores.
The following explicit verification-weighted rubric therefore must not be
reported as a same-scale “92 to 100” improvement:

| Category | Weight | Verified score |
| --- | ---: | ---: |
| Authority seam and Rust/science ownership | 15 | 15 |
| Runtime DAG and one-way dependencies | 15 | 15 |
| Scientific module depth and lifecycle locality | 15 | 15 |
| Durable identity, protocol, and replay | 15 | 15 |
| Typed expected outcomes and semantic errors | 10 | 10 |
| Solver adapter, workstation, and runner seams | 10 | 10 |
| External examples and report ownership | 10 | 10 |
| Sonnet naming, sustainability ratchets, and verification | 10 | 10 |
| **Total under this recorded rubric** | **100** | **100** |

Relative to the facts explicitly named by the prior review—no production
cycle, no line-count-driven module split, no framework rewrite, and preserved
Authority/science ownership—no category regressed. The complete gates above
discharged the six verification points that were held back in the independent
pre-gate reassessment.

## Planned phase-archive disposition

Stage tag name in both repositories:
`pre-brief-validation-2026-07-30`.

Preserve:

- code `main` and its complete history;
- report `main` and its complete history;
- existing code tag `next-v0.0.0`, tag object
  `45499e44e4de0ceeec19081ecd82fc41bee35d5f`, peeled commit
  `8b6a3f9589026d790a0f1cf0e4f35ddd6040503a`;
- the new matching annotated stage tags;
- complete pre-cleanup bundles and the report LFS payload archive.

Remove only after verified bundles exist:

- patch-equivalent branch `sonnet-ticket04` at
  `dcd796b6643935ec66ea3797b865d83694753ab0`;
- patch-equivalent branch `sonnet-ticket05` at
  `4c8f0bf84acf2ede90a1b7017acef4e43816f105`;
- merged branches `worktree-agent-a27909811c73974b1` and
  `worktree-agent-a4ba1a4eb563664f9`, both at
  `db50a09da90a2907b34a69882990cd20b5672f6b`;
- their exact stale worktrees under
  `code/.claude/worktrees/agent-a27909811c73974b1` and
  `code/.claude/worktrees/agent-a4ba1a4eb563664f9`.

The code repository will not be reinitialized, reset, or squashed. Ordinary
Git maintenance follows only after bundle and LFS-payload verification.

## Handoff

The baseline refactoring phase ends here. The next authorized work is the
separate four-brief validation phase using the external canonical briefs and
the still-separate decisions under `.scratch/four-brief-grounding/`. Those
grounding decisions are not silently merged into this implementation closure.
