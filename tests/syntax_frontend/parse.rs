use unifier::core::syntax::{parse_source, SyntaxLanguage};

#[test]
fn parses_python_rust_c_and_cpp_sources() {
    let cases = [
        (SyntaxLanguage::Python, "def run() -> int:\n    return 1\n"),
        (SyntaxLanguage::Rust, "pub fn run() -> i32 { 1 }\n"),
        (SyntaxLanguage::C, "int run(void) { return 1; }\n"),
        (
            SyntaxLanguage::Cpp,
            "class Runner { public: int run(); };\n",
        ),
    ];

    for (language, source) in cases {
        let parsed = parse_source(language, source).unwrap();
        assert!(!parsed.root_kind().is_empty());
        assert!(!parsed.has_error());
    }
}
