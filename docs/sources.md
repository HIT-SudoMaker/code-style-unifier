# Primary Sources

These sources bound the Coding Standards and CSU implementation. Language
documents establish what source forms mean; project choices decide which of
those forms CSU governs. A project choice must not be presented as a language
requirement.

## Units and identifier representation

- [BIPM SI Brochure, 9th edition](https://www.bipm.org/en/publications/si-brochure/)
  defines SI quantity and unit notation. CSU uses an ASCII suffix registry as a
  project naming convention; the suffix does not prove dimensional correctness.
- [NIST SP 811](https://www.nist.gov/pml/special-publication-811) documents SI
  usage conventions. CSU does not perform unit conversion or value analysis.

## Python

- [Python lexical analysis](https://docs.python.org/3/reference/lexical_analysis.html#identifiers)
  defines identifier forms.
- [Python function definitions](https://docs.python.org/3/reference/compound_stmts.html#function-definitions)
  and [ast.get_docstring](https://docs.python.org/3/library/ast.html#ast.get_docstring)
  establish docstring placement and recognition.
- [PEP 8 naming](https://peps.python.org/pep-0008/#naming-conventions) and
  [imports](https://peps.python.org/pep-0008/#imports) provide style guidance.
- [PEP 257](https://peps.python.org/pep-0257/) provides docstring conventions.
- [Python import statements](https://docs.python.org/3/reference/simple_stmts.html#the-import-statement)
  and [typing.TYPE_CHECKING](https://docs.python.org/3/library/typing.html#typing.TYPE_CHECKING)
  define the direct dependency forms CSU observes.

## Rust

- [Rust identifiers](https://doc.rust-lang.org/reference/identifiers.html) and
  [comments](https://doc.rust-lang.org/reference/comments.html) define native
  source forms.
- [Rust Style Guide](https://doc.rust-lang.org/style-guide/) and
  [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/naming.html)
  provide naming and ordering guidance.
- [rustdoc documentation guidance](https://doc.rust-lang.org/rustdoc/how-to-write-documentation.html)
  defines the native public documentation form.
- [Rust use declarations](https://doc.rust-lang.org/reference/items/use-declarations.html)
  and [Rust import style](https://doc.rust-lang.org/stable/style-guide/items.html#imports-use-statements)
  bound dependency judgments.

## C and C++

- [WG14 N3220](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n3220.pdf)
  defines C identifiers, linkage, comments, and preprocessing behavior.
- [WG21 working draft](https://eel.is/c++draft/) defines C++ declarations,
  access, preprocessing, and modules.
- [C++ Core Guidelines: naming](https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#S-naming)
  provides non-normative naming guidance.

C and C++ standards do not define a documentation-comment attachment contract.
CSU therefore recognizes controlled documentation blocks only through explicit
project Authority and never treats physical adjacency alone as proof.

## Observation and determinism

- [Tree-sitter basic parsing](https://tree-sitter.github.io/tree-sitter/using-parsers/2-basic-parsing.html)
  defines the parse lifecycle.
- [Tree-sitter ERROR and MISSING nodes](https://tree-sitter.github.io/tree-sitter/using-parsers/queries/1-syntax.html#the-error-node)
  bound syntax-health evidence.
- [tree-sitter Rust Parser](https://docs.rs/tree-sitter/0.26.13/tree_sitter/struct.Parser.html)
  and [Node](https://docs.rs/tree-sitter/0.26.13/tree_sitter/struct.Node.html)
  bound parser ownership and node lifetimes.
- [Rust BTreeMap](https://doc.rust-lang.org/std/collections/struct.BTreeMap.html)
  and [HashMap](https://doc.rust-lang.org/std/collections/struct.HashMap.html)
  motivate explicit canonical ordering rather than runtime hash iteration.
- [SARIF 2.1.0, Appendix F](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html#appendix-F)
  describes deterministic result ordering for parallel analysis.

## Frozen workload

The release workload uses commit-pinned snapshots listed in
[`bench/targets/README.md`](../bench/targets/README.md). Their licenses remain
with each snapshot. The snapshots are evidence inputs, not normative examples
and not sources of CSU rule meaning.
