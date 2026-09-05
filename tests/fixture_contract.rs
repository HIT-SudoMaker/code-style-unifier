use csu::AuthorityInput;
use csu::DocumentSet;
use csu::FactFamily;
use csu::FactFamilyState;
use csu::ReviewInput;
use csu::ReviewTerminal;
use csu::SourceDocument;
use csu::WorkspaceReviewer;
use serde_json::Value;
use std::collections::BTreeSet;
use std::path::Path;

/// 读取靶场清单的必需文本字段
fn text<'value>(value: &'value Value, field: &str) -> &'value str {
    value[field].as_str().expect("fixture field must be text")
}

/// 验证每个冻结样例和语法损坏样例产生精确预期结果
#[test]
fn frozen_fixture_cells_and_syntax_damage_execute_exact_oracles() {
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
                std::fs::read(fixture_root.join(text(document, "path")))
                    .expect("fixture source must be readable")
            })
            .collect();
        let documents: Vec<_> = scenario_documents
            .iter()
            .zip(&sources)
            .map(|(document, bytes)| SourceDocument {
                relative_path: text(document, "path"),
                bytes,
            })
            .collect();
        let terminal = reviewer.review(ReviewInput::Documents(DocumentSet {
            revision: scenario,
            documents: &documents,
        }));
        assert_eq!(
            serde_json::to_value(terminal.disposition()).unwrap(),
            contract["disposition"],
            "{scenario} disposition"
        );
        let ReviewTerminal::Sealed(review) = terminal else {
            panic!("{scenario} must produce a sealed terminal");
        };
        assert_eq!(
            serde_json::to_value(review.completion()).unwrap(),
            contract["completion"],
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
            let path = text(document, "path");
            let language = text(document, "language");
            let findings: Vec<_> = review
                .findings()
                .iter()
                .filter(|finding| finding.path() == path)
                .collect();
            assert_eq!(findings.len(), expected_findings.len(), "{path}");
            for expected in expected_findings {
                assert!(findings.iter().any(|finding| {
                    finding.rule() == text(expected, "rule")
                        && serde_json::to_value(finding.grade()).unwrap()
                            == expected["grade"]
                        && finding.subject() == text(expected, "subject")
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
                .filter(|(_, state)| {
                    matches!(state, FactFamilyState::Blocked(_))
                })
                .map(|(family, _)| serde_json::to_string(family).unwrap())
                .collect();
            let expected_blocked: BTreeSet<_> =
                expected_blocked.iter().map(Value::to_string).collect();
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
                assert_eq!(structure_reason, text(anchor, "reason"), "{path}");
            }
        }
        let metrics = review.metrics();
        assert_eq!(metrics.files_read, 4, "{scenario}");
        assert_eq!(metrics.byte_sweeps, 4, "{scenario}");
        assert_eq!(metrics.structural_parses, 4, "{scenario}");
    }
}
