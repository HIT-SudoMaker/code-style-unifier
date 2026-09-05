# CSU 设计理念

CSU 用一个无持久状态的 Rust 审查器，检查 Python、Rust、C 和 C++ 的源码规范。
[编码规范](coding_standards.md) 决定应当遵守什么；本文解释为什么这样实现，以及如何验证它。

## 设计取舍

我们追求的不是分析最多，而是在明确边界内给出可信、可定位的结果。

1. 结论正确优先于结论详细；缺少事实时宁可不完整，也不猜成通过
2. 一个清楚的生命周期优先于扩展框架；一次性速度优先于跨次复用
3. 四语言共享规则意图，但不抹平原生语法、文档归属和依赖差异
4. 证据大小随文件、固定类别和实际问题增长，不随全部可能义务组合增长
5. 项目事实补足知识，不反过来改变标准

早期方案暴露了四类不值得保留的复杂度：

| 方案 | 问题 | 当前选择 |
|---|---|---|
| 只逐行扫描 | 无法证明声明作用域和文档归属，补充缩进与关键字猜测会形成第二个解析器 | 用语法树证明结构 |
| 只遍历语法树 | 为物理行、字符和已知范围内的文本增加不必要的结构处理 | 直接检查已读取字节 |
| 为每个义务创建丰富收据 | 重复保存状态，扩大内存、序列化与未完成状态的组合 | 每文件固定六类完成状态 |
| 增量缓存 | 需要失效、迁移、依赖追踪和中断恢复 | 每次独立检查，不复用旧结果 |

## 一个接口，一次生命周期

公共入口是 `WorkspaceReviewer::compile(AuthorityInput)` 和 `review(ReviewInput)`。
调用方只需理解输入、拒绝条件和终态；解析器、语言适配、事实提取和内部索引均不公开。

```text
校验并编译 Authority
  → 确定源码范围与语言
  → 每文件读取一次
  → 观察物理行与语法结构
  → 按固定规则判断
  → 完成六类事实记录
  → 封存结果
  → 输出文本或 JSON
```

两个观察通道共用同一份字节和位置坐标，不是两个独立检查器。
字节通道处理物理行、字符及结构已经确定的文本范围；Tree-sitter 处理声明种类、作用域、
接收者、文档附着、依赖声明和代码与注释的先后关系。

每个已读取文件至多进行一次结构解析；无效 UTF-8 不进入解析器。
事实提取完成后释放语法树、游标与源码缓冲区，借用的节点不能逃出文件处理过程。

`byte_sweeps` 只统计物理行观察次数，不代表所有内存读取。
哈希、UTF-8 校验、错误定位与结构观察仍读取同一缓冲区；当前没有行索引，
无效 UTF-8 的位置通过有界前缀遍历确定，列号按字节计数。

工作区与内存文档共用同一套路径和语言判断。每项输入只能成为受检源码、非受管文件或明确拒绝。
绝对路径、空段、当前或父目录段、规范化后的路径碰撞均被拒绝。
隐藏清单不能选择源码或覆盖语言；性能语料清单只用于发布证据。

## 三种信息，各自负责

| 信息 | 来源 | 责任 |
|---|---|---|
| 固定规则 `StandardLaw` | 二进制 | 规则、等级、优先级、语言要求和终态计算 |
| 源码事实 | 规范化路径、已读取字节和原生语法树 | 证明实际存在的声明、位置与文档关系 |
| 项目事实 `ProjectFacts` | 经校验的 Authority | 补充源码无法证明的项目意图 |

项目负责人对业务事实负责。CSU 只能保证输入格式、源码对应关系和影响范围，不能认证事实本身为真。
六种项目事实的用途和禁止事项统一定义在编码规范中，不在这里维护第二套规则表。

Authority schema 4 的七个字段在读取源码前一次反序列化、完整解构并校验。
新增字段若未处理，会暴露在解构检查中。重复原始键、规范化碰撞、未知字段、
重叠依赖分类、无效量值后缀和不支持的外部协议身份均在此拒绝。

