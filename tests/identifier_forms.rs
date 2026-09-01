use csu::AuthorityDocument;
use csu::AuthorityInput;
use csu::DocumentSet;
use csu::FindingGrade;
use csu::ReviewInput;
use csu::ReviewTerminal;
use csu::SourceDocument;
use csu::WorkspaceReviewer;
use std::collections::BTreeSet;

const AUTHORITY: &[u8] =
    include_bytes!("../docs/fixtures/core/authority.json");

/// 审查内存源码并返回封存终态
fn review<'source>(
    documents: &'source [SourceDocument<'source>],
) -> csu::SealedReview {
    let authority = [AuthorityDocument {
        relative_path: "authority.json",
        bytes: AUTHORITY,
    }];
    let reviewer =
        WorkspaceReviewer::compile(AuthorityInput::Documents(&authority))
            .expect("frozen Authority must compile");
    let ReviewTerminal::Sealed(review) =
        reviewer.review(ReviewInput::Documents(DocumentSet {
            revision: "identifier-forms",
            documents,
        }))
    else {
        panic!("valid source must seal");
    };
    review
}

/// 验证标识符形式证据场景
#[test]
fn four_language_role_forms_accept_the_frozen_baseline() {
    let sources = [
        (
            "src/forms.py",
            concat!(
                "VELOCITY = 1\nclass Velocity:\n",
                "    def calculate_velocity(self, distance_m):\n",
                "        return distance_m\n"
            ),
        ),
        (
            "src/forms.rs",
            concat!(
                "struct Velocity { distance_m: f64 }\n",
                "const VELOCITY: f64 = 1.0;\n",
                "enum Distance { Velocity }\n",
                "fn calculate_velocity(distance_m: f64) -> f64 ",
                "{ distance_m }\n"
            ),
        ),
        (
            "src/forms.c",
            concat!(
                "#define VELOCITY 1\n",
                "typedef struct distance { double distance_m; } velocity_t;\n",
                "enum distance { VELOCITY };\n",
                "double calculate_velocity(double distance_m);\n"
            ),
        ),
        (
            "src/forms.cpp",
            concat!(
                "#define VELOCITY 1\n",
                "class Velocity { public: double distance_m; ",
                "private: double velocity_m_per_s_; };\n",
                "enum Distance { VELOCITY };\n",
                "double calculate_velocity(double distance_m);\n"
            ),
        ),
    ];
    let documents: Vec<_> = sources
        .iter()
        .map(|(relative_path, bytes)| SourceDocument {
            relative_path,
            bytes: bytes.as_bytes(),
        })
        .collect();
    let review = review(&documents);

    assert!(
        review
            .findings()
            .iter()
            .all(|finding| !finding.rule().starts_with("identifier.")),
        "findings: {:#?}",
        review.findings()
    );
}

/// 验证标识符形式证据场景
#[test]
fn four_language_role_forms_and_reserved_identifiers_are_hard() {
    let sources = [
        (
            "src/invalid.py",
            concat!(
                "velocity = 1\nclass calculate_velocity:\n",
                "    def Velocity(self, Distance_velocity):\n",
                "        Q = Distance_velocity\n",
                "        return Q\n"
            ),
        ),
        (
            "src/invalid.rs",
            concat!(
                "struct calculate_velocity;\n",
                "const velocity: f64 = 1.0;\n",
                "enum Distance { VELOCITY }\n",
                "fn Velocity(distance_m: f64) { let Q = distance_m; }\n"
            ),
        ),
        (
            "src/invalid.c",
            concat!(
                "typedef int Velocity;\n",
                "enum distance { velocity };\n",
                "double Velocity(double distance_m);\n",
                "int _Velocity;\nint __velocity;\nint _velocity;\nint Q;\n"
            ),
        ),
        (
            "src/invalid.cpp",
            concat!(
                "class calculate_velocity { public: double velocity_; ",
                "private: static double distance_; ",
                "double velocity_m_per_s_; };\n",
                "enum Distance { velocity };\n",
                "double Velocity(double distance_m);\n",
                "int _Velocity;\nint velocity__distance;\n",
                "int _velocity;\nint Q;\n"
            ),
        ),
    ];
    let documents: Vec<_> = sources
        .iter()
        .map(|(relative_path, bytes)| SourceDocument {
            relative_path,
            bytes: bytes.as_bytes(),
        })
        .collect();
    let review = review(&documents);
    let hard_by_path: Vec<_> = sources
        .iter()
        .map(|(path, _)| {
            review
                .findings()
                .iter()
                .filter(|finding| {
                    finding.path() == *path
                        && finding.grade() == FindingGrade::HardViolation
                        && finding.rule().starts_with("identifier.")
                })
                .count()
        })
        .collect();

    assert_eq!(hard_by_path, [4, 4, 6, 8], "{:#?}", review.findings());
}

/// 验证标识符形式证据场景
#[test]
fn candidate_priority_still_yields_one_identifier_finding_per_declaration() {
    let sources = [
        ("src/candidate.py", "Q = 1\n"),
        ("src/candidate.rs", "const Q: i32 = 1;\n"),
        ("src/candidate.c", "int _Q;\n"),
        ("src/candidate.cpp", "int _Q;\n"),
    ];
    let documents: Vec<_> = sources
        .iter()
        .map(|(relative_path, bytes)| SourceDocument {
            relative_path,
            bytes: bytes.as_bytes(),
        })
        .collect();
    let review = review(&documents);
    let identifier_findings: Vec<_> = review
        .findings()
        .iter()
        .filter(|finding| finding.rule().starts_with("identifier."))
        .collect();
    let locations: BTreeSet<_> = identifier_findings
        .iter()
        .map(|finding| (finding.path(), finding.line(), finding.column()))
        .collect();

    assert_eq!(identifier_findings.len(), 4);
    assert_eq!(locations.len(), 4);
    assert!(identifier_findings.iter().all(|finding| {
        finding.rule() == "identifier.candidate"
            && finding.grade() == FindingGrade::ReviewRequired
            && !finding.observation().is_empty()
            && finding.question().is_some()
    }));
}

/// 验证标识符形式证据场景
#[test]
fn module_namespace_tag_lifetime_and_label_forms_are_not_unchecked() {
    let sources = [
        (
            "src/roles.rs",
            concat!(
                "mod CalculateVelocity {}\n",
                "fn calculate_velocity<'Velocity>() { ",
                "'CalculateVelocity: loop { break 'CalculateVelocity; } }\n"
            ),
        ),
        (
            "src/roles.c",
            concat!(
                "struct CalculateVelocity { int distance_m; };\n",
                "void calculate_velocity(void) ",
                "{ CalculateVelocity: return; }\n"
            ),
        ),
        (
            "src/roles.cpp",
            "namespace CalculateVelocity { int distance_m; }\n",
        ),
    ];
    let documents: Vec<_> = sources
        .iter()
        .map(|(relative_path, bytes)| SourceDocument {
            relative_path,
            bytes: bytes.as_bytes(),
        })
        .collect();
    let review = review(&documents);
    let hard_subjects: BTreeSet<_> = review
        .findings()
        .iter()
        .filter(|finding| {
            finding.grade() == FindingGrade::HardViolation
                && finding.rule() == "identifier.canonical_form"
        })
        .map(|finding| finding.subject())
        .collect();

    assert!(
        hard_subjects.contains("CalculateVelocity"),
        "{:#?}",
        review.findings()
    );
    assert!(hard_subjects.contains("'Velocity"));
    assert!(hard_subjects.contains("'CalculateVelocity"));
}
