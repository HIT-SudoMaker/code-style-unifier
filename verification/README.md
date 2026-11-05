# CSU 验证

本目录保存 CSU 的验证输入、专用 Authority、脚本与收据，不增加用户规则，也不进入二进制包。
[编码规范](../docs/coding_standards.md)定义要求，[设计原理](../docs/design.md)解释取舍，
[技术参考](../docs/technical.md)说明实现。

## 证据轨道

各轨道回答不同问题，彼此不能补偿。

| 轨道 | 建立的证据 | 不证明什么 |
|---|---|---|
| Format 与 Clippy | Rust 源码满足格式和静态检查 | 产品行为正确 |
| 行为测试 | 公共入口对固定样例给出预期结果 | 外部项目合规或性能达标 |
| CSU 自检 | 产品及测试源码达到 `Sealed + Clean + Complete` | 运行时或科学正确性 |
| 解析准入 | 固定解析器对冻结源码的接纳与排除可复现 | 发布阈值或完整语言支持 |
| 性能测量 | 指定 Windows 环境中冻结负载的耗时与峰值工作集 | 其他平台性能 |
| 候选绑定 | 收据、脚本、Authority、源码和二进制属于同一候选 | 已提交、打标签或发布 |

机器检查建立结构、行为与交付证据，不建立科学判断。收据只适用于其绑定的候选、输入和环境。

## 材料

路径均相对源码仓库根目录。

| 类别 | 位置 | 职责 |
|---|---|---|
| 测试输入 | [fixtures/documents/](fixtures/documents/) | 四语言合法、违规和损坏样例 |
| 测试输入 | [tests/fixtures/](../tests/fixtures/) | 表驱动回归数据 |
| 冻结输入 | [bench/targets/](../bench/targets/README.md) | 八个真实项目的固定源码子集与许可证 |
| 项目事实 | [authorities/](authorities/) | 自检、解析准入和性能测量的专用 Authority |
| 清单 | [fixtures/manifest.json](fixtures/manifest.json) | 绑定样例字节与精确预期 |
| 清单 | [benchmark-manifest.json](benchmark-manifest.json) | 绑定目标、排除、语料、脚本、环境与预算 |
| 收据 | [parser-admission.json](parser-admission.json) | 固定解析器的准入观察 |
| 收据 | [release_runs.json](release_runs.json) | 性能运行、资源使用与结果摘要 |
| 脚本 | [verify-inputs.ps1](verify-inputs.ps1) | 重算身份、验证适用性并晋升收据 |
| 脚本 | `measure-*.ps1` | 生成解析、性能和自检暂存收据 |
| 临时产物 | `target/<运行标识>/` | 可重建语料与待验证收据，不提交 |
| 审查记录 | `.csu/runs/<运行标识>/` | 普通 CSU 审查证据，与发布测量分离 |

`self_check.json` 是本地或 CI 晋升的候选收据，不提交。样例、冻结输入、生成语料和收据是不同材料；
清理临时产物不能删除冻结输入。发布包只携带 `docs/*.md`，不携带本目录。

## 样例与冻结负载

四语言样例覆盖合法文档、普通注释冒充、缺失公开字段、候选短名和语法损坏。
测试通过表示 CSU 给出 manifest 规定的结果，不表示所有样例合规。
[声明覆盖清单](declaration-coverage.md)连接语法入口、处理边界和专项测试。

[fixtures/authority.json](fixtures/authority.json)只登记本组样例的 Project Facts。
其中的 `quantity_concepts` 是命名关系示例，不是通用单位词表，也不证明维度、换算、值域或运行时正确性。

`bench/targets` 保留性能与解析校准范围内的源码并集，不是完整上游工程。
目标路径、字节和许可证保持不变；解析器暂不支持的输入进入明确排除记录，不能静默删除。
20 万行语料由 manifest 重建，不提交，也不作为跨次审查缓存。

## 收据适用性

性能收据绑定 release 二进制、Authority、语料、脚本、Cargo.lock、参考环境和候选补丁。
耗时使用 30 次新进程测量的 nearest-rank p95；峰值工作集读取 Windows 保存的进程生命周期最大值，
不以定时采样替代。[Windows 定义](https://learn.microsoft.com/en-us/windows/win32/psapi/process-memory-usage-information)
说明该指标；它不等于私有分配量。

自检收据另行绑定格式、Clippy、测试、两组 CSU 自检和最终候选身份。
验证器把存在的 `.gitattributes` 与 `.csu/plans/` 登记为未跟踪维护输入，这些路径和摘要均参与候选身份。
测量后的功能补丁只排除规范性能收据 `release_runs.json`，
benchmark manifest 在测量前后保持不变。

源码、测试、Authority、规范、文档、脚本或冻结清单变化都会使旧收据失效。
历史收据可以描述历史运行，不能改名、重绑或手工修改成当前候选证据。

## 复现与晋升

以下命令从仓库根目录运行，参考测量环境为 Windows 与 PowerShell 7。

1. 运行开发检查并构建 release 二进制。

   ```powershell
   cargo fmt --all -- --check
   cargo clippy --locked --all-targets -- -D warnings
   cargo test --locked
   cargo build --locked --release
   ```

2. 为一次未使用的运行目录构建并验证语料，同时冻结测量候选。

   ```powershell
   pwsh -NoProfile -File verification/verify-inputs.ps1 -BuildCorpus -PrepareMeasurement -OutputDirectory target/<运行标识>/corpus
   ```

   已有语料时改用 `-VerifyCorpusDirectory <语料目录> -PrepareMeasurement`。语料目录必须不存在或为空，
   且其祖先不能是重解析点。

3. 生成性能暂存收据。`-DiagnosticIncomplete` 保留冻结负载的真实不完整结论，不关闭规则。

   ```powershell
   pwsh -NoProfile -File verification/measure-release.ps1 -AuthorityDirectory verification/authorities/performance -Workspace target/<运行标识>/corpus -DiagnosticIncomplete -OutputPath target/<运行标识>/release-staging.json
   ```

4. 计算暂存文件的 SHA-256，并在输入未变时验证、晋升性能收据。

   ```powershell
   pwsh -NoProfile -File verification/verify-inputs.ps1 -ReleaseEvidencePath target/<运行标识>/release-staging.json -ExpectedStagingSha256 <sha256> -VerifyReleaseEvidenceOnly -PromoteReleaseEvidence
   ```

5. 生成并独立晋升自检收据。

   ```powershell
   pwsh -NoProfile -File verification/measure-self-check.ps1 -Workspace target/<运行标识>/corpus -OutputPath target/<运行标识>/self-staging.json
   pwsh -NoProfile -File verification/verify-inputs.ps1 -SelfCheckEvidencePath target/<运行标识>/self-staging.json -ExpectedSelfCheckStagingSha256 <sha256> -PromoteSelfCheckEvidence
   ```

6. 运行无参数校验，确认规范收据、候选和全部身份一致。

   ```powershell
   pwsh -NoProfile -File verification/verify-inputs.ps1
   ```

暂存收据位于语料之外；准备后任何候选输入变化都要求重新开始。脚本负责测量和验证，只有校验器可以晋升规范收据。

## 发布边界

本地收据不代表已经提交、打标签、推送、打包或发布。
最终发布由干净标签的 CI 构建平台构件，并需要人工验收实际 CI 结果。
