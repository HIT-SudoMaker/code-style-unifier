use csu::AuthorityInput;
use csu::Completion;
use csu::Disposition;
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
    assert!(review.findings().is_empty());
    assert!(review.coverage().files().iter().all(|file| {
        file.families().len() == 6
            && file.families().iter().all(|(_, state)| {
                matches!(state, csu::FactFamilyState::Complete(_))
            })
    }));
    let metrics = review.metrics();
    let files = review.coverage().files().len() as u64;
    assert_eq!(metrics.files_read, files);
    assert_eq!(metrics.byte_sweeps, files);
    assert_eq!(metrics.structural_parses, files);
}

/// 验证产品源码通过完整三零自检
#[test]
fn product_source_has_complete_three_zero_self_check() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    review_three_zero(&root.join("src"));
}

/// 验证测试源码通过完整三零自检
#[test]
fn test_source_has_complete_three_zero_self_check() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    review_three_zero(&root.join("tests"));
}

/// 验证文档中的产品身份和两端技能包一致
#[test]
fn review_documents_have_product_identity() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    for (first, second) in [(".agents", ".claude"), (".claude", ".agents")] {
        let first = root.join(first).join("skills/csu-review");
        let second = root.join(second).join("skills/csu-review");
        let content = fs::read_to_string(first.join("SKILL.md")).unwrap();
        assert_eq!(content.lines().next(), Some("---"));
        assert!(
            content
                .lines()
                .skip(1)
                .take_while(|line| *line != "---")
                .any(|line| line == "name: csu-review")
        );
        for entry in walkdir::WalkDir::new(&first) {
            let entry = entry.unwrap();
            let path = entry.path().strip_prefix(&first).unwrap();
            if entry.file_type().is_file()
                && path != Path::new("agents/openai.yaml")
            {
                assert_eq!(
                    fs::read(entry.path()).unwrap(),
                    fs::read(second.join(path)).unwrap()
                );
            }
        }
    }
    let content = fs::read_to_string(root.join("README.md")).unwrap();
    assert_eq!(content.lines().next(), Some("# CSU"));
    assert_eq!(env!("CARGO_PKG_NAME"), "code-style-unifier");
}
