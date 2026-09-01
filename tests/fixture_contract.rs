use csu::AuthorityInput;
use csu::Completion;
use csu::Disposition;
use csu::DocumentSet;
use csu::FactFamily;
use csu::FactFamilyState;
use csu::FindingGrade;
use csu::ReviewInput;
use csu::ReviewTerminal;
use csu::SourceDocument;
use csu::WorkspaceReviewer;
use serde_json::Value;
use std::collections::BTreeSet;
use std::path::Path;

/// 返回事实族的规范 JSON 拼写
fn fact_family_name(family: FactFamily) -> &'static str {
    match family {
        FactFamily::Capture => "capture",
        FactFamily::PhysicalLines => "physical_lines",
        FactFamily::Structure => "structure",
        FactFamily::Identifier => "identifier",
        FactFamily::Documentation => "documentation",
        FactFamily::DependencyDeclaration => "dependency_declaration",
        FactFamily::DeclarationOrder => "declaration_order",
    }
}

/// 将 manifest completion 映射到公开终态
fn expected_completion(value: &str) -> Completion {
    match value {
        "complete" => Completion::Complete,
        "incomplete" => Completion::Incomplete,
        _ => panic!("unknown fixture completion: {value}"),
    }
}

/// 将 manifest disposition 映射到公开终态
fn expected_disposition(value: &str) -> Disposition {
    match value {
        "clean" => Disposition::Clean,
        "findings" => Disposition::Findings,
        "incomplete" => Disposition::Incomplete,
        _ => panic!("unknown fixture disposition: {value}"),
    }
}

/// 将 manifest grade 映射到公开 Finding 等级
fn expected_grade(value: &str) -> FindingGrade {
    match value {
        "hard_violation" => FindingGrade::HardViolation,
        "soft_friction" => FindingGrade::SoftFriction,
        "review_required" => FindingGrade::ReviewRequired,
        _ => panic!("unknown fixture grade: {value}"),
    }
}

/// 验证冻结 fixture 的每个 cell 都产生精确预期结果
#[test]
fn frozen_fixture_cells_execute_their_exact_oracles() {
    let repository = Path::new(env!("CARGO_MANIFEST_DIR"));
    let fixture_root = repository.join("docs/fixtures/core");
    let manifest: Value = serde_json::from_str(include_str!(
        "../docs/fixtures/core/fixture-manifest.json"
    ))
    .expect("fixture manifest must be valid JSON");
    let reviewer =
        WorkspaceReviewer::compile(AuthorityInput::Directory(&fixture_root))
            .expect("fixture Authority must compile");
    let contracts = manifest["scenario_contracts"]
        .as_object()
        .expect("scenario contracts must be an object");
    let manifest_documents = manifest["documents"]
        .as_array()
        .expect("fixture documents must be an array");

    for (scenario, contract) in contracts {
        let scenario_documents: Vec<_> = manifest_documents
            .iter()
            .filter(|document| document["scenario"].as_str() == Some(scenario))
            .collect();
        assert_eq!(scenario_documents.len(), 4, "{scenario} cell totality");
        let sources: Vec<_> = scenario_documents
            .iter()
            .map(|document| {
                let path = document["path"]
                    .as_str()
                    .expect("fixture path must be text");
                std::fs::read(fixture_root.join(path))
                    .expect("fixture source must be readable")
            })
            .collect();
        let documents: Vec<_> = scenario_documents
            .iter()
            .zip(&sources)
            .map(|(document, bytes)| SourceDocument {
                relative_path: document["path"]
                    .as_str()
                    .expect("fixture path must be text"),
                bytes,
            })
            .collect();
        let terminal = reviewer.review(ReviewInput::Documents(DocumentSet {
            revision: scenario,
            documents: &documents,
        }));
        assert_eq!(
            terminal.disposition(),
            expected_disposition(
                contract["disposition"]
                    .as_str()
                    .expect("fixture disposition must be text")
            ),
            "{scenario} disposition"
        );
        let ReviewTerminal::Sealed(review) = terminal else {
            panic!("{scenario} must produce a sealed terminal");
        };
        assert_eq!(
            review.completion(),
            expected_completion(
                contract["completion"]
                    .as_str()
                    .expect("fixture completion must be text")
            ),
            "{scenario} completion"
        );

        let expected_findings = contract["findings"]
            .as_array()
            .expect("fixture findings must be an array");
        let expected_blocked = contract["blocked_families"]
            .as_array()
            .expect("blocked families must be an array");
        assert_eq!(
            review.findings().len(),
            expected_findings.len() * scenario_documents.len(),
            "{scenario} finding total"
        );

        for document in &scenario_documents {
            let path = document["path"]
                .as_str()
                .expect("fixture path must be text");
            let language = document["language"]
                .as_str()
                .expect("fixture language must be text");
            let findings: Vec<_> = review
                .findings()
                .iter()
                .filter(|finding| finding.path() == path)
                .collect();
            assert_eq!(findings.len(), expected_findings.len(), "{path}");
            for expected in expected_findings {
                assert!(findings.iter().any(|finding| {
                    finding.rule()
                        == expected["rule"]
                            .as_str()
                            .expect("expected rule must be text")
                        && finding.grade()
                            == expected_grade(
                                expected["grade"]
                                    .as_str()
                                    .expect("expected grade must be text"),
                            )
                        && finding.subject()
                            == expected["subject"]
                                .as_str()
                                .expect("expected subject must be text")
                }));
            }

            let coverage = review
                .coverage()
                .files()
                .iter()
                .find(|coverage| coverage.path() == path)
                .expect("each fixture cell must have coverage");
            let actual_blocked: BTreeSet<_> = coverage
                .families()
                .iter()
                .filter_map(|(family, state)| {
                    matches!(state, FactFamilyState::Blocked(_))
                        .then_some(fact_family_name(*family))
                })
                .collect();
            let expected_blocked: BTreeSet<_> = expected_blocked
                .iter()
                .map(|family| {
                    family.as_str().expect("blocked family must be text")
                })
                .collect();
            assert_eq!(actual_blocked, expected_blocked, "{path}");

            if let Some(anchor) = contract["parse_anchors"].get(language) {
                let structure_reason = coverage
                    .families()
                    .iter()
                    .find_map(|(family, state)| {
                        if *family == FactFamily::Structure
                            && let FactFamilyState::Blocked(reason) = state
                        {
                            Some(reason)
                        } else {
                            None
                        }
                    })
                    .expect("parse anchor requires a Structure blocker");
                assert_eq!(
                    structure_reason,
                    anchor["reason"]
                        .as_str()
                        .expect("parse reason must be text"),
                    "{path}"
                );
            }
        }
        let metrics = review.metrics();
        assert_eq!(metrics.files_read, 4, "{scenario}");
        assert_eq!(metrics.byte_sweeps, 4, "{scenario}");
        assert_eq!(metrics.structural_parses, 4, "{scenario}");
    }
}
