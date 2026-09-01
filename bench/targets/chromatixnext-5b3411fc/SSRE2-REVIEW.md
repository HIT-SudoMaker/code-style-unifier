# ChromatixNext 扩展准备度 SSRE2 Review

> **Historical / superseded (2026-08-23):** 本文件是对未扩展封存基线的早期
> readiness review，不是当前 Scalar Multislice 方案的 admission verdict。
> 当前实施权威为 [SSRE2-DESIGN.md](SSRE2-DESIGN.md)、
> `.scratch/scalar-multislice-foundation/spec.md` 和活动 Tickets 01–08。

## 1. Disposition

**当前候选 `a8dc9855c372b173380981eec477f04a65b78f47` 不可封档。**

五个相互隔离的 dimension verdict 为：

| Dimension | Verdict | 决定性依据 |
| --- | --- | --- |
| Simple | `UNPROVEN` | 新四条 roadmap axis 尚无冻结 owner/deletion witness；另有四项当前 multi-owner debt |
| Sonnet | `UNPROVEN` | 当前语法基本忠实，但 DOE、volume、optimization 与 distributed grammar 尚未获授权 |
| Reliable | `FAIL` | `REL-1`：合法构造后原位污染为 NaN 的强 Physical Value 被成功发布 |
| Evidenced | `UNPROVEN` | 30-action universal evidence claim 无 exhaustive closure；r2 provenance 不属于 Git tree |
| Evolvable | `UNPROVEN` | DOE/unary Element seam 有正证据，但 thick-sample state、optimization boundary 与 parallel axis 未冻结 |

旧 r2 `SEAL WITH DEBT LIST` 对其当时冻结的修复链仍是可定位历史事实；本轮在更宽的
supported-domain replay boundary 上构造出了同域反例，因此它不能继续承担“当前候选可终封”的结论。
这不是把未来未实现能力误判为缺陷：四条新方向仍严格保持为 `UNKNOWN/UNPROVEN`，唯一
seal-blocking `FAIL` 来自当前已发布 Interface。

## 2. Frozen review input

- Target：`E:\Year2026_Project_ChromatixNext\code-ssre2-claude`
- Commit：`a8dc9855c372b173380981eec477f04a65b78f47`
- Tree：`7b65fa0a3943b8580341294cb009d1f102853c4c`
- Branch：`ssre2-admission-closure`
- Target-code effect：`READ_ONLY`
- Scope authority：[SSRE2-SCOPE.md](SSRE2-SCOPE.md)
- Python：`C:\Users\Administrator\miniforge3\envs\research_env\python.exe`
- Environment：Python 3.12.13，PyTorch 2.12.0+cu130，Windows 11，CUDA available，1 GPU

初次 inventory 使用了 ignore-aware file discovery，未显示 candidate 中被 Git 忽略的 `.scratch`
terminal artifacts。定位这些 artifacts 后，scope 被更正，五个独立审计全部基于同一更正后的冻结
输入重新开始；因此没有 dimension 使用旧 scope 形成 verdict。

## 3. What is already strong

### 3.1 Deep foundation modules

- `_role_contract.py` 是五种 Optical Role、callable shape、ports 与三种 Physical Value closure 的
  单一 runtime authority；Assembly 与 Workstation 消费它，而不是各写一套 role switch。
- `Assembly` 吸收 topology、typed connections、cycle detection、freeze、exposure 与 replay plan；
  删除它会把这些机制扩散到每个 branched caller。
- `Workstation` 吸收 device ownership、host/release、meta/real replay、memory admission、randomness 与
  run record；其异常/中断后的 re-entry 有可执行正证据。
- `field.py:_transform_field`、spatial sampling、medium wave number 与 phase factor 已有窄、可定位的
  numerical/derived-value owner。
- Wave 与 Ray 的关系是 faithful asymmetry，不是虚假的统一 Optical State；新增能力不应破坏这一点。

### 3.2 DOE/D2NN mechanical closure already exists

独立 probe 已闭合：

