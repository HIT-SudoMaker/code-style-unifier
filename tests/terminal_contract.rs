use csu::AuthorityDocument;
use csu::AuthorityInput;
use csu::Completion;
use csu::Disposition;
use csu::DocumentSet;
use csu::FactFamily;
use csu::FactFamilyState;
use csu::ReviewInput;
use csu::ReviewTerminal;
use csu::SourceDocument;
use csu::WorkspaceReviewer;
use csu::project_human;
use std::path::Path;

const AUTHORITY: &str = include_str!("../docs/fixtures/core/authority.json");

const VALID_PYTHON: &str = concat!(
    "def _calculate_velocity(distance_m: float, ",
    r#"duration_s: float) -> float:
    """
    计算平均速度
    """
    return distance_m / duration_s
"#,
);

/// 构造测试 Reviewer
fn reviewer() -> WorkspaceReviewer {
    let documents = [AuthorityDocument {
        relative_path: "authority.json",
        bytes: AUTHORITY.as_bytes(),
    }];
    WorkspaceReviewer::compile(AuthorityInput::Documents(&documents)).unwrap()
}

/// 构造指定来源形态的测试 Reviewer
fn reviewer_with_source_form(source_form: &str) -> WorkspaceReviewer {
    let mut authority: serde_json::Value =
        serde_json::from_str(AUTHORITY).unwrap();
    authority["source_form"] = serde_json::json!(source_form);
    let bytes = serde_json::to_vec(&authority).unwrap();
    let documents = [AuthorityDocument {
        relative_path: "authority.json",
        bytes: &bytes,
    }];
    WorkspaceReviewer::compile(AuthorityInput::Documents(&documents)).unwrap()
}

/// 验证审查终态证据场景
#[test]
fn incomplete_projection_is_rejected_before_review() {
    let mut authority: serde_json::Value =
        serde_json::from_str(AUTHORITY).unwrap();
    authority["families"][0]["projections"]
        .as_object_mut()
        .unwrap()
        .remove("cpp");
    let authority = serde_json::to_vec(&authority).unwrap();
    let documents = [AuthorityDocument {
        relative_path: "authority.json",
        bytes: &authority,
    }];
    let rejection =
        WorkspaceReviewer::compile(AuthorityInput::Documents(&documents))
            .expect_err("missing C++ projection must reject the Authority");
    assert_eq!(rejection.code(), "authority.projection");
}

/// 验证审查终态证据场景
#[test]
fn selected_dependency_family_requires_enabled_authority() {
    let mut authority: serde_json::Value =
        serde_json::from_str(AUTHORITY).unwrap();
    authority["families"]
        .as_array_mut()
        .unwrap()
        .push(serde_json::json!({
            "name": "dependency",
            "operator": "dependency_v1",
            "projections": {
                "python": "supported",
                "rust": "supported",
                "c": "supported",
                "cpp": "supported"
            }
        }));
    let authority = serde_json::to_vec(&authority).unwrap();
    let documents = [AuthorityDocument {
        relative_path: "authority.json",
        bytes: &authority,
    }];
    let rejection =
        WorkspaceReviewer::compile(AuthorityInput::Documents(&documents))
            .expect_err(
                "selected dependency family must not be silently disabled",
            );
    assert_eq!(rejection.code(), "authority.dependency");
}

/// 验证审查终态证据场景
#[test]
fn projection_state_controls_runtime_family_closure() {
    let authority = AUTHORITY
        .replace("\"cpp\": \"supported\"", "\"cpp\": \"needs_authority\"");
    let authority_documents = [AuthorityDocument {
        relative_path: "authority.json",
        bytes: authority.as_bytes(),
    }];
    let reviewer = WorkspaceReviewer::compile(AuthorityInput::Documents(
        &authority_documents,
    ))
    .expect("Needs Authority is a total projection");
    let documents = [SourceDocument {
        relative_path: "src/value.cpp",
        bytes: b"int value;\n",
    }];
    let terminal = reviewer.review(ReviewInput::Documents(DocumentSet {
        revision: "needs-authority",
        documents: &documents,
    }));
    assert_eq!(terminal.disposition(), Disposition::Incomplete);
}

