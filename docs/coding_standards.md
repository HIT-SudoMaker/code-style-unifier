# CSU 四语言编程规范

> **状态：CURRENT**
>
> **适用语言：Python、Rust、C、C++**
>
> **定位：规则语义 Authority 与人工复核基础**

本规范只保留四种语言共同需要、且能由语言本地事实诚实表达的代码合同。
共同目标保持一致；语法、文档载体、公开接口所有权和依赖机制留在各自
Language Profile 中。任何实现、测试、历史设计或报告都不得反向改写本规范。

## 1. 使用方式

### 1.1 Authority 顺序

1. 用户对当前任务的明确要求
2. 项目需求与公开接口合同
3. 本规范
4. 经本规范约束的项目 typed Authority
5. 当前实现与工具默认行为

项目 typed Authority 负责选择已发布 Rule、冻结四语言 Profile 参数以及提供
token、Concept、suffix 和 public owner 等数据。它不能增加动态规则、改变 Grade，
也不能用目标路径或项目名称创建例外。

### 1.2 规范词

| 规范词 | 含义 |
|---|---|
| 必须 / 禁止 | 适用性与所需事实均已成立；违反时产生 Hard Violation |
| 需确认 | 结构风险已成立，但语义需要 Owner 裁决；产生 Review Required |
| 需要补充 Authority | 适用性或事实不足；不是 Finding，相关 family 必须 Blocked |
| 建议 | 非 CSU 门禁要求；偏离时应有清楚理由 |

Finding Grade、Review Completion 和消费者 Gate 是三件事。Gate 可以阻断
Review Required，但不能把它改写成 Hard Violation；没有 Finding 也不能覆盖
Blocked family。

### 1.3 当前边界

CSU 当前机器合同只覆盖：

- source parseability
- author-chosen identifier
- callable documentation
- direct dependency declaration

79 视觉列宽、声明排列、完整编译或链接语义、unused dependency、宏与预处理展开、
最终公开可达性、formatter 和自动修复不属于当前 Seal。它们必须由明确的后续
operator 或外部工具链拥有，不能由源码字符串启发式补齐。

### 1.4 证据作用域不是规则豁免

Conformance Authority 回答“源码是否符合本规范”；Performance Authority 只回答
“同一生命周期在冻结工作量上是否完整、确定且足够快”。后者可以把与吞吐量无关的
family 明确设为 `NotApplicable`，但必须同时满足：

- 不修改本规范、Rule Grade 或 operator 实现
- 不从完整性语料删除已经 admitted 的 Rule 工作
- 结果为 `Sealed + Complete`，并保留其余 family 的全部 Findings
- 不把性能结果描述为源码 Clean 或规则合规

外部校准可以诚实得到 `Sealed + Incomplete`，用于暴露 Authority 或 observation
能力缺口。Conformance、Performance 与 Diagnostic 三类证据不得互相冒充。

## 2. 统一生命周期与四语言总化

每次 Review 都是一次性、只读且无缓存的：

```text
compile Authority
  -> freeze scope
  -> capture each file once
  -> byte/line observation once
  -> Tree-sitter structural observation at most once
  -> extract language-local facts
  -> execute closed Rule operators
  -> close every required fact family
  -> seal
  -> read-only projection
```

byte/line 轨只能拥有物理行和已知范围内的字符事实。structural 轨拥有声明种类、
作用域、owner、source order、文档附着和 identifier role。前者不得靠关键字、
缩进或邻近注释猜结构；后者不得重新读取文件。

每个 Shared Rule Family 必须恰好具有 Python、Rust、C 和 C++ 四个投影格。
每格只能是：

```text
Supported(local contract)
NotApplicable(reason)
NeedsAuthority(capability)
```

缺格、借用另一语言事实、未知 operator 或矛盾 typed row 必须在读取目标文件前拒绝。
C 和 C++ 始终是两个 Profile；相似语法不构成共享语义。

### 2.1 可解析性合同

CSU 不执行、导入、编译或链接被检查代码。完整结构结论只要求源码是有效 UTF-8，
并且固定版本 Tree-sitter 没有产生 `ERROR` 或 `MISSING` 节点。

