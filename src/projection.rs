use crate::model::Completion;
use crate::model::Disposition;
use crate::model::FactFamily;
use crate::model::FactFamilyState;
use crate::model::Finding;
use crate::model::FindingGrade;
use crate::model::PresentationPlan;
use crate::model::ReviewMetrics;
use crate::model::ReviewTerminal;
use crate::model::ReviewedScope;
use crate::model::SealedReview;
use serde::Serialize;
use std::fmt::Write;
#[derive(Serialize)]
struct SealedProjection<'projection> {
    schema_version: u32,
    terminal: &'static str,
    disposition: Disposition,
    review: SealedBody<'projection>,
}
#[derive(Serialize)]
struct SealedBody<'projection> {
    scope: &'projection ReviewedScope,
    completion: Completion,
    finding_summary: FindingSummary,
    blocked_families: usize,
    findings: Vec<&'projection Finding>,
    blocked_family_details: Vec<BlockedFamilyDetail<'projection>>,
    metrics: ReviewMetrics,
    presentation: &'projection PresentationPlan,
    seal: &'projection str,
}
#[derive(Serialize)]
struct BlockedFamilyDetail<'projection> {
    file: &'projection str,
    family: FactFamily,
    reason: &'projection str,
}
#[derive(Default, Serialize)]
struct FindingSummary {
    total: usize,
    hard_violation: usize,
    soft_friction: usize,
    review_required: usize,
}
#[derive(Serialize)]
struct ErrorProjection<'projection> {
    schema_version: u32,
    terminal: &'static str,
    disposition: Disposition,
    error: ErrorBody<'projection>,
}
#[derive(Serialize)]
struct ErrorBody<'projection> {
    code: &'projection str,
    message: &'projection str,
}
/// 将审查终态投影为稳定 JSON
///
/// # Arguments
/// - terminal：待投影的唯一审查终态
/// # Returns
/// - 对外 JSON 字节
/// # Errors
/// - JSON 序列化失败时返回错误
pub fn project_javascript_object_notation(
    terminal: &ReviewTerminal,
) -> Result<Vec<u8>, serde_json::Error> {
    match terminal {
        ReviewTerminal::Sealed(review) => {
            let blocked_family_details = blocked_family_details(review);
            let finding_summary = summarize(review);
            serde_json::to_vec(&SealedProjection {
                schema_version: 2,
                terminal: "sealed",
                disposition: terminal.disposition(),
                review: SealedBody {
                    scope: review.scope(),
                    completion: review.completion(),
                    finding_summary,
                    blocked_families: blocked_family_details.len(),
                    findings: presentation_ordered_findings(review),
                    blocked_family_details,
                    metrics: review.metrics(),
                    presentation: &review.presentation,
                    seal: review.seal(),
                },
            })
        }
        ReviewTerminal::Rejected(rejection) => {
            serde_json::to_vec(&ErrorProjection {
                schema_version: 2,
                terminal: "rejected",
                disposition: Disposition::Rejected,
                error: ErrorBody {
                    code: rejection.code(),
                    message: rejection.message(),
                },
            })
        }
        ReviewTerminal::Failed(failure) => {
            serde_json::to_vec(&ErrorProjection {
                schema_version: 2,
                terminal: "failed",
                disposition: Disposition::Failed,
                error: ErrorBody {
                    code: failure.code(),
                    message: failure.message(),
                },
            })
        }
    }
}
/// 执行 `summarize` 内部逻辑
fn summarize(review: &SealedReview) -> FindingSummary {
    let mut summary = FindingSummary {
        total: review.findings().len(),
        ..FindingSummary::default()
    };
    for finding in review.findings() {
        match finding.grade() {
            FindingGrade::HardViolation => summary.hard_violation += 1,
            FindingGrade::SoftFriction => summary.soft_friction += 1,
            FindingGrade::ReviewRequired => summary.review_required += 1,
        }
    }
    summary
}
/// 返回不改变封存结果的认知顺序 Finding 引用
fn presentation_ordered_findings(review: &SealedReview) -> Vec<&Finding> {
    let mut findings: Vec<_> = review.findings().iter().collect();
    findings.sort_by_key(|finding| {
        (
            finding.grade(),
            presentation_entry(review, finding.rule()).0,
        )
    });
    findings
}
/// 返回规则在认知展示中的全序位置与章节
fn presentation_entry<'review>(
    review: &'review SealedReview,
    rule: &str,
) -> (usize, &'review str) {
    review
        .presentation
        .chapters
        .iter()
        .flat_map(|chapter| {
            chapter
                .rules
                .iter()
                .map(move |identity| (identity, chapter.chapter.as_str()))
        })
        .enumerate()
        .find(|(_, (identity, _))| identity.as_str() == rule)
        .map(|(rank, (_, chapter))| (rank, chapter))
        .expect("compiled presentation must contain every Finding Rule")
}
/// 从封存覆盖账本提取稳定排序的 Blocked family 证据
fn blocked_family_details(
    review: &SealedReview,
) -> Vec<BlockedFamilyDetail<'_>> {
    let mut details: Vec<_> = review
        .coverage()
        .files()
        .iter()
        .flat_map(|file| {
            file.families().iter().filter_map(move |(family, state)| {
                let FactFamilyState::Blocked(reason) = state else {
                    return None;
                };
                Some(BlockedFamilyDetail {
                    file: file.path(),
                    family: *family,
                    reason,
                })
            })
        })
        .collect();
    details.sort_by(|left, right| {
        (left.file, left.family).cmp(&(right.file, right.family))
    });
    details
}
/// 将审查终态投影为人类可读文本
///
/// # Arguments
/// - terminal：待投影的唯一审查终态
/// # Returns
/// - 人类可读终态文本
/// # Errors
/// - 无
pub fn project_human(terminal: &ReviewTerminal) -> String {
    match terminal {
        ReviewTerminal::Rejected(rejection) => format!(
            "Terminal: Rejected\nDisposition: Rejected\nError: {}: {}\n",
            rejection.code(),
            rejection.message()
        ),
        ReviewTerminal::Failed(failure) => format!(
            "Terminal: Failed\nDisposition: Failed\nError: {}: {}\n",
            failure.code(),
            failure.message()
        ),
        ReviewTerminal::Sealed(review) => {
            let blocked = blocked_family_details(review);
            let completion = match review.completion() {
                Completion::Complete => "Complete",
                Completion::Incomplete => "Incomplete",
            };
            let mut output = format!(
                concat!(
                    "Terminal: Sealed\n",
                    "Disposition: {:?}\n",
                    "Scope: {}\n",
                    "Completion: {}\n",
                    "Findings: {}\n",
                    "Blocked families: {}\n",
                    "Seal: {}\n"
                ),
                terminal.disposition(),
                scope_label(review.scope()),
                completion,
                review.findings().len(),
                blocked.len(),
                review.seal(),
            );
            if review.findings().is_empty() {
                output.push_str("Finding evidence: none\n");
            } else {
                output.push_str("Finding evidence:\n");
                let mut chapter = "";
                for finding in presentation_ordered_findings(review) {
                    let finding_chapter =
                        presentation_entry(review, finding.rule()).1;
                    if finding_chapter != chapter {
                        chapter = finding_chapter;
                        let _ = writeln!(output, "Chapter: {chapter}");
                    }
                    let _ = writeln!(
                        output,
                        "- [{:?}] {}:{}:{} {} ({})",
                        finding.grade(),
                        finding.path(),
                        finding.line(),
                        finding.column(),
                        finding.rule(),
                        finding.subject(),
                    );
                    let _ = writeln!(
                        output,
                        "  Observation: {}",
                        finding.observation()
                    );
                    let _ =
                        writeln!(output, "  Message: {}", finding.message());
                    if let Some(question) = finding.question() {
                        let _ = writeln!(output, "  Question: {question}");
                    }
                }
            }
            if blocked.is_empty() {
                output.push_str("Blocked family evidence: none\n");
            } else {
                output.push_str("Blocked family evidence:\n");
                for detail in blocked {
                    let _ = writeln!(
                        output,
                        "- {} {:?}: {}",
                        detail.file, detail.family, detail.reason,
                    );
                }
            }
            output
        }
    }
}
/// 执行 `scope_label` 内部逻辑
fn scope_label(scope: &ReviewedScope) -> String {
    match scope {
        ReviewedScope::Documents { revision, files } => {
            format!("documents:{revision} ({} files)", files.len())
        }
        ReviewedScope::Workspace { root, files } => {
            format!("workspace:{root} ({} files)", files.len())
        }
    }
}
