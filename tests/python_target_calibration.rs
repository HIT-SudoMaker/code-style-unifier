use csu::AuthorityInput;
use csu::Completion;
use csu::DocumentSet;
use csu::FactFamilyState;
use csu::FindingGrade;
use csu::ReviewInput;
use csu::ReviewTerminal;
use csu::SourceDocument;
use csu::WorkspaceReviewer;
use serde_json::Value;
use std::path::Path;

/// 验证真实靶场回归场景
#[test]
fn target_derived_python_cases_cannot_evade_documentation_rules() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let authority = root.join("docs/authority/csu-self");
    let reviewer =
        WorkspaceReviewer::compile(AuthorityInput::Directory(&authority))
            .expect("the reviewed CSU project Authority must compile");
    let fixture: Value = serde_json::from_str(include_str!(
        "fixtures/python_target_cases.json"
    ))
    .expect("target fixture must be valid JSON");

    for case in fixture["cases"].as_array().expect("cases must be an array") {
        let case_identity =
            case["id"].as_str().expect("case identity must be text");
        let source = case["source"].as_str().expect("source must be text");
        let path = format!("target_cases/{case_identity}.py");
        let documents = [SourceDocument {
            relative_path: &path,
            bytes: source.as_bytes(),
        }];
        let terminal = reviewer.review(ReviewInput::Documents(DocumentSet {
            revision: case_identity,
            documents: &documents,
        }));
        let ReviewTerminal::Sealed(review) = terminal else {
            panic!("case {case_identity} must seal");
        };
        assert_eq!(
            review.completion(),
            Completion::Complete,
            "case {case_identity}: {:?}",
            review.coverage()
        );
        assert!(
            review.coverage().files()[0].families().iter().all(
                |(_, state)| !matches!(state, FactFamilyState::Blocked(_))
            )
        );

        let subject = case["expected_subject"]
            .as_str()
            .expect("expected subject must be text");
        let documentation_findings: Vec<_> = review
            .findings()
            .iter()
            .filter(|finding| {
                finding.subject() == subject
                    && finding.rule().starts_with("documentation.")
            })
            .collect();
        match case["expected_rule"].as_str() {
            Some(rule) => assert!(
                documentation_findings.iter().any(|finding| {
                    finding.rule() == rule
                        && finding.grade() == FindingGrade::HardViolation
                }),
                "case {case_identity} did not produce {rule}: {documentation_findings:?}"
            ),
            None => assert!(
                documentation_findings.is_empty(),
                "positive control {case_identity} produced {documentation_findings:?}"
            ),
        }
    }
}