```text
PlaneWave
  -> OpticalPathModulation
  -> ScalarAngularSpectrum
  -> OpticalPathModulation
  -> ScalarAngularSpectrum
  -> IntensityDetection
  -> user-owned loss / backward / SGD
```

两个 phase-plane `Parameter` identity 均保持，梯度 finite/nonzero；Evidenced probe 的一次 SGD
把 objective 从 `-0.73494251988683135` 改善到 `-1.0968226072429297`。因此 continuous、ideal、
thin、polarization-neutral 的 DOE/D2NN **mechanical composability 已是 `OBSERVED`**。它不证明
DOE scientific correctness，也不等同于 material height、dispersion、quantization、minimum feature
或 fabrication uncertainty。

### 3.3 A narrow thick-sample seam is structurally plausible

一个 synthetic unary `Element[OpticalField -> OpticalField]` 无需修改 Assembly、Workstation 或
role contract，就能完成 `include -> connect -> expose -> freeze -> host -> run`。这说明第一版
scalar isotropic unidirectional multislice 可以被设计成一个拥有 internal material state 的 deep
Element，而不必先增加 public Volume Physical Value 或通用 Sample hierarchy。

该 probe 只证明结构接受性；recurrence、applicability、state shape、observable、误差预算与梯度
正确性仍依赖 Owner 对 thick-sample support domain 的冻结。

## 4. Dimension findings

### 4.1 Simple — `UNPROVEN`

Current positive：role/topology/runtime/numerical seams 通过 deletion test，当前也没有 speculative
optimizer/distributed abstraction。

Located debts：

- `SIM-1`：polarization eigenstate ellipticity bounds 在四个 Wave/Ray Element 中分别拥有。
- `SIM-2`：splitter transmissivity admission 与 `("transmitted", "reflected")` branch metadata 多写。
- `SIM-3`：production-module inventory 同时由 shared reader 与多个 raw `glob/rglob` traversal 拥有。
- `SIM-4`：accepted ADR closed set 有两个 byte-equivalent authoritative copies。

Verdict basis：manufacturing DOE、thick sample、shared optimization 与 multi-GPU 尚无冻结 owner 或
真实 caller，不能对 future architecture 做 deletion test；缺证据不升格为 `FAIL`。

### 4.2 Sonnet — `UNPROVEN`

Current positive：五种 role、三种 Physical Value、30 actions、Wave/Ray asymmetry 与
`construct -> freeze -> host -> replay -> publish` rhythm 可从代码重建。

Located debts：

- `SON-1`：三处 architecture policy 使用 shadow traversal；nested role subpackage 可获得较弱扫描。
- `SON-2`：cycles-only phase-call guard 只识别 bare `ast.Name`，alias/attribute spelling 可绕过。
- `SON-3`：`test_public_component_calls_return_only_physical_values` 宣称覆盖全部 role，却只构造 Wave
  path 并只承认 `OpticalField/Intensity`，漏掉当前公开 `RayBundle` grammar。

Main-session navigation 还确认了两个同类 truth defects：`CONTEXT.md:63-64` 的“current optical
results”也漏写 `RayBundle`；`Workstation.run` docstring 把 `root` 描述为“未托管模块树根”，而实现
在 replay 前调用 `_assert_hosted_root`。它们不改变独立 verdict，但应和 `SON-3` 一起纳入窄修复。

Verdict basis：新四条 axis 的 correspondence/grammar 未冻结；当前局部 vocabulary/enforcement debt
没有构成 supported-domain scientific runtime counterexample。

### 4.3 Reliable — `FAIL`

`REL-1` 是 Important / seal-blocking：

1. 公开 constructor 合法建立 `OpticalField`；
2. 其公开 Tensor payload 被原位写入 `NaN`；
3. 公开 `Workstation.cpu().host(...).run(...)` direct replay 接受该输入；
4. 返回成功的 `NamedOutputs + RunRecord`，且 output envelope 非 finite。

