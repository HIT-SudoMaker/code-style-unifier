# CSU 靶场与发布验收

本目录是源码仓库的维护资料，不增加用户规则，也不随二进制包分发。
[编码规范](../../coding_standards.md) 定义要求，[设计原理](../../design.md) 解释取舍，[技术参考](../../technical.md) 定位实现。

## 开发检查

从源码仓库根目录运行：

```bash
cargo fmt --all -- --check
cargo clippy --locked --all-targets -- -D warnings
cargo test --locked
```

产品及测试源码自检、技能镜像检查属于测试集。文档变更还应核对本地链接、章节锚点、可运行示例与发布包中的文档入口。
发布包携带 `docs` 顶层五份用户文档；`docs/fixtures`、自检 Authority、测试和冻结源码属于仓库开发资料，不进入安装包。新增文档也属于待验收候选输入，不能遗漏其身份。
下面的性能和候选校验是独立验收步骤；本地测试通过不代替它们。

## 目录位置

下表路径均相对 CSU 源码仓库根目录。靶场不搬进安装包，也不改放到用户配置目录。

| 位置 | 内容与维护方式 |
|---|---|
| [documents/](documents/) | 四语言合法与故意违规样例；文件身份和预期由 fixture manifest 绑定 |
| [tests/fixtures/](../../../tests/fixtures/) | 行末注释、Authority 拒绝和真实 Python 规避样例；由对应 Rust 测试解释 |
| [bench/targets/](../../../bench/targets/README.md) | 八份真实项目的冻结源码子集；保留校准范围内的源码与许可证，不改写源码 |
| `target/<本次运行>/corpus/` | 从冻结快照生成的 20 万行语料；可以重建，不提交 |
| `target/<本次运行>/release-staging.json` | 测量暂存收据；位于语料目录外，校验通过后才能晋升 |
| 本目录的 `release_runs.json` 与 `self_check.json` | 性能与自检规范收据；后者不提交，两者均不能手工改成通过 |
| 目标项目的 `.csu/runs/<运行标识>/` | 普通 CSU 审查报告；与性能语料和安装目录分离 |

样例、冻结源码、生成语料和结果收据是四种不同材料。清理临时产物时不能反向清理冻结输入。

## 数据与职责

| 材料 | 用途 |
|---|---|
| [fixture-manifest.json](fixture-manifest.json) | 绑定四语言样例的文件身份与精确预期 |
| [benchmark-manifest.json](benchmark-manifest.json) | 固定目标快照、排除项、语料、Authority、解析器、脚本、环境与预算 |
| [release_runs.json](release_runs.json) | 保存各次新进程测量的终态、耗时、内存和结果摘要 |
| `self_check.json` | 本地或 CI 生成的当前候选自检收据，不提交 |
| [parser-admission.json](parser-admission.json) | 保存固定解析器对目标源码的准入观察 |
| [verify-inputs.ps1](verify-inputs.ps1) | 重算身份、检查适用性、验收并晋升收据 |
| [measure-release.ps1](measure-release.ps1) | 生成原始性能测量，不自行宣告发布通过 |
| [measure-parser-admission.ps1](measure-parser-admission.ps1) | 生成解析准入测量 |

Markdown 不复制当前哈希、耗时、计数、Seal 或发布状态；实际结论取决于收据与校验结果。
性能门槛以 benchmark manifest 的 `runner` 和 `release_evidence` 为准，不沿用旧 README 的历史口径。

## 测试什么

四语言样例覆盖合法文档、普通注释冒充、缺失公开字段、候选短名和语法损坏。
测试变绿表示工具给出精确预期，包括正确检出违规和保留不完整状态，不表示所有样例都合规。
普通注释不能替代原生文档，候选名称不自动改名，损坏源码不能被判为通过。
更细的行为由以下公共入口测试负责；对应预期保留在测试源码中。

测试分组、单组命令和共享样例的职责统一见 [tests/README](../../../tests/README.md)。

[声明覆盖清单](declaration-coverage.md) 将主要语法入口连接到具体测试，并记录尚缺专项正反证据的边界。

性能 Authority 与用户项目执行同一套固定规则，不能关闭文档或其他检查类别。
它只提供冻结语料拥有的最少项目事实，并完整保留问题与受阻项，不能靠减少检查工作制造性能数字。
性能测量不替代四语言行为测试，也不证明外部项目符合规范。

## 项目事实示例

[authority.json](authority.json) 的 `quantity_concepts` 是本组样例的登记数据，不是通用单位词表。
例如 `velocity` 登记 `m_per_s`，`acceleration` 登记 `m_per_s2`；完整关系以 JSON 为准。
其他项目可以登记自己的精确关系，但必须满足编码规范的格式与影响限制。
后缀只表示命名约定，不证明量纲、换算、值域或运行时正确性。

