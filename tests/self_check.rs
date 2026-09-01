use csu::AuthorityInput;
use csu::Completion;
use csu::Disposition;
use csu::FindingGrade;
use csu::ReviewInput;
use csu::ReviewTerminal;
use csu::WorkspaceReviewer;
use std::fs;
use std::path::Path;

/// 验证指定 Rust 源码目录满足三零自检
fn review_three_zero(source: &Path) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let authority = root.join("docs/authority/csu-self");
    let reviewer =
        WorkspaceReviewer::compile(AuthorityInput::Directory(&authority))
            .expect("the reviewed CSU project Authority must compile");
    let terminal = reviewer.review(ReviewInput::Workspace(source));

    assert_eq!(terminal.disposition(), Disposition::Clean);
    let ReviewTerminal::Sealed(review) = terminal else {
        panic!("CSU self-check must produce a sealed terminal");
    };
    assert_eq!(review.completion(), Completion::Complete);
    for grade in [
        FindingGrade::HardViolation,
        FindingGrade::SoftFriction,
        FindingGrade::ReviewRequired,
    ] {
        assert_eq!(
            review
                .findings()
                .iter()
                .filter(|finding| finding.grade() == grade)
                .count(),
            0,
            "self-check must have zero {grade:?} findings"
        );
    }
    assert!(review.coverage().files().iter().all(|file| {
        file.required_mask() == file.executed_mask()
            && file.families().iter().all(|(_, state)| {
                !matches!(state, csu::FactFamilyState::Blocked(_))
            })
    }));
    let metrics = review.metrics();
    let files = review.coverage().files().len() as u64;
    assert_eq!(metrics.files_read, files);
    assert_eq!(metrics.byte_sweeps, files);
    assert_eq!(metrics.structural_parses, files);
}

/// 验证 CSU 三零自检场景
#[test]
fn product_source_has_complete_three_zero_self_check() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    review_three_zero(&root.join("src"));
}

/// 验证 CSU 三零自检场景
#[test]
fn test_source_has_complete_three_zero_self_check() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    review_three_zero(&root.join("tests"));
}

/// 验证发布文档一致使用产品身份
#[test]
fn review_documents_have_product_identity() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let first =
        fs::read(root.join(".agents/skills/csu-review/SKILL.md")).unwrap();
    let second =
        fs::read(root.join(".claude/skills/csu-review/SKILL.md")).unwrap();
    assert_eq!(first, second);
    let other_identity = ["ss", "re", "2"].concat();
    let entries = [
        root.join("README.md"),
        root.join("Cargo.toml"),
        root.join("docs"),
        root.join(".agents"),
        root.join(".claude"),
    ]
    .into_iter()
    .flat_map(walkdir::WalkDir::new)
    .filter_map(Result::ok)
    .filter(|entry| entry.file_type().is_file());

    for entry in entries {
        let content = fs::read_to_string(entry.path()).unwrap_or_default();
        assert!(!content.to_ascii_lowercase().contains(&other_identity));
    }
}
