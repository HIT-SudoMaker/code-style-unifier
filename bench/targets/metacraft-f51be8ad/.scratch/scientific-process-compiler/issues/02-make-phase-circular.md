# 02 — 让相位回到圆上

**What to build:** 为所有当前相位表达与匹配建立唯一的圆周语义，使 `0` 与 `2π` 等价，并让传播相位与 PB 相位共享确定、可复用的 canonical phase 与 cyclic distance。

**Blocked by:** None — can start immediately.

**Status:** wontfix

**Superseded by:** [Metalens Sonnet convergence](../../metalens-sonnet-convergence/spec.md).

- [x] 所有 canonical phase 都落在 `[0, 2π)`，包括负角度、整周角度与浮点边界。
- [x] 所有 phase matching 使用 cyclic distance，跨越 `0/2π` 分支时得到科学上正确的近邻。
- [x] tie-breaking 明确且确定，相同候选集合在不同输入顺序下产生相同选择。
- [x] propagation 与 geometric phase 使用同一套相位数学，但不因此混用两者的证据类型。
- [x] 分支切口、负角度、整周角度与等距候选均有高层行为测试。

## Verification

- 精确 Decimal 与浮点入口分别由 `canonical_phase` 和 `phase_from_float` 表达，不再猜测数值来源。
- 传播、PB、阵面量化与 Lumerical 观测共享 `science.phase`；传播与 PB 的 evidence 类型仍然分离。
- 相位定向测试 43 个通过；完整测试 155 个通过、7 个 live solver 测试按门控跳过。
- Standards review 与 Spec review 均为 PASS；Rust 工作树无差异。
