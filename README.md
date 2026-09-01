# CSU

High-performance semantic code style unification across Python, Rust, C, and
C++ for next-generation scientific software engineering.

Review source once. Return one sealed answer.

CSU is a stateless semantic source reviewer for Python, Rust, C, and C++. It
compiles a project-owned Authority, observes a frozen source scope, and returns
one deterministic terminal. Target code remains read-only during review.

## Why CSU exists

Formatters make code look consistent. Compilers prove syntax and type facts.
Linters catch common local mistakes. None of them can prove that a Python
comment is a real docstring, that a physical symbol carries its declared
meaning, or that four languages express the same project rule through their
native source forms.

Those gaps are easy for generated code to exploit accidentally. A Finding can
disappear because a declaration was renamed, documentation was changed into an
ordinary comment, or an unsupported file was silently skipped. The report gets
greener while the source gets less trustworthy.

CSU closes that gap with explicit source evidence. Missing evidence remains
Incomplete. A review is Clean only when the scope is complete, every required
fact family is closed, and no Finding remains.

## The CLI and the skill

CSU ships one reviewer and one agent skill:

| Entry | Use it when | Produces | Target code |
|---|---|---|---|
| `csu review` | Scripts, CI, and direct terminal use | Human text or schema-versioned JSON | `READ_ONLY` |
| `$csu-review` | An agent should run CSU, preserve evidence, and explain the terminal | One captured JSON projection and a chat summary | `READ_ONLY` unless repair is explicitly requested |

The skill is CSU's own orchestration layer. It does not replace the executable
or invent judgments outside the returned terminal.

## Four languages, one review model

The rule families remain parallel while each language keeps its native carrier:

| Meaning | Python | Rust | C | C++ |
|---|---|---|---|---|
| Callable documentation | Suite-first docstring | Attached outer rustdoc | Controlled adjacent block | Controlled adjacent block |
| Public contract | Args, Returns, Raises | Arguments, Returns, Errors | Parameters, return, errors | Parameters, return, errors |
| Dependency declaration | `import` | `use` | `#include` | `#include` |
| Identifier semantics | Shared role prefixes and representation suffixes through the Python profile | Shared semantics through the Rust profile | Shared semantics through the C profile | Shared semantics through the C++ profile |

The normative rules live in [Coding Standards](docs/coding_standards.md). This
table is orientation, not a second rule source.

## Installation

### Prebuilt packages