| Profile | 固定 observation method |
|---|---|
| Python | `tree-sitter-python@0.25.0+direct-source-facts-v1` |
| Rust | `tree-sitter-rust@0.24.2+direct-source-facts-v1` |
| C | `tree-sitter-c@0.24.2+direct-source-facts-v1` |
| C++ | `tree-sitter-cpp@8b5b49eb+direct-source-facts-v1` |

| 输入状态 | Direct Source | External Source | 可靠保留 |
|---|---|---|---|
| 可解析 | 执行所选结构 Rule | 执行所选结构 Rule | 全部已闭合 family |
| 非法 UTF-8 或语法损坏 | Hard `source.parseability` | 不产生源码 Finding | PhysicalLines 与损坏锚点 |
| 文件读取失败 | 不产生源码 Finding | 不产生源码 Finding | Capture blocker |

损坏文件的 structure-dependent family 必须 Blocked，结果为 `Sealed + Incomplete`；
其他文件继续独立检查。不得在错误树上用逐行猜测恢复结构结论。

## 3. 语义命名合同

### 3.1 唯一名称语法

每个作者选择的 identifier 都必须表达完整 Canonical Concept。value-like 名称只允许：

```text
language form
  -> optional Semantic Role Prefix
  -> Canonical Concept
  -> optional Representation Suffix
```

Language Profile 必须先剥离本地形式，例如 Python private 前导 `_`、Rust `r#`、
Rust lifetime 前导 `'`、C typedef 尾 `_t` 和 C++ private member 尾 `_`。这些都不
参与业务语义拆分。

命名判断只有一个固定优先链：

1. coverage guard：事实不足则 Blocked，不判 Clean
2. structural exclusion：只排除语言固定拼写或有证据的外部固定名称
3. candidate symbolic form：产生 Review Required
4. lexical/canonical form：已证明的形式错误为 Hard，未知 token 为 Review Required

同一声明在 identifier family 内只产生最高优先级的一个原子 Finding。

### 3.2 Semantic Role Prefix

| Prefix | 唯一含义 |
|---|---|
| `is_` | 当前是否处于某状态 |
| `has_` | 是否拥有对象或事实 |
| `can_` | 是否具有执行能力 |
| `should_` | 策略是否建议执行 |
| `needs_` | 当前是否需要对象或动作 |
| `lower_` / `upper_` | 允许或配置区间的端点 |
| `minimum_` / `maximum_` | 集合、计算或观测得到的实际极值 |

`min_` 和 `max_` 不是许可缩写。只有类型、签名或 Authority 已证明 Subject 是
boolean、bound 或 extremum 时，才强制相应 prefix；不得从名称反推运行时语义。

### 3.3 Representation Suffix

Authority 标记为 quantity-bearing 的 value、parameter、field/member 或 constant
必须使用唯一 ASCII Representation Suffix。suffix 只编码名称中的表示，不证明
量纲、换算、值域或运行时正确性；首版不实现单位表达式 parser。

| Suffix | 表示 | Suffix | 表示 |
|---|---|---|---|
| `s` / `ms` / `us` | 秒 / 毫秒 / 微秒 | `m` / `mm` / `um` | 米 / 毫米 / 微米 |
| `k` | 开尔文 | `pa` | 帕斯卡 |
| `v` / `a` | 伏特 / 安培 | `hz` | 赫兹 |
| `w` / `j` | 瓦特 / 焦耳 | `rad` / `deg` | 弧度 / 度 |
| `m_per_s` | 米每秒 | `m_per_s2` | 米每二次方秒 |
| `v_per_m` | 伏特每米 | `count` / `ratio` / `percent` | 计数 / 比率 / 百分比 |
| `index` | 索引表示 |  |  |

首版 quantity-bearing Concept 为：

| Concept | Allowed suffixes |
|---|---|
| `duration`, `time_interval`, `timestamp` | `s`, `ms`, `us` |
| `distance`, `length`, `width`, `height` | `m`, `mm`, `um` |
| `temperature` | `k` |
| `pressure` | `pa` |
| `voltage` | `v` |
| `electric_current` | `a` |
| `frequency` | `hz` |
| `power` | `w` |
| `energy` | `j` |
| `velocity` | `m_per_s` |
| `acceleration` | `m_per_s2` |
| `electric_field` | `v_per_m` |
| `phase` | `rad`, `deg` |
| `efficiency` | `ratio`, `percent` |

例如 `upper_temperature_k`、`maximum_velocity_m_per_s` 和 `phase_rad` 具有唯一
名称分解。强类型 wrapper 当前不豁免 suffix。

