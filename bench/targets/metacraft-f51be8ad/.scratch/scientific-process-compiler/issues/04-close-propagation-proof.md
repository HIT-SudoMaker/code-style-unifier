# 04 — 让传播相位闭合为 result

**What to build:** 让低 NA propagation-phase metalens 的现有成功科学能力通过新的 study proof 完整闭合：一个被采纳的高度建议、一个 fixed-height complex transmission library、独立的 8/12/16 phase sets、realized aperture、`0.8f–1.2f` scalar ASM evaluation 与可加工的 result。

**Blocked by:** 01 — 让 brief 编译为 study; 02 — 让相位回到圆上; 03 — 让未来目标通过同一种语言.

**Status:** wontfix

**Superseded by:** [Metalens Sonnet convergence](../../metalens-sonnet-convergence/spec.md).

- [x] adviser 只推荐一个待采用高度；编译器记录并验证该 advice，不生成无条件 height-by-geometry Cartesian survey。
- [x] exact-compatible 的既有 height、cell-library、phase-set、aperture 与 field evidence 能关闭新 proof 中对应的 claims。
- [x] 8、12、16 state phase sets 保持三个独立结果，使用 cyclic distance、明确 loss 与 deterministic tie-break。
- [x] aperture 使用 selected cells 的 realized complex response，而不是 ideal phase mask。
- [x] field evaluation 覆盖 `0.8f–1.2f`，返回焦点、x/y FWHM、depth、transmission ratio 与 concentration ratio。
- [x] result 保留 cell identity、shape、dimensions、materials、height、state table、aperture labels 与完整 provenance。
- [x] propagation evidence 不能关闭 geometric claims。

## Verification

- 传播 tracer 通过公开的 `conclude_propagation` seam 闭合，不依赖内部 conclusion 导入。
- 8、12、16 三个 `PhaseSet`、`Study` 与 result 保持独立；没有自动选择赢家。
- result 验收覆盖 realized complex field、`0.8f–1.2f`、x/y FWHM、depth、transmission、concentration、fabrication cells 与 fixed-height library provenance。
- 定向验收：传播 result `12 passed`；高度、相位集、跨 route 与架构边界 `38 passed`。
- 完整测试：`160 passed, 7 skipped`；live solver tests 保持显式门控。
- `compileall` 与 `git diff --check` 通过；Rust 树无差异。
- 双轴审查：Standards PASS；Spec PASS。
- ready-task evidence gathering 属于 Ticket 06；brief-first loop 属于 Ticket 07；旧 route conclusion 回收属于 Ticket 08，本 ticket 不越界实现。
