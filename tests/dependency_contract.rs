use csu::AuthorityDocument;
use csu::AuthorityInput;
use csu::Disposition;
use csu::DocumentSet;
use csu::FindingGrade;
use csu::ReviewInput;
use csu::ReviewTerminal;
use csu::SourceDocument;
use csu::WorkspaceReviewer;

/// 构造测试 Reviewer
fn reviewer() -> WorkspaceReviewer {
    let mut authority: serde_json::Value = serde_json::from_str(include_str!(
        "../docs/fixtures/core/authority.json"
    ))
    .unwrap();
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
    authority["dependency_authority"] = serde_json::json!({
        "enabled": true,
        "python_standard_library": ["os", "sys"],
        "python_third_party": ["numpy"],
        "python_project_roots": ["project"],
        "python_reorder_safe": true,
        "rust_reorder_safe": true
    });
    let authority = serde_json::to_vec(&authority).unwrap();
    let documents = [AuthorityDocument {
        relative_path: "authority.json",
        bytes: &authority,
    }];
    WorkspaceReviewer::compile(AuthorityInput::Documents(&documents)).unwrap()
}

/// 验证依赖声明证据场景
#[test]
fn python_and_rust_safe_groups_use_language_local_order() {
    let python = b"import sys\nimport os\n\nimport numpy\n";
    let rust = b"use zeta::module;\nuse alpha::module;\n";
    let procedural = b"#include \"zeta.h\"\n#include \"alpha.h\"\n";
    let object_oriented = b"#include <zeta>\n#include <alpha>\n";
    let documents = [
        SourceDocument {
            relative_path: "src/dependencies.py",
            bytes: python,
        },
        SourceDocument {
            relative_path: "src/dependencies.rs",
            bytes: rust,
        },
        SourceDocument {
            relative_path: "src/dependencies.c",
            bytes: procedural,
        },
        SourceDocument {
            relative_path: "src/dependencies.cpp",
            bytes: object_oriented,
        },
    ];
    let terminal = reviewer().review(ReviewInput::Documents(DocumentSet {
        revision: "dependency-order",
        documents: &documents,
    }));
    assert_eq!(terminal.disposition(), Disposition::Incomplete);
    let ReviewTerminal::Sealed(review) = terminal else {
        panic!("dependency order violations must seal");
    };
    let order_paths: Vec<_> = review
        .findings()
        .iter()
        .filter(|finding| finding.rule() == "dependency.order")
        .map(|finding| finding.path())
        .collect();
    assert_eq!(order_paths, ["src/dependencies.py", "src/dependencies.rs"]);
}

/// 验证依赖声明证据场景
#[test]
fn python_star_and_rust_glob_are_hard_violations() {
    let python = b"from os import  *\n";
    let rust = b"use crate::module :: *;\n";
    let documents = [
        SourceDocument {
            relative_path: "src/star.py",
            bytes: python,
        },
        SourceDocument {
            relative_path: "src/glob.rs",
            bytes: rust,
        },
    ];
    let terminal = reviewer().review(ReviewInput::Documents(DocumentSet {
        revision: "dependency-glob",
        documents: &documents,
    }));
    let ReviewTerminal::Sealed(review) = terminal else {
        panic!("wildcard violations must seal");
    };
    assert_eq!(
        review
            .findings()
            .iter()
            .filter(|finding| {
                finding.rule() == "dependency.wildcard"
                    && finding.grade() == FindingGrade::HardViolation
            })
            .count(),
        2
    );
}

/// 验证依赖声明证据场景
#[test]
fn python_multi_module_imports_cannot_pass_as_clean() {
    let documents = [
        SourceDocument {
            relative_path: "src/third_party_first.py",
            bytes: b"import numpy, os\n",
        },
        SourceDocument {
            relative_path: "src/standard_library_first.py",
            bytes: b"import os, numpy\n",
        },
    ];
    let terminal = reviewer().review(ReviewInput::Documents(DocumentSet {
        revision: "python-multi-module-imports",
        documents: &documents,
    }));

    assert_eq!(terminal.disposition(), Disposition::Incomplete);
    let ReviewTerminal::Sealed(review) = terminal else {
        panic!("multi-module imports must have sealed blocking evidence");
    };
    assert!(review.coverage().files().iter().all(|file| {
        file.families().iter().any(|(family, state)| {
            *family == csu::FactFamily::DependencyDeclaration
                && matches!(state, csu::FactFamilyState::Blocked(_))
        })
    }));
}

/// 验证依赖声明证据场景
#[test]
fn unknown_python_classification_blocks_instead_of_guessing() {
    let documents = [SourceDocument {
        relative_path: "src/unknown.py",
        bytes: b"import unclassified_package\n",
    }];
    let terminal = reviewer().review(ReviewInput::Documents(DocumentSet {
        revision: "unknown-dependency",
        documents: &documents,
    }));
    assert_eq!(terminal.disposition(), Disposition::Incomplete);
}

/// 验证依赖声明证据场景
#[test]
fn cpp_module_import_must_precede_ordinary_top_level_declarations() {
    let documents = [
        SourceDocument {
            relative_path: "src/valid.cpp",
            bytes: b"export module velocity;\nimport math;\nint value;\n",
        },
        SourceDocument {
            relative_path: "src/misplaced.cpp",
            bytes: b"int value;\nimport math;\n",
        },
    ];
    let terminal = reviewer().review(ReviewInput::Documents(DocumentSet {
        revision: "cpp-module-placement",
        documents: &documents,
    }));
    let ReviewTerminal::Sealed(review) = terminal else {
        panic!("C++ module placement must seal");
    };
    let placement_paths: Vec<_> = review
        .findings()
        .iter()
        .filter(|finding| finding.rule() == "dependency.module_placement")
        .map(|finding| finding.path())
        .collect();
    assert_eq!(placement_paths, ["src/misplaced.cpp"]);
}

