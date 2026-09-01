# 06 — 让 runner 只负责采集证据

**What to build:** 让 route-neutral runner 在 Rust authority 管控下采集任意 ready task 的证据：等待共享 permit、调度 bounded work、验证 observation、提出 receipt 或 close、读取新的 authority view，并以 admitted evidence 重新编译 study。

**Blocked by:** 04 — 让传播相位闭合为 result; 05 — 让 PB 相位闭合为 result.

**Status:** wontfix

**Superseded by:** [Metalens Sonnet convergence](../../metalens-sonnet-convergence/spec.md).

- [x] runner 不按 aim、control strategy、phase route 或 solver product 分支。
- [x] task 只在 prerequisites closed 且 binding complete 时出现，并携带 exact inputs、expected evidence、references 与 capacity scope。
- [x] capability、method、realization、binding、capacity 与 permit 在类型和行为上保持不同含义。
- [x] fake/local integration 覆盖 permit acquisition、observation validation、receipt、close、authority refresh 与 recompilation。
- [x] crash recovery 依靠 authority replay 与 immutable study，不新增 Python task status、retry ledger 或 resume token。
- [x] 现有 workstation lane、NUMA、memory、license capacity 与 product Adapter 边界保持不变。

## Verification

- `EvidenceRunner.gather_study()` 只读取 immutable `ScientificTask`；传播相位与 PB tracer 通过同一调用，不存在 aim、route、control strategy 或 solver product 分支。
- permit 使用完整 task 的 canonical identity；expected schema、prerequisite references、binding reference 与 capacity scope 均来自 compiled task，绑定任务只由匹配 scope 的 runner 执行。
- typed observation 在 receipt 前通过 exact schema 与 method-supplied task contract 校验；replay 时再次执行同一 validator，admitted body reference 与 exact binding 才被恢复为 `EvidenceFact` 并交回纯 compiler 重编译。
- receipt 后 compiler 崩溃时，下一进程从 authority replay 恢复 evidence 而不重复 observation；replayed expired permit 以 `expired` close，非法 observation 以 `revoked` close。
- runner、standard Study 与两类 solver sweep 的定向验收通过；workstation、NUMA、memory、license capacity 与 Lumerical Adapter 未改动。
- Python 没有新增 task status、retry ledger、resume token 或 durable queue；Rust 树无差异。
- 完整测试：`168 passed, 7 skipped`；live solver tests 保持显式门控。
- 双轴审查：Standards PASS；Spec PASS。
