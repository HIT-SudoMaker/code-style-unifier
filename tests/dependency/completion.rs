use super::dependency_state;
use super::review;
use super::review_sources;
use super::reviewer;
use csu::ReviewTerminal;

// 完成：保留已知问题与各自的受阻原因

/// 验证能力受阻和缺失分类提供不同的关闭路径
#[test]
fn dependency_capability_and_classification_are_distinct() {
    for (path, source, capability) in [
        ("src/value.py", "import os, numpy\n", true),
        ("src/value.py", "import unknown\n", false),
        ("src/value.c", "#include <stddef.h>\n", true),
        (
            "src/value.cpp",
            "export module value;\nimport math;\n",
            true,
        ),
    ] {
        let ReviewTerminal::Sealed(result) =
            review("dependency-reason", &[(path, source)])
        else {
            panic!("dependency review must seal");
        };
        let csu::FactFamilyState::Blocked(reason) =
            dependency_state(result.coverage().files()[0].families())
        else {
            panic!("missing dependency evidence must remain blocked");
        };
        assert_eq!(reason.contains("unsupported"), capability, "{reason}");
        assert_eq!(
            reason.contains("classification is absent from Authority"),
            !capability,
            "{reason}"
        );
    }
}
/// 验证混合分类布局与缺失分类同时保留各自关闭路径
#[test]
fn python_mixed_layout_and_unknown_classification_remain_visible() {
    let source = "import numpy, os\ndef _load():\n    from missing_package import value\n";
    let ReviewTerminal::Sealed(result) =
        review("mixed-layout-and-missing", &[("src/value.py", source)])
    else {
        panic!("mixed dependency evidence must seal");
    };
    let csu::FactFamilyState::Blocked(reason) =
        dependency_state(result.coverage().files()[0].families())
    else {
        panic!("mixed layout and classification must remain blocked");
    };
    assert!(reason.contains("unsupported"), "{reason}");
    assert!(reason.contains("at 1:1"), "{reason}");
    assert!(
        reason.contains(
            "classification is absent from Authority at 3:5: missing_package"
        ),
        "{reason}"
    );
}

/// 验证 Python 缺口不遮蔽独立排序且不跨未知项比较
#[test]
fn python_dependency_order_preserves_evidence() {
    for (source, expected) in [
        ("import sys\nimport os\nimport unknown\n", vec![2]),
        ("import unknown\nimport sys\nimport os\n", vec![3]),
        ("import sys\nimport unknown\nimport os\n", vec![]),
        ("import sys\nimport os, numpy\nimport os\n", vec![2, 3]),
        ("import sys\nimport os\nimport os, numpy\n", vec![2]),
        (
            "import sys\nimport os\ndef _value():\n    import unknown\n",
            vec![2],
        ),
        (
            "import sys\ndef _value():\n    import unknown\nimport os\n",
            vec![],
        ),
        (
            "import unknown\nif TYPE_CHECKING:\n    import sys\n    import os\n",
            vec![4],
        ),
        ("import unknown\nimport os\nimport numpy\n", vec![3]),
    ] {
        for reorder_safe in [false, true] {
            let ReviewTerminal::Sealed(result) = review_sources(
                &reviewer(reorder_safe),
                "partial-order",
                &[("src/value.py", source)],
            ) else {
                panic!("partial dependency review must seal");
            };
            assert!(matches!(
                dependency_state(result.coverage().files()[0].families()),
                csu::FactFamilyState::Blocked(_)
            ));
            let lines: Vec<_> = result
                .findings()
                .iter()
                .filter(|finding| finding.rule() == "dependency.order")
                .map(|finding| finding.line())
                .collect();
            assert_eq!(
                lines,
                if reorder_safe {
                    expected.clone()
                } else {
                    vec![]
                },
                "{source}"
            );
        }
    }
}

/// 验证多模块未知分类逐项定位且不能跨越未知项比较
#[test]
fn python_unknown_import_members_keep_locations_and_findings() {
    let source = "def _load():\n    import sys, first_missing as missing, os\n    import second_missing, sys, os\n";
    for reorder_safe in [false, true] {
        let ReviewTerminal::Sealed(result) = review_sources(
            &reviewer(reorder_safe),
            "unknown-import-members",
            &[("src/value.py", source)],
        ) else {
            panic!("unknown member review must seal");
        };
        let csu::FactFamilyState::Blocked(reason) =
            dependency_state(result.coverage().files()[0].families())
        else {
            panic!("unknown classifications must block completion");
        };
        assert!(reason.contains("at 2:17: first_missing"), "{reason}");
        assert!(reason.contains("at 3:12: second_missing"), "{reason}");
        assert!(!reason.contains("unsupported"), "{reason}");
        let lines: Vec<_> = result
            .findings()
            .iter()
            .filter(|finding| finding.rule() == "dependency.order")
            .map(|finding| finding.line())
            .collect();
        assert_eq!(lines, if reorder_safe { vec![3] } else { vec![] });
    }
}

