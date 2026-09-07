use super::compile_value;
use super::review_sources;
use csu::AuthorityDocument;
use csu::AuthorityInput;
use csu::WorkspaceReviewer;

// 输入：Authority 事实接纳

/// 验证依赖分类重叠在源码审查前被拒绝
#[test]
fn overlapping_dependency_classes_are_rejected_before_review() {
    let mut authority: serde_json::Value = serde_json::from_str(include_str!(
        "../../docs/fixtures/core/authority.json"
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

/// 验证依赖事实接纳原生单根并拒绝关键词和附加语法
#[test]
fn python_dependency_authority_uses_native_roots() {
    for name in ["数据", "℘", "a\u{0301}", "match", "case", "type", "_vendor"]
    {
        let authority = serde_json::json!({
            "schema_version": 4,
            "dependency_authority": {"python_project_roots": [name]},
            "token_vocabulary": ["value"]
        });
        let reviewer = compile_value(&authority).unwrap();
        let source = format!("from {name} import value\n");
        let terminal = review_sources(
            &reviewer,
            "native-dependency-root",
            &[("value.py", &source)],
        );
        assert_eq!(terminal.disposition(), csu::Disposition::Clean, "{name}");
    }
    for name in [
        "class",
        "async",
        "await",
        "True",
        "None",
        "a.b",
        "a, b",
        "a as b",
        "a#comment",
        "a\nimport b",
        "a\\\n",
        " a",
        "a ",
        "a\u{200b}",
        "\u{0301}a",
        "7zip",
        "",
        "a;",
        "a\0",
    ] {
        let authority = serde_json::json!({
            "schema_version": 4,
            "dependency_authority": {"python_project_roots": [name]}
        });
        let rejection = compile_value(&authority).unwrap_err();
        assert_eq!(rejection.code(), "authority.dependency", "{name:?}");
    }
    let overlap = serde_json::json!({
        "schema_version": 4,
        "dependency_authority": {
            "python_standard_library": ["数据"],
            "python_project_roots": ["数据"]
        }
    });
    assert_eq!(
        compile_value(&overlap).unwrap_err().code(),
        "authority.dependency"
    );
}
