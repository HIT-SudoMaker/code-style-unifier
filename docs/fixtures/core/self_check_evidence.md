# CSU 自检证据

记录时间：2026-09-01 Asia/Singapore

## 候选身份

- release binary SHA-256：
  `a5a873a0b4e0700956aeb3460d3f98cea2c39425270f9b9d6880870977979c0e`
- CSU 项目 Authority SHA-256：
  `dda01890494c8e13626642b1e96412730f5371fe5040becb1391c03ad8c932fc`
- 产品范围：`src/**/*.rs`，6 files
- 测试宿主范围：`tests/**/*.rs`，11 files
- 产品 Rust：7,114 physical LOC
- 测试 Rust：3,496 physical LOC

## 双三零终态

| 范围 | Terminal | Completion | Hard | Soft | Review Required | Blocked | read/sweep/parse | Seal |
|---|---|---|---:|---:|---:|---:|---|---|
| `src` | Sealed/Clean | Complete | 0 | 0 | 0 | 0 | 6/6/6 | `d6c980a002da98a06514c565568ca2095360f4bc6ad9e5846c96fe18751813b4` |
| `tests` | Sealed/Clean | Complete | 0 | 0 | 0 | 0 | 11/11/11 | `cff5d73f25deaf7cabffe6a130d9d85420cf10ee6000a6f2bfed178357727177` |

同一个 versioned Authority 对两个范围启用 Identifier、Documentation 与
Dependency 三族。测试用的故意坏源码是 `SourceDocument`/JSON fixture 数据；
维护中的 Rust 测试宿主自身没有 ignore、fallback 或测试专用产品分支。

## 复现命令

```powershell
target/release/csu.exe review `
  --authority docs/authority/csu-self `
  --workspace src `
  --format json

target/release/csu.exe review `
  --authority docs/authority/csu-self `
  --workspace tests `
  --format json
```

两条命令预期 exit code 均为 0。`tests/self_check.rs` 固定三个 Finding 等级为零、
Blocked 为零，并要求每文件一次 read/sweep/parse。