根因是 construction-time owner 检查了 finite invariants，而
`Workstation._assert_physical_value` 在 input、module result 与 final output beats 只复核 type、device、
dtype，没有让 Physical Value owner 重验当前 value invariants。主 session 独立复现：

```text
RUN_RETURNED=NamedOutputs
FINITE=False
RECORD_DEVICE=cpu
```

这不是 out-of-model objection：当前所谓 immutable Physical Value 的 Tensor payload 可被普通 PyTorch
原位更新；即便 Owner 宣称该更新非法，公开 replay boundary 也必须稳定拒绝，而不是成功发布。

Positive evidence 仍成立：213 个定向测试通过，CUDA seam 6/6；adapter crash、real calculation crash、
`KeyboardInterrupt` 后可 re-enter；两层 DOE parameter/gradient lifecycle 通过；D1/D5 当前行为正确但
regression pin debt 仍在。

### 4.4 Evidenced — `UNPROVEN`

- `EVI-1`：public surface exact-closes 30 actions，但 bounded evidence-independence inventory 只有 15 个
  owner paths，二者没有 canonical claim ID relation。项目声明 “every public Component requires four
  evidence layers”，却无法让新增 action 缺 evidence entry 时自动失败。
- `EVI-2`：r2 seal/manifest/gate/double-review artifacts 只存在于 Git-ignored `.scratch`；它们在本机
  可读，但不属于 frozen tree，清理后不能仅由 commit 恢复。

Positive evidence：79 个相关 tests 与 3 个 SAS independent-reference/sensitivity nodes 通过；DOE SGD
probe 关闭 mechanical loop。没有同维度 scientific counterexample，因此不能使用 `FAIL`。

### 4.5 Evolvable — `UNPROVEN`

- `EVO-1`：action/ADR/Example counts 与 inventories 在 active docs、package contracts 和 indexes 中
  literal duplication；传播有限可预测，属于 non-blocking debt。
- `EVO-2 depends on U3`：只有当 volume 成为 public Physical Value 时，closed union/check 才会跨
  `_role_contract`、`_assembly_replay`、`assembly` 与 `workstation` 形成真实 extension debt；若 volume
  是一个 deep Element 的 internal state，本项不触发。

Positive evidence：unary Element extension 不要求修改 execution spine；ideal thin DOE stack 不要求
project optimization framework。Verdict 仍为 `UNPROVEN`，因为 U3/U5/U6 会改变 type、module 与
lifecycle 的实际修改集。

## 5. Validated interactions

以下 grouping 只表达同 locus 或依赖关系，不合并、平均或重排独立 verdict：

1. `SIM-3 <-> SON-1 <-> r2 D2`：同一 production inventory/shadow traversal locus，已由具体文件
   与 nested-subpackage trigger 验证。
2. `SON-2 <-> r2 D2/D6`：phase-call vocabulary 与 import spelling closure 同 locus；应由现有
   test-owned import/symbol facts 修复，不能引入 production catalog。
3. `SON-3 <-> r2 D3`：公开 grammar/test wording 陈旧；`CONTEXT.md` 与 `Workstation.run` docstring
   是 main-session 找到的同类 truth repairs。
4. `SIM-4 <-> EVO-1 <-> EVI-2`：下一次 ADR/capability reopen 与 provenance 持久化会同时触发，
   但 accepted ADR set、public API expected contract 与 evidence bundle 必须保持不同 ownership。
5. `REL-1` 的 repair `reinforces Reliable`，但每-beat finite/invariant reduction 可能 `costs` runtime；
   必须同时量测 CPU/CUDA 同步成本。性能成本不能授权 silent nonfinite publication。
6. Ideal DOE Example `reinforces Simple/Sonnet/Evidenced/Evolvable`，且不触发 30-action reopen。
7. Thick-sample module shape `requires U3`；optimization extraction `requires U5 + two real callers`；
   distributed execution `requires U6 + native Linux 2+ GPU evidence`。

## 6. Advisory repair and expansion order

