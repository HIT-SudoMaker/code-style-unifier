# CSU

**Review source contracts. Return evidence you can inspect.**

High-performance semantic code style unification across Python, Rust, C, and
C++ for next-generation scientific software engineering.

CSU is a read-only source reviewer written in Rust. It checks a captured source
scope against shared coding standards, uses project-owned facts where source
alone is insufficient, and returns a deterministic result. It does not execute
the target program or change its files.

## Why CSU exists

Consistent formatting does not guarantee consistent meaning. A short identifier
can hide an unresolved concept, a unit suffix can disagree with the project's
declared convention, and an ordinary comment can leave a public function without
a documentation contract.

CSU makes these source obligations inspectable:

- naming follows language-native forms, explicit concepts and declared suffixes;
- public interfaces carry documentation contracts; internal methods stay concise;
- documentation fields align, and ordinary comments do not replace native docs;
- trailing comments and direct dependencies follow defined, language-aware rules;
- missing project facts remain visible instead of becoming a silent pass.

The four languages share rule intent, not identical syntax. The
[Coding Standards](docs/coding_standards.md) own the precise requirements.

## The CLI and the skill

| Entry | Use it for | Produces | Target code during review |
|---|---|---|---|
| `csu review` | Source review with explicit scope and Authority | Human or JSON output on stdout | `READ_ONLY` |
| [csu-review](.agents/skills/csu-review/SKILL.md) | Agent-guided review and result interpretation | Captured evidence and a bounded next action | `READ_ONLY` |

The CLI owns source judgments. The skill owns invocation, evidence handling and
interpretation; it does not add rules. A review request authorizes neither source
repair nor Authority edits.

## Works alongside design and review

Different layers answer different questions:

| Layer | Owns |
|---|---|
| Design and code review | Software architecture and fidelity to the requested change |
| CSU | Observable source-standard conformance within its declared rule boundary |
| Scientific review | Scientific meaning, methods, claims and their supporting evidence |

Located evidence can inform another review; a pass in one layer cannot compensate
for missing evidence in another. No companion skill is required to run CSU.

## Installation

### Native CLI

