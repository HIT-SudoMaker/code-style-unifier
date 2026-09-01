# CSU 靶场 Target Snapshot Manifest

本文件是 CSU 靶场唯一的 Target Snapshot Manifest（T-02 建立并冻结于干净基线）。它为八个靶场逐一记录：

- **目录身份**：仓库内冻结目录名（目录名内嵌上游短 revision）。
- **上游身份**：上游分支/标签 + 完整 revision，逐字取自 [`bench/targets/README.md`](README.md) 的固定版本表。
- **接纳范围**：按语言接纳的源码文件扩展名（以 T-02 对各靶场实际文件构成的逐项实测为准）与排除项。

目录身份与上游身份以 `README.md` 表格为权威；本 Manifest 与其保持一致。若发现不一致，以 `README.md` 为准并修正本 Manifest，不得反向修改 README 表格或任何靶场内容（冻结纪律见 README：更新上游只新增带新提交后缀的目录，不原地刷新、重写或删减）。

## 靶场清单

| # | 目录身份 | 上游身份（分支/标签@完整 revision） | 语言 | 接纳扩展名（实测构成） | 排除项（不进入接纳范围） |
|---|---|---|---|---|---|
| 1 | `chromatixnext-5b3411fc` | `scientific-foundation-final-seal@5b3411fc9b710a5a79620eea0d3ce1ef0d11eb28` | Python | `*.py`（.py×294） | 文档 `.md`、配置 `.toml`/`.in`、构建产物与二进制（`.exe`）、`LICENSE`、`.gitignore` 等非源码材料 |
| 2 | `metacraft-f51be8ad` | `experiment/continuous-achromatic-native-test@f51be8ad4db700b6af0274bf82ca6fd463ad7e90` | Python + Rust | `*.py`（.py×271）、`*.rs`（.rs×11，位于 `rust/`） | 文档/数据/配置 `.md`/`.json`/`.jsonl`/`.txt`/`.toml`/`.lock`/`.b64`、图片 `.png` 等非源码材料 |
| 3 | `onns-0245bd34` | `experiment/restoration-sonnet-architecture@0245bd346fb1451ddaa91348ec99f44a1d96a91e` | Python | `*.py`（.py×345） | 文档与数据 `.md`/`.json`/`.csv`/`.bib`/`.bmp`、二进制 `.dll`；附带的 vendor 原生头文件 `utils/devices/stage/vendor/include/acs_motion_stage.h`（.h×1）不接纳 |
| 4 | `ripgrep-3fce3b5b` | `ripgrep@3fce3b5bb0236da2df6d99672afb8a719642eca7` | Rust | `*.rs`（.rs×110） | 文档/配置/数据 `.md`/`.toml`/`.csv`/`.yml`/`.sh`/`.lock`/`.gitignore` 等非源码材料 |
| 5 | `serde-a874a1b1` | `serde@a874a1b1bb1cc16cf5ee3b1b7b527af5705742bb` | Rust | `*.rs`（.rs×208） | 文档/配置 `.md`/`.toml`/`.yml`/`.gitignore`；`.stderr` 测试期望输出不接纳；快照内上游相对符号链接（15 处之一，另见 `ripgrep`）按原样保留为链接条目，链接本身不作为接纳源 |
| 6 | `zlib-e3dc0a85` | `zlib@e3dc0a85b7032e98380dec011bc8f2c2ee0d8fca` | C | `*.c`（.c×43）、`*.h`（.h×31） | 文档/构建/平台示例 `.txt`/`.in`/`.cmake`/`.yml`/`.rc` 及 `contrib/` 其他语言示例（`.cs`/`.pas`/`.adb`）不接纳；`contrib/iostream*` 的 C++ 包装源（.cc×2、.cpp×3）不接纳 |
| 7 | `curl-72dfda5f` | `curl@72dfda5f5ac3825fc26b82fa404225f3e7a0fc31` | C | `*.c`（.c×759）、`*.h`（.h×257） | 文档 `.md` 不接纳；测试与构建脚本 `.py`/`.pl`/`.sh`/`.m4`/`.cmake`/`.yml` 等不接纳；示例 C++ 源 `docs/examples/htmltitle.cpp`、`tests/cmake/test.cpp`（.cpp×2）不接纳 |
| 8 | `fmt-e27cc20b` | `fmt@e27cc20bd93a4e280fb9268d41cd131069a9c73f` | C++ | `*.cc`（.cc×47）、`*.h`（.h×26）；`*.cpp` 属 C++ 接纳扩展但本快照实测为 0 | 文档/配置 `.yml`/`.md`/`.txt`/`.in`/`.properties`/`.cmake` 不接纳；`support/` 辅助脚本（.py×4）与 C 兼容测试 `test/c-test.c`（.c×1）不接纳 |

## 冻结与保真备注

- 八个目录共同构成 CSU 首轮唯一的固定性能靶场（三份 Python、一份 Python+Rust、两份 Rust、两份 C、一份 C++）。某个靶场尚未被当前 Language Profile 接纳，不等于可以从集合中删除或以较小范围替代。
- 快照内上游自带的文件随原项目整体保留：许可证文件、上游 `.gitignore`/`.gitattributes`/`.github` 等、以及上游相对符号链接结构（`ripgrep` 的 `HomebrewFormula`、`serde` 系 14 处，均以符号链接条目原样冻结）。
- 实测构成计数为 T-02 建立本 Manifest 时对冻结快照的统计（`find <dir> -type f -name <ext> | wc -l`），仅用于核对接纳范围；快照本体永不因统计口径而修改。
