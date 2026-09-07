use super::dependency_state;
use super::review;
use super::review_sources;
use super::reviewer;
use csu::Disposition;
use csu::ReviewTerminal;

// 观察：声明身份、数量与作用域

/// 验证来源路径只取语法标识符和点号且保留相对层级
#[test]
fn python_dependency_paths_ignore_spacing_and_continuations() {
    for source in [
        "import os.path, sys\n",
        "import os . path, sys\n",
        "import os \\\n    . path as value, sys\n",
        "from os . path import value\n",
        "from os \\\n    . path import value\n",
        "from . . project . inner import value\n",
        "from . \\\n    . project . inner import value\n",
    ] {
        let ReviewTerminal::Sealed(result) =
            review("python-path-whitespace", &[("src/value.py", source)])
        else {
            panic!("valid Python import must seal: {source}");
        };
        assert_eq!(
            dependency_state(result.coverage().files()[0].families()),
            &csu::FactFamilyState::Complete(1),
            "{source}"
        );
        assert!(
            !result
                .findings()
                .iter()
                .any(|finding| finding.rule().starts_with("dependency.")),
            "{source}"
        );
    }
    let ReviewTerminal::Sealed(result) = review(
        "relative-path-depth",
        &[(
            "src/value.py",
            "from .project import value\nfrom . . project import value\n",
        )],
    ) else {
        panic!("relative paths must seal");
    };
    assert!(
        result
            .findings()
            .iter()
            .any(|finding| finding.rule() == "dependency.order"
                && finding.line() == 2)
    );
}

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

/// 验证 Python 静态依赖覆盖所有作用域且保留分类缺口
#[test]
fn python_dependency_scope_covers_static_statement() {
    for (path, source, reason) in [
        ("src/exact.py", "if TYPE_CHECKING:\n    import os\n", None),
        ("src/continued.py", "import \\\n    os\n", None),
        (
            "src/qualified.py",
            "if typing.TYPE_CHECKING:\n    import os\n",
            None,
        ),
        ("src/other.py", "if OTHER_GUARD:\n    import os\n", None),
        ("src/local.py", "def _local():\n    import os\n", None),
        (
            "src/unknown.py",
            "import unclassified_package\n",
            Some("classification is absent from Authority"),
        ),
        (
            "src/multi.py",
            "import numpy, os\n",
            Some("mixed-class import statement layout is unsupported"),
        ),
        (
            "src/multi_reverse.py",
            "import os, numpy\n",
            Some("mixed-class import statement layout is unsupported"),
        ),
        (
            "src/nested_guard.py",
            "if TYPE_CHECKING:\n    if TYPE_CHECKING:\n        import os\n",
            None,
        ),
    ] {
        let ReviewTerminal::Sealed(review) =
            review("python-dependency-scope", &[(path, source)])
        else {
            panic!("dependency scope review must seal");
        };
        match reason {
            None => assert_eq!(
                dependency_state(review.coverage().files()[0].families()),
                &csu::FactFamilyState::Complete(1),
                "{path}"
            ),
            Some(expected) => {
                let csu::FactFamilyState::Blocked(actual) =
                    dependency_state(review.coverage().files()[0].families())
                else {
                    panic!(
                        "missing dependency evidence must remain blocked: {path}"
                    );
                };
                assert!(actual.contains(expected), "{path}: {actual}");
                assert_eq!(
                    actual.contains("classification is absent from Authority"),
                    expected == "classification is absent from Authority",
                    "{path}: {actual}"
                );
            }
        }
    }
}

