use csu::AuthorityDocument;
use csu::AuthorityInput;
use csu::Disposition;
use csu::DocumentSet;
use csu::FactFamily;
use csu::FactFamilyState;
use csu::ReviewInput;
use csu::ReviewTerminal;
use csu::SealedReview;
use csu::SourceDocument;
use csu::WorkspaceReviewer;

mod review_fixture;

use review_fixture::review_sources;

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

/// 根据测试 Authority 创建审查器
fn reviewer() -> WorkspaceReviewer {
    compile_value(&serde_json::from_str(AUTHORITY).unwrap())
        .expect("frozen Project Authority must compile")
}

/// 编译指定 JSON 值
fn compile_value(
    authority: &serde_json::Value,
) -> Result<WorkspaceReviewer, csu::ReviewRejection> {
    let bytes = serde_json::to_vec(authority).unwrap();
    WorkspaceReviewer::compile(AuthorityInput::Documents(&[
        AuthorityDocument {
            relative_path: "authority.json",
            bytes: &bytes,
        },
    ]))
}

/// 断言原始 Authority 输入在访问源码前被拒绝
fn assert_raw_authority_rejected(rows: &[&str]) {
    for raw in rows {
        let documents = [AuthorityDocument {
            relative_path: "authority.json",
            bytes: raw.as_bytes(),
        }];
        assert!(
            WorkspaceReviewer::compile(AuthorityInput::Documents(&documents))
                .is_err(),
            "{raw}"
        );
    }
}

/// 从公共审查结果中取出封存值
fn sealed(terminal: ReviewTerminal) -> SealedReview {
    match terminal {
        ReviewTerminal::Sealed(review) => review,
        _ => panic!("review must seal"),
    }
}

/// 断言无关项目事实不能消除源码已证明的硬违规
fn assert_trailing_hard(authority: &serde_json::Value) {
    let review = sealed(review_sources(
        &compile_value(authority).unwrap(),
        "effect-ceiling",
        &[("src/value.py", "distance_m = 1  # explanation\n")],
    ));
    assert!(
        review
            .findings()
            .iter()
            .any(|finding| finding.rule() == "source.trailing_comment")
    );
}

/// 返回封存结果中的 Authority 语义摘要
fn authority_digest(review: &SealedReview) -> String {
    let value: serde_json::Value =
        serde_json::from_slice(&review.canonical_bytes()).unwrap();
    value["semantic_authority_digest"]
        .as_str()
        .unwrap()
        .to_owned()
}

/// 用固定源码观察一份 Authority 的摘要与 Seal
fn authority_identity(authority: &serde_json::Value) -> (String, String) {
    let bytes = serde_json::to_vec(authority).unwrap();
    authority_identity_bytes(&bytes)
}

/// 用固定源码观察原始 Authority 字节的摘要与 Seal
fn authority_identity_bytes(bytes: &[u8]) -> (String, String) {
    let documents = [AuthorityDocument {
        relative_path: "authority.json",
        bytes,
    }];
    let reviewer =
        WorkspaceReviewer::compile(AuthorityInput::Documents(&documents))
            .expect("Project Authority must compile");
    let review = sealed(review_sources(
        &reviewer,
        "authority-identity",
        &[("src/velocity.py", VALID_PYTHON)],
    ));
    (authority_digest(&review), review.seal().to_owned())
}

/// 验证规则目录同时决定问题分类和语义身份
#[test]
fn rule_catalog_finding_and_semantic_identity() {
    let review = sealed(review_sources(
        &reviewer(),
        "rule-catalog",
        &[("src/value.py", "distance_m = 1  # explanation\n")],
    ));
    let finding = review.findings().first().unwrap();

    assert_eq!(finding.rule(), "source.trailing_comment");
    assert_eq!(finding.grade(), csu::FindingGrade::HardViolation);
    assert_eq!(
        finding.message(),
        "ordinary comments must not share a physical line with code"
    );
    assert_eq!(finding.question(), None);
    let fixture = include_str!("../docs/fixtures/core/fixture-manifest.json");
    let manifest: serde_json::Value = serde_json::from_str(fixture).unwrap();
    let expected = manifest["semantic_authority_digest"].as_str().unwrap();
    assert_eq!(authority_digest(&review), expected);
    assert_eq!(
        review.seal(),
        "1a1f9b91e0a672198a97bc7f9a2b80ef245381f337fee4f003f57bd7a1bc59ad"
    );

    let canonical: serde_json::Value =
        serde_json::from_slice(&review.canonical_bytes()).unwrap();
    assert!(canonical.get("presentation").is_none());
}

