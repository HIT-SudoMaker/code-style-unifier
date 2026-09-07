use super::dependency_state;
use super::review;
use super::review_sources;
use super::reviewer;
use csu::Disposition;
use csu::FindingGrade;
use csu::ReviewTerminal;

// 判断：顺序、重排授权与模块位置

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
        assert!(matches!(
            dependency_state(file.families()),
            csu::FactFamilyState::Blocked(_)
        ));
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

/// 验证 Rust 导入树按结构递归检查且保持声明计数
#[test]
fn rust_use_trees_have_recursive_order_and_complete_coverage() {
    let cases: Vec<(String, usize, u32)> =
        serde_json::from_str(include_str!("../fixtures/rust-use-trees.json"))
            .expect("Rust import cases must be valid JSON");
    for (source, order_findings, declarations) in cases {
        let ReviewTerminal::Sealed(result) =
            review("rust-use-tree", &[("src/imports.rs", &source)])
        else {
            panic!("Rust use-tree review must seal: {source}");
        };
        assert_eq!(
            dependency_state(result.coverage().files()[0].families()),
            &csu::FactFamilyState::Complete(declarations),
            "{source}"
        );
        let count = result
            .findings()
            .iter()
            .filter(|finding| finding.rule() == "dependency.order")
            .count();
        assert_eq!(count, order_findings, "{source}");
    }
    let source = "use crate::{\n    beta,\n    /* explanation */ alpha,\n};\n";
    let ReviewTerminal::Sealed(result) =
        review("rust-use-layout", &[("src/imports.rs", source)])
    else {
        panic!("Rust use-tree layout must seal");
    };
    let findings: Vec<_> = result
        .findings()
        .iter()
        .filter(|finding| finding.rule() == "dependency.order")
        .collect();
    assert_eq!(findings.len(), 1);
    assert_eq!((findings[0].line(), findings[0].column()), (3, 23));
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
    assert!(review.coverage().files().iter().all(|file| matches!(
        dependency_state(file.families()),
        csu::FactFamilyState::Blocked(_)
    )));
}

/// 验证注释和预处理分支保留可证明的模块位置事实
#[test]
fn cpp_module_placement_preserves_comments_and_condition_evidence() {
    for (source, lines) in [
        (
            "export module value;\nexport\n/* explanation */\nimport math;\n",
            vec![],
        ),
        (
            "export\n/* explanation */\nmodule value;\nimport math;\n",
            vec![],
        ),
        (
            "module;\n#if ENABLED\nimport math;\n#endif\nimport other;\n",
            vec![3, 5],
        ),
        ("module;\n#define ENABLED 1\nimport math;\n", vec![3]),
        (
            "// explanation\nexport module value;\nimport math;\n",
            vec![],
        ),
        (
            "export module value;\nimport first;\n/* explanation */\nimport second;\n",
            vec![],
        ),
        (
            "#if ENABLED\nimport math;\n#elif OTHER\nimport other;\n#else\nimport fallback;\n#endif\n",
            vec![],
        ),
        ("int value;\n#if ENABLED\nimport math;\n#endif\n", vec![3]),
        (
            "#if ENABLED\nnamespace detail { import math; }\n#endif\n",
            vec![2],
        ),
        (
            "module;\n#if ENABLED\nexport module value;\n#endif\nimport math;\n",
            vec![],
        ),
    ] {
        let ReviewTerminal::Sealed(result) = review(
            "conditional-module-placement",
            &[("src/value.cpp", source)],
        ) else {
            panic!("conditional module placement must seal");
        };
        assert!(
            matches!(
                dependency_state(result.coverage().files()[0].families()),
                csu::FactFamilyState::Blocked(_)
            ),
            "{source}"
        );
        let actual: Vec<_> = result
            .findings()
            .iter()
            .filter(|finding| finding.rule() == "dependency.module_placement")
            .map(|finding| finding.line())
            .collect();
        assert_eq!(actual, lines, "{source}");
    }
}

/// 验证分支内按顺序判断、替代分支隔离及出口共同事实
#[test]
fn cpp_module_branch_order_keeps_proven_positions() {
    for (source, lines) in [
        (
            "module;\n#if ENABLED\nimport math;\nexport module value;\n#endif\n",
            vec![3],
        ),
        ("#if ENABLED\nint value;\nimport math;\n#endif\n", vec![3]),
        (
            "#if ENABLED\nint value;\n#else\nimport math;\n#endif\nimport other;\n",
            vec![],
        ),
        (
            "#if ENABLED\nint value;\n#elif OTHER\nimport math;\n#else\nimport other;\n#endif\n",
            vec![],
        ),
        (
            "#ifdef ENABLED\nint value;\nimport math;\n#else\nimport other;\n#endif\n",
            vec![3],
        ),
        (
            "#if ENABLED\nint value;\n#else\nint other;\n#endif\nimport math;\n",
            vec![6],
        ),
        ("#if ENABLED\nint value;\n#endif\nimport math;\n", vec![]),
        (
            "module;\n#if ENABLED\nexport module value;\n#else\nimport math;\n#endif\nimport other;\n",
            vec![5],
        ),
        (
            "#if ENABLED\nmodule;\n#else\nint value;\n#endif\nimport math;\nexport module value;\nimport other;\n",
            vec![6],
        ),
        (
            "#if ENABLED\nint value;\n#if OTHER\nimport math;\n#endif\n#endif\n",
            vec![4],
        ),
        ("#if ENABLED\nimport math;\nint value;\n#endif\n", vec![]),
        (
            "#if ENABLED\n#define VALUE 1\nimport math;\n#endif\n",
            vec![],
        ),
    ] {
        let ReviewTerminal::Sealed(result) =
            review("conditional-module-order", &[("src/value.cpp", source)])
        else {
            panic!("conditional module order must seal");
        };
        let csu::FactFamilyState::Blocked(reason) =
            dependency_state(result.coverage().files()[0].families())
        else {
            panic!("native target analysis must remain blocked");
        };
        assert!(
            reason
                .contains("target and preprocessing analysis is unsupported"),
            "{reason}"
        );
        let actual: Vec<_> = result
            .findings()
            .iter()
            .filter(|finding| finding.rule() == "dependency.module_placement")
            .map(|finding| (finding.line(), finding.column()))
            .collect();
        let expected: Vec<_> = lines.iter().map(|line| (*line, 1)).collect();
        assert_eq!(actual, expected, "{source}");
    }
}
