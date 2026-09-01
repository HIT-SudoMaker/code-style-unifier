# CSU command examples

## Check a project

```bash
csu check src --format json --output .csu/issues.json --no-history
```

## Check with a custom profile file

```bash
csu check src --profile-path profiles/default.toml --format jsonl --no-history
```

## Write scan history outside the source tree

```bash
csu check src --history-dir .csu/history --format json --output .csu/issues.json
csu history --history-dir .csu/history list
csu history --history-dir .csu/history prune
```

## Inspect rule contracts

```bash
csu rules --format json
csu rules --format toml
```

## Calibrate with reviewed cases

```bash
csu calibrate --issues .csu/issues.json --cases .csu/cases.jsonl --output .csu/calibration.json
```