这是一条按后果与依赖排序的建议，不是未经 Owner 授权的 implementation plan：

1. **先保存证据。** 在任何 workspace cleanup 前，将 r2 的 snapshot IDs、commands、outputs、verdicts
   与 hashes 建成 managed read-only provenance bundle，或在 tree 中保存 immutable artifact URI + hash。
2. **NARROW RELIABILITY REOPEN。** 让 `OpticalField`、`Intensity`、`RayBundle` 各自拥有可重复调用、
   无复制的 runtime-state validator；由 Workstation 在 direct input、Assembly intermediate 与 final
   output publication beats 调用，并加入 poison/re-entry CPU/CUDA regressions 和成本量测。
3. **顺手关闭同-locus truth/enforcement debt。** 统一 test-owned inventory traversal；关闭 phasor
   alias/attribute/star spellings；修正 RayBundle 与 hosted-root 文案；pin D1/D5。
4. **先交付 ideal DOE/D2NN Example。** 复用现有 30 actions；冻结 analytic target、wrong-sign/
   wrong-wavelength counterfactual、finite-difference gradient 与 deterministic loss-decrease acceptance。
5. **再设计第一版 thick sample。** 推荐 scalar、isotropic、unidirectional multislice，作为一个
   internal-volume-state deep Element；证据至少含 zero-contrast reduction、uniform slab、明确的
   amplitude/intensity absorption law、slice-refinement convergence、independent solver 与 FD gradient。
6. **两个真实 optimization Examples 后再抽 support。** 只有 DOE 与 thick-sample workflow 显示真实
   重复 lifecycle，且 deletion test 成立，才从 Example-owned code 抽 reusable support；不要预先安装
   project optimizer/loss/history framework。
7. **多卡先选 parallel axis。** 最窄路径是 Workstation 外层 process-per-GPU independent experiments；
   data parallel、state sharding 与 distributed FFT 是不同 lifecycle，不能共用一个模糊 `multi_gpu=True`。
   任何同步多卡 claim 都需要 native Linux/NCCL 2+ GPU 的数值、failure/re-entry 与 scaling evidence。

## 7. Verification manifest

- 当前规划 worktree：authoritative CSU gate `0 findings`；required isort check passed；selected
  package/architecture tests `31 passed, 55 deselected`。
- Candidate targeted lifecycle/DOE/reliability suite：`213 passed`；isolated CUDA seam `6 passed`。
- Candidate Evidenced selection：`79 passed`；SAS independent reference/sensitivity `3 passed`。
- Candidate Simple selection：`21 passed`；OPM parameter/grad selection `1 passed, 52 deselected`。
- Executed DOE probes：two-plane output finite、Parameter identity preserved、both gradients finite/nonzero；
  user-owned SGD one-step objective improved。
- Executed Reliable counterexample：nonfinite Physical Value was published successfully。
- Limits：未重跑全量 3034 nodes；无 native Linux、2+ GPU 或 NCCL evidence；未证明 future thick-sample
  或 fabrication-aware DOE scientific correctness。

## 8. Formal review boundaries

- `ssre2-review`：本文件完成当前冻结 candidate 的五维审查与 synthesis。
- `code-review`：尚未启动，因为 skill contract 要求 Owner 给出 fixed point。候选可按完整
  `35573738405ecfc340bca65f4fa361c2c9934033...a8dc9855c372b173380981eec477f04a65b78f47`
  或 repair-only `a716530...a8dc985` 审查；推荐前者。
- `ssre2-design`：依 Grill/Wayfinder，厚样品 support domain、destination 与 product boundary 未决前
  不生成伪确定的 architecture。Owner 回答第一轮 frontier 后，再建立 Wayfinder map 与
  `SSRE2-DESIGN.md`。

## 9. Non-mutation statement

冻结 target 始终保持 commit/tree 不变，最终 tracked porcelain 为空。审查没有修改 candidate 的
source、tests、docs、configuration、scientific data 或 lock files；所有报告写入独立 planning worktree。
