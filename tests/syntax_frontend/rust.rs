use std::fs;

use tempfile::tempdir;
use unifier::core::evaluators::evaluate_all;
use unifier::core::evidence::{EvidenceStore, ExpressionKind, SymbolVisibility, TextRole};
use unifier::core::frontend::extract_text_evidence;
use unifier::core::profile::Profile;
use unifier::core::scanner::scan_workspace;

fn store_from_rust_source(source: &str) -> EvidenceStore {
    let dir = tempdir().unwrap();
    fs::write(dir.path().join("bench_list.rs"), source).unwrap();
    let state = scan_workspace(dir.path(), &[]).unwrap();
    extract_text_evidence(&state).unwrap()
}

#[test]
fn extracts_rust_public_unsafe_async_and_panic_facts() {
    let dir = tempdir().unwrap();
    fs::write(
        dir.path().join("lib.rs"),
        "#![feature(test)]\n\
#[cfg(feature = \"fast\")]\n\
pub mod prelude { pub use crate::run; }\n\
use std::{fs, thread};\n\
\n\
/// 运行任务\n\
pub async fn run(lock: std::sync::Mutex<i32>) {\n\
    let guard = lock.lock().unwrap();\n\
    thread::sleep(std::time::Duration::from_millis(1));\n\
    async_call().await;\n\
    drop(guard);\n\
}\n\
\n\
#[no_mangle]\n\
pub extern \"C\" fn run_ffi() -> i32 { 0 }\n\
pub fn reader() -> Box<dyn Read> { todo!() }\n\
unsafe fn raw() {}\n",
    )
    .unwrap();
    let state = scan_workspace(dir.path(), &[]).unwrap();
    let store = extract_text_evidence(&state).unwrap();

    assert!(store.symbols.iter().any(|symbol| symbol.name == "run"
        && symbol.visibility == SymbolVisibility::Public
        && symbol.is_async
        && symbol.doc_region_id.is_some()));
    assert!(store
        .public_surfaces
        .iter()
        .any(|surface| surface.symbol_name == "run" && surface.has_doc_region));
    assert!(store
        .symbols
        .iter()
        .any(|symbol| symbol.name == "raw" && symbol.is_unsafe));
    assert!(store.expressions.iter().any(|expr| {
        expr.kind == ExpressionKind::MacroInvocation && expr.callee.as_deref() == Some("feature")
    }));
    assert!(store.expressions.iter().any(|expr| {
        expr.kind == ExpressionKind::MacroInvocation && expr.callee.as_deref() == Some("cfg")
    }));
    assert!(store.symbols.iter().any(|symbol| symbol.name == "run_ffi"
        && symbol
            .type_text
            .as_deref()
            .is_some_and(|text| text.contains("extern C"))
        && symbol.attributes.contains(&"no_mangle".to_string())));
    assert!(store.symbols.iter().any(|symbol| symbol.name == "reader"
        && symbol
            .return_annotation
            .as_deref()
            .is_some_and(|text| text.contains("dyn Read"))));
    assert!(store
        .expressions
        .iter()
        .any(|expr| expr.kind == ExpressionKind::Panic && expr.text.contains("unwrap")));
    assert!(store
        .expressions
        .iter()
        .any(|expr| expr.kind == ExpressionKind::Await));
    assert!(store
        .expressions
        .iter()
        .any(|expr| expr.kind == ExpressionKind::Lock));
}