/// 验证 Rust 通配违规独立于重排开关且未知树仍受阻
#[test]
fn rust_use_tree_unknown_and_wildcard_remain_visible() {
    for reorder_safe in [false, true] {
        let ReviewTerminal::Sealed(result) = review_sources(
            &reviewer(reorder_safe),
            "rust-use-limit",
            &[
                ("src/wildcard.rs", "use crate::{beta, alpha, *};\n"),
                ("src/unknown.rs", "use $unknown; use a::{z,b};\n"),
            ],
        ) else {
            panic!("Rust use limits must seal");
        };
        let count = |rule| {
            result
                .findings()
                .iter()
                .filter(|finding| finding.rule() == rule)
                .count()
        };
        assert_eq!(count("dependency.wildcard"), 1);
        assert_eq!(count("dependency.order"), 2 * usize::from(reorder_safe));
        for file in result.coverage().files() {
            let state = dependency_state(file.families());
            assert!(if file.path() == "src/unknown.rs" {
                matches!(state, csu::FactFamilyState::Blocked(_))
            } else {
                *state == csu::FactFamilyState::Complete(1)
            });
        }
    }
}

/// 验证 Rust 多个未知导入均定位且已知导入树仍可检查
#[test]
fn rust_unknown_dependencies_keep_all_locations_and_known_order() {
    let source = "use $first;\nuse crate::{zeta, alpha};\nuse $second;\n";
    for reorder_safe in [false, true] {
        let ReviewTerminal::Sealed(result) = review_sources(
            &reviewer(reorder_safe),
            "rust-unknown-locations",
            &[("src/value.rs", source)],
        ) else {
            panic!("unknown Rust imports must seal");
        };
        let csu::FactFamilyState::Blocked(reason) =
            dependency_state(result.coverage().files()[0].families())
        else {
            panic!("unknown Rust imports must remain blocked");
        };
        let first = reason
            .find("at 1:1:")
            .expect("first unknown import location");
        let second = reason
            .find("at 3:1:")
            .expect("second unknown import location");
        assert!(first < second, "{reason}");
        assert_eq!(reason.matches(" at ").count(), 2, "{reason}");
        let lines: Vec<_> = result
            .findings()
            .iter()
            .filter(|finding| finding.rule() == "dependency.order")
            .map(|finding| finding.line())
            .collect();
        assert_eq!(lines, if reorder_safe { vec![2] } else { vec![] });
    }
}

/// 验证未知 Rust 列表项保留已知相邻项和独立子列表的证据
#[test]
fn rust_unknown_members_preserve_known_list_evidence() {
    for (source, expected, wildcard) in [
        ("use crate::{zeta, alpha, $unknown};\n", vec![(1, 19)], 0),
        ("use crate::{$unknown, zeta, alpha};\n", vec![(1, 29)], 0),
        (
            "use crate::{zeta, alpha, inner::{$unknown}};\n",
            vec![(1, 19)],
            0,
        ),
        (
            "use crate::{before::{zeta, alpha}, $unknown};\n",
            vec![(1, 28)],
            0,
        ),
        ("use crate::{zeta, $unknown, alpha};\n", vec![], 0),
        ("use crate::{zeta, alpha, $unknown, *};\n", vec![(1, 19)], 1),
        (
            "use zeta;\nuse crate::{zeta, alpha, $unknown};\nuse alpha;\n",
            vec![(2, 19)],
            0,
        ),
    ] {
        for reorder_safe in [false, true] {
            let ReviewTerminal::Sealed(result) = review_sources(
                &reviewer(reorder_safe),
                "rust-unknown-members",
                &[("src/value.rs", source)],
            ) else {
                panic!("partial Rust list review must seal");
            };
            assert!(matches!(
                dependency_state(result.coverage().files()[0].families()),
                csu::FactFamilyState::Blocked(_)
            ));
            let positions: Vec<_> = result
                .findings()
                .iter()
                .filter(|finding| finding.rule() == "dependency.order")
                .map(|finding| (finding.line(), finding.column()))
                .collect();
            assert_eq!(
                positions,
                if reorder_safe {
                    expected.clone()
                } else {
                    vec![]
                },
                "{source}"
            );
            assert_eq!(
                result
                    .findings()
                    .iter()
                    .filter(|finding| finding.rule() == "dependency.wildcard")
                    .count(),
                wildcard,
                "{source}"
            );
        }
    }
}

/// 验证原生语言受阻位置覆盖全部声明并按源码顺序排列
#[test]
fn native_dependency_locations_follow_source_order() {
    for (path, source, locations) in [
        (
            "src/value.c",
            "#include <stddef.h>\n#if ENABLED\n#include <stdint.h>\n#endif\n",
            "1:1, 3:1",
        ),
        (
            "src/value.cpp",
            "import first;\n#include <vector>\n#if ENABLED\nimport second;\n#include <string>\n#endif\n",
            "1:1, 2:1, 4:1, 5:1",
        ),
    ] {
        let ReviewTerminal::Sealed(result) =
            review("native-dependency-locations", &[(path, source)])
        else {
            panic!("native imports must seal");
        };
        let csu::FactFamilyState::Blocked(reason) =
            dependency_state(result.coverage().files()[0].families())
        else {
            panic!("native imports must retain capability limit");
        };
        assert_eq!(
            reason.rsplit_once(" at ").map(|(_, value)| value),
            Some(locations),
            "{reason}"
        );
    }
}
