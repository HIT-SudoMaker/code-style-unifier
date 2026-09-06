use csu::AuthorityDocument;
use csu::AuthorityInput;
use csu::Disposition;
use csu::FindingGrade;
use csu::ReviewTerminal;
use csu::WorkspaceReviewer;

mod review_fixture;

use review_fixture::compile_value;
use review_fixture::review_sources;

/// 验证相对导入保留项目依赖分类和排序检查
#[test]
fn python_relative_dependencies_have_project_identity() {
    for source in [
        "from .value import distance_m\n",
        "from ..value import distance_m\n",
        "from . import value\n",
        "import sys\n\nfrom .value import distance_m\n",
    ] {
        let terminal = review(
            "relative-import",
            &[("src/project/inner/value.py", source)],
        );
        assert_eq!(
            terminal.disposition(),
            Disposition::Clean,
            "{terminal:#?}"
        );
    }
    for (source, rule) in [
        ("from .value import *\n", "dependency.wildcard"),
        (
            "from .value import distance_m\nimport sys\n",
            "dependency.order",
        ),
        (
            "from .upper import value\nfrom .lower import value\n",
            "dependency.order",
        ),
    ] {
        let ReviewTerminal::Sealed(review) =
            review("relative-import", &[("src/project/value.py", source)])
        else {
            panic!("relative imports must seal");
        };
        assert_eq!(review.completion(), csu::Completion::Complete);
        assert!(
            review
                .findings()
                .iter()
                .any(|finding| finding.rule() == rule)
        );
    }
    let terminal = review(
        "absolute-unknown",
        &[("src/project/value.py", "from unregistered import value\n")],
    );
    assert_eq!(terminal.disposition(), Disposition::Incomplete);
}

/// 创建测试审查器
fn reviewer(reorder_safe: bool) -> WorkspaceReviewer {
    let mut authority: serde_json::Value = serde_json::from_str(include_str!(
        "../docs/fixtures/core/authority.json"
    ))
    .unwrap();
    authority["dependency_authority"] = serde_json::json!({
        "python_standard_library": ["os", "sys"],
        "python_third_party": ["numpy"],
        "python_project_roots": ["project"],
        "python_reorder_safe": reorder_safe,
        "rust_reorder_safe": reorder_safe
    });
    compile_value(&authority).unwrap()
}

/// 审查一组依赖声明样例
fn review(revision: &str, sources: &[(&str, &str)]) -> ReviewTerminal {
    review_sources(&reviewer(true), revision, sources)
}

/// 验证依赖排序和通配符按各语言规则检查
#[test]
fn dependency_order_and_wildcard_are_profile_local() {
    let terminal = review(
        "dependency-order",
        &[
            (
                "src/dependencies.py",
                "import sys\nimport os\n\nimport numpy\n",
            ),
            (
                "src/dependencies.rs",
                "use zeta::module;\nuse alpha::module;\n",
            ),
            ("src/star.c", "#include \"*\"\n"),
            ("src/star.cpp", "#include \"*\"\n"),
            ("src/star.py", "from os import *\n"),
            ("src/glob.rs", "use crate::module::*;\n"),
            ("src/groups.py", "import sys\nvalue = 1\nimport os\n"),
            (
                "src/groups.rs",
                "use zeta::module;\nmod inner { use alpha::module; }\n",
            ),
        ],
    );
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
    let wildcard_paths: Vec<_> = review
        .findings()
        .iter()
        .filter(|finding| {
            finding.rule() == "dependency.wildcard"
                && finding.grade() == FindingGrade::HardViolation
        })
        .map(|finding| finding.path())
        .collect();
    assert_eq!(wildcard_paths, ["src/glob.rs", "src/star.py"]);
    for path in ["src/star.c", "src/star.cpp"] {
        let file = review
            .coverage()
            .files()
            .iter()
            .find(|file| file.path() == path)
            .unwrap();
        assert!(file.families().iter().any(|(family, state)| {
            *family == csu::FactFamily::DependencyDeclaration
                && matches!(state, csu::FactFamilyState::Blocked(_))
        }));
    }
}