/// 验证项目只能提交项目事实，不能重定义标准规则
#[test]
fn project_authority_has_only_project_owned_facts() {
    let authority: serde_json::Value =
        serde_json::from_str(AUTHORITY).unwrap();
    let fields = authority
        .as_object()
        .unwrap()
        .keys()
        .map(String::as_str)
        .collect::<Vec<_>>();
    assert_eq!(
        fields.join(","),
        "dependency_authority,external_fixed_identifiers,header_languages,public_callables,quantity_concepts,schema_version,token_vocabulary"
    );
    let mut previous_schema = authority.clone();
    previous_schema["schema_version"] = serde_json::json!(3);
    let rejection = compile_value(&previous_schema).unwrap_err();
    assert_eq!(rejection.code(), "authority.version");

    let mut invalid = authority;
    invalid["rules"] = serde_json::Value::Null;
    let rejection = compile_value(&invalid).unwrap_err();
    assert_eq!(rejection.code(), "authority.syntax");
}

/// 验证工作区内的旧清单不能改变文件范围或语言
#[test]
fn workspace_inventory_has_no_review_effect() {
    let workspace = tempfile::tempdir().unwrap();
    std::fs::write(workspace.path().join("velocity.py"), VALID_PYTHON)
        .unwrap();
    let baseline =
        sealed(reviewer().review(ReviewInput::Workspace(workspace.path())));
    for inventory in [
        r#"{"schema_version":1,"entries":[{"path":"velocity.py","language":"rust"}]}"#,
        "{malformed",
        r#"{"entries":[{"path":"../missing.rs","language":"rust"}]}"#,
    ] {
        std::fs::write(
            workspace.path().join(".csu-inventory.json"),
            inventory,
        )
        .unwrap();
        let review = sealed(
            reviewer().review(ReviewInput::Workspace(workspace.path())),
        );
        assert_eq!(review.canonical_bytes(), baseline.canonical_bytes());
    }
}

/// 验证各事实类别均有检查结果且不依赖位掩码
#[test]
fn coverage_closes_all_owned_families_without_mask() {
    let review =
        sealed(reviewer().review(ReviewInput::Documents(DocumentSet {
            revision: "invalid-utf8",
            documents: &[SourceDocument {
                relative_path: "src/velocity.py",
                bytes: b"# \xce\xb1\r\n    \xc3\xa9\xff",
            }],
        })));
    let expected = "observation method tree-sitter-python@0.25.0+direct-source-facts-v3 rejected source at 2:7: source is not valid UTF-8";
    let blocked = FactFamilyState::Blocked(expected.to_owned());

    assert_eq!(review.completion(), csu::Completion::Incomplete);
    assert_eq!(review.findings()[0].rule(), "source.parseability");
    assert_eq!(review.findings()[0].observation(), expected);
    assert_eq!(review.metrics().files_read, 1);
    assert_eq!(review.metrics().byte_sweeps, 1);
    assert_eq!(review.metrics().structural_parses, 0);
    assert_eq!(
        review.coverage().files()[0].families(),
        &[
            (FactFamily::Capture, FactFamilyState::Complete(1)),
            (FactFamily::PhysicalLines, FactFamilyState::Complete(2)),
            (FactFamily::Structure, blocked.clone()),
            (FactFamily::Identifier, blocked.clone()),
            (FactFamily::Documentation, blocked.clone()),
            (FactFamily::DependencyDeclaration, blocked),
        ]
    );
}

