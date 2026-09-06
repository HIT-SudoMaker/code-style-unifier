# CSU 使用说明

本文面向使用 CLI 或 Agent 审查项目的读者。源码要求见[编码规范](coding_standards.md)，库调用及结果结构见[技术参考](technical.md)。

## 安装

CLI 和 skill 的安装及调用入口见 [README](../README.md#installation)。

按所用版本配套阅读文档。升级时整体替换官方构件；目标项目的源码、Authority 和审查记录独立保存。
项目适配由负责人维护 Authority，不通过编辑安装目录中的二进制、规范或 skill 改变规则。
产品源码开发按独立候选和版本审查处理，不将修改后的副本作为原官方版本使用。
这一部署约定不改变许可证；归档校验和用于核对下载文件，CLI 不逐文件验证解压后的安装目录。

## 完成第一次审查

下面是一个独立的教学项目：作者约定 `distance` 使用后缀 `m`，源码只有一个距离值。
它说明输入格式，不提供可直接套用到其他项目的业务事实。

```text
example/
├── .csu/authority/authority.json
└── src/distance.py
```

将以下内容保存为 `src/distance.py`：

```python
distance_m = 1
```

将作者确认的示例事实保存为 `.csu/authority/authority.json`：

```json
{
  "schema_version": 4,
  "public_callables": {},
  "token_vocabulary": ["distance"],
  "quantity_concepts": {"distance": ["m"]},
  "header_languages": {},
  "external_fixed_identifiers": [],
  "dependency_authority": null
}
```

在 `example` 目录运行：

```bash
csu review --authority .csu/authority --workspace src --format human
```

这个示例应得到完整、无问题的封存结果，退出码为 0。
真实项目的六类事实用途和影响限制见[编码规范 §1.1](coding_standards.md#11-规则依据)。缺失事实可能产生待确认或受阻状态；负责人应先回答相应问题，再开始新一轮审查。

## 选择 Authority 与范围

`--authority` 接收含 `authority.json` 的目录；`--workspace` 接收待审查的源码根目录。
CLI 路径相对当前工作目录解释，Authority 内的源码路径相对审查范围解释。
例如 `--workspace src` 下的 `src/api/velocity.h`，在 `header_languages` 或 `public_callables` 中写为 `api/velocity.h`。
改变范围后应重新核对这些路径；项目根目录和审查范围可以不同。

Authority 输入使用 schema 4；审查 JSON 也使用 schema 4，两者独立管理。schema 3 输入会被拒绝。
CSU 的 `docs/authority/csu-self` 只属于 CSU 自身，不是其他项目的默认配置。
输入文件的完整形状及接纳条件见[技术参考：输入合同](technical.md#输入合同)。

## 读取结果

| 退出码 | 结果 | 下一步 |
|---:|---|---|
| 0 | `Sealed + Complete + Clean` | 在当前规则和范围内通过；继续项目自己的构建、测试与其他审查 |
| 1 | `Sealed + Complete + Findings` | 按位置检查硬违规，并回答待确认问题中的负责人问题 |
| 2 | `Incomplete`、`Rejected`、`Failed`，或输出失败 | 先读受阻原因、错误字段和 stderr，确定缺少的事实或失败步骤 |

`Incomplete` 中已经证明的问题仍然有效；零问题不能代替完整性。
Seal 标识本次审查的语义证据，不证明运行时行为、架构质量或科学结论。

自动化使用 JSON 输出：

```bash
csu review --authority .csu/authority --workspace src --format json
```

CLI 只向 stdout 输出结果，不自动创建报告文件；输出错误可能写入 stderr。
自动化调用应分别保存完整 stdout、stderr 和退出码，校验终态与字段一致性，并同时检查完整性和问题数量。
不要把终端截断的 JSON 或退出码 2 单独解释为源码审查结论。字段说明见[技术参考：结果与身份](technical.md#结果与身份)。

## 通过 Agent 使用

安装后在 Codex 使用 `$csu-review`，在 Claude Code 使用 `/csu-review`，并给出范围和 Authority。

也可以提供已有结果，请 Agent 解读；历史记录只描述原来的输入。
缺少可执行文件、Authority、范围或完整输出时，先处理 setup/capture blocker，不生成推测的源码结论。

[CSU Review](../.agents/skills/csu-review/SKILL.md) 负责运行和解释，在目标项目 `.csu/runs/<UTC-run-id>/` 下保留原始结果及 `RUN.txt` 来源记录，保存非空 stderr，保留旧运行。
文件命名、捕获失败处理和结束条件由该 skill 统一维护。
审查保持源码只读；需要修复或登记事实时，按单独授权的[修复指引](../.agents/skills/csu-review/references/remediation.md)继续。
