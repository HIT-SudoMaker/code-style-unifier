# 01 — 让 brief 编译为 study

**What to build:** 让当前两种低 NA metalens brief 通过同一个纯编译接口得到确定、可解释的 immutable study。study 应声明 design、route、proof、ready tasks 与 waiting findings，但不得运行求解器或改变 authority；旧接口暂时保留，使迁移期间始终可用。

**Blocked by:** None — can start immediately.

**Status:** wontfix

**Superseded by:** [Metalens Sonnet convergence](../../metalens-sonnet-convergence/spec.md).

- [x] 一个小而稳定的公开编译接口接收 immutable brief、reviewable advice、admitted evidence 与 qualified capabilities，并返回 immutable study。
- [x] propagation phase 与 geometric phase brief 都由 claim–method 关系编译，不再由公开的 phase-specific workflow 决定结构。
- [x] 相同的精确输入始终生成相同的 canonical study，与无科学意义的输入排列顺序无关。
- [x] brief 的原始事实、aim-specific objectives 与诚实 omissions 被保留；advice 不能改写用户事实。
- [x] 缺少 advice、capability、binding 或 evidence 时返回 typed waiting findings；矛盾或破损的 proof 才产生 compilation error。
- [x] 现有默认测试保持通过，Rust source 与 authority protocol 不发生变化。