### 3.4 Candidate Naming Registry

下列完整 token 必须进入 Review Required，不能自动放行、自动改名或升级为 Hard：

- ASCII 拉丁单字母 `A`–`Z` 和 `a`–`z`
- 常用希腊转写：`alpha`, `beta`, `gamma`, `delta`, `epsilon`, `zeta`, `eta`,
  `theta`, `iota`, `kappa`, `lambda`, `mu`, `nu`, `xi`, `omicron`, `pi`,
  `rho`, `sigma`, `tau`, `upsilon`, `phi`, `chi`, `psi`, `omega`
- 对应希腊大小写字形及常见变体 `ϕ/φ`, `ϑ/θ`, `ϵ/ε`, `ϖ/π`, `ϱ/ρ`, `ς/σ`

匹配必须使用完整 token，禁止 substring 匹配和 Unicode 字形归一。`phi`、`φ` 与
`ϕ` 是三个独立观察，但都只能询问“它对应哪个完整 Canonical Concept”。公式、论文
记号和语言社区惯例都不能让作者选择的短符号直接通过。

### 3.5 四语言名称形式

| Declaration role | Python | Rust | C | C++ |
|---|---|---|---|---|
| value、parameter、function/method | `lower_snake_case` | `lower_snake_case` | `lower_snake_case` | `lower_snake_case` |
| private value/member | `_lower_snake_case` | 与普通 binding 相同 | 与普通 object 相同 | private non-static member 为 `lower_snake_case_` |
| type/class/struct/enum/alias | `PascalCase` | `PascalCase` | tag 为 `lower_snake_case`；typedef 为 `lower_snake_case_t` | `PascalCase` |
| enum variant/enumerator | Profile form | `PascalCase` | `UPPER_SNAKE_CASE` | `UPPER_SNAKE_CASE` |
| named constant | `UPPER_SNAKE_CASE` | `UPPER_SNAKE_CASE` | `UPPER_SNAKE_CASE` | `UPPER_SNAKE_CASE` |
| macro definition | 不适用 | `lower_snake_case` | `UPPER_SNAKE_CASE` | `UPPER_SNAKE_CASE` |
| type generic | 完整 `PascalCase` Concept | 完整 `PascalCase` Concept | 不适用 | 完整 `PascalCase` Concept |
| const/non-type generic | 不适用 | 完整 `UPPER_SNAKE_CASE` Concept | 不适用 | 完整 `UPPER_SNAKE_CASE` Concept |
| author-chosen lifetime | 不适用 | 完整 `'lower_snake_case` Concept | 不适用 | 不适用 |

本地结构排除必须精确：Python 只排除 receiver 位置的 `self`/`cls`；Rust 只排除
receiver `self`、类型拼写 `Self`、`'_` 和 `'static`；C 没有 receiver 豁免；C++
排除 `this`、constructor/destructor 的固定拼写和 operator token。`T`、`K`、`V`、
`N`、`'a` 仍是作者命名。

C 与 C++ 的保留 identifier 规则分别检查；外部 linkage、`extern`、`public:`、
`export` 或 `extern "C"` 都不能单独成为本地名称豁免。

## 4. Documentation Contract

### 4.1 共同语义

每个能由本地结构事实证明、具有稳定名称和合法载体附着点的 Direct Source named
callable 都必须有 Profile-recognized Documentation Carrier。普通注释不能替代它。

- internal、private 或 nested callable 使用 `SummaryOnly`
- public contract callable 使用 `PublicCallableContract`
- Summary 和受控单行 field description 不得以 `。` 或 `.` 结束
- body paragraph、代码、URL、路径、版本号和小数不执行全局句号检查

`PublicCallableContract` 始终包含 Arguments、Returns 和 Failures 三个 role，且按
本地 Profile 顺序出现。没有参数、返回或已声明失败契约时，也必须使用本地空值明确
写出，不能通过省略表达“没有”。

### 4.2 四语言 Profile