/// 验证审查终态证据场景
#[test]
fn candidate_registry_must_cover_the_frozen_latin_and_greek_minimum() {
    for equivalent_forms in [
        &["q"][..],
        &["Q"][..],
        &["alpha"][..],
        &["α"][..],
        &["Α"][..],
        &["ϕ"][..],
    ] {
        let mut authority: serde_json::Value =
            serde_json::from_str(AUTHORITY).unwrap();
        authority["candidate_tokens"]
            .as_array_mut()
            .unwrap()
            .retain(|token| {
                !equivalent_forms.contains(&token.as_str().unwrap())
            });
        let authority = serde_json::to_vec(&authority).unwrap();
        let documents = [AuthorityDocument {
            relative_path: "authority.json",
            bytes: &authority,
        }];
        let rejection =
            WorkspaceReviewer::compile(AuthorityInput::Documents(&documents))
                .expect_err("incomplete candidate registry must reject");
        assert_eq!(rejection.code(), "authority.candidate_registry");
    }
}

/// 验证审查终态证据场景
#[test]
fn authority_must_cover_every_closed_rule_operator() {
    let mut authority: serde_json::Value =
        serde_json::from_str(AUTHORITY).unwrap();
    authority["rules"]
        .as_array_mut()
        .unwrap()
        .retain(|rule| rule["operator"] != "dependency_order");
    let bytes = serde_json::to_vec(&authority).unwrap();
    let documents = [AuthorityDocument {
        relative_path: "authority.json",
        bytes: &bytes,
    }];
    let rejection =
        WorkspaceReviewer::compile(AuthorityInput::Documents(&documents))
            .expect_err("a partial rule catalog must reject");

    assert_eq!(rejection.code(), "authority.rule_catalog");
}

/// 验证审查终态证据场景
#[test]
fn parseability_contract_must_be_explicit_and_supported() {
    let authority: serde_json::Value =
        serde_json::from_str(AUTHORITY).unwrap();
    for invalid in [
        {
            let mut candidate = authority.clone();
            candidate.as_object_mut().unwrap().remove("source_form");
            candidate
        },
        {
            let mut candidate = authority.clone();
            candidate["source_form"] = serde_json::json!("fallback");
            candidate
        },
        {
            let mut candidate = authority;
            candidate["profile_contracts"]["python"]["observation_method"] =
                serde_json::json!("unpinned");
            candidate
        },
    ] {
        let bytes = serde_json::to_vec(&invalid).unwrap();
        let documents = [AuthorityDocument {
            relative_path: "authority.json",
            bytes: &bytes,
        }];
        WorkspaceReviewer::compile(AuthorityInput::Documents(&documents))
            .expect_err("parseability policy must reject before Review");
    }

    let cargo = include_str!("../Cargo.toml");
    for (language, method, dependency) in [
        (
            "python",
            "tree-sitter-python@0.25.0",
            "tree-sitter-python = \"0.25.0\"",
        ),
        (
            "rust",
            "tree-sitter-rust@0.24.2",
            "tree-sitter-rust = \"0.24.2\"",
        ),
        ("c", "tree-sitter-c@0.24.2", "tree-sitter-c = \"0.24.2\""),
        (
            "cpp",
            "tree-sitter-cpp@8b5b49eb",
            "rev = \"8b5b49eb196bec7040441bee33b2c9a4838d6967\"",
        ),
    ] {
        assert!(
            AUTHORITY.contains(&format!("\"observation_method\": \"{method}")),
            "{language} observation method must remain pinned"
        );
        assert!(cargo.contains(dependency));
    }
}

