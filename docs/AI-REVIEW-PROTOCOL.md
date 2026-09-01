# CSU AI 证据优先审查协议

本协议约束使用 CSU 结果修改代码的 AI。目标是修复被证明的源码问题，而不是让
报告表面变绿。

## 固定输入

一次修复循环必须冻结并记录：

- Authority 路径或摘要
- 审查范围与起始 revision
- 起始 Terminal、Completion、Disposition 和 Seal
- 选中的 Finding 的 rule、grade、path、line、subject 与 observation

Authority 与范围在修复闭环中保持不变。源码字节改变后必须生成新的 revision；
旧/新 revision 与 Seal 共同证明两个 Snapshot 的身份，不能把修改后的源码冒充为
原 Snapshot。

## 处置规则

| Evidence | AI 可执行动作 | AI 不得声称 |
|---|---|---|
| Hard Violation | 修复 observation 指向的源码契约并重跑 | 仅因 Finding 消失就已修复 |
| Soft Friction | 保持语义的小幅整理或明确保留理由 | 它等同 Hard Violation |
| Review Required | 向 Owner 提交具体问题并等待 Authority 裁决 | 自行扩充词表或猜测语义 |
| Blocked family | 补足缺失 Authority/能力或缩小声明过的能力边界 | Incomplete 是 Clean |
| Rejected/Failed | 修复输入或执行故障后重新开始 | 存在有效源码结论 |

## 禁止的规避式修复

以下变化即使让 Finding 消失也一律判为无效：

- 把 Python docstring、Rust rustdoc 或 C/C++ 受控文档改成普通注释
- 删除、移动、改为动态生成或改名隐藏受审声明，而没有语义需求
- 给源码增加 `allow`、ignore、exclude 或条件编译来避开审查范围
- 把本次观察到的 token 自动加入 vocabulary 或移出 candidate registry
- 降低 grade、关闭 family、把 projection 改为 not applicable
- 修改测试期望去接受旧问题，或只运行不覆盖该声明的子集
- 将 Incomplete、Rejected、Failed 或未封存输出描述为通过

## 最小可靠闭环

1. 保存旧 Seal 和目标 Finding 身份
2. 确认声明仍属于 Direct Source 与同一 Documentation Owner
3. 进行最小语义修复；文档问题必须使用该语言认可的 carrier
4. 用同一 Authority 和范围、代表新源码字节的新 revision 重跑 CSU
5. 确认目标 Finding 消失，Completion 仍为 Complete，且没有新增 Finding 或 Blocked
6. 检查 read/sweep/parse 计数仍为每个文件各一次
7. 报告源码 diff、旧/新 revision 与 Seal，以及每个增减 Finding 的解释

如果第 5 步失败，AI 应回滚本轮思路并重新分析，不得通过扩大修改范围来掩盖新增
证据。

## Python docstring 专项检查

对函数、方法和 property，AI 必须同时回答：

- carrier 是否是 suite 第一条 triple-double-quoted string expression
- ordinary comment、赋值后的 string 或类级 docstring 是否被误当成方法 carrier
- public callable 是否完整提供 Args、Returns、Raises 且与直接签名一致
- internal callable 是否至少有非空中文摘要
- 关闭 Finding 后，原 callable 是否仍存在且仍被 Documentation family 计数

靶场校准见 `tests/fixtures/python_target_cases.json`。它包含普通注释替代 docstring、
类文档遮盖方法、乱码载体、延迟字符串与 public role 缺失等最小反例。