/// 验证无法完整识别的 Python 和 Rust 导入不能判为干净
#[test]
fn complex_python_and_rust_imports_cannot_pass_as_clean() {
    let terminal = review(
        "python-multi-module-imports",
        &[
            ("src/third_party_first.py", "import numpy, os\n"),
            ("src/standard_library_first.py", "import os, numpy\n"),
            ("src/nested.rs", "use crate::{alpha, beta};\n"),
        ],
    );

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

/// 验证 C++ 模块导入必须先于普通顶层声明
#[test]
fn cpp_module_import_must_precede_ordinary_top_level_declarations() {
    let terminal = review(
        "cpp-module-placement",
        &[
            (
                "src/named.cpp",
                "module;\nexport module velocity;\nexport import math;\n",
            ),
            (
                "src/header.cpp",
                "export module velocity;\nimport <vector>;\n",
            ),
            ("src/global.cpp", "module;\nimport math;\n"),
            ("src/misplaced.cpp", "int value;\nimport math;\n"),
            ("src/nested.cpp", "namespace detail { import math; }\n"),
            ("src/private.cpp", "module :private;\nimport math;\n"),
        ],
    );
    let ReviewTerminal::Sealed(review) = terminal else {
        panic!("C++ module placement must seal");
    };
    let placement_paths: Vec<_> = review
        .findings()
        .iter()
        .filter(|finding| finding.rule() == "dependency.module_placement")
        .map(|finding| finding.path())
        .collect();
    assert_eq!(
        placement_paths,
        [
            "src/global.cpp",
            "src/misplaced.cpp",
            "src/nested.cpp",
            "src/private.cpp"
        ]
    );
    assert!(review.coverage().files().iter().all(|file| {
        file.families().iter().any(|(family, state)| {
            *family == csu::FactFamily::DependencyDeclaration
                && matches!(state, csu::FactFamilyState::Blocked(_))
        })
    }));
}

/// 验证 Python 仅检查模块级和精确类型检查块中的依赖
#[test]
fn python_dependency_scope_is_module_level_or_exact_type_checking() {
    for (path, source, blocked) in [
        ("src/exact.py", "if TYPE_CHECKING:\n    import os\n", false),
        ("src/continued.py", "import \\\n    os\n", false),
        (
            "src/qualified.py",
            "if typing.TYPE_CHECKING:\n    import os\n",
            true,
        ),
        ("src/other.py", "if OTHER_GUARD:\n    import os\n", true),
        ("src/local.py", "def _local():\n    import os\n", true),
        ("src/unknown.py", "import unclassified_package\n", true),
    ] {
        let ReviewTerminal::Sealed(review) =
            review("python-dependency-scope", &[(path, source)])
        else {
            panic!("dependency scope review must seal");
        };
        let observed = review.coverage().files()[0].families().iter().any(
            |(family, state)| {
                *family == csu::FactFamily::DependencyDeclaration
                    && matches!(state, csu::FactFamilyState::Blocked(_))
            },
        );
        assert_eq!(observed, blocked, "{path}");
    }
}

/// 验证依赖分组拒绝多余空行并保持确定的排序
#[test]
fn dependency_groups_reject_extra_blank_lines_and_have_total_order() {
    let ReviewTerminal::Sealed(review) = review(
        "dependency-spacing-and-total-order",
        &[
            ("src/spacing.py", "import os\n\nimport sys\n"),
            ("src/tiers.py", "import os\nimport numpy\n"),
            (
                "src/version_tie.rs",
                "use alpha1::module;\nuse alpha01::module;\n",
            ),
            (
                "src/rust_roots.rs",
                "use alpha::module;\npub(crate) use self::module;\n",
            ),
        ],
    ) else {
        panic!("dependency ordering must seal");
    };
    let paths: Vec<_> = review
        .findings()
        .iter()
        .filter(|finding| finding.rule() == "dependency.order")
        .map(|finding| finding.path())
        .collect();

    assert_eq!(
        paths,
        [
            "src/rust_roots.rs",
            "src/spacing.py",
            "src/tiers.py",
            "src/version_tie.rs",
        ]
    );
}

/// 验证未授权重排时保留 Python 和 Rust 原有顺序
#[test]
fn reorder_disabled_preserves_python_and_rust_order() {
    let terminal = review_sources(
        &reviewer(false),
        "dependency-preserve-order",
        &[
            ("src/order.py", "import numpy\nimport os\n"),
            ("src/order.rs", "use zeta::module;\nuse alpha::module;\n"),
        ],
    );
    let ReviewTerminal::Sealed(review) = terminal else {
        panic!("preserved order must seal")
    };
    assert!(
        review
            .findings()
            .iter()
            .all(|finding| finding.rule() != "dependency.order")
    );
}

/// 验证依赖分类重叠在源码审查前被拒绝
#[test]
fn overlapping_dependency_classes_are_rejected_before_review() {
    let mut authority: serde_json::Value = serde_json::from_str(include_str!(
        "../docs/fixtures/core/authority.json"
    ))
    .unwrap();
    authority["dependency_authority"] = serde_json::json!({
        "python_standard_library": ["shared"],
        "python_third_party": ["shared"],
        "python_project_roots": []
    });
    assert!(compile_value(&authority).is_err());
    for invalid in ["os.path", " os", "7zip"] {
        authority["dependency_authority"] = serde_json::json!({
            "python_standard_library": ["os"], "python_third_party": [invalid]
        });
        assert!(compile_value(&authority).is_err(), "{invalid}");
    }
    let unsupported =
        br#"{"schema_version":4,"header_languages":{"src/a.h":"rust"}}"#;
    let documents = [AuthorityDocument {
        relative_path: "authority.json",
        bytes: unsupported,
    }];
    let rejection =
        WorkspaceReviewer::compile(AuthorityInput::Documents(&documents))
            .expect_err(
                "unsupported Profile must reject before dependency review",
            );
    assert_eq!(rejection.code(), "authority.header_language");
}