/// 验证块内排序覆盖静态声明且保留原始语句计数
#[test]
fn python_nested_static_imports_keep_statement_counts() {
    for (source, count, lines) in [
        ("def _load():\n    import sys\n    import os\n", 2, vec![3]),
        ("class Loader:\n    import sys\n    import os\n", 2, vec![3]),
        (
            "if FLAG:\n    import sys\n    import os\nelse:\n    import sys\n    import os\n",
            4,
            vec![3, 6],
        ),
        (
            "try:\n    import sys\n    import os\nexcept ImportError:\n    import sys\n    import os\nfinally:\n    import sys\n    import os\n",
            6,
            vec![3, 6, 9],
        ),
        (
            "if typing.TYPE_CHECKING:\n    if FLAG:\n        import sys as system\n        import os as operating_system\n",
            2,
            vec![4],
        ),
        (
            "def _load():\n    from sys import (\n        version as runtime_version,\n    )\n    from os import path as filesystem_path\n",
            2,
            vec![5],
        ),
        (
            "def _load():\n    import sys as system, os as operating_system\n",
            1,
            vec![2],
        ),
        (
            "for item in values:\n    import sys\n    import os\n",
            2,
            vec![3],
        ),
        ("while FLAG:\n    import sys\n    import os\n", 2, vec![3]),
        (
            "with context():\n    import sys\n    import os\n",
            2,
            vec![3],
        ),
        (
            "match value:\n    case 1:\n        import sys\n        import os\n",
            2,
            vec![4],
        ),
        (
            "async def _load():\n    import sys\n    import os\n",
            2,
            vec![3],
        ),
        ("import os, sys\n", 1, vec![]),
    ] {
        for reorder_safe in [false, true] {
            let ReviewTerminal::Sealed(result) = review_sources(
                &reviewer(reorder_safe),
                "nested-static-imports",
                &[("src/value.py", source)],
            ) else {
                panic!("nested static imports must seal");
            };
            assert_eq!(
                dependency_state(result.coverage().files()[0].families()),
                &csu::FactFamilyState::Complete(count),
                "{source}"
            );
            assert_eq!(result.metrics().files_read, 1);
            assert_eq!(result.metrics().byte_sweeps, 1);
            assert_eq!(result.metrics().structural_parses, 1);
            let actual: Vec<_> = result
                .findings()
                .iter()
                .filter(|finding| finding.rule() == "dependency.order")
                .map(|finding| finding.line())
                .collect();
            assert_eq!(
                actual,
                if reorder_safe { lines.clone() } else { vec![] },
                "{source}"
            );
        }
    }
}

/// 验证作用域、分支和普通语句隔开排序分组
#[test]
fn python_nested_import_groups_keep_scope() {
    for source in [
        "import sys\ndef _load():\n    import os\n",
        "if FLAG:\n    import sys\nelse:\n    import os\n",
        "try:\n    import sys\nexcept ImportError:\n    import os\nfinally:\n    import numpy\n",
        "def _load():\n    import sys\n    value = 1\n    import os\n",
        "if FLAG:\n    import sys\n    if OTHER_FLAG:\n        import os\n    import os\n",
        "class Loader:\n    import sys\n    def _load(self):\n        import os\n",
    ] {
        let ReviewTerminal::Sealed(result) =
            review("nested-import-groups", &[("src/value.py", source)])
        else {
            panic!("nested import groups must seal");
        };
        assert!(
            matches!(
                dependency_state(result.coverage().files()[0].families()),
                csu::FactFamilyState::Complete(_)
            ),
            "{source}"
        );
        assert!(
            result
                .findings()
                .iter()
                .all(|finding| finding.rule() != "dependency.order"),
            "{source}"
        );
    }
}

/// 验证 future 指令独立分组且普通导入仍需分类依据
#[test]
fn python_directives_have_isolated_dependency_groups() {
    for (source, count) in [
        ("from __future__ import annotations\nimport os\n", 2),
        (
            "from __future__ import annotations\nfrom __future__ import generator_stop\nimport os\n",
            3,
        ),
        (
            "from __future__ import (\n    annotations,\n    generator_stop,\n)\nimport os\n",
            2,
        ),
    ] {
        let ReviewTerminal::Sealed(result) =
            review("future-directives", &[("src/value.py", source)])
        else {
            panic!("future directives must seal");
        };
        assert_eq!(
            dependency_state(result.coverage().files()[0].families()),
            &csu::FactFamilyState::Complete(count),
            "{source}"
        );
        assert!(
            result
                .findings()
                .iter()
                .all(|finding| finding.rule() != "dependency.order"),
            "{source}"
        );
    }
    let ReviewTerminal::Sealed(result) = review(
        "future-module-import",
        &[("src/value.py", "import __future__\n")],
    ) else {
        panic!("ordinary future module import must seal");
    };
    let csu::FactFamilyState::Blocked(reason) =
        dependency_state(result.coverage().files()[0].families())
    else {
        panic!("ordinary future module import needs classification");
    };
    assert!(
        reason.contains(
            "classification is absent from Authority at 1:8: __future__"
        ),
        "{reason}"
    );
}