| Profile | Carrier | Arguments | Returns | Failures | 空值 |
|---|---|---|---|---|---|
| Python | suite 第一条三双引号字符串（`suite_first_triple_double_quoted_string`） | `Args:` | `Returns:` | `Raises:` | `无` |
| Rust | outer `///`、`/** */` 或 literal `#[doc = "..."]`（`outer_rustdoc`） | `# Arguments` | `# Returns` | `# Errors` | `- 无` |
| C | 紧邻 owner 的受控 `/** ... */`（`controlled_adjacent_block`） | `参数：` | `返回：` | `错误：` | `- 无` |
| C++ | 紧邻 owner 的受控 `/** ... */`（`controlled_adjacent_block`） | `参数：` | `返回：` | `错误：` | `- 无` |

语言适配规则如下：

- Python：模块体 public-syntax function、public-syntax class 的普通 public method、
  property contract 等按本地结构决定 public tier；`self`/`cls` 不进入 Arguments。
  private、nested 和 local callable 仍需 SummaryOnly。模块级 docstring 不属于本项目
  文档 owner，suite 第一条模块字符串会产生 carrier Finding。
- Rust：Direct Source named free、inherent、trait 和 foreign callable 都需要 carrier。
  无限制 `pub` 只建立本地 public-contract tier，不证明最终 crate 可达性。`unsafe fn`
  和 `unsafe trait` 额外要求非空 `# Safety`；必要时可增加 `# Panics`，但不能替代
  三个基础 role。inner rustdoc `//!`/`/*!` 与普通注释不能替代 item outer rustdoc。
- C：public tier 和唯一 Documentation Owner 必须来自明确的 header language 与
  Public Surface Authority；`extern`、linkage、文件夹或最近注释都不能证明公开性。
  同一 declaration identity 的实现不得复制 public contract。
- C++：与 C 使用相似 carrier，但保持独立 Profile。public owner 必须来自明确 surface
  Authority；`public:` 或 `export` 只是输入事实。constructor、destructor 和 operator
  需要适用的 `效果：`；template 需要适用的 `模板参数：`。这些字段不能替代三个
  基础 role。

public/internal tier、跨文件 identity 或 owner 无法唯一确定时，已经证明的 carrier
Finding 可以保留，但 Documentation family 必须 Blocked；不得降级为 SummaryOnly。

## 5. Dependency Access Declaration

四种语言只共享“依赖必须由本地结构定位、不得按行长度排序、不得猜 target 或
usedness”的工程意图。它们不共享一个虚构的 import 语法。

| Profile | Direct Source subject | 当前可靠规则 | Authority 边界 |
|---|---|---|---|
| Python | module-level `import` / `from` 与精确 `TYPE_CHECKING` block | 禁止 `import *`；已冻结分类且允许重排时，组内按完整模块路径字典序 | stdlib、dependency inventory、package roots、re-export 和 unused |
| Rust | `use` / `pub use` 与本地 group | 禁止 glob；允许重排时采用 Rust version-sort，并保持 group 边界 | Cargo graph、`cfg`、re-export reachability 和 unused |
| C | 直接 `#include` candidate | 默认保持源顺序 | dialect、include path、header identity、有效预处理和 unused |
| C++ | `#include`、module/header-unit `import` | module import 必须位于普通顶层声明之前；include 默认保持源顺序 | module map、header-unit、有效预处理、重排安全和 unused |

C/C++ 有直接依赖声明但缺少 target 或预处理 Authority 时，Dependency family 必须
Blocked；不能根据尖括号、引号、路径前缀或目录猜 standard、third-party 或 project。
首版不自动重排、不删除依赖，也不以源码名称出现次数推导 unused。

## 6. 同一公共函数的四语言投影

以下唯一通用示例展示相同 Inputs、Output 和 Failure 合同。错误通道保留语言本地
形态；示例不创建新的规则。

```python
def calculate_velocity(distance_m: float, duration_s: float) -> float:
    """
    计算平均速度

    Args:
        distance_m: 行进距离
        duration_s: 持续时间
    Returns:
        float: 平均速度
    Raises:
        ValueError: 持续时间不大于零
    """
    if duration_s <= 0.0:
        raise ValueError("持续时间必须大于零")
    velocity_m_per_s = distance_m / duration_s
    return velocity_m_per_s
```

```rust
/// 计算平均速度
///
/// # Arguments
/// - distance_m：行进距离
/// - duration_s：持续时间
/// # Returns
/// - 平均速度
/// # Errors
/// - 持续时间不大于零时返回错误
pub fn calculate_velocity(
    distance_m: f64,
    duration_s: f64,
) -> Result<f64, &'static str> {
    if duration_s <= 0.0 {
        return Err("持续时间必须大于零");
    }
    let velocity_m_per_s = distance_m / duration_s;
    Ok(velocity_m_per_s)
}
```

