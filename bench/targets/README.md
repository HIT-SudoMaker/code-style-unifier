# CSU 靶场

这里保存固定版本的真实项目代码，供 CSU 检验检出能力、误报、完成性、确定性和性能。它们不是“零问题示范工程”：不能为了少报 Issue 修改靶场、加项目特供 suppressions，或缩小真实源码范围。

- 每个目录都是一次冻结；要更新上游时新增目录，不原地覆盖。
- 靶场当前不接入旧 CSU runner、旧测试或旧基线。
- 外部项目的许可证文件随原项目保留。

| 目录 | 固定版本 | 用途 |
| --- | --- | --- |
| `chromatixnext-5b3411fc` | `scientific-foundation-final-seal@5b3411fc9b710a5a79620eea0d3ce1ef0d11eb28` | 科学计算与光学 Python 项目 |
| `metacraft-f51be8ad` | `experiment/continuous-achromatic-native-test@f51be8ad4db700b6af0274bf82ca6fd463ad7e90` | Python + Rust 的科学编排项目 |
| `onns-0245bd34` | `experiment/restoration-sonnet-architecture@0245bd346fb1451ddaa91348ec99f44a1d96a91e` | 实验与数据管线 Python 项目 |
| `ripgrep-3fce3b5b` | `ripgrep@3fce3b5bb0236da2df6d99672afb8a719642eca7` | 多 crate Rust CLI 与平台条件编译 |
| `serde-a874a1b1` | `serde@a874a1b1bb1cc16cf5ee3b1b7b527af5705742bb` | Rust 宏、泛型、attribute 与 `no_std` |
| `zlib-e3dc0a85` | `zlib@e3dc0a85b7032e98380dec011bc8f2c2ee0d8fca` | 紧凑 C、宏与可移植性分支 |
| `curl-72dfda5f` | `curl@72dfda5f5ac3825fc26b82fa404225f3e7a0fc31` | 大型跨平台 C 网络代码 |
| `fmt-e27cc20b` | `fmt@e27cc20bd93a4e280fb9268d41cd131069a9c73f` | 现代 C++ 模板、`constexpr` 与 Unicode |

## 首轮性能靶场锁定

上表的八个目录共同构成 CSU 首轮唯一的固定性能靶场：三份真实科学 Python 项目、两份 Rust 项目、两份 C 项目和一份 C++ 项目。它们用于暴露规则缺口、完成性问题、确定性问题与资源成本；某个靶场尚未被当前 Language Profile 接纳，不等于可以从集合中删除或以较小范围替代。

- 靶场身份由目录名中的上游提交、表中的完整 revision，以及每次 Review 生成的 Snapshot 身份共同确定。目录名不是对运行中工作区的信任替代。
- 任何上游更新都新增一个带新提交后缀的目录；不得原地刷新、重写、删减或为性能结果修改现有靶场。
- 性能比较必须使用相同的 Compiled Authority、接纳范围与完整性语义。Finding 数量不是优化目标，也不能用项目专用 suppression 换取更快的结果。

## 性能使用规则

首轮工作负载是冷启动、离线、只读、单工作区的完整批处理 Review；靶场不接入守护进程、增量状态、持久缓存、自动修复或 Compatibility Layer。

“越快越好”在这里是受语义约束的优化目标：先保证相同 Authority/Snapshot 下完整性与 Seal 一致，再比较冷启动耗时和峰值 RSS。首条可接受的语义切片会为每个已接纳靶场记录冷启动基线；之后同一语义输入的实现不能以更慢的 p95 冷启动或更高的峰值 RSS 换取所谓优化。若二者存在真实权衡，必须单独记录所有者决议。

当前没有虚构的全局毫秒上限。历史 `200k LOC / <= 6s` 仅作为校准警报和回归调查触发条件，不自动成为不同规则范围或不同机器上的通过线。每次比较仍必须报告 Authority、Snapshot、接纳/受阻数、读取/parse次数与字节数、阶段耗时、峰值 RSS、Finding/Receipt 计数和跨 worker 数的 Seal 一致性。
