# CSU

**Name scientific intent. Verify source contracts.**

Semantic source review for next-generation scientific software engineering.

CSU pairs a native Rust reviewer with an agent skill for Python, Rust, C and C++.
The reviewer checks naming, documentation and dependency contracts against fixed
rules. The skill records the run, interprets located evidence and guides authorized
follow-up with the project owner.

The CLI returns a terminal result. The skill preserves each run under the target
project's `.csu/runs/`. Target source remains `READ_ONLY` during review.

## Why CSU exists

Scientific code needs names and interfaces that expose its intent. A short symbol
can hide an unresolved concept, a suffix can lose a declared representation, and a
public function can leave callers without a usable contract. Formatting alone does
not settle these questions.

CSU makes those source obligations explicit:

- names follow native declaration roles and project-recognized concepts;
- quantity names carry their registered representation suffixes;
- public interfaces document their parameters, returns and failures;
- comments and dependencies follow bounded, language-aware rules;
- unresolved facts remain questions or incomplete checks in the result.

The [coding standard](docs/coding_standards.md) defines the precise requirements.

## The CLI and the skill

| Entry | Responsibility | Output | Target source |
|---|---|---|---|
| `csu review` | Apply fixed rules to a captured source scope | Text or JSON on stdout | `READ_ONLY` |
| [`$csu-review`](.agents/skills/csu-review/SKILL.md) | Capture a run and interpret its evidence | Original result, provenance and next action | `READ_ONLY` |

```text
project facts + source -> CLI review -> captured evidence -> owner decision
                          judgment       interpretation      follow-up
```

The reviewer owns source judgments; the skill owns invocation and evidence handling.
A review can finish with findings. Repair and fact registration then follow their
own [authorized workflow](.agents/skills/csu-review/references/remediation.md).

## Works with software and scientific review

Scientific software needs several kinds of review, each with a distinct question:

| Layer | Question it owns |
|---|---|
| Codebase design | Does the software expose useful interfaces and localize change? |
| Code review | Does the change follow its standards and requested specification? |
| Scientific review | Do scientific design and implementation connect claims to adequate evidence? |
| CSU | Do observed source declarations satisfy their coding contracts? |

Use each result for the question its layer owns. A registered `distance_m` spelling
establishes a naming convention; the quantity's physical interpretation and the
method's validity need their own evidence. Located facts can inform another review,
while acceptance decisions remain separate.

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

Project facts can answer an unknown-token question or declare a public callable.
They cannot lower a grade, disable a rule or erase an independently proved violation.
The [design](docs/design.md) explains these choices; the
[technical reference](docs/technical.md) connects them to the implementation.

## Evidence before confidence

| Exit | Result |
|---:|---|
| 0 | Sealed, complete and clean |
| 1 | Sealed and complete, with hard violations or owner questions |
| 2 | Incomplete, rejected, failed, or unable to output the result |

A clean result requires zero hard violations, zero owner questions and zero blocked
families. Zero findings alone is insufficient. Incomplete coverage preserves the
findings already proved and explains which judgments remain unavailable.

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

The suite includes CSU reviewing its own product and test source. Candidate identity,
frozen-corpus measurement and release checks are separate gates in the
[verification guide](https://github.com/HIT-SudoMaker/code-style-unifier/blob/main/docs/fixtures/core/README.md).

## Contributing

Use [GitHub Issues](https://github.com/HIT-SudoMaker/code-style-unifier/issues) for
reproducible failures. Include the version, language, minimal source, relevant facts
and observed result. Change rule meaning in the standard first, then align behavior
and evidence. The [documentation index](docs/README.md) identifies each document's role.

## License

[MIT](LICENSE) © HIT-SudoMaker.
