use std::fs;

use tempfile::tempdir;
use unifier::core::evidence::{EvidenceStore, TextRole};
use unifier::core::frontend::extract_text_evidence;
use unifier::core::scanner::scan_workspace;

#[test]
fn extracts_line_comment_and_python_docstring_summary_facts() {
    let dir = tempdir().unwrap();
    let source = r#"
def public_api():
    """Return SSIM score."""
    # This comment needs review
    return 1
"#;
    fs::write(dir.path().join("module.py"), source).unwrap();
    let state = scan_workspace(dir.path(), &[]).unwrap();

    let store: EvidenceStore = extract_text_evidence(&state).unwrap();

    assert!(store.line_spans.iter().any(|line| line.visual_width > 0));
    assert!(store
        .comment_regions
        .iter()
        .any(|comment| comment.kind == "line_comment"));
    assert!(store
        .text_spans
        .iter()
        .any(|text| text.role == TextRole::DocSummary
            && text.normalized_text == "Return SSIM score."));
}

#[test]
fn escaped_triple_quotes_are_not_docstring_delimiters() {
    let dir = tempdir().unwrap();
    let source = r#"
def public_api():
    \"\"\"Return SSIM score.\"\"\"
    return 1
"#;
    fs::write(dir.path().join("module.py"), source).unwrap();
    let state = scan_workspace(dir.path(), &[]).unwrap();

    let store: EvidenceStore = extract_text_evidence(&state).unwrap();

    assert!(!store
        .text_spans
        .iter()
        .any(|text| text.role == TextRole::DocSummary));
}

#[test]
fn extracts_docstring_when_file_starts_with_utf8_bom() {
    let dir = tempdir().unwrap();
    let mut source = vec![0xEF, 0xBB, 0xBF];
    source.extend_from_slice(b"def public_api():\n    \"\"\"Return result.\"\"\"\n");
    fs::write(dir.path().join("module.py"), source).unwrap();
    let state = scan_workspace(dir.path(), &[]).unwrap();

    let store: EvidenceStore = extract_text_evidence(&state).unwrap();

    assert!(store
        .text_spans
        .iter()
        .any(|text| text.role == TextRole::DocSummary && text.normalized_text == "Return result."));
}

#[test]
fn skips_non_utf8_files_without_aborting_evidence_extraction() {
    let dir = tempdir().unwrap();
    fs::write(
        dir.path().join("latin1.py"),
        [
            0xFF_u8, b'\n', b'#', b' ', b'T', b'h', b'i', b's', b' ', b's', b'h', b'o', b'u', b'l',
            b'd', b' ', b'n', b'o', b't', b' ', b'b', b'e', b' ', b'd', b'e', b'c', b'o', b'd',
            b'e', b'd', b'\n',
        ],
    )
    .unwrap();
    fs::write(
        dir.path().join("module.py"),
        "def public_api():\n    \"\"\"Return result.\"\"\"\n",
    )
    .unwrap();
    let state = scan_workspace(dir.path(), &[]).unwrap();

    let store: EvidenceStore = extract_text_evidence(&state).unwrap();

    assert_eq!(store.file_units.len(), 2);
    assert!(store
        .text_spans
        .iter()
        .any(|text| text.role == TextRole::DocSummary && text.normalized_text == "Return result."));
    assert!(!store
        .text_spans
        .iter()
        .any(|text| text.normalized_text.contains("should not be decoded")));
}

#[test]
fn text_evidence_ids_stay_stable_when_earlier_file_changes() {
    let dir = tempdir().unwrap();
    fs::write(dir.path().join("a.py"), "def first():\n    return 1\n").unwrap();
    fs::write(
        dir.path().join("b.py"),
        "def second():\n    # stable comment\n    return 2\n",
    )
    .unwrap();

    let first_state = scan_workspace(dir.path(), &[]).unwrap();
    let first_store = extract_text_evidence(&first_state).unwrap();
    let first_comment = text_by_content(&first_store, "stable comment");

    fs::write(
        dir.path().join("a.py"),
        "# unrelated earlier comment\n\ndef first():\n    return 1\n",
    )
    .unwrap();

    let second_state = scan_workspace(dir.path(), &[]).unwrap();
    let second_store = extract_text_evidence(&second_state).unwrap();
    let second_comment = text_by_content(&second_store, "stable comment");

    assert_eq!(first_comment.file_id, second_comment.file_id);
    assert_eq!(first_comment.range, "2:7-2:21");
    assert_eq!(first_comment.id, second_comment.id);
    assert_eq!(
        first_comment.id,
        format!(
            "ev:{}:text:comment:2:7:{}",
            first_comment.file_id,
            short_hash("stable comment")
        )
    );
}