/// 验证审查终态证据场景
#[test]
fn duplicate_operator_cannot_duplicate_an_atomic_finding() {
    let mut wrong_grade: serde_json::Value =
        serde_json::from_str(AUTHORITY).unwrap();
    wrong_grade["rules"][0]["grade"] = serde_json::json!("soft_friction");
    let wrong_grade = serde_json::to_vec(&wrong_grade).unwrap();
    let wrong_grade_documents = [AuthorityDocument {
        relative_path: "authority.json",
        bytes: &wrong_grade,
    }];
    let rejection = WorkspaceReviewer::compile(AuthorityInput::Documents(
        &wrong_grade_documents,
    ))
    .expect_err("Candidate grade must remain Review Required");
    assert_eq!(rejection.code(), "authority.rule_catalog");

    let mut authority: serde_json::Value =
        serde_json::from_str(AUTHORITY).unwrap();
    authority["rules"]
        .as_array_mut()
        .unwrap()
        .push(serde_json::json!({
            "id": "identifier.symbolic_alias",
            "family": "identifier",
            "fact": "declaration_name",
            "operator": "identifier_candidate",
            "grade": "review_required",
            "message": "symbolic alias should be expanded before release",
            "question": "该别名是否已有规范全名？"
        }));
    let bytes = serde_json::to_vec(&authority).unwrap();
    let authority_documents = [AuthorityDocument {
        relative_path: "authority.json",
        bytes: &bytes,
    }];
    let rejection = WorkspaceReviewer::compile(AuthorityInput::Documents(
        &authority_documents,
    ))
    .expect_err("one operator must not duplicate an atomic Finding");
    assert_eq!(rejection.code(), "authority.rule_catalog");
}

/// 验证审查终态证据场景
#[test]
fn presentation_must_be_total_before_review() {
    let base: serde_json::Value = serde_json::from_str(AUTHORITY).unwrap();
    let mut cases = Vec::new();

    let mut missing_chapter = base.clone();
    missing_chapter["presentation"]
        .as_array_mut()
        .unwrap()
        .pop();
    cases.push(missing_chapter);

    let mut duplicate_rule = base.clone();
    duplicate_rule["presentation"][0]["rules"] =
        serde_json::json!(["identifier.candidate"]);
    cases.push(duplicate_rule);

    let mut missing_profile = base;
    missing_profile["presentation"][4]["profiles"]
        .as_object_mut()
        .unwrap()
        .remove("cpp");
    cases.push(missing_profile);

    for authority in cases {
        let bytes = serde_json::to_vec(&authority).unwrap();
        let documents = [AuthorityDocument {
            relative_path: "authority.json",
            bytes: &bytes,
        }];
        let rejection =
            WorkspaceReviewer::compile(AuthorityInput::Documents(&documents))
                .expect_err(
                    "incomplete presentation must reject before review",
                );
        assert_eq!(rejection.code(), "authority.presentation");
    }
}

/// 验证审查终态证据场景
#[test]
fn presentation_only_change_preserves_scientific_identity() {
    let first: serde_json::Value = serde_json::from_str(AUTHORITY).unwrap();
    let mut second = first.clone();
    second["presentation"][4]["rules"]
        .as_array_mut()
        .unwrap()
        .swap(0, 4);

    let first_bytes = serde_json::to_vec(&first).unwrap();
    let second_bytes = serde_json::to_vec(&second).unwrap();
    let first_authority = [AuthorityDocument {
        relative_path: "authority.json",
        bytes: &first_bytes,
    }];
    let second_authority = [AuthorityDocument {
        relative_path: "authority.json",
        bytes: &second_bytes,
    }];
    let first_reviewer = WorkspaceReviewer::compile(
        AuthorityInput::Documents(&first_authority),
    )
    .unwrap();
    let second_reviewer = WorkspaceReviewer::compile(
        AuthorityInput::Documents(&second_authority),
    )
    .unwrap();
    let sources = [SourceDocument {
        relative_path: "src/names.py",
        bytes:
            b"Q = 1\nmystery_token = 2\ndef undocumented():\n    return 1\n",
    }];
    let input = ReviewInput::Documents(DocumentSet {
        revision: "presentation-invariance",
        documents: &sources,
    });
    let first_terminal = first_reviewer.review(input);
    let second_terminal = second_reviewer.review(input);
    let (
        ReviewTerminal::Sealed(first_review),
        ReviewTerminal::Sealed(second_review),
    ) = (&first_terminal, &second_terminal)
    else {
        panic!("valid presentation fixtures must seal");
    };

    assert_eq!(
        first_review.canonical_bytes(),
        second_review.canonical_bytes()
    );
    assert_eq!(first_review.seal(), second_review.seal());
    let first_human = project_human(&first_terminal);
    let second_human = project_human(&second_terminal);
    assert_ne!(first_human, second_human);
    assert!(
        first_human.find("[HardViolation]")
            < first_human.find("[ReviewRequired]")
    );
}