`AuthorityIndexes` 只从已校验事实和固定规则构建前后缀标记与精确量值名称索引。
`CompiledAuthority` 统一提供行为查询；调用方不能读取原始输入并自行解释。
不引入正则规则、脚本、回调、插件或通用规则语言。

单字符先判为候选；其他完整词元使用同一个 Rust Unicode 小写函数，再查候选表与普通词表。
前缀按长度优先排序一次，名称判断不逐声明重新建立或排序标记表。
外部协议身份只能解决精确匹配的未知名称，不能压过候选、保留名称、命名形式或后缀规则。

## 规则必须真正参与判断

同一条规则记录保存操作符、标识、等级、说明、待确认问题和局部语义修订。
语言记录直接提供文档形式、标题顺序、空值、字段格式、返回拼写和依赖规则。
全局记录保存共用的叙述要求和指令参数字符规则；Rust 行末指令名单明确为空。

判断代码直接使用这些记录，而不是维护一份只参与哈希、不影响执行的影子规则。
语法树遍历、源码可解析性和代码与注释同行判断仍是固定算法，不伪装成可配置数据。

语义摘要序列化实际使用的固定规则、算法修订与项目事实。
`project_fact_revision` 标识固定的项目事实校验和影响协议，只是身份元数据，不是运行开关。
更换索引表示不改变摘要；集合与映射重排不改变摘要；影响判断的规则或事实变化会改变摘要。
章节和展示顺序在同一记录中维护，但明确排除在语义序列化之外，也不接受项目配置。

序列化字节直接进入 BLAKE3 derive-key，不附加手工前缀。
序列化布局属于身份协议；序列化失败返回 `authority.identity`，不能回退为另一种摘要。

## 四语言一致，但不假装相同

Python 使用语句块首条 docstring，Rust 使用附属外层文档，C/C++ 使用紧邻声明的规范文档块。
C/C++ 的歧义头文件和公开归属需要项目事实；目录、访问标签、链接属性或相邻文字不能代替证明。
预处理、构建配置、宏展开和别名解析不属于当前能力，不能以近似匹配补齐。

语言适配器负责确认名称是语言固定、结构约定、外部协议、丢弃位置还是作者自选。
结构不能证明时标记对应类别受阻，不发明归属。

返回状态只根据直接声明判断为 `NoValue | Never | Value | Unknown`。
不返回状态优先；未知返回类型使公开文档检查不完整，不能猜成有返回值。
具体拼写、空值和各语言的不对称要求只在编码规范中定义。

注释位置根据语法节点判断，字符串内的符号不冒充注释。
文档字段保留相对文档标记的缩进，统一切分名称、分隔符、空格与描述，并在同一部分内检查最短对齐。
表达是否简洁由作者审查，不增加文风分类器，也不将机器通过解释为文字质量证明。

## 让完成状态不能遗漏

每个文件固定记录六类事实：读取、物理行、源码结构、标识符、文档和依赖。
每类只有两种状态：

```text
Complete(已观察对象数)
Blocked(原因)
```

`Complete(0)` 表示已经检查且没有该类对象，不是跳过检查。
没有待处理或不需要状态，也没有两套“应执行／已执行”位掩码；六类记录由构造过程保证存在。
问题与受阻原因按实际数量保存，类别状态保持固定大小。

空间随“文件数 × 六类状态 ＋ 实际问题与原因”增长，而不是义务、对象和要求的笛卡尔积。
某类受阻不抹去其他已证明的问题。语法损坏阻止该文件的结构判断，但独立物理事实与其他文件仍可检查。
当前不引入按损坏区间传播的复杂关系图。

## 终态与证据

公共终态只有 `Rejected`、`Failed` 和 `Sealed`。
输入校验不通过是拒绝；进入审查后内部不变量损坏是失败；正常完成处理则封存已有证据。

| 封存证据 | 结论 |
|---|---|
| 所有类别完整，硬违规和待确认均为零 | Clean |
| 所有类别完整，存在问题 | Findings |
| 任一类别受阻 | Incomplete |

