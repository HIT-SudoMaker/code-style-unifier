# 03 — 让未来目标通过同一种语言

**What to build:** 用非执行的 golden relationship fixtures 证明新的 claim–method 编译语言能够表达 large-NA metalens、holographic metasurface、quasi-BIC metasurface 与 frequency selective surface，而不会把当前 metalens 的 phase、aperture 或 focus 强加给所有目标。

**Blocked by:** 01 — 让 brief 编译为 study.

**Status:** wontfix

**Superseded by:** [Metalens Sonnet convergence](../../metalens-sonnet-convergence/spec.md).

- [x] large-NA fixture 保留 metalens focus objective，但以未实现的 qualified method need 替代低 NA scalar method。
- [x] holographic fixture 声明 reconstruction、fidelity、efficiency 与 crosstalk claims，不需要 focus claim。
- [x] quasi-BIC fixture 声明 resonance、Q、linewidth、symmetry、radiation-channel 与相应 evidence needs，不需要 phase、aperture 或 focus。
- [x] frequency-selective fixture 声明 reflection、transmission、absorption、bandwidth、angle 与 polarization claims，不需要 imaging。
- [x] fixtures 只验证编译语言和 honest waiting，不实现未来求解器、优化器或产品 Adapter。
- [x] 新增 aim 或 method 不需要新的 lifecycle、公开 registry、plugin、reflection 或 Rust 变更。

## Verification

- `compile_study → Study` 仍是唯一公共编译 seam；claim–method relationships 留在私有、显式、静态的 Python 声明中。
- large-NA 在 `NA = 1.00` 时仍诚实等待 qualified vector capability，且不继承 low-NA `CellPolicy`。
- holographic、quasi-BIC 与 frequency-selective fixtures 均只形成各自的 route、proof 与 findings；不生成 task。
- 完整测试：`160 passed, 7 skipped`。
- `compileall` 与 `git diff --check` 通过；Rust 树无差异。
- 双轴审查：Standards PASS；Spec PASS。