#[test]
fn rust_frontend_allows_reasoned_abi_naming_for_core014() {
    let cases = [
        (
            r#"
#[allow(non_snake_case, reason = "must be named `PyInit_<module>`")]
#[no_mangle]
pub unsafe extern "C" fn PyInit_sequential() -> *mut PyObject {
    core::ptr::null_mut()
}
"#,
            "extern C",
            "no_mangle",
        ),
        (
            r#"
#[allow(non_snake_case, reason = "must be named `PyInit_<module>`")]
#[unsafe(no_mangle)]
pub unsafe extern "C" fn PyInit_sequential() -> *mut PyObject {
    core::ptr::null_mut()
}
"#,
            "extern C",
            "unsafe(no_mangle)",
        ),
        (
            r#"
#[allow(non_snake_case, reason = "must be named `PyInit_<module>`")]
#[export_name = "PyInit_sequential"]
pub unsafe extern "system" fn PyInit_sequential() -> *mut PyObject {
    core::ptr::null_mut()
}
"#,
            "extern system",
            "export_name = \"PyInit_sequential\"",
        ),
    ];

    for (source, abi_fragment, export_attr) in cases {
        let store = store_from_rust_source(source);
        let symbol = store
            .symbols
            .iter()
            .find(|symbol| symbol.name == "PyInit_sequential")
            .expect("PyInit_sequential symbol should be extracted");

        assert!(symbol
            .type_text
            .as_deref()
            .is_some_and(|text| text.contains(abi_fragment)));
        assert!(symbol.attributes.contains(&export_attr.to_string()));
        assert!(symbol.attributes.contains(
            &"allow(non_snake_case, reason = \"must be named `PyInit_<module>`\")".to_string()
        ));

        let profile = Profile::from_toml_str(include_str!("../../profiles/default.toml")).unwrap();
        let issues = evaluate_all(&store, &profile);

        assert!(
            !issues.iter().any(|issue| issue.rule == "Core014"),
            "{export_attr} ABI evidence must prevent Core014"
        );
    }
}

#[test]
fn rust_module_paths_do_not_trigger_core008_dependency_grouping() {
    let dir = tempdir().unwrap();
    fs::write(
        dir.path().join("lib.rs"),
        "use anyhow::Result;\n\
use crate::core::issue::Issue;\n\
use super::frontend::extract_text_evidence;\n",
    )
    .unwrap();

    let state = scan_workspace(dir.path(), &[]).unwrap();
    let store = extract_text_evidence(&state).unwrap();
    let profile = Profile::from_toml_str(include_str!("../../profiles/default.toml")).unwrap();
    let issues = evaluate_all(&store, &profile);

    assert!(
        !issues
            .iter()
            .any(|issue| issue.rule == "Core008" && issue.path.as_deref() == Some("lib.rs")),
        "Rust crate/super module paths should not trigger Python-style dependency grouping"
    );
}

#[test]
fn rust_frontend_ignores_source_like_text_inside_multiline_strings() {
    let dir = tempdir().unwrap();
    fs::write(
        dir.path().join("lib.rs"),
        r#"
fn fixture_source() -> &'static str {
    "
pub mod prelude { pub use crate::run; }
use std::{fs, thread};
pub fn generated_fixture() {}
"
}
"#,
    )
    .unwrap();

    let state = scan_workspace(dir.path(), &[]).unwrap();
    let store = extract_text_evidence(&state).unwrap();

    assert!(!store
        .dependency_edges
        .iter()
        .any(|edge| matches!(edge.source.as_str(), "std" | "crate")));
    assert!(!store
        .symbols
        .iter()
        .any(|symbol| matches!(symbol.name.as_str(), "prelude" | "generated_fixture")));
}

#[test]
fn extracts_rust_ordinary_block_comments_without_reclassifying_doc_blocks() {
    let store = store_from_rust_source(
        r#"
/* csu:allow reason=test fixture */
/** Public API. */
pub fn render() -> &'static str { "ok" }
"#,
    );

    assert!(store
        .text_spans
        .iter()
        .any(|text| text.role == TextRole::Comment
            && text.normalized_text == "csu:allow reason=test fixture"));
    assert!(store.text_spans.iter().any(|text| {
        text.role == TextRole::DocSummary && text.normalized_text == "Public API."
    }));
}

