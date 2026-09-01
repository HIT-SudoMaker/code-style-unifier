# 09 — 封住科学编译边界

**What to build:** 对完成迁移的科学编译器进行最终边界硬化，使其在默认测试、架构约束、Rust 零改动、真实 Lumerical gate 与 Sonnet/CSU 命名检查下都保持清晰稳定。

**Blocked by:** 08 — 收回旧 route 编排.

**Status:** wontfix

**Superseded by:** [Metalens Sonnet convergence](../../metalens-sonnet-convergence/spec.md).

- [x] 完整默认测试与类型检查通过，pure compiler 是主要科学行为测试 seam。
- [x] architecture checks 证明 native import 仍只存在于 authority Adapter，scientific growth 未穿透 Rust boundary。
- [x] Rust source、native protocol、schema、public verbs 与 lifecycle meanings 相对冻结基线为零差异。
- [x] workstation、capacity、solver qualification 与 Adapter contracts 的既有测试保持通过。
- [x] Lumerical 25v2 live checks 只能显式开启，并单独报告 installation、license、material read-back、native construction 与 observation 结果。
- [x] offline fixture 不伪装成 live result，缺少 live 条件时明确返回未运行原因。
- [x] public names 使用自然名词与动词、成对意义和短 surface；不存在公开 DSL、registry、plugin、reflection 或 speculative framework。

## Verification

- Required research interpreter, `-m pyright`: `0 errors, 0 warnings`.
- Default suite: `194 passed, 12 deselected in 307.01s`. The ten
  `lumerical_live` checks and two complete integration checks do not enter the
  default run.
- Explicit live gate with both local flags disabled: `10 skipped`, with
  separate reasons for smoke and solve stages. The named tests report product
  25v2, license capacity, material read-back, propagation/geometric native
  construction, and native observation separately when enabled.
- Boundary/workstation/qualification/sweep gate: `54 passed, 10 skipped`
  before live tests were removed from the default marker; final focused
  architecture check: `10 passed`.
- Rust is compared against frozen commit
  `8b6a3f9589026d790a0f1cf0e4f35ddd6040503a`, including committed history,
  tracked bytes, and untracked worktree state. No Rust path differs.
- Offline execution provenance now accepts only a real boolean. A receipt
  containing textual `"false"` is rejected rather than becoming native.

## CSU review

The default CSU scan reports no remaining actionable hard rule. Its remaining
`112` blocking findings were classified rather than erased:

- `Core011` (`105`) is `NarrowRuleContract`: CSU treats private `_local`
  modules, nested functions, and names outside package `__all__` as public.
  The five genuine exported-member gaps were documented; architecture tests
  now require contract docs on the actual `field`, `local`, and `science`
  exports and their public members.
- `Core009` (`7`) is `NarrowRuleContract`: CSU classifies relative imports as
  `dep_unknown` and then reports their stable package ordering as invalid.

The real hard findings found during the scan—`Py001`, `Py005`, `Core012`, and
the standard-library `Core009` ordering case—were corrected in code. The
remaining `under_review` findings are preserved for human judgement rather
than treated as failures or optimized away.

The reviewed examples and their traceable rationale/actions live in
`csu-cases.jsonl`; `csu-calibration.json` records two accepted
`false_positive` / `narrow_rule_contract` calibration actions without using
finding count as an optimization goal.
