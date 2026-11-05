# CSU

Declare source contracts. Audit captured source.

CSU is a native reviewer and optional agent skill for Python, Rust, C and C++ source.
The reviewer turns one captured scope into a sealed CSU Terminal; the skill preserves
and interprets that result. Target source remains `READ_ONLY` during review.

## Why CSU exists

Scientific code needs names and interfaces that expose its intent. A short symbol
can hide an unresolved concept, a suffix can lose a declared representation, and a
public function can leave callers without a usable contract. Formatting alone does
not settle these questions.

CSU makes those source obligations explicit:

- names follow native declaration roles and project-recognized concepts;
- quantity names carry their registered representation suffixes;
- public interfaces document their parameters, returns and failures;
- ordinary comments follow fixed placement and prose rules;
- dependency declarations follow language-specific rules when their facts are available;
- unresolved facts remain questions or incomplete checks in the result.

The [coding standard](docs/coding_standards.md) defines the precise requirements.

## The reviewer and the skill

| Entry | Responsibility | Output | Target source |
|---|---|---|---|
| `csu review` | Apply fixed rules to one captured source scope | Human or JSON projection of the CSU Terminal | `READ_ONLY` |
| [`$csu-review`](.agents/skills/csu-review/SKILL.md) | Capture a run and interpret its evidence | Original result, provenance and next action | `READ_ONLY` |

```text
Authority + source -> native review -> CSU Terminal -> skill interpretation -> owner action
                      source judgment                  evidence handling
```

The reviewer owns source judgment; the skill owns invocation provenance, evidence
preservation and interpretation. Repair and Project Fact registration use the
[authorized workflow](.agents/skills/csu-review/references/remediation.md).

## Federates with design and review

CSU is a sibling lane, not a replacement workflow.

| Lane | Owns |
|---|---|
| Codebase design | Module depth, Interfaces, Seams, Leverage and Locality |
| Code review | Standards and Spec fidelity |
| [SSRE2](https://github.com/HIT-SudoMaker/ssre2-skills) | Scientific meaning, supported regimes, correspondence and challenging evidence |
| CSU | Fixed source-contract judgments over directly observed declarations |

After source identity and inspection coverage align, a Sibling Reference may carry
located facts across the federated seam. Judgments remain with their owner: CSU Clean
supplies no scientific proof, and an SSRE2 verdict supplies no CSU compliance result.

## Installation

### Native reviewer

Download your platform's archive and `checksums.txt` from
[GitHub Releases](https://github.com/HIT-SudoMaker/code-style-unifier/releases).
Verify the archive, extract it and add `bin` to PATH. To build from a source checkout:

```bash
cargo install --path . --locked
```

### Project skill

Run this inside the project that should use CSU:

```bash
npx skills@latest add HIT-SudoMaker/code-style-unifier --skill csu-review --agent codex --agent claude-code --yes
```

For a user-wide installation, add `--global`. Choose one installation scope to avoid
duplicate host entries. The installer supplies the skill; install the native reviewer
separately.

## Use

Prepare the project's Authority and select its source scope:

```bash
csu review --authority .csu/authority --workspace src --format human
```

Use `--format json` for automation. For an agent-guided run:

```text
$csu-review Review src using .csu/authority. Keep target source read-only.
```

In Claude Code, invoke `/csu-review`. A complete Authority example and scope-path
explanation are in the [usage guide](docs/usage.md). Existing results can also be
interpreted without rescanning their source.

## The CSU model

| Concept | Role |
|---|---|
| Standard Law | Fixes rules, grades, language requirements and completion conditions |
| Source Facts | Describe captured bytes, declarations and direct structural relationships |
| Project Facts | Supply typed, owner-confirmed knowledge within fixed effect limits |
| Coverage | Records what completed and what lacks the facts needed for judgment |
| Seal | Identifies the source scope and semantic evidence of a completed review run |
| CSU Terminal | Owns the sealed result, disposition, findings, blocked families and presentation |

The [design](docs/design.md) explains these boundaries; the
[technical reference](docs/technical.md) connects the model to the implementation.

## Evidence before confidence

| Exit | Result |
|---:|---|
| 0 | Sealed + Complete + Clean |
| 1 | Sealed + Complete + Findings |
| 2 | Incomplete, Rejected, Failed or projection failure |

Completion records judgment coverage; Disposition records the outcome. Clean requires
complete coverage, zero Findings and zero Blocked families. Incomplete coverage
preserves proved Findings and names the unavailable judgments.

## Trust and limits

- Review reads source without importing, executing, compiling or changing it.
- The rule boundary covers direct syntax; macro expansion, build graphs and dynamic
  alias resolution require capabilities CSU does not provide.
- Project owners remain responsible for business facts that source cannot establish.
- A Seal does not establish runtime behavior, scientific validity or prose quality.
- Official builds, project facts and repair records have separate identities; the
  [usage guide](docs/usage.md) explains deployment and evidence handling.

## Compatibility

Python, Rust, C and C++ share rule intent while retaining native declaration and
documentation forms. The shared skill supports Codex and Claude Code; host, model
and permissions can affect interpretation. Use the documents shipped with the chosen
CSU version. Input and output contracts are specified in the technical reference.

## Development

From the source checkout:

```bash
cargo fmt --all -- --check
cargo clippy --locked --all-targets -- -D warnings
cargo test --locked
```

Formatting, lint, tests, CSU self-review, parser admission, frozen-corpus measurement
and candidate binding establish different properties. None substitutes for another,
and none proves runtime behavior or scientific validity. Their release gates are in the
[verification guide](https://github.com/HIT-SudoMaker/code-style-unifier/blob/main/verification/README.md).

## Contributing

Use [GitHub Issues](https://github.com/HIT-SudoMaker/code-style-unifier/issues) for
reproducible failures. Include the version, language, minimal source, relevant facts
and observed result. Change rule meaning in the standard first, then align behavior
and evidence. The [documentation index](docs/README.md) identifies each document's role.

## License

[MIT](LICENSE) © HIT-SudoMaker.
