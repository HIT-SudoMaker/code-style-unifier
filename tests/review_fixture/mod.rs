use csu::AuthorityDocument;
use csu::AuthorityInput;
use csu::DocumentSet;
use csu::ReviewInput;
use csu::ReviewTerminal;
use csu::SourceDocument;
use csu::WorkspaceReviewer;

/// 将文本样例装配成一次内存审查
pub(crate) fn review_sources(
    reviewer: &WorkspaceReviewer,
    revision: &str,
    sources: &[(&str, &str)],
) -> ReviewTerminal {
    let documents: Vec<_> = sources
        .iter()
        .map(|(relative_path, source)| SourceDocument {
            relative_path,
            bytes: source.as_bytes(),
        })
        .collect();
    reviewer.review(ReviewInput::Documents(DocumentSet {
        revision,
        documents: &documents,
    }))
}

/// 编译指定 JSON 值
pub(crate) fn compile_value(
    authority: &serde_json::Value,
) -> Result<WorkspaceReviewer, csu::ReviewRejection> {
    let bytes = serde_json::to_vec(authority).unwrap();
    WorkspaceReviewer::compile(AuthorityInput::Documents(&[
        AuthorityDocument {
            relative_path: "authority.json",
            bytes: &bytes,
        },
    ]))
}