/// 验证依赖声明证据场景
#[test]
fn cpp_nested_module_import_cannot_pass_as_clean() {
    let documents = [SourceDocument {
        relative_path: "src/nested.cpp",
        bytes: b"namespace detail { import math; }\n",
    }];
    let terminal = reviewer().review(ReviewInput::Documents(DocumentSet {
        revision: "cpp-nested-module-import",
        documents: &documents,
    }));
    let ReviewTerminal::Sealed(review) = terminal else {
        panic!("nested module syntax must have a terminal evidence state");
    };
    let dependency_blocked = review.coverage().files()[0]
        .families()
        .iter()
        .any(|(family, state)| {
            *family == csu::FactFamily::DependencyDeclaration
                && matches!(state, csu::FactFamilyState::Blocked(_))
        });
    let placement_finding = review
        .findings()
        .iter()
        .any(|finding| finding.rule() == "dependency.module_placement");
    assert!(dependency_blocked || placement_finding);
}

/// 验证依赖声明证据场景
#[test]
fn python_dependency_scope_is_module_level_or_exact_type_checking() {
    let source = r#"def _local():
    """
    执行局部工作
    """
    import unknown_inside_function

if OTHER_GUARD:
    import unknown_inside_other_guard

if TYPE_CHECKING:
    import os
"#;
    let documents = [SourceDocument {
        relative_path: "src/scopes.py",
        bytes: source.as_bytes(),
    }];
    let terminal = reviewer().review(ReviewInput::Documents(DocumentSet {
        revision: "python-dependency-scope",
        documents: &documents,
    }));
    assert_eq!(terminal.disposition(), Disposition::Incomplete);
    let ReviewTerminal::Sealed(review) = terminal else {
        panic!("dependency scope review must seal");
    };
    let state = review.coverage().files()[0]
        .families()
        .iter()
        .find(|(family, _)| *family == csu::FactFamily::DependencyDeclaration)
        .map(|(_, state)| state);
    assert!(matches!(state, Some(csu::FactFamilyState::Blocked(_))));
}

/// 验证依赖声明证据场景
#[test]
fn dependency_order_never_crosses_statement_or_scope_boundaries() {
    let python = b"import sys\nvalue = 1\nimport os\n";
    let rust = b"use zeta::module;\nmod inner { use alpha::module; }\n";
    let documents = [
        SourceDocument {
            relative_path: "src/groups.py",
            bytes: python,
        },
        SourceDocument {
            relative_path: "src/groups.rs",
            bytes: rust,
        },
    ];
    let terminal = reviewer().review(ReviewInput::Documents(DocumentSet {
        revision: "dependency-group-boundaries",
        documents: &documents,
    }));
    let ReviewTerminal::Sealed(review) = terminal else {
        panic!("group-boundary review must seal");
    };
    assert!(
        review
            .findings()
            .iter()
            .all(|finding| finding.rule() != "dependency.order")
    );
}

/// 验证依赖声明证据场景
#[test]
fn rust_safe_group_orders_self_super_crate_before_external_paths() {
    let source = b"use alpha::module;\nuse self::module;\n";
    let documents = [SourceDocument {
        relative_path: "src/rust_roots.rs",
        bytes: source,
    }];
    let terminal = reviewer().review(ReviewInput::Documents(DocumentSet {
        revision: "rust-root-order",
        documents: &documents,
    }));
    let ReviewTerminal::Sealed(review) = terminal else {
        panic!("Rust order review must seal");
    };
    assert!(
        review
            .findings()
            .iter()
            .any(|finding| finding.rule() == "dependency.order")
    );
}

/// 验证依赖声明证据场景
#[test]
fn dependency_groups_reject_extra_blank_lines_and_have_total_order() {
    let python = b"import os\n\nimport sys\n";
    let rust = b"use alpha1::module;\nuse alpha01::module;\n";
    let documents = [
        SourceDocument {
            relative_path: "src/spacing.py",
            bytes: python,
        },
        SourceDocument {
            relative_path: "src/version_tie.rs",
            bytes: rust,
        },
    ];
    let ReviewTerminal::Sealed(review) =
        reviewer().review(ReviewInput::Documents(DocumentSet {
            revision: "dependency-spacing-and-total-order",
            documents: &documents,
        }))
    else {
        panic!("dependency ordering must seal");
    };
    let paths: Vec<_> = review
        .findings()
        .iter()
        .filter(|finding| finding.rule() == "dependency.order")
        .map(|finding| finding.path())
        .collect();

    assert_eq!(paths, ["src/spacing.py", "src/version_tie.rs"]);
}

/// 验证依赖声明证据场景
#[test]
fn overlapping_dependency_classes_are_rejected_before_review() {
    let mut authority: serde_json::Value = serde_json::from_str(include_str!(
        "../docs/fixtures/core/authority.json"
    ))
    .unwrap();
    authority["families"]
        .as_array_mut()
        .unwrap()
        .push(serde_json::json!({
            "name": "dependency",
            "operator": "dependency_v1",
            "projections": {
                "python": "supported", "rust": "supported",
                "c": "supported", "cpp": "supported"
            }
        }));
    authority["dependency_authority"] = serde_json::json!({
        "enabled": true,
        "python_standard_library": ["shared"],
        "python_third_party": ["shared"],
        "python_project_roots": []
    });
    let bytes = serde_json::to_vec(&authority).unwrap();
    let documents = [AuthorityDocument {
        relative_path: "authority.json",
        bytes: &bytes,
    }];

    assert!(
        WorkspaceReviewer::compile(AuthorityInput::Documents(&documents))
            .is_err()
    );
}