```c
#include <stdbool.h>

/**
 * 计算平均速度
 *
 * 参数：
 * - distance_m：行进距离
 * - duration_s：持续时间
 * - velocity_m_per_s：平均速度输出位置
 * 返回：
 * - 计算是否成功
 * 错误：
 * - duration_s不大于零时返回false
 */
bool calculate_velocity(
    double distance_m,
    double duration_s,
    double *velocity_m_per_s
);
```

```cpp
/**
 * 计算平均速度
 *
 * 参数：
 * - distance_m：行进距离
 * - duration_s：持续时间
 * 返回：
 * - 平均速度
 * 错误：
 * - duration_s不大于零时抛出std::invalid_argument
 */
double calculate_velocity(double distance_m, double duration_s);
```

## 7. Finding、完成性与修复纪律

当前 Finding Grade 为：

- Hard Violation：规则适用且事实充分，源码明确违反必须或禁止条款
- Soft Friction：已证明的非阻断维护成本；当前发布 Rule Catalog 没有启用此等级
- Review Required：候选符号或未知 token 已被观察，但完整语义需要 Owner 决定

需要补充 Authority 不是 Finding。每个 required `(file, fact family)` 必须终结为
`NotRequired`、`Complete(count)` 或 `Blocked(reason)`。只有
`Sealed + Complete + zero Findings` 才是 Clean。

每条 Finding 必须包含 path、位置、subject、observation、Rule identity、Grade 和
消息；Review Required 还必须包含具体问题。输出先按 Grade，再按 path、位置和 Rule
稳定排序。

禁止以下规避式修复：

- 把 Python docstring、Rust rustdoc 或 C/C++ 受控块改成普通注释
- 删除、移动、动态生成或改名隐藏 Subject，只为了让 Finding 消失
- 加 ignore、allow、exclude、条件编译或目标路径特例绕过审查
- 删除候选字母或希腊 token、扩充通用词表或降低 Grade 来制造 Clean
- 在 Blocked、Rejected 或 Failed 时声称规则已经通过

完整 AI 修复循环见 [AI 审查协议](AI-REVIEW-PROTOCOL.md)。

## 8. 四语言快速检查清单

- [ ] 文件可由固定 Profile grammar 完整解析；损坏处没有被伪装成 Clean
- [ ] 作者选择的声明名表达完整 Concept，语言固定拼写只按本地结构排除
- [ ] boolean、bound、extremum 和 quantity 名称使用正确 prefix/suffix
- [ ] 单字母、希腊字形及转写均进入 Review Required，没有猜测或自动改名
- [ ] 每个 named callable 使用本语言合法 carrier；普通注释没有冒充文档
- [ ] internal/private/nested callable 至少有 SummaryOnly
- [ ] public callable 按本地顺序具有 Arguments、Returns 和 Failures
- [ ] Summary 与受控 field description 不以 `。` 或 `.` 结束
- [ ] Python import、Rust use、C include 与 C++ include/module import 分别判断
- [ ] C 与 C++ 的 header language 和 public owner 均由 Authority 明示
- [ ] 所有 required family 均有终态；Blocked 没有被零 Finding 覆盖
- [ ] 修复后使用相同 Authority 和新 Snapshot 重新 Review

## 9. 维护纪律

新增 token、Concept、prefix、suffix 或 owner row，只修改 typed Authority 数据并增加
四语言或明确本地 fixture。新增 predicate、Subject kind、跨文件 identity、展开事实
或 Rule operator 属于实现变化，必须先修改本规范和 Design。

任何新 Shared Rule Family 都必须先回答：

1. 四种语言各自检查什么 Subject
2. 本地语法或项目 construct 是什么
3. 需要哪些可靠事实
4. Supported、NotApplicable 与 NeedsAuthority 的边界是什么
5. 产生哪个 Grade，Blocked 时保留哪些已证明事实

如果四格无法写清，该规则不得进入运行时。规则的可执行证据见
[测试合同映射](TEST-CONTRACT-MAP.md)，架构取舍见
[CSU Design](design.md)，语言与实现边界见
[Primary Sources](sources.md)。