/// 验证审查终态证据场景
#[test]
fn rule_catalog_row_order_does_not_change_scientific_identity() {
    let first: serde_json::Value = serde_json::from_str(AUTHORITY).unwrap();
    let mut second = first.clone();
    second["rules"].as_array_mut().unwrap().swap(0, 12);
    let first_bytes = serde_json::to_vec(&first).unwrap();
    let second_bytes = serde_json::to_vec(&second).unwrap();
    let first_documents = [AuthorityDocument {
        relative_path: "authority.json",
        bytes: &first_bytes,
    }];
    let second_documents = [AuthorityDocument {
        relative_path: "authority.json",
        bytes: &second_bytes,
    }];
    let first = WorkspaceReviewer::compile(AuthorityInput::Documents(
        &first_documents,
    ))
    .unwrap();
    let second = WorkspaceReviewer::compile(AuthorityInput::Documents(
        &second_documents,
    ))
    .unwrap();
    let sources = [SourceDocument {
        relative_path: "src/symbol.py",
        bytes: b"Q = 1\n",
    }];
    let input = ReviewInput::Documents(DocumentSet {
        revision: "catalog-order-invariance",
        documents: &sources,
    });
    let ReviewTerminal::Sealed(first) = first.review(input) else {
        panic!("first Authority must seal");
    };
    let ReviewTerminal::Sealed(second) = second.review(input) else {
        panic!("reordered Authority must seal");
    };
    assert_eq!(first.canonical_bytes(), second.canonical_bytes());
    assert_eq!(first.seal(), second.seal());
}

/// 验证审查终态证据场景
#[test]
fn invalid_and_duplicate_document_paths_are_rejected() {
    let invalid = [SourceDocument {
        relative_path: "../escape.py",
        bytes: VALID_PYTHON.as_bytes(),
    }];
    let terminal = reviewer().review(ReviewInput::Documents(DocumentSet {
        revision: "invalid-path",
        documents: &invalid,
    }));
    assert_eq!(terminal.disposition(), Disposition::Rejected);

    let duplicate = [
        SourceDocument {
            relative_path: "src/a.py",
            bytes: VALID_PYTHON.as_bytes(),
        },
        SourceDocument {
            relative_path: "src/a.py",
            bytes: VALID_PYTHON.as_bytes(),
        },
    ];
    let terminal = reviewer().review(ReviewInput::Documents(DocumentSet {
        revision: "duplicate-path",
        documents: &duplicate,
    }));
    assert_eq!(terminal.disposition(), Disposition::Rejected);
}

/// 验证审查终态证据场景
#[test]
fn unknown_memory_document_language_is_rejected() {
    let documents = [SourceDocument {
        relative_path: "src/notes.txt",
        bytes: b"not governed source\n",
    }];
    let terminal = reviewer().review(ReviewInput::Documents(DocumentSet {
        revision: "unknown-language",
        documents: &documents,
    }));
    assert_eq!(terminal.disposition(), Disposition::Rejected);
}

/// 验证审查终态证据场景
#[test]
fn invalid_encoding_obeys_the_compiled_parseability_regime() {
    let invalid_utf8 = [SourceDocument {
        relative_path: "src/invalid.py",
        bytes: &[0xff, b'\n'],
    }];
    for (source_form, finding_expected) in
        [("direct", true), ("external", false)]
    {
        let terminal = reviewer_with_source_form(source_form).review(
            ReviewInput::Documents(DocumentSet {
                revision: source_form,
                documents: &invalid_utf8,
            }),
        );
        let ReviewTerminal::Sealed(review) = terminal else {
            panic!("invalid source encoding must seal incomplete");
        };
        assert_eq!(review.completion(), Completion::Incomplete);
        assert_eq!(
            review
                .findings()
                .iter()
                .any(|finding| finding.rule() == "source.parseability"),
            finding_expected
        );
        assert_eq!(review.metrics().byte_sweeps, 1);
        assert_eq!(review.metrics().structural_parses, 0);
        assert!(
            review.coverage().files()[0]
                .families()
                .iter()
                .any(|(family, state)| *family == FactFamily::PhysicalLines
                    && matches!(state, FactFamilyState::Complete(1)))
        );
    }
}