Seal 绑定规则与项目事实摘要、源码快照、范围、类别状态、数量、问题、完整性、版本与规范顺序。
明确的审查范围仍属于身份；除此之外的临时路径、时钟、线程顺序、展示布局和输出位置不影响摘要。
文本与 JSON 是同一终态的只读展示，渲染或写入失败不能改写语义结果。

修复必须保留受检声明，在相同 Authority 和范围下审查新源码并保留新旧证据。
完整操作由 [CSU Review](../.agents/skills/csu-review/SKILL.md) 及其
[修复指引](../.agents/skills/csu-review/references/remediation.md) 维护，不再复制协议文档。

## 测试应证明关键行为

主要入口是“编译内存 Authority → 审查四语言文档 → 断言终态与 Seal”。
测试通过的含义是正确识别预期问题，不是把所有测试样例改成合规代码。

以下是源码仓库中的定位索引，不复制测试数量、预期、哈希或发布状态：

| 行为 | 主要测试文件 |
|---|---|
| 四语言合法、违规、候选与语法受损样例 | `tests/fixture_contract.rs` |
| Authority 边界、输入拒绝、路径、六类完成状态、行末指令及身份确定性 | `tests/terminal_contract.rs` |
| 声明提取、语言固定名称、候选与外部协议归属 | `tests/identifier_subjects.rs` |
| 命名形式、前缀与量值后缀 | `tests/identifier_forms.rs` |
| 四语言公开文档的共同要求 | `tests/public_review.rs` |
| 原生文档、叙述、对齐、标点、内部方法与真实规避样例 | `tests/documentation_regressions.rs` |
| C++ 模板、构造析构、作用说明与重载歧义 | `tests/cpp_documentation_roles.rs` |
| 四语言直接返回声明 | `tests/return_shape_contract.rs` |
| 依赖分类、分组、顺序、通配与模块位置 | `tests/dependency_contract.rs` |
| 文本、JSON 与 CLI 退出码 | `tests/projection_cli.rs` |
| 产品及测试源码自检、技能包一致性 | `tests/self_check.rs` |

同一生产判断的输入变体放在现有测试文件的局部表中；语言语法可独立变化时保留独立样例。
新增测试文件前，说明删除它会失去哪一类独立证据，避免按字符串变体扩张目录。
共享辅助只负责装配内存输入并调用公共审查接口；Authority、源码变异和预期留在各测试文件中。
源码树中的 `tests/review_fixture/mod.rs` 承担这项装配工作。