## 冻结输入

真实维护源位于仓库的 `bench/targets`，由 benchmark manifest 的相对路径唯一指定。
这里保留性能与解析校准范围的源码并集，不是完整上游工程；范围外资料已清理，源码路径、字节和必要许可证保持原样。
不能使用用户配置目录，也不能从已生成语料反向重建目标源来替代校验。
脚本逐文件重算目标、排除项和语料身份，只接受列明扩展名的普通文件，不接受符号链接。
目录、其他扩展及源码树之外的数据、配置和构建产物不进入语料。

生成的 20 万行语料可以重建，不作为跨次审查缓存，也不提交仓库。
路径顺序、物理行、逐文件摘要和语言汇总由校验脚本计算；manifest 保存冻结结果。
选择清单只存在于校验内存和测量收据中，不写入 CSU 审查的目标工作区。

## 收据适用性

性能收据仅描述实际测量的可执行文件、性能 Authority、语料、脚本与参考环境。
Windows 参考平台的耗时和内存不能用于宣称 Linux 或 macOS 性能；其他平台仍需通过构建、测试和自检。
复合性能校验使用 Windows 系统与电源计划接口，不是跨平台打包入口。

自检收据绑定基础 HEAD、完整已跟踪补丁、每个未跟踪输入、Cargo.lock、工具链、
release 二进制和自检 Authority。产品及递归测试源码必须分别达到 `Sealed + Clean + Complete` 且三零。
读取、物理行观察和结构解析次数须与自检文件数一致；物理行观察次数不表示全部内存读取次数。

测量前的完整补丁哈希保留为历史记录。用于跨测量核对的功能补丁只排除测量后替换的 `release_runs.json`。
benchmark manifest 在测量前后必须逐字一致，不反向记录动态收据哈希。
最终自检绑定生成证据后的完整补丁，并检查功能补丁仍对应同一测前候选。

源码、测试、Authority、规范或说明资料变化后，必须重新验证当前候选。
历史数字可以描述历史运行，但不能改名、重新绑定或抄成新候选证据；不同语义结果之间不作相对性能声明。

## 复现与重测

以下命令从 CSU 源码仓库根目录运行，使用 Windows 参考环境与 PowerShell 7。
已有当前性能和自检收据时，执行完整校验：

```powershell
cargo build --locked --release
pwsh -NoProfile -File docs/fixtures/core/verify-inputs.ps1
```

重测时，为本次运行选择一个未使用的 `target/<本次运行>/` 路径。
语料输出目录必须不存在或为空；测量暂存文件必须不存在，父目录必须已存在且不能是重解析点。
以下占位路径需换成同一次运行的实际位置：

```powershell
pwsh -NoProfile -File docs/fixtures/core/verify-inputs.ps1 -BuildCorpus -PrepareMeasurement -OutputDirectory target/<本次运行>/corpus
pwsh -NoProfile -File docs/fixtures/core/measure-release.ps1 -AuthorityDirectory docs/fixtures/core/performance-authority -Workspace target/<本次运行>/corpus -DiagnosticIncomplete -OutputPath target/<本次运行>/release-staging.json
```

已有语料时，第一条改用 `-VerifyCorpusDirectory <语料目录> -PrepareMeasurement`，不重建或覆盖原目录。
`-DiagnosticIncomplete` 保留当前冻结负载的真实不完整结论，不关闭规则或隐藏问题。

测量完成后，计算暂存收据的 SHA-256，并向校验脚本传入 `-ReleaseEvidencePath`、
`-ExpectedStagingSha256`、`-VerifyReleaseEvidenceOnly -PromoteReleaseEvidence`，校验后晋升性能收据。
准备期间不得修改候选源码、说明文件、Authority、脚本或冻结清单，否则应重新准备和测量。

自检收据是独立输入；无参数校验不会自动生成缺失的 `self_check.json`。
当前候选自检暂存收据准备好后，用 `-SelfCheckEvidencePath`、`-ExpectedSelfCheckStagingSha256`、
`-PromoteSelfCheckEvidence` 单独校验并晋升，不能与性能晋升参数混用。
最后运行无参数校验，核对当前候选、自检与性能收据的完整绑定；缺失或过期就停止验收。

测量脚本不负责晋升；校验脚本检查输入未变后原子替换规范收据。
拒绝或中断必须保留真实失败原因，不能只修改记录以获得绿灯。

## 发布边界

本地收据不代表已经提交、打标签、推送、打包或发布。
计划发布的未跟踪输入必须先纳入版本控制，再由干净标签的 CI 构建各平台构件。
最终发布需要人工验收和实际 CI 结果，任何说明文档都不能代替。