Every version tag is built on its native GitHub runner and published on the
[Releases](https://github.com/HIT-SudoMaker/code-style-unifier/releases) page:

| Platform | Architecture | Asset |
|---|---|---|
| Windows | x86-64 | `csu-<version>-windows-x86_64.zip` |
| Linux | x86-64 | `csu-<version>-linux-x86_64.tar.gz` |
| Linux | ARM64 | `csu-<version>-linux-aarch64.tar.gz` |
| macOS | Intel | `csu-<version>-macos-x86_64.tar.gz` |
| macOS | Apple Silicon | `csu-<version>-macos-aarch64.tar.gz` |

Each release also publishes `checksums.txt`.

### Build from source

```bash
git clone https://github.com/HIT-SudoMaker/code-style-unifier.git
cd code-style-unifier
cargo install --path . --locked
```

### Install the agent skill

```bash
npx skills@latest add HIT-SudoMaker/code-style-unifier \
  --skill csu-review \
  --agent codex \
  --agent claude-code \
  --yes
```

The repository includes matching `.agents/skills/csu-review` and
`.claude/skills/csu-review` layouts, so either agent can discover the same
review contract immediately after installation. The Codex copy is canonical;
tests require the Claude projection to remain byte-identical.

## Authority before review

An Authority is the project-owned executable mapping from coding standards to
a concrete source scope. It declares enabled families, language profiles,
public callables, identifier vocabulary, header ownership, Rules, grades, and
presentation order.

An external project may keep its Authority at:

```text
.csu/authority/authority.json
```

CSU has no universal fallback Authority. Its self Authority at
`docs/authority/csu-self/authority.json` belongs only to this repository. When
an external project has no Authority, `$csu-review` returns
`BLOCKED_MISSING_AUTHORITY` instead of borrowing another project's semantics.

## Use

With the skill:

```text
$csu-review Review src with the Authority at .csu/authority.
```

With the CLI:

```bash
csu review \
  --authority .csu/authority \
  --workspace src \
  --format human
```

Use `--format json` for automation. One invocation performs one review. Human
and JSON output are projections of the same terminal, not two reasons to scan
the workspace twice.

## Where results go

The executable writes the complete terminal projection to `stdout`, writes
projection failures to `stderr`, and creates no files. This keeps the Rust core
stateless and lets the caller own persistence.

The agent skill captures the JSON projection here:

```text
.csu/
├── authority/
│   └── authority.json              project input; may be versioned
└── runs/
    └── <UTC-run-id>/
        ├── CSU-REVIEW.json          authoritative terminal projection
        ├── CSU-STDERR.txt           only when stderr is non-empty
        └── CSU-STDOUT.txt           only when stdout is not valid JSON
```

`.csu/runs` is generated evidence, not a cache or runtime input. It is ignored
by this repository. The skill explains the terminal in chat; it does not write
a second Markdown interpretation.

## The terminal contract

| Exit | Terminal meaning |
|---:|---|
| 0 | `Sealed + Complete + Clean` |
| 1 | `Sealed + Complete + Findings` |
| 2 | `Incomplete`, `Rejected`, `Failed`, or projection output failure; read the terminal to distinguish them |

A sealed JSON result includes the frozen scope, Completion, Finding summary,
ordered Findings, blocked family evidence, metrics, presentation, and Seal.
Exit codes are transport signals and never replace those fields.

## How CSU works

```text
WorkspaceReviewer::compile(Authority)
    -> review(frozen scope)
    -> ReviewTerminal
```

- Each source file is read once.
- Byte and line observation handles tight lexical facts.
- At most one pinned Tree-sitter observation handles structural ownership.
- Both observations close inside one File Review lifecycle.
- Each fact family ends as `NotRequired`, `Complete(count)`, or
  `Blocked(reason)`.
- The compact ledger closes before the deterministic Seal is projected.

The product Rust source has a hard 20,000 physical LOC ceiling. Generation 0
uses no cache, incremental graph, or persisted runtime state.

## Evidence before repair

The agent skill keeps review read-only by default. When repair is explicitly
requested, it records the original Seal and Finding identity, makes the
smallest semantic source change, and starts a new review.

A real repair preserves the governed declaration and uses the language's real
carrier. Hiding the declaration, replacing documentation with an ordinary
comment, changing Authority to remove a Finding, or accepting Incomplete as
Clean does not close the evidence.

## Release contract

A tag is publishable only when `v<version>` exactly matches the Cargo package
version. The tag workflow runs the complete test suite on every native runner,
builds the release binary, creates the five platform archives, generates SHA-256
checksums, and publishes one GitHub Release at the next five-minute clock
boundary. A failed platform prevents the release job from running.

Release archives contain the executable, README, license, Coding Standards,
design rationale, AI review protocol, and both `csu-review` skill layouts.
Signing and macOS notarization are separate trust decisions and are not claimed
by unsigned archives.

## Trust and limits

- A Finding proves only the rule and observation it names.
- `ReviewRequired` asks for owner context; it is not permission to guess.
- Incomplete, Rejected, and Failed terminals are never Clean.
- CSU does not replace compilation, tests, architecture review, scientific
  validation, safety assessment, or domain expertise.

## Compatibility

The executable is released natively for Windows x86-64, Linux x86-64 and
ARM64, and macOS Intel and Apple Silicon. The portable skill uses shared
frontmatter and keeps Codex UI metadata in `agents/openai.yaml`; both committed
skill layouts carry the same runtime instructions.

Compatibility means the same review contract can be installed and invoked. It
does not claim identical agent prose, model behavior, operating-system path
rendering, or target compiler behavior.

## Development

```bash
cargo test --locked
cargo clippy --all-targets --all-features -- -D warnings
cargo fmt --all -- --check
```

- [Documentation map](docs/README.md)
- [Coding Standards](docs/coding_standards.md)
- [Design rationale](docs/design.md)
- [AI evidence-first review protocol](docs/AI-REVIEW-PROTOCOL.md)
- [Four-language fixtures and release evidence](docs/fixtures/core/README.md)
- [Primary sources](docs/sources.md)

`bench/targets` contains frozen real-project snapshots used for calibration and
performance evidence. They are not Clean example projects.

## Contributing

Change normative wording in the Coding Standards before changing Authority or
implementation. Include the Authority identity, source scope, Terminal, Seal,
and a minimal four-language reproducer when reporting semantic behavior.

Run the complete development commands and CSU self-review before proposing a
change. New source capabilities must preserve the single lifecycle, explicit
Completion, and the 20,000-line product ceiling.

## License

MIT