#[test]
fn comment_ranges_use_character_columns_and_original_source_span() {
    let dir = tempdir().unwrap();
    fs::write(dir.path().join("module.py"), "def run():\n    # 中文注释\n").unwrap();
    let state = scan_workspace(dir.path(), &[]).unwrap();

    let store = extract_text_evidence(&state).unwrap();
    let comment = store
        .comment_regions
        .iter()
        .find(|comment| comment.kind == "line_comment")
        .unwrap();
    let text = store
        .text_spans
        .iter()
        .find(|text| text.id == comment.text_id)
        .unwrap();

    assert_eq!(comment.file_id, text.file_id);
    assert_eq!(comment.range, "2:5-2:11");
    assert_eq!(text.range, "2:7-2:11");
    assert_eq!(text.normalized_text, "中文注释");
    assert_eq!(
        comment.id,
        format!(
            "ev:{}:comment:line_comment:2:5:{}",
            comment.file_id,
            short_hash("中文注释")
        )
    );
}

#[test]
fn ignores_comment_markers_inside_python_triple_quoted_strings() {
    let dir = tempdir().unwrap();
    let source = r#"
def run():
    """
    # not a comment
    // also not a comment
    """
    # real comment
"#;
    fs::write(dir.path().join("module.py"), source).unwrap();
    let state = scan_workspace(dir.path(), &[]).unwrap();

    let store = extract_text_evidence(&state).unwrap();
    let comments: Vec<_> = store
        .text_spans
        .iter()
        .filter(|text| text.role == TextRole::Comment)
        .map(|text| text.normalized_text.as_str())
        .collect();

    assert_eq!(comments, vec!["real comment"]);
}

#[test]
fn ignores_comment_markers_inside_assigned_python_triple_quoted_strings() {
    let dir = tempdir().unwrap();
    let source = r#"
def run():
    value = """
    # not a comment
    """
    other = r'''
    # also not a comment
    '''
    # real comment
"#;
    fs::write(dir.path().join("module.py"), source).unwrap();
    let state = scan_workspace(dir.path(), &[]).unwrap();

    let store = extract_text_evidence(&state).unwrap();
    let comments: Vec<_> = store
        .text_spans
        .iter()
        .filter(|text| text.role == TextRole::Comment)
        .map(|text| text.normalized_text.as_str())
        .collect();

    assert_eq!(comments, vec!["real comment"]);
}

#[test]
fn preserves_real_comments_that_mention_triple_quotes() {
    let dir = tempdir().unwrap();
    let source = r#"
def run():
    # mention """ here
    # still a comment
"#;
    fs::write(dir.path().join("module.py"), source).unwrap();
    let state = scan_workspace(dir.path(), &[]).unwrap();

    let store = extract_text_evidence(&state).unwrap();
    let comments: Vec<_> = store
        .text_spans
        .iter()
        .filter(|text| text.role == TextRole::Comment)
        .map(|text| text.normalized_text.as_str())
        .collect();

    assert_eq!(comments, vec!["mention \"\"\" here", "still a comment"]);
}

#[test]
fn preserves_comments_after_triple_quote_text_inside_single_quoted_string() {
    let dir = tempdir().unwrap();
    let source = r#"
def run():
    marker = '"""'
    # real comment
"#;
    fs::write(dir.path().join("module.py"), source).unwrap();
    let state = scan_workspace(dir.path(), &[]).unwrap();

    let store = extract_text_evidence(&state).unwrap();
    let comments: Vec<_> = store
        .text_spans
        .iter()
        .filter(|text| text.role == TextRole::Comment)
        .map(|text| text.normalized_text.as_str())
        .collect();

    assert_eq!(comments, vec!["real comment"]);
}

#[test]
fn extracts_async_class_prefixed_and_multiline_docstring_summaries() {
    let dir = tempdir().unwrap();
    let source = r#"
async def fetch():
    r"""Fetch result."""
    return 1

class Runner:
    R'''Run jobs.

    Ignore details.
    '''
"#;
    fs::write(dir.path().join("module.py"), source).unwrap();
    let state = scan_workspace(dir.path(), &[]).unwrap();

    let store = extract_text_evidence(&state).unwrap();
    let summaries: Vec<_> = store
        .text_spans
        .iter()
        .filter(|text| text.role == TextRole::DocSummary)
        .map(|text| (text.normalized_text.as_str(), text.range.as_str()))
        .collect();
    let docs: Vec<_> = store
        .doc_regions
        .iter()
        .map(|doc| (doc.symbol_name.as_str(), doc.range.as_str()))
        .collect();

    assert_eq!(
        summaries,
        vec![("Fetch result.", "3:9-3:22"), ("Run jobs.", "7:9-7:18")]
    );
    assert_eq!(docs, vec![("fetch", "3:5-3:25"), ("Runner", "7:5-10:8")]);
}

fn text_by_content<'a>(
    store: &'a EvidenceStore,
    normalized_text: &str,
) -> &'a unifier::core::evidence::TextSpanFact {
    store
        .text_spans
        .iter()
        .find(|text| text.normalized_text == normalized_text)
        .unwrap()
}

fn short_hash(text: &str) -> String {
    blake3::hash(text.as_bytes()).to_hex()[..12].to_string()
}