/// 验证五类审查输入的规范字节与封存摘要
#[test]
fn review_identity_is_canonical() {
    let cases: [(&str, &str, &[u8], &str, &str); 5] = [
        (
            "clean",
            "src/velocity.py",
            "def _calculate_velocity():\n    \"\"\"\n    计算平均速度\n    \"\"\"\n    return 1\n".as_bytes(),
            "f7cf255153f561a3522da6804825949a25afafc8c6da39eb36010aa5f2298256",
            "92d931b0397b490dd162c731a9189dca307abc62e15400774161185db1b297f1",
        ),
        ("findings", "src/value.py", b"Q = 1\n", "04b3106d02de61ccdd7ba0778c1e9a3c7939b08f54e5acacc9def0f01573d9bd", "26c29d14c5324fcf01943fe62fe39cb566446f532e3dff30b42b43d2c8997703"),
        ("source-rejected", "src/value.py", b"\xff", "54b934be912cecdcb9339412074be7af4a1830f4a0e1c357734656c9eb1f1201", "1015ef6ed11dd99ef4baba04e27f1229198f4bb5b16b4a27df97b4c6a4f36fb2"),
        ("documentation-blocked", "src/unowned.c", "/**\n * 计算平均速度\n */\ndouble calculate_velocity(void);\n".as_bytes(), "de125e4e34a7bc5e601d7f3c1ea7a657353eae4c819a43ebbb2b44398650b0fc", "51284c30f00839daab75a77872e60b5b8cf5965a80ce32a0db051debab3aa7b2"),
        ("dependency-blocked", "src/dependency.py", b"import os\n", "e76b7754a992e5f3ea64215a1e1a1705a28873136eba1932306c6f1f94658996", "3b43f48187bfafceab4f392d43f1057dcb4d1a34c5ef6000d8b1400cc5037585"),
    ];
    for (identity, path, bytes, canonical, seal) in cases {
        let documents = [SourceDocument {
            relative_path: path,
            bytes,
        }];
        let review =
            sealed(reviewer().review(ReviewInput::Documents(DocumentSet {
                revision: &format!("golden-{identity}"),
                documents: &documents,
            })));
        assert_eq!(
            blake3::hash(&review.canonical_bytes()).to_hex().as_str(),
            canonical
        );
        assert_eq!(review.seal(), seal);
    }
}

/// 验证四语言允许的行末指令及相近的非法写法
#[test]
fn profile_directives_and_trailing_comments_are_exact() {
    for row in include_str!("fixtures/trailing-comments.tsv").lines() {
        let mut fields = row.splitn(3, '\t');
        let path = fields.next().unwrap();
        let expected = fields.next().unwrap().parse::<usize>().unwrap();
        let source = fields.next().unwrap().replace("\\n", "\n");
        let review =
            sealed(review_sources(&reviewer(), path, &[(path, &source)]));
        let count = review
            .findings()
            .iter()
            .filter(|finding| finding.rule() == "source.trailing_comment")
            .count();
        assert_eq!(count, expected, "{path}");
    }
}

/// 验证未注册词元的结果确定，注册变更可还原
#[test]
fn project_registry_changes_new_authority_identity() {
    let mut base: serde_json::Value = serde_json::from_str(AUTHORITY).unwrap();
    base["token_vocabulary"]
        .as_array_mut()
        .unwrap()
        .extend([serde_json::json!("phase"), serde_json::json!("value")]);
    let mut admitted = base.clone();
    admitted["token_vocabulary"]
        .as_array_mut()
        .unwrap()
        .push(serde_json::json!("mystery"));
    let execute = |authority: &serde_json::Value| {
        sealed(review_sources(
            &compile_value(authority).unwrap(),
            "registration",
            &[
                ("src/registration.py", "mystery_value = 1\nphase_m = 1\n"),
                ("src/registration.c", "int _mystery;\n"),
            ],
        ))
    };
    let first = execute(&base);
    let second = execute(&admitted);
    let third = execute(&base);

    assert_eq!(first.canonical_bytes(), third.canonical_bytes());
    assert_ne!(authority_digest(&first), authority_digest(&second));
    assert!(
        first
            .findings()
            .iter()
            .any(|finding| finding.rule() == "identifier.unknown_token")
    );
    assert!(
        !second
            .findings()
            .iter()
            .any(|finding| finding.rule() == "identifier.unknown_token")
    );
    for rule in ["identifier.reserved", "identifier.representation_suffix"] {
        assert!(
            second
                .findings()
                .iter()
                .any(|finding| finding.rule() == rule)
        );
    }
}

/// 验证六类项目事实在访问源码前检查格式、位置和重复项
#[test]
fn authority_rows_are_closed_before_source_access() {
    let rows = include_str!("fixtures/authority-rejections.jsonl")
        .lines()
        .collect::<Vec<_>>();
    assert_raw_authority_rejected(&rows);
    let mut authority: serde_json::Value =
        serde_json::from_str(AUTHORITY).unwrap();
    authority["external_fixed_identifiers"] = serde_json::json!([{
        "profile": "rust",
        "role": "function",
        "owner": "fmt::r#type",
        "spelling": "fmt"
    }]);
    let review = sealed(review_sources(
        &compile_value(&authority).unwrap(),
        "raw-trait-owner",
        &[(
            "src/value.rs",
            "struct Velocity;\nimpl fmt::r#type for Velocity {\n    /// 格式化速度\n    fn fmt(&self) {}\n}\n",
        )],
    ));
    assert!(!review.findings().iter().any(|finding| {
        finding.rule() == "identifier.unknown_token"
            && finding.subject() == "fmt"
    }));
}