CSU 自检分别检查产品与测试源码，必须完整封存且三零。
真实冻结语料用于验证吞吐、确定性和能力边界，不是合规示范，不能通过修剪问题提高分数。
操作、收据与复现入口统一放在源码仓库的 [靶场指南](https://github.com/HIT-SudoMaker/code-style-unifier/blob/main/docs/fixtures/core/README.md)。

## 性能、规模与发布

产品 Rust 上限为 7,795 物理行，测试 Rust 上限为 4,816 行。
样例和第三方语料单独统计，不能承载生产逻辑；上限不是允许填充代码的预算。

参考负载为 20 万物理行，30 次无缓存的新进程检查应产生同一个结果摘要，p95 小于十秒。
性能证据须绑定可执行文件、规则、项目事实、语料、测量脚本与平台。
相对比较必须明确控制这些条件，不能把不同语义或环境的数字混成同一基线。
Windows 参考平台的时间与内存结果不能直接推广到 Linux 和 macOS。

GitHub Actions 在五个原生平台构建、测试和打包：Windows x86-64、Linux x86-64/ARM64、macOS Intel/Apple Silicon。
所有包齐备后统一计算校验和，并按发布流程等待五分钟时间边界发布。
打包只分发 README、编码规范、设计理念、技能包、许可证与二进制；测试语料和维护指南留在源码仓库。
操作成功与否由实际 CI 和收据证明，本文不宣告当前候选已经发布。

## 何时需要重新设计

出现第二套规则来源、动态规则执行、公开解析器接口、重复源码读取或完整解析、
跨次缓存、项目特例豁免、可配置等级或完成条件、丰富义务收据图、跨语言猜测或突破行数上限时，暂停并重新论证。

新增规则必须逐语言回答：检查什么对象、由什么原生结构证明、需要哪些事实、
缺少事实时保留什么证据，以及事实充分时给出哪种固定等级。
回答不完整时不进入实现。

新增项目词元通常只需登记事实；新增规则或事实能力必须贯穿规范、观察、判断、完成状态和公共接口测试。
仅转发数据、不承担独立约束的辅助层应并回负责该约束的位置。

## 参考依据

以下来源解释语言和工具行为，不把 CSU 的项目选择冒充语言标准。
句号、中文摘要、对齐、单位后缀及 C/C++ 文档块格式均是 CSU 的规范选择。

| 范围 | 原始参考 |
|---|---|
| 单位与表示 | [BIPM SI Brochure](https://www.bipm.org/en/publications/si-brochure/)、[NIST SP 811](https://www.nist.gov/pml/special-publication-811) |
| Python 名称与函数 | [词法](https://docs.python.org/3/reference/lexical_analysis.html#identifiers)、[函数定义](https://docs.python.org/3/reference/compound_stmts.html#function-definitions)、[ast.get_docstring](https://docs.python.org/3/library/ast.html#ast.get_docstring) |
| Python 风格与依赖 | [PEP 8 命名](https://peps.python.org/pep-0008/#naming-conventions)、[导入](https://peps.python.org/pep-0008/#imports)、[PEP 257](https://peps.python.org/pep-0257/)、[import 语句](https://docs.python.org/3/reference/simple_stmts.html#the-import-statement)、[TYPE_CHECKING](https://docs.python.org/3/library/typing.html#typing.TYPE_CHECKING) |
| Rust 名称与文档 | [标识符](https://doc.rust-lang.org/reference/identifiers.html)、[注释](https://doc.rust-lang.org/reference/comments.html)、[风格指南](https://doc.rust-lang.org/style-guide/)、[API 命名](https://rust-lang.github.io/api-guidelines/naming.html)、[rustdoc](https://doc.rust-lang.org/rustdoc/how-to-write-documentation.html) |
| Rust 依赖 | [use 声明](https://doc.rust-lang.org/reference/items/use-declarations.html)、[导入风格](https://doc.rust-lang.org/stable/style-guide/items.html#imports-use-statements) |
| C 与 C++ | [WG14 N3220](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n3220.pdf)、[WG21 工作草案](https://eel.is/c++draft/)、[C++ 命名指南](https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#S-naming) |
| 解析与错误节点 | [Tree-sitter 生命周期](https://tree-sitter.github.io/tree-sitter/using-parsers/2-basic-parsing.html)、[ERROR/MISSING](https://tree-sitter.github.io/tree-sitter/using-parsers/queries/1-syntax.html#the-error-node)、[Rust Parser](https://docs.rs/tree-sitter/0.26.13/tree_sitter/struct.Parser.html)、[Node](https://docs.rs/tree-sitter/0.26.13/tree_sitter/struct.Node.html) |
| 确定性 | [BTreeMap](https://doc.rust-lang.org/std/collections/struct.BTreeMap.html)、[HashMap](https://doc.rust-lang.org/std/collections/struct.HashMap.html)、[SARIF Appendix F](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html#appendix-F) |

固定的观察身份为：

| 语言 | 观察身份 |
|---|---|
| Python | `tree-sitter-python@0.25.0+direct-source-facts-v3` |
| Rust | `tree-sitter-rust@0.24.2+direct-source-facts-v3` |
| C | `tree-sitter-c@0.24.2+direct-source-facts-v3` |
| C++ | `tree-sitter-cpp@8b5b49eb+direct-source-facts-v3` |

这些版本标识描述实现来源，不是作者命名要求。升级解析器或提取协议时，必须同步语言记录与行为证据。
冻结第三方快照的修订和许可证入口见源码仓库的 [bench/targets](https://github.com/HIT-SudoMaker/code-style-unifier/blob/main/bench/targets/README.md)；快照不定义 CSU 规则。
