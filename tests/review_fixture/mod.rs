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