/// 验证工作区拒绝非 Unicode 路径和规范化后重名的路径
#[cfg(unix)]
#[test]
fn workspace_source_identity_is_unique() {
    use std::os::unix::ffi::OsStringExt;

    let assert_workspace_rejected = |path: &std::path::Path| {
        assert_eq!(
            reviewer()
                .review(ReviewInput::Workspace(path))
                .disposition(),
            Disposition::Rejected
        );
    };
    let invalid = tempfile::tempdir().unwrap();
    let name = std::ffi::OsString::from_vec(b"value\xff.py".to_vec());
    std::fs::write(invalid.path().join(name), VALID_PYTHON).unwrap();
    assert_workspace_rejected(invalid.path());
    let root = tempfile::tempdir().unwrap();
    let root = root
        .path()
        .join(std::ffi::OsString::from_vec(b"root\xff".to_vec()));
    std::fs::create_dir(&root).unwrap();
    assert_workspace_rejected(&root);

    let collision = tempfile::tempdir().unwrap();
    std::fs::create_dir(collision.path().join("src")).unwrap();
    std::fs::write(collision.path().join("src/value.py"), VALID_PYTHON)
        .unwrap();
    std::fs::write(collision.path().join("src\\value.py"), VALID_PYTHON)
        .unwrap();
    assert_workspace_rejected(collision.path());
}

