use csu::AuthorityDocument;
use csu::AuthorityInput;
use csu::FindingGrade;
use csu::ReviewTerminal;
use csu::WorkspaceReviewer;
use std::collections::BTreeSet;

mod review_fixture;

use review_fixture::review_sources;

const AUTHORITY: &[u8] =
    include_bytes!("../docs/fixtures/core/authority.json");

/// 审查内存源码并返回封存终态
fn review(sources: &[(&str, &str)]) -> csu::SealedReview {
    let authority = [AuthorityDocument {
        relative_path: "authority.json",
        bytes: AUTHORITY,
    }];
    let reviewer =
        WorkspaceReviewer::compile(AuthorityInput::Documents(&authority))
            .expect("frozen Authority must compile");
    let ReviewTerminal::Sealed(review) =
        review_sources(&reviewer, "identifier-forms", sources)
    else {
        panic!("valid source must seal");
    };
    review
}

/// 验证四语言接纳各声明角色的规范名称
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
                "const double VELOCITY = 1.0;\n",
                "typedef struct distance { double distance_m; } velocity_t;\n",
                "enum distance { VELOCITY };\n",
                "double calculate_velocity(double distance_m);\n"
            ),
        ),
        (
            "src/forms.cpp",
            concat!(
                "#define VELOCITY 1\n",
                "constexpr double VELOCITY = 1.0;\n",
                "class Velocity { public: double distance_m; ",
                "private: double velocity_m_per_s_; };\n",
                "enum Distance { VELOCITY };\n",
                "double calculate_velocity(double distance_m);\n"
            ),
        ),
    ];
    let review = review(&sources);

    assert!(
        review
            .findings()
            .iter()
            .all(|finding| !finding.rule().starts_with("identifier.")),
        "findings: {:#?}",
        review.findings()
    );
}

/// 验证四语言拒绝错误命名形式和保留名称
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
    let review = review(&sources);
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

