# 07 — 让一个 brief 得到诚实答案

**What to build:** 提供一个 brief-first 的应用闭环，让调用者只提交 brief 与可用输入，系统便反复执行“compiler composes、runner gathers、Rust admits、compiler recompiles”，最终返回一个诚实的 waiting study 或 complete result，而不是要求调用者手工拼装生命周期。

**Blocked by:** 06 — 让 runner 只负责采集证据.

**Status:** wontfix

**Superseded by:** [Metalens Sonnet convergence](../../metalens-sonnet-convergence/spec.md).

- [x] 应用入口接受 brief，而不是 phase-specific workflow 或预先选定的 solver procedure。
- [x] 没有 ready task、缺少 advice、capability、binding、license 或 evidence 时返回结构化 waiting，不猜测、不降级到相邻方法。
- [x] proof 完整闭合时返回 result，并保留 brief、route、method、binding 与 evidence provenance。
- [x] propagation 与 PB 标准 brief 均通过同一入口工作。
- [x] standard briefs 位于小型 examples 输入中，不再由 compiler implementation 构造。
- [x] examples 只提交 brief 并检查 study 或 result，不再手工串联 consultation、admission、sweep、matching、field 与 conclusion。

## Verification

- `conduct(brief, available=...)` 是唯一新增应用入口；公开的 `AvailableScience` 只含事实，Authority、runner 与 route-owned interpreter 均留在私有应用边界之后。
- 缺少可用执行或 proof facts 时返回 immutable `Study`，保留 ready tasks 与 typed findings；无邻近方法回退。
- application loop 只接受 brief/proof 不变、完整 `EvidenceFact` 单调增加的新 Study；local Authority integration 覆盖 gather、receipt 与 recompile。
- complete proof 先由应用统一 admission brief、design 与 study closure，再由 route-owned interpreter 形成科学结论；结论必须通过具体 result type、closure、schema、provenance 校验与 Rust structured admission。
- propagation 与 PB 均以同一入口真实完成 8、12、16 三个独立 Study 的匹配、阵面、ASM 与 Result，不自动选择赢家。
- `metacraft_next.examples` 保存两个小型标准输入；`examples/conduct_briefs.py` 只提交 brief 并检查 Study。旧 live/evaluate 手工示例与 compatibility constructors 留给 Ticket 08 统一回收。
- 验收：定向边界 `36 passed`，真实 conduct 结论 `2 passed`，全量 `177 passed, 7 skipped`；Rust 树无差异，science import 不加载 native extension。
- 独立复审：Standards `PASS`；Spec `PASS`。
