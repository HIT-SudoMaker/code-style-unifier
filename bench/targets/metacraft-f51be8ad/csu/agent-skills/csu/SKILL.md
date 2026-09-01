---
name: csu
description: Use when interpreting CSU JSON, triaging findings, writing calibration cases, or choosing code/profile/rule actions
---

# CSU Agent Skill

## Use When

Use this skill for CSU JSON output, self-check cleanup, profile decisions, and calibration cases.

## Commands

```powershell
csu check <path> --format json --output <file> --no-history
csu calibrate --issues <issues.json> --cases <cases.jsonl> --output <report.json>
csu rules --format json
```

## Decision Rules

- Do not optimize for findings count
- `hard_violation`: fix code, profile, or rule boundary before passing
- `soft_friction`: explain the tradeoff and keep it non-blocking unless a profile says otherwise
- `under_review`: inspect evidence and choose whether to keep, clean up code, or write a calibration case
- Framework overrides and ABI names are profile policy, not default rule relaxation
- If evidence points to strings or the wrong span, write `NarrowRuleContract`
- If a real issue is missed, write `BroadenRuleContract`

## Output Format

```text
classification: CodeCleanup | NarrowRuleContract | BroadenRuleContract | AddProfilePolicy | KeepUnderReview
rationale: <one sentence grounded in evidence, rule, kind, range, or profile>
next_action: <specific file, profile, or calibration fixture>
```