/// 验证量值名称在去重和访问源码前完成语法检查
#[test]
fn quantity_admission_closes_raw_grammar_before_review() {
    for (case, quantity) in [
        ("empty concept", r#"{"":["rad"]}"#),
        ("concept whitespace", r#"{"phase offset":["rad"]}"#),
        ("empty family", r#"{"phase":[]}"#),
        ("duplicate suffix", r#"{"phase":["rad","rad"]}"#),
        ("uppercase concept", r#"{"Phase":["rad"]}"#),
        ("uppercase suffix", r#"{"phase":["RAD"]}"#),
        ("suffix whitespace", r#"{"phase":["rad "]}"#),
        ("leading separator", r#"{"_phase":["rad"]}"#),
        ("trailing separator", r#"{"phase_":["rad"]}"#),
        ("repeated separator", r#"{"phase__offset":["rad"]}"#),
        ("suffix leading separator", r#"{"phase":["_rad"]}"#),
        ("suffix trailing separator", r#"{"phase":["rad_"]}"#),
        ("suffix repeated separator", r#"{"phase":["m__s"]}"#),
        ("leading digit", r#"{"phase":["2m"]}"#),
        ("interleaved digit", r#"{"phase":["m2s"]}"#),
        ("decomposition", r#"{"phase":["rad"],"phase_rad":["deg"]}"#),
    ] {
        let mut authority = serde_json::json!({"schema_version": 4});
        authority["quantity_concepts"] =
            serde_json::from_str(quantity).unwrap();
        let code = compile_value(&authority)
            .err()
            .map(|rejection| rejection.code().to_owned());
        assert_eq!(code.as_deref(), Some("authority.quantity"), "{case}");
    }
    let mut valid = serde_json::json!({"schema_version": 4});
    valid["quantity_concepts"] =
        serde_json::json!({"acceleration": ["m_per_s2"]});
    compile_value(&valid).expect("trailing suffix digits must compile");
}

/// 验证项目事实重排不改变身份，内容变化改变身份
#[test]
fn project_fact_identity_is_canonical_and_changes_with_facts() {
    let base: serde_json::Value = serde_json::from_str(AUTHORITY).unwrap();
    let base_identity = authority_identity(&base);
    let mut explicit_empty_dependency = base.clone();
    explicit_empty_dependency["dependency_authority"] = serde_json::json!({});
    assert_eq!(
        base_identity,
        authority_identity(&explicit_empty_dependency)
    );
    let mut permuted = base.clone();
    permuted["token_vocabulary"]
        .as_array_mut()
        .unwrap()
        .reverse();
    for suffixes in permuted["quantity_concepts"]
        .as_object_mut()
        .unwrap()
        .values_mut()
    {
        suffixes.as_array_mut().unwrap().reverse();
    }
    assert_eq!(base_identity, authority_identity(&permuted));
    for (field, value) in [
        ("public_callables", "{}"),
        ("token_vocabulary", "[]"),
        ("quantity_concepts", "{}"),
        (
            "external_fixed_identifiers",
            r#"[{"profile":"rust","role":"function","owner":"fmt::Display","spelling":"fmt"}]"#,
        ),
        ("dependency_authority", r#"{"python_reorder_safe":true}"#),
    ] {
        let mut changed = base.clone();
        changed[field] = serde_json::from_str(value).unwrap();
        assert_ne!(base_identity, authority_identity(&changed), "{field}");
        assert_trailing_hard(&changed);
    }
    let mut changed_header = base.clone();
    changed_header["header_languages"]["documents/valid/c/calculate_velocity.h"] =
        serde_json::json!("cpp");
    assert_ne!(base_identity, authority_identity(&changed_header));
    assert_trailing_hard(&changed_header);
    let first = br#"{"schema_version":4,"quantity_concepts":{"alpha":["rad"],"beta":["deg"]}}"#;
    let second = br#"{"schema_version":4,"quantity_concepts":{"beta":["deg"],"alpha":["rad"]}}"#;
    assert_eq!(
        authority_identity_bytes(first),
        authority_identity_bytes(second)
    );
}

/// 验证文件与内存输入对六种语言选择情形给出相同证据
#[test]
fn source_inputs_share_profile_admission() {
    let mut authority: serde_json::Value =
        serde_json::from_str(AUTHORITY).unwrap();
    authority["public_callables"] = serde_json::json!({});
    authority["header_languages"] =
        serde_json::json!({"c_header.h": "c", "cpp_header.h": "cpp"});
    let reviewer = compile_value(&authority).unwrap();
    let cases: [(&str, &[u8]); 6] = [
        ("value.py", b"distance_m = 1\n"),
        ("value.rs", b"const DISTANCE_M: i32 = 1;\n"),
        ("value.c", b"int distance_m;\n"),
        ("value.cpp", b"int distance_m;\n"),
        ("c_header.h", b"int distance_m;\n"),
        ("cpp_header.h", b"int distance_m;\n"),
    ];
    let documents = cases.map(|(relative_path, bytes)| SourceDocument {
        relative_path,
        bytes,
    });
    let document_review =
        sealed(reviewer.review(ReviewInput::Documents(DocumentSet {
            revision: "transport-correspondence",
            documents: &documents,
        })));
    let workspace_results: [SealedReview; 2] = std::array::from_fn(|_| {
        let workspace = tempfile::tempdir().unwrap();
        for (relative_path, bytes) in cases {
            std::fs::write(workspace.path().join(relative_path), bytes)
                .unwrap();
        }
        sealed(reviewer.review(ReviewInput::Workspace(workspace.path())))
    });
    let [first, second] = &workspace_results;
    let projections = [&document_review, first, second].map(|review| {
        let mut value: serde_json::Value =
            serde_json::from_slice(&review.canonical_bytes()).unwrap();
        value.as_object_mut().unwrap().remove("scope");
        value.as_object_mut().unwrap().remove("seal");
        value
    });
    assert!(projections.windows(2).all(|pair| pair[0] == pair[1]));
    assert_ne!(first.seal(), second.seal());
}

/// 验证无效文档身份与未知语言在读取源码前被拒绝
#[test]
fn document_identity_validate_before_capture() {
    let reviewer = reviewer();
    let assert_rejected = |sources: &[(&str, &str)]| {
        assert_eq!(
            review_sources(&reviewer, "invalid-document", sources)
                .disposition(),
            Disposition::Rejected
        );
    };
    assert_rejected(&[
        ("src/value.py", "distance_m = 1\n"),
        ("src\\value.py", "distance_m = 1\n"),
    ]);
    for path in [
        "",
        "src/./value.py",
        "src/../value.py",
        "src//value.py",
        "/src/value.py",
        r"C:\src\value.py",
        "src/value.h",
        "src/value.txt",
    ] {
        assert_rejected(&[(path, "distance_m = 1\n")]);
    }
}