#[test]
fn rust_panic_and_unsafe_facts_ignore_strings_comments_and_safe_fallbacks() {
    let dir = tempdir().unwrap();
    fs::write(
        dir.path().join("lib.rs"),
        "/// unsafe appears in documentation\n\
pub fn run(value: Option<i32>, result: Result<i32, String>) {\n\
    let text = \"panic! unsafe unwrap\";\n\
    let _ = value.unwrap_or_default();\n\
    let _ = result.unwrap_or(1);\n\
    let _ = value.unwrap();\n\
    unsafe { call(); }\n\
    panic!(\"boom\");\n\
}\n",
    )
    .unwrap();
    let state = scan_workspace(dir.path(), &[]).unwrap();
    let store = extract_text_evidence(&state).unwrap();
    let unsafe_blocks = store
        .block_regions
        .iter()
        .filter(|block| block.kind == "unsafe")
        .collect::<Vec<_>>();
    let panic_expressions = store
        .expressions
        .iter()
        .filter(|expr| expr.kind == ExpressionKind::Panic)
        .collect::<Vec<_>>();

    assert_eq!(unsafe_blocks.len(), 1);
    assert_eq!(panic_expressions.len(), 2);
    assert!(panic_expressions
        .iter()
        .any(|expr| expr.text.contains("value.unwrap()")));
    assert!(panic_expressions
        .iter()
        .any(|expr| expr.text.contains("panic!")));
    assert!(!panic_expressions
        .iter()
        .any(|expr| expr.text.contains("unwrap_or") || expr.text.contains("unsafe unwrap")));
}

#[test]
fn rust_safety_comment_binds_to_unsafe_block() {
    let dir = tempdir().unwrap();
    let file = dir.path().join("bench_list.rs");
    fs::write(
        &file,
        r#"
fn sum_items(list: &List) -> usize {
    let mut sum = 0;
    // SAFETY: `i` is always in bounds and a critical section is held
    sum += unsafe { list.get_item_unchecked(i) };
    sum
}
"#,
    )
    .unwrap();

    let state = scan_workspace(dir.path(), &[]).unwrap();
    let store = extract_text_evidence(&state).unwrap();

    let unsafe_block = store
        .block_regions
        .iter()
        .find(|block| block.kind == "unsafe")
        .expect("unsafe block extracted");
    let safety_comment = store
        .text_spans
        .iter()
        .find(|span| {
            span.role == TextRole::Comment
                && span.range.starts_with("4:")
                && span.normalized_text.starts_with("SAFETY:")
        })
        .expect("preceding SAFETY comment extracted");

    assert_eq!(
        unsafe_block.intent_comment_id.as_deref(),
        Some(safety_comment.id.as_str()),
        "SAFETY comment on the preceding line must bind to the unsafe block"
    );
}

#[test]
fn rust_non_leading_safety_markers_do_not_bind_to_unsafe_block() {
    for marker in [
        "UNSAFETY: this is not an adjacent safety intent marker",
        "TODO SAFETY: add a real rationale later",
    ] {
        let store = store_from_rust_source(&format!(
            r#"
fn sum_items(list: &List) -> usize {{
    // {marker}
    unsafe {{ list.get_item_unchecked(i) }}
}}
"#
        ));

        let unsafe_block = store
            .block_regions
            .iter()
            .find(|block| block.kind == "unsafe")
            .expect("unsafe block extracted");

        assert!(
            unsafe_block.intent_comment_id.is_none(),
            "{marker:?} must not bind to the unsafe block"
        );
    }
}

#[test]
fn rust_safety_comment_separated_by_blank_line_does_not_bind_to_unsafe_block() {
    let store = store_from_rust_source(
        r#"
fn sum_items(list: &List) -> usize {
    // SAFETY: `i` is always in bounds and a critical section is held

    unsafe { list.get_item_unchecked(i) }
}
"#,
    );

    let unsafe_block = store
        .block_regions
        .iter()
        .find(|block| block.kind == "unsafe")
        .expect("unsafe block extracted");

    assert!(
        unsafe_block.intent_comment_id.is_none(),
        "SAFETY comment separated by a blank line must not bind"
    );
}

#[test]
fn rust_safety_marker_variants_bind_to_unsafe_block() {
    for marker in [
        "Safety: `i` is always in bounds",
        "安全 `i` is always in bounds",
    ] {
        let store = store_from_rust_source(&format!(
            r#"
fn sum_items(list: &List) -> usize {{
    // {marker}
    unsafe {{ list.get_item_unchecked(i) }}
}}
"#
        ));

        let unsafe_block = store
            .block_regions
            .iter()
            .find(|block| block.kind == "unsafe")
            .expect("unsafe block extracted");

        assert!(
            unsafe_block.intent_comment_id.is_some(),
            "{marker:?} must bind to the unsafe block"
        );
    }
}