/// 验证审查终态证据场景
#[test]
fn identical_inputs_produce_identical_seal_bytes_thirty_times() {
    let reviewer = reviewer();
    let documents = [SourceDocument {
        relative_path: "src/velocity.py",
        bytes: VALID_PYTHON.as_bytes(),
    }];
    let mut expected = None;
    for _ in 0..30 {
        let terminal = reviewer.review(ReviewInput::Documents(DocumentSet {
            revision: "deterministic",
            documents: &documents,
        }));
        let ReviewTerminal::Sealed(review) = terminal else {
            panic!("valid input must seal");
        };
        let bytes = review.canonical_bytes();
        if let Some(expected) = &expected {
            assert_eq!(&bytes, expected);
        } else {
            expected = Some(bytes);
        }
    }
}

/// 验证审查终态证据场景
#[test]
fn four_language_syntax_damage_obeys_the_compiled_regime() {
    let fixture_root =
        Path::new(env!("CARGO_MANIFEST_DIR")).join("docs/fixtures/core");
    let manifest: serde_json::Value = serde_json::from_str(include_str!(
        "../docs/fixtures/core/fixture-manifest.json"
    ))
    .unwrap();
    let cases = [
        ("python/calculate_velocity.py", "python"),
        ("rust/calculate_velocity.rs", "rust"),
        ("c/calculate_velocity.h", "c"),
        ("cpp/calculate_velocity.hpp", "cpp"),
    ];
    for (relative, language) in &cases {
        let source_path =
            fixture_root.join("documents/syntax_damaged").join(relative);
        let bytes = std::fs::read(&source_path).unwrap();
        let document_path = format!("documents/syntax_damaged/{relative}");
        let documents = [SourceDocument {
            relative_path: &document_path,
            bytes: &bytes,
        }];
        let terminal = reviewer_with_source_form("direct").review(
            ReviewInput::Documents(DocumentSet {
                revision: language,
                documents: &documents,
            }),
        );
        let ReviewTerminal::Sealed(review) = terminal else {
            panic!("{language} syntax damage must seal incomplete");
        };
        assert_eq!(review.completion(), Completion::Incomplete);
        let finding = review
            .findings()
            .iter()
            .find(|finding| finding.rule() == "source.parseability")
            .expect("direct source damage must create parseability evidence");
        assert_eq!(finding.grade(), csu::FindingGrade::HardViolation);
        let reason = review.coverage().files()[0]
            .families()
            .iter()
            .find_map(|(family, state)| {
                (*family == FactFamily::Structure)
                    .then_some(state)
                    .and_then(|state| match state {
                        FactFamilyState::Blocked(reason) => Some(reason),
                        _ => None,
                    })
            })
            .expect("syntax damage must block Structure");
        assert_eq!(
            reason,
            manifest["scenario_contracts"]["syntax_damaged"]["parse_anchors"]
                [language]["reason"]
                .as_str()
                .unwrap()
        );
        assert_eq!(review.metrics().byte_sweeps, 1);
        assert_eq!(review.metrics().structural_parses, 1);
    }
}

/// 验证审查终态证据场景
#[test]
fn inventoried_file_read_failure_seals_incomplete() {
    let workspace = tempfile::tempdir().unwrap();
    std::fs::write(
        workspace.path().join(".csu-inventory.json"),
        concat!(
            r#"{"schema_version":1,"entries":[{"path":"missing.py","#,
            r#""language":"python"}]}"#
        ),
    )
    .unwrap();

    let terminal = reviewer().review(ReviewInput::Workspace(workspace.path()));

    assert_eq!(terminal.disposition(), Disposition::Incomplete);
    let ReviewTerminal::Sealed(review) = terminal else {
        panic!("post-inventory capture failure must still produce a Seal");
    };
    assert_eq!(review.completion(), Completion::Incomplete);
    assert!(review.findings().is_empty());
    let coverage = &review.coverage().files()[0];
    let blocked: Vec<_> = coverage
        .families()
        .iter()
        .filter_map(|(family, state)| {
            matches!(state, FactFamilyState::Blocked(_)).then_some(*family)
        })
        .collect();
    assert_eq!(
        blocked,
        vec![
            FactFamily::Capture,
            FactFamily::PhysicalLines,
            FactFamily::Structure,
            FactFamily::Identifier,
            FactFamily::Documentation,
        ]
    );
    assert_eq!(review.metrics().files_read, 0);
    assert_eq!(review.metrics().byte_sweeps, 0);
    assert_eq!(review.metrics().structural_parses, 0);
}