/// 验证候选判定优先且每个声明只报告一项命名问题
#[test]
fn candidate_priority_still_yields_one_identifier_finding_per_declaration() {
    let sources = [
        ("src/candidate.py", "Q = 1\n"),
        ("src/candidate.rs", "const Q: i32 = 1;\n"),
        ("src/candidate.c", "int _Q;\n"),
        ("src/candidate.cpp", "int _Q;\n"),
    ];
    let review = review(&sources);
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

/// 创建扩展指定词表的测试审查器
fn reviewer_with_vocabulary(extra: &[&str]) -> csu::WorkspaceReviewer {
    let mut authority: serde_json::Value =
        serde_json::from_slice(AUTHORITY).unwrap();
    for token in extra {
        authority["token_vocabulary"]
            .as_array_mut()
            .unwrap()
            .push(serde_json::json!(token));
    }
    let bytes = serde_json::to_vec(&authority).unwrap();
    let documents = [AuthorityDocument {
        relative_path: "authority.json",
        bytes: &bytes,
    }];
    WorkspaceReviewer::compile(AuthorityInput::Documents(&documents)).unwrap()
}

/// 验证源码词元与注册输入使用相同的小写处理
#[test]
fn observed_tokens_and_admission_share_one_lowercase_owner() {
    // 全大写段按完整 token 的 str::to_lowercase 归一化：词尾大写
    // 西格玛产生 ς；词表注册 abς 后该 token 命中词表，混合大小写
    // 形式随之成为 canonical form 证据而不是 unknown token
    let reviewer = reviewer_with_vocabulary(&["abς"]);
    // 单字符按原始 token 判断，小写展开不改变其 Candidate 身份
    for (sources, expected) in [
        (
            ["ABΣ = 1\n", "i\u{307} = 1\n"],
            ("identifier.canonical_form", FindingGrade::HardViolation),
        ),
        (
            ["abΣ = 1\n", "İ = 1\n"],
            ("identifier.candidate", FindingGrade::ReviewRequired),
        ),
    ] {
        for source in sources {
            assert_identifier_outcome(
                &reviewer,
                "src/final_sigma.py",
                source,
                Some(expected),
            );
        }
    }
}

/// 验证前缀接纳九种角色并拒绝 min/max 与复合形式
#[test]
fn forbidden_and_compound_prefixes_keep_frozen_contract() {
    let reviewer = reviewer_with_vocabulary(&[]);
    let source: String = [
        "maximum", "minimum", "should", "lower", "needs", "upper", "can",
        "has", "is",
    ]
    .into_iter()
    .map(|prefix| format!("{prefix}_duration_s = 1\n"))
    .chain([
        "min_duration_s = 1\n".to_owned(),
        "max_duration_s = 1\n".to_owned(),
        "is_has_duration_s = 1\n".to_owned(),
        "is_min_duration_s = 1\n".to_owned(),
    ])
    .collect();
    let ReviewTerminal::Sealed(review) = review_sources(
        &reviewer,
        "prefix-outcomes",
        &[("src/prefix_forms.py", &source)],
    ) else {
        panic!("prefix probe must seal");
    };
    let hard_subjects: Vec<_> = review
        .findings()
        .iter()
        .filter(|finding| finding.grade() == FindingGrade::HardViolation)
        .map(|finding| finding.subject())
        .collect();
    assert_eq!(
        hard_subjects,
        [
            "min_duration_s",
            "max_duration_s",
            "is_has_duration_s",
            "is_min_duration_s",
        ],
        "{:#?}",
        review.findings()
    );
}

/// 验证模块、命名空间、标签和生命周期名称均受检
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
    let review = review(&sources);
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

/// 表示 Quantity 声明使用的语法画像
#[derive(Clone, Copy)]
enum QuantitySyntax {
    Python,
    Rust,
    Native,
}

const QUANTITY_PROFILES: [(&str, QuantitySyntax); 4] = [
    ("src/quantity.py", QuantitySyntax::Python),
    ("src/quantity.rs", QuantitySyntax::Rust),
    ("src/quantity.c", QuantitySyntax::Native),
    ("src/quantity.cpp", QuantitySyntax::Native),
];
const HARD_SUFFIX: (&str, FindingGrade) = (
    "identifier.representation_suffix",
    FindingGrade::HardViolation,
);

/// 构造指定语言的变量声明源码
fn quantity_source(syntax: QuantitySyntax, spelling: &str) -> String {
    match syntax {
        QuantitySyntax::Python => format!("{spelling} = 1\n"),
        QuantitySyntax::Rust => format!(
            concat!(
                "/// 计算持续时长\n",
                "fn calculate_duration() -> f64 {{\n",
                "    let {spelling} = 1.0;\n",
                "    {spelling}\n",
                "}}\n",
            ),
            spelling = spelling,
        ),
        QuantitySyntax::Native => format!("double {spelling} = 1.0;\n"),
    }
}

/// 断言单文档没有命名问题或仅有指定问题
fn assert_identifier_outcome(
    reviewer: &csu::WorkspaceReviewer,
    path: &str,
    source: &str,
    expected: Option<(&str, FindingGrade)>,
) {
    let terminal =
        review_sources(reviewer, "quantity-disposition", &[(path, source)]);
    let ReviewTerminal::Sealed(review) = terminal else {
        panic!("quantity disposition probe must seal: {terminal:#?}")
    };
    let actual: Vec<_> = review
        .findings()
        .iter()
        .map(|finding| (finding.rule(), finding.grade()))
        .collect();
    assert_eq!(actual, expected.into_iter().collect::<Vec<_>>(), "{path}");
}

/// 验证量值名称、显式复合名称及后缀别名按登记关系判断
#[test]
fn quantity_name_dispositions_close_per_declared_concepts() {
    let reviewer = reviewer_with_vocabulary(&["offset", "phase"]);
    let mut authority: serde_json::Value =
        serde_json::from_slice(AUTHORITY).unwrap();
    let mut isolated = authority.clone();
    isolated["token_vocabulary"] = serde_json::json!(["delivery"]);
    isolated["quantity_concepts"] = serde_json::json!({"phase": ["mystery"]});
    let isolated = reviewer_from_value(&isolated);
    for (path, syntax) in QUANTITY_PROFILES {
        for (spelling, expected) in [
            ("phase", Some(HARD_SUFFIX)),
            ("phase_rad", None),
            ("phase_m", Some(HARD_SUFFIX)),
        ] {
            assert_identifier_outcome(
                &reviewer,
                path,
                &quantity_source(syntax, spelling),
                expected,
            );
        }
    }
    assert_identifier_outcome(
        &isolated,
        "src/quantity.py",
        &quantity_source(QuantitySyntax::Python, "delivery_mystery"),
        Some(("identifier.unknown_token", FindingGrade::ReviewRequired)),
    );
    for token in ["offset", "phase"] {
        authority["token_vocabulary"]
            .as_array_mut()
            .unwrap()
            .push(serde_json::json!(token));
    }
    authority["quantity_concepts"]["phase_offset"] =
        serde_json::json!(["rad"]);
    let compound = reviewer_from_value(&authority);
    for (path, syntax) in QUANTITY_PROFILES {
        for (spelling, expected) in [
            ("phase_offset", Some(HARD_SUFFIX)),
            ("phase_offset_rad", None),
        ] {
            assert_identifier_outcome(
                &compound,
                path,
                &quantity_source(syntax, spelling),
                expected,
            );
        }
    }
    let mut alias = authority;
    let not_allowed = reviewer_from_value(&alias);
    alias["quantity_concepts"]["phase"] =
        serde_json::json!(["rad", "deg", "radians"]);
    let allowed = reviewer_from_value(&alias);
    for (path, syntax) in QUANTITY_PROFILES {
        assert_identifier_outcome(
            &not_allowed,
            path,
            &quantity_source(syntax, "phase_radians"),
            Some(("identifier.unknown_token", FindingGrade::ReviewRequired)),
        );
        assert_identifier_outcome(
            &allowed,
            path,
            &quantity_source(syntax, "phase_radians"),
            None,
        );
    }
}

/// 根据 JSON 值创建审查器
fn reviewer_from_value(
    authority: &serde_json::Value,
) -> csu::WorkspaceReviewer {
    let bytes = serde_json::to_vec(authority).unwrap();
    WorkspaceReviewer::compile(AuthorityInput::Documents(&[
        AuthorityDocument {
            relative_path: "authority.json",
            bytes: &bytes,
        },
    ]))
    .unwrap()
}
