# 05 — 让 PB 相位闭合为 result

**What to build:** 让低 NA geometric-phase metalens 的现有成功科学能力通过新的 study proof 完整闭合：明确 polarization convention、一个 anisotropic cell、完整 Jones response、解析 orientation states、converted/retained apertures、`0.8f–1.2f` scalar ASM evaluation 与可加工的 result。

**Blocked by:** 01 — 让 brief 编译为 study; 02 — 让相位回到圆上; 03 — 让未来目标通过同一种语言.

**Status:** wontfix

**Superseded by:** [Metalens Sonnet convergence](../../metalens-sonnet-convergence/spec.md).

- [x] polarization handedness、basis、phase sign 与 channel order 被显式记录并参与 evidence matching。
- [x] x-input 与 y-input observations 在同一 permit 下顺序采集，一个 cell 只占用一个 bounded solver worker。
- [x] 一个合适的 anisotropic cell 在 orientation 前被选择；orientation states 由 qualified PB convention 解析导出，不生成 orientation-specific FDTD sweep。
- [x] converted 与 retained channels 从 aperture 到 field、focus 和 result 始终分离。
- [x] field evaluation 覆盖 `0.8f–1.2f`，并为两个 channel 返回明确、可追溯的指标。
- [x] result 保留 cell identity、shape、dimensions、materials、height、orientation table、aperture labels 与完整 provenance。
- [x] Jones/channel evidence 不能关闭 propagation claims。

## Verification

- `PolarizationConvention` 明示 linear/circular basis、converted/retained channel order 与由 handedness、rotation sign 决定的 `phase_sign`；solver projection、orientation derivation 与 exact evidence 使用同一 convention。
- x/y observations 仍在一个 permit 下顺序采集；orientation states 仍为纯解析生成，没有新增 solver task。
- converted channel 产生 bracketed focus；retained channel 在相同的 `0.8f–1.2f` 轴向采样上独立传播并报告 leakage scan，不借用 useful-focus 语义。
- 8、12、16 三个 phase sets、Studies 与 results 保持独立；result 保存 cell、materials、orientation table、aperture labels、convention、library 与完整 closure。
- Jones/channel evidence → propagation proof 的直接 cross-route 拒绝测试通过。
- 定向验收：PB/Jones/solver contracts `50 passed`；完整 geometric result `5 passed`。
- 完整测试：`160 passed, 7 skipped`；live solver tests 保持显式门控。
- Rust 树无差异；Ticket 06–08 的 runner、brief-first 与 route 回收职责未提前实现。
- 双轴审查：Standards PASS；Spec PASS。