Choose a native archive and `checksums.txt` from
[GitHub Releases](https://github.com/HIT-SudoMaker/code-style-unifier/releases).
Verify the archive and add its `bin` directory to PATH.

The release workflow targets Windows x86-64, Linux x86-64 and ARM64, and macOS
Intel and Apple Silicon. Use the documentation shipped with your chosen version.

To build from a source checkout with Rust:

```bash
git clone https://github.com/HIT-SudoMaker/code-style-unifier.git
cd code-style-unifier
cargo install --path . --locked
```

### Agent skill

Run this inside the project that should use CSU:

```bash
npx skills@latest add HIT-SudoMaker/code-style-unifier --skill csu-review --agent codex --agent claude-code --yes
```

Add `--global` for a user-wide installation. Prefer one installation scope to avoid
duplicate entries. The [skills installer](https://github.com/vercel-labs/skills)
installs the skill package, not the CSU executable.

## Use

Provide the target project's typed facts in `.csu/authority/authority.json`,
following the [Authority contract](docs/coding_standards.md#11-规则依据).
Pass the containing directory and the source scope to CSU:

```bash
csu review --authority .csu/authority --workspace src --format human
```

Use `--format json` for automation. The CLI writes its result to stdout and
creates no report files; projection errors may appear on stderr.

For an agent-guided review, invoke `$csu-review` in Codex or `/csu-review` in
Claude Code, followed by the same request:

```text
Review src with the Authority at .csu/authority. Keep source code unchanged.
```

You can also supply an existing result for interpretation without a new scan.
Missing inputs or execution capability produce a setup blocker, not an invented
source verdict. CSU's self-review Authority belongs to CSU, not to other projects.

## The CSU model

One lifecycle connects the three sources of authority:

1. **Standard Law** fixes rules, grades and language contracts in the binary.
2. **Project Facts** supply admitted, narrowly scoped knowledge from Authority.
3. **Source Facts** come from captured bytes, physical-line observation and native
   syntax structure.

Physical and structural observations share the captured source. There is no
persistent scan cache, target execution or second scan for another output format.
The result records what was checked, what was found and what could not be judged.

Authority registers facts, not exceptions. An exact vocabulary entry can close an
unknown-token question; it cannot exempt a Candidate spelling or an independently
proved hard violation. Facts cannot disable rule families, lower grades or invent
a custom dependency order. CSU constrains their effects; the Owner remains
responsible for the truth of business facts that source cannot establish.

## Evidence before confidence

| Exit | Meaning |
|---:|---|
| 0 | `Sealed + Complete + Clean` |
| 1 | `Sealed + Complete + Findings` |
| 2 | `Incomplete`, `Rejected`, `Failed`, or projection failure; inspect the result |

Only a complete sealed review with zero Hard Violation, zero Review Required and
zero Blocked families is Clean. Zero Findings alone is insufficient. A Seal binds
the review's semantic identity; it is not a certificate of scientific correctness.

The skill saves each new review under the **target project's** root:

```text
.csu/runs/<UTC-run-id>/
├── CSU-REVIEW.json
├── RUN.txt
├── CSU-STDERR.txt
└── CSU-STDOUT.txt
```

`CSU-REVIEW.json` preserves the valid terminal; `RUN.txt` records the executable,
inputs and exit code. Nonempty stderr is saved separately. Invalid, unsupported
or incomplete output goes to `CSU-STDOUT.txt` instead of being reconstructed as a
valid terminal. Existing runs are preserved; these files are evidence, not a cache.

## Trust and limits

- Treat an official release's executable, standards, skills and other shipped
  files as one unchanged deployment. Replace the release as a whole when upgrading;
  project adaptation belongs in separate typed Authority, not edited product files.
  Authorized source repairs and new evidence under the target project's `.csu/runs/`
  remain separate. This deployment convention does not change the license or add
  runtime tamper protection; archive checksums do not lock extracted files.
- CSU does not import, execute, compile or link target code. Invalid UTF-8 or
  syntax yields parseability evidence and blocks dependent structural judgments.
- Rules cover direct source, not expanded macros, preprocessing, alias resolution,
  dependency build graphs or the quality of scientific prose.
- Comments stay brief and local: one point per line, with essential constraints
  beside the code. Product capabilities belong here; extended technical reasoning
  belongs in design documents. These author requirements need human or agent review.
- Formatters, compilers, tests, code review and scientific validation remain
  complementary. Clean means conformance within the declared review boundary.
- Repair and registration require their own workflow. Replacing a docstring with
  a comment or changing Authority to hide a defect does not count as a repair.

## Compatibility

Authority input and JSON review output have independent schema-4 contracts;
schema 3 is rejected rather than silently reinterpreted.

The shared skill package is maintained under `.agents/skills/csu-review` and
mirrored byte for byte under `.claude/skills/csu-review`. Only
`agents/openai.yaml` is platform-specific UI metadata. Shared instructions do not
depend on a particular shell, tool name, subagent or companion skill.

Package checks enforce shared-file equality. Agent interpretation still depends
on the host, model, permissions and available evidence; compatibility does not
promise identical behavior across all configurations.

## Development

Run the local Rust checks before proposing a change:

```bash
cargo fmt --all -- --check
cargo clippy --locked --all-targets -- -D warnings
cargo test --locked
```

The tests include CSU reviewing its own product and test source, plus skill-package
consistency. Frozen-corpus, candidate identity and performance verification are
separate gates described in the [fixture guide](https://github.com/HIT-SudoMaker/code-style-unifier/blob/main/docs/fixtures/core/README.md);
a green unit suite alone does not establish release readiness.

## Documentation and contributions

Start with the [Coding Standards](docs/coding_standards.md), then the
[Design](docs/design.md). These are the two core documents: source requirements
and architectural reasoning. The [skill](.agents/skills/csu-review/SKILL.md) owns
agent workflows; the [fixture guide](https://github.com/HIT-SudoMaker/code-style-unifier/blob/main/docs/fixtures/core/README.md) in the source
repository owns verification procedures and receipt interpretation.

For a reproducible [issue](https://github.com/HIT-SudoMaker/code-style-unifier/issues),
include the CSU version, language, minimal source, relevant Authority facts and
observed result. Redact private material before sharing. Change rule meaning in
the standards first, then align implementation, tests and documentation.

## License

[MIT](LICENSE) © HIT-SudoMaker.
