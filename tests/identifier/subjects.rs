use csu::AuthorityInput;
use csu::FactFamily;
use csu::FactFamilyState;
use csu::FindingGrade;
use csu::ReviewTerminal;
use csu::WorkspaceReviewer;

#[path = "../review_fixture/mod.rs"]
mod review_fixture;

use review_fixture::compile_value;
use review_fixture::review_sources;

const AUTHORITY: &[u8] =
    include_bytes!("../../docs/fixtures/core/authority.json");
const UNKNOWN_REVIEW: (&str, FindingGrade) =
    ("identifier.unknown_token", FindingGrade::ReviewRequired);
const HARD_CANONICAL: (&str, FindingGrade) =
    ("identifier.canonical_form", FindingGrade::HardViolation);
const HARD_RESERVED: (&str, FindingGrade) =
    ("identifier.reserved", FindingGrade::HardViolation);

/// 验证范围绑定与普通绑定具有相同的声明和命名义务
#[test]
fn native_binding_forms_keep_identifier_subjects() {
    for (source, count, names) in [
        (
            "void calculate_distance() { int distance_m[2]; for (int BadName : distance_m) {} }",
            3,
            vec!["BadName"],
        ),
        (
            "void calculate_distance() { int distance_m[2][2]; for (auto &[BadName, OtherName] : distance_m) {} }",
            4,
            vec!["BadName", "OtherName"],
        ),
        (
            "void calculate_distance() { int distance_m[2]; auto [BadName, OtherName] = distance_m; }",
            4,
            vec!["BadName", "OtherName"],
        ),
        (
            "void calculate_distance() { if (int BadName = 1) {} while (int OtherName = 1) {} }",
            3,
            vec!["BadName", "OtherName"],
        ),
    ] {
        let review = review_source("src/range.cpp", source);
        assert_eq!(identifier_count(&review), count, "{source}");
        for name in names {
            assert!(
                review
                    .findings()
                    .iter()
                    .any(|finding| finding.subject() == name
                        && finding.rule() == HARD_CANONICAL.0),
                "{source}"
            );
        }
    }
}

/// 验证对象角色来自各声明的限定层级而不是共享的类型说明符
#[test]
fn native_declarator_type_forms_keep_object_roles() {
    for path in ["src/objects.c", "src/objects.cpp"] {
        for source in [
            "const int *distance_m;",
            "const int DISTANCE_M = 1, *duration_s = 0;",
            "int *const DISTANCE_M = 0;",
            "void (*calculate_distance)(int distance_m);",
        ] {
            let review = review_source(path, source);
            assert!(
                review.findings().is_empty(),
                "{path}: {source}: {:#?}",
                review.findings()
            );
        }
        let review = review_source(path, "int *const distance_m = 0;");
        assert_single_rule(&review, Some(HARD_CANONICAL));
    }
}

/// 验证合法常量形式保持精确量值登记而不制造候选后缀
#[test]
fn constant_forms_keep_registered_representation() {
    for (path, source) in [
        ("src/quantity.py", "NAME = 1\n"),
        ("src/quantity.rs", "const NAME: f64 = 1.0;\n"),
        ("src/quantity.c", "const double NAME = 1.0;\n"),
        ("src/quantity.cpp", "constexpr double NAME = 1.0;\n"),
    ] {
        for (name, expected) in [
            ("DISTANCE_M", None),
            (
                "DISTANCE",
                Some((
                    "identifier.representation_suffix",
                    FindingGrade::HardViolation,
                )),
            ),
            (
                "DISTANCE_S",
                Some((
                    "identifier.representation_suffix",
                    FindingGrade::HardViolation,
                )),
            ),
            (
                "Q",
                Some(("identifier.candidate", FindingGrade::ReviewRequired)),
            ),
        ] {
            let review = review_source(path, &source.replace("NAME", name));
            assert_eq!(identifier_count(&review), 1);
            assert_single_rule(&review, expected);
        }
    }
}

/// 验证 Python 原生类型和成员的来源证据沿不同声明形式保持一致
#[test]
fn python_native_sources_keep_declaration_roles() {
    for source in [
        "from typing import TypeAlias as Declaration\nFieldValue: Declaration = int\n",
        "from enum import Enum, member\nclass Direction(Enum):\n    @member\n    def LEFT():\n        return 1\n",
        "from enum import Enum, nonmember\nclass Direction(Enum):\n    left = nonmember(1)\n",
        "from enum import Enum\nclass Direction(Enum):\n    @staticmethod\n    def lower_name():\n        return 1\n",
        "from enum import Enum, member as staticmethod\nclass Direction(Enum):\n    @staticmethod\n    def LEFT():\n        return 1\n",
        "from enum import Enum\nclass Direction(Enum):\n    @classmethod\n    def lower_name(cls):\n        return 1\n",
        "from enum import Enum, member as classmethod\nclass Direction(Enum):\n    @classmethod\n    def LEFT():\n        return 1\n",
        "from enum import Enum\nclass Direction(Enum):\n    @property\n    def lower_name(self):\n        return 1\n",
        "from enum import Enum, member as property\nclass Direction(Enum):\n    @property\n    def LEFT():\n        return 1\n",
        "from enum import Enum, nonmember\nclass Direction(Enum):\n    @nonmember\n    def lower_name():\n        return 1\n",
    ] {
        let review = review_source("src/roles.py", source);
        assert!(identifier_count(&review) > 0);
        assert!(
            !review
                .findings()
                .iter()
                .any(|finding| finding.rule() == HARD_CANONICAL.0),
            "{source}: {:#?}",
            review.findings()
        );
    }
    let review = review_source(
        "src/roles.py",
        "TypeAlias = int\nFieldValue: TypeAlias = 1\n",
    );
    assert!(
        review
            .findings()
            .iter()
            .any(|finding| finding.subject() == "FieldValue"
                && finding.rule() == HARD_CANONICAL.0)
    );
}

/// 验证 Python 原生声明角色不会退化成普通赋值或接收者
#[test]
fn python_native_declaration_roles_keep_canonical_names() {
    for (source, subject, expected_count) in [
        (
            "from builtins import classmethod as method\nclass Distance:\n    @method\n    def value(cls) -> int:\n        return 1\n",
            "cls",
            4,
        ),
        (
            "class Distance:\n    @property\n    def value(self) -> int:\n        \"\"\"\n        读取数值\n\n        Args:\n            无\n        Returns:\n            int: 输出值\n        Raises:\n            无\n        \"\"\"\n        return 1\n    @value.setter\n    def value(self, distance_m: int) -> None:\n        \"\"\"\n        读取数值\n\n        Args:\n            distance_m: 输入距离\n        Returns:\n            无\n        Raises:\n            无\n        \"\"\"\n        pass\n    @value.deleter\n    def value(self) -> None:\n        \"\"\"\n        读取数值\n\n        Args:\n            无\n        Returns:\n            无\n        Raises:\n            无\n        \"\"\"\n        pass\n",
            "self",
            8,
        ),
        (
            "class Distance:\n    @transform\n    def value(self) -> int:\n        \"\"\"\n        读取数值\n\n        Args:\n            无\n        Returns:\n            int: 输出值\n        Raises:\n            无\n        \"\"\"\n        return 1\n",
            "self",
            3,
        ),
        (
            "from enum import Enum\nclass Direction(Enum):\n    LEFT = 1\n",
            "LEFT",
            2,
        ),
        (
            "from typing import TypeVar\n_FieldValue = TypeVar(\"_FieldValue\")\n",
            "_FieldValue",
            1,
        ),
        (
            "class Medium:\n    def __init_subclass__(cls) -> None:\n        pass\n",
            "cls",
            3,
        ),
        (
            "import ctypes\nclass MemoryStatus(ctypes.Structure):\n    _fields_ = []\n",
            "_fields_",
            2,
        ),
        (
            "from enum import IntFlag as Options\nclass Direction(Options):\n    LEFT = 1\n",
            "LEFT",
            3,
        ),
        (
            "import enum as choices\nclass Direction(choices.StrEnum):\n    LEFT = 'left'\n",
            "LEFT",
            3,
        ),
        (
            "from typing import TypeVar as Parameter\n_FieldValue = Parameter(\"_FieldValue\")\n",
            "_FieldValue",
            2,
        ),
        (
            "import typing as types\n_FieldValue = types.TypeVar(\"_FieldValue\")\n",
            "_FieldValue",
            2,
        ),
        (
            "from ctypes import Union as Storage\nclass MemoryStatus(Storage):\n    _fields_ = []\n",
            "_fields_",
            3,
        ),
        (
            "class Medium:\n    def __init_subclass__(\n        # 子类接收者\n        cls,\n    ) -> None:\n        pass\n",
            "cls",
            3,
        ),
        (
            "class Medium:\n    def __class_getitem__(cls, index):\n        pass\n",
            "cls",
            4,
        ),
    ] {
        let review = review_source("src/native_roles.py", source);
        assert_eq!(identifier_count(&review), expected_count, "{source}");
        if source.contains("Args:") {
            assert!(
                !review.findings().iter().any(|finding| finding.rule()
                    == "documentation.public_contract"),
                "{source}: {:#?}",
                review.findings()
            );
        }
        assert!(
            !review.findings().iter().any(|finding| {
                finding.subject() == subject
                    && (finding.grade() == FindingGrade::HardViolation
                        || matches!(subject, "self" | "cls"))
            }),
            "{subject}: {:#?}",
            review.findings()
        );
    }
    let review = review_source(
        "src/native_roles.py",
        "from enum import Enum\nclass Direction(Enum):\n    Q = 1\n",
    );
    assert_eq!(identifier_count(&review), 2);
    assert_eq!(candidate_subjects(&review), ["Q"]);
}

/// 验证原生角色识别不会豁免普通绑定、同名对象或不合规形式
#[test]
fn python_native_roles_require_direct_import_and_binding_evidence() {
    for (source, subject) in [
        (
            "from builtins import staticmethod as method\nclass Distance:\n    @method\n    def value(cls) -> int:\n        return 1\n",
            "cls",
        ),
        ("class Direction:\n    LEFT = 1\n", "LEFT"),
        (
            "class Enum:\n    pass\nclass Direction(Enum):\n    LEFT = 1\n",
            "LEFT",
        ),
        (
            "from enum import Enum\nEnum = object\nclass Direction(Enum):\n    LEFT = 1\n",
            "LEFT",
        ),
        (
            "from enum import Enum\nif active:\n    Enum = object\nclass Direction(Enum):\n    LEFT = 1\n",
            "LEFT",
        ),
        (
            "from enum import Enum\nif active:\n    Enum = object\n    class Direction(Enum):\n        LEFT = 1\n",
            "LEFT",
        ),
        (
            "from another import Enum\nclass Direction(Enum):\n    LEFT = 1\n",
            "LEFT",
        ),
        (
            "from enum import Enum\nclass Direction(Enum):\n    left = 1\n",
            "left",
        ),
        (
            "from typing import TypeVar\nTypeVar = object\n_FieldValue = TypeVar(\"_FieldValue\")\n",
            "_FieldValue",
        ),
        (
            "from typing import TypeVar\nfield_value = TypeVar(\"field_value\")\n",
            "field_value",
        ),
        ("class MemoryStatus:\n    _fields_ = []\n", "_fields_"),
        (
            "import ctypes\nctypes = other\nclass MemoryStatus(ctypes.Structure):\n    _fields_ = []\n",
            "_fields_",
        ),
        (
            "import ctypes\nctypes.Structure = other\nclass MemoryStatus(ctypes.Structure):\n    _fields_ = []\n",
            "_fields_",
        ),
        (
            "import ctypes\nctypes . Structure = other\nclass MemoryStatus(ctypes.Structure):\n    _fields_ = []\n",
            "_fields_",
        ),
        ("def __init_subclass__(cls) -> None:\n    pass\n", "cls"),
        (
            "class Medium:\n    @staticmethod\n    def __init_subclass__(cls) -> None:\n        pass\n",
            "cls",
        ),
    ] {
        let review = review_source("src/native_roles.py", source);
        assert!(identifier_count(&review) > 0);
        assert!(
            review.findings().iter().any(|finding| {
                finding.subject() == subject
                    && finding.rule()
                        == if subject == "cls" {
                            "identifier.unknown_token"
                        } else {
                            "identifier.canonical_form"
                        }
            }),
            "{source}: {:#?}",
            review.findings()
        );
    }
}

/// 验证枚举动态成员归属不被猜成普通变量或已通过的常量
#[test]
fn python_unresolved_variant_declarations_keep_identifier_coverage_incomplete()
{
    for source in [
        "from enum import Enum\nclass Direction(Enum):\n    left = descriptor()\n",
        "from enum import Enum\nclass Direction(Enum):\n    _ignore_ = names\n    LEFT = 1\n",
        "from enum import Enum\nfrom typing import TypeVar\nclass Direction(Enum):\n    FieldValue = TypeVar('FieldValue')\n",
        "from enum import Enum, member\nclass Direction(Enum):\n    @transform\n    @member\n    def LEFT():\n        return 1\n    RIGHT = 2\n",
        "from enum import Enum, member\nclass Direction(Enum):\n    _ignore_ = names\n    @member\n    def LEFT():\n        return 1\n",
        "from enum import Enum, member\nDECORATOR = member\nclass Direction(Enum):\n    @DECORATOR\n    def lower_name(cls):\n        return 1\n",
        "from enum import Enum, member\nclass Direction(Enum):\n    DECORATOR = member\n    @DECORATOR\n    def lower_name(cls):\n        return 1\n",
        "from enum import Enum\nfrom other import DECORATOR\nclass Direction(Enum):\n    @DECORATOR\n    def lower_name(cls):\n        return 1\n",
        "from enum import Enum, member\nif active:\n    DECORATOR = member\nclass Direction(Enum):\n    @DECORATOR\n    def lower_name(cls):\n        return 1\n",
        "from enum import Enum, member\nclass Direction(Enum):\n    if active:\n        DECORATOR = member\n    @DECORATOR\n    def lower_name(cls):\n        return 1\n",
        "from other import *\nfrom enum import Enum\nclass Direction(Enum):\n    @DECORATOR\n    def lower_name(cls):\n        return 1\n",
        "from enum import Enum\nclass Direction(Enum):\n    @unknown\n    def lower_name(cls):\n        return 1\n",
    ].into_iter().flat_map(|source| {
        ["staticmethod", "classmethod", "property"].map(|name| source.replace("DECORATOR", name))
    }) {
        let review = review_source("src/native_roles.py", &source);
        assert!(
            review.coverage().files()[0].families().iter().any(
                |(family, state)| {
                    *family == FactFamily::Identifier
                        && matches!(state, FactFamilyState::Blocked(_))
                }
            ),
            "{source}"
        );
        if source.contains("(cls)") {
            assert!(review.findings().iter().any(|finding| finding.subject() == "cls"), "{source}");
        }
        assert!(
            !review
                .findings()
                .iter()
                .any(|finding| finding.rule() == "identifier.canonical_form" && finding.subject() != "cls")
        );
    }
}

/// 审查单份内存源码并返回封存终态
fn review_source<'source>(
    path: &'source str,
    source: &'source str,
) -> csu::SealedReview {
    let reviewer = compile_value(&serde_json::from_slice(AUTHORITY).unwrap())
        .expect("frozen Authority must compile");
    reviewed_source(&reviewer, path, source)
}

/// 用指定审查器检查单份内存源码
fn reviewed_source(
    reviewer: &WorkspaceReviewer,
    path: &str,
    source: &str,
) -> csu::SealedReview {
    let ReviewTerminal::Sealed(review) =
        review_sources(reviewer, "identifier-subjects", &[(path, source)])
    else {
        panic!("valid direct source must seal");
    };
    review
}

/// 收集需要复核的候选名称
fn candidate_subjects(review: &csu::SealedReview) -> Vec<String> {
    review
        .findings()
        .iter()
        .filter(|finding| finding.rule() == "identifier.candidate")
        .map(|finding| finding.subject().to_owned())
        .collect()
}

/// 读取已检查的标识符声明数量
fn identifier_count(review: &csu::SealedReview) -> u32 {
    let (_, state) = review.coverage().files()[0]
        .families()
        .iter()
        .find(|(family, _)| *family == FactFamily::Identifier)
        .expect("Identifier family must be recorded");
    match state {
        FactFamilyState::Complete(count) => *count,
        other => panic!("Identifier family did not close: {other:?}"),
    }
}

/// 验证 Python 绑定只检查一次且不把引用当作声明
#[test]
fn python_observes_each_binding_declaration_once_and_excludes_uses() {
    let source = r#"class X:
    Q: int = 1

    def f(self, T, /, *, V=1):
        K, *N = (T, V)
        self.W = K
        other.Z = W
        for I in K:
            pass
        with open("input") as H:
            pass
        try:
            pass
        except Exception as E:
            pass
"#;
    let review = review_source("src/subjects.py", source);

    assert_eq!(
        candidate_subjects(&review),
        ["X", "Q", "f", "T", "V", "K", "N", "W", "I", "H", "E"]
    );
    // 接收者 self 仍计入声明数量，但作为结构约定名称不报问题
    assert_eq!(identifier_count(&review), 12);
}

/// 验证 Python 类型参数、匿名函数参数和导入别名均被检查
#[test]
fn python_observes_type_parameters_anonymous_parameters_import_aliases() {
    let source = r#"type A[T] = tuple[T]
class C[T]:
    def F[U](self, V):
        G = lambda H: H
        import package as I
        match V:
            case J:
                return J
        return G(V)
"#;
    let review = review_source("src/python_generics.py", source);

    assert_eq!(
        candidate_subjects(&review),
        ["A", "T", "C", "T", "F", "U", "V", "G", "H", "I", "J"]
    );
    // 接收者 self 仍计入声明数量，但作为结构约定名称不报问题
    assert_eq!(identifier_count(&review), 12);
}

/// 验证 Rust 各类名称声明和绑定均只检查一次
#[test]
fn rust_observes_items_generics_lifetimes_fields_variants_and_bindings_once() {
    let source = r#"macro_rules! M { () => {} }
mod Q {
    use crate::thing as V;
    struct T<'a, K, const N: usize> { V: K }
    enum E { X, Y { Z: i32 } }
    trait H { type I; const J: i32; fn F(P: i32); }
    type A = i32;
    const B: i32 = 1;
    static C: i32 = 1;
    fn D<'b, L, const O: usize>(P: i32) {
        let (R, S) = (P, 2);
        'c: loop { break 'c; }
    }
    union U { W: i32 }
}
"#;
    let review = review_source("src/subjects.rs", source);

    assert_eq!(
        candidate_subjects(&review),
        [
            "M", "Q", "V", "T", "'a", "K", "N", "V", "E", "X", "Y", "Z", "H",
            "I", "J", "F", "P", "A", "B", "C", "D", "'b", "L", "O", "P", "R",
            "S", "'c", "U", "W"
        ]
    );
    assert_eq!(identifier_count(&review), 30);
}

/// 验证 Rust 枚举变体模式不被误判为绑定声明
#[test]
fn rust_variant_patterns_are_references_not_binding_declarations() {
    let source = r#"fn calculate() {
    match None {
        None => {}
        Some(Q) => { let R = Q; }
    }
}
"#;
    let review = review_source("src/variant_patterns.rs", source);

    assert_eq!(candidate_subjects(&review), ["Q", "R"]);
    assert_eq!(identifier_count(&review), 3);
}

/// 验证 Rust 大驼峰变量绑定仍触发命名形式违规
#[test]
fn rust_pascal_binding_remains_variant_reference() {
    let review = review_source(
        "src/pascal_binding.rs",
        "fn calculate() { let Velocity = 1; }\n",
    );

    assert!(review.findings().iter().any(|finding| {
        finding.subject() == "Velocity"
            && finding.rule() == "identifier.canonical_form"
    }));
}

/// 验证 C 各类直接声明均被检查
#[test]
fn procedural_source_observes_all_direct_declaration_kinds() {
    let source = r#"#define M(P, Q) ((P) + (Q))
#define O 1
typedef struct T { int F; } T_t;
enum E { A, B = 2 };
union U { int V; };
int G;
static int H(int I) {
J:
    for (int K = 0; K < 1; K++) {
        int L = K;
    }
    return I;
}
"#;
    let review = review_source("src/subjects.c", source);

    assert_eq!(
        candidate_subjects(&review),
        [
            "M", "P", "Q", "O", "T", "F", "T_t", "E", "A", "B", "U", "V", "G",
            "H", "I", "J", "K", "L"
        ]
    );
    assert_eq!(identifier_count(&review), 18);
}

/// 验证 C++ 检查声明名称但不把固定函数拼写和引用当作自选名称
#[test]
fn cpp_observes_declared_names_but_excludes_fixed_callable_spellings_and_uses()
{
    let source = r#"#define M(P, Q) ((P) + (Q))
namespace N {
template<class T, int K> using A = T;
class C {
public:
    int F;
    C();
    ~C();
    C& operator=(const C&);
    void G(int H);
private:
    int I_;
};
enum E { J, K };
struct S { int L; };
union U { int V; };
int W;
void X(int Y) {
Z:
    int Q = Y;
    auto [R, B] = std::pair{1, 2};
    auto O = [P = Y](int Q) { return P + Q; };
}
}
"#;
    let review = review_source("src/subjects.cpp", source);

    assert_eq!(
        candidate_subjects(&review),
        [
            "M", "P", "Q", "N", "T", "K", "A", "C", "F", "G", "H", "I_", "E",
            "J", "K", "S", "L", "U", "V", "W", "X", "Y", "Q", "R", "B", "O",
            "P", "Q"
        ]
    );
    assert_eq!(identifier_count(&review), 28);
}

/// 验证拉丁和希腊候选名称按完整词元及 Unicode 小写匹配
#[test]
fn candidate_registry_matches_frozen_latin_and_greek_forms() {
    const NAMED: [&str; 24] = [
        "alpha", "beta", "chi", "delta", "epsilon", "eta", "gamma", "iota",
        "kappa", "lambda", "mu", "nu", "omega", "omicron", "phi", "pi", "psi",
        "rho", "sigma", "tau", "theta", "upsilon", "xi", "zeta",
    ];
    let source: String = NAMED
        .into_iter()
        .map(|token| format!("_{token} = 1\n"))
        .chain(["Alpha = 1\n", "Q = 1\n", "Α = 1\n"].map(str::to_owned))
        .chain(["_alphabeta = 1\n", "_αβ = 1\n"].map(str::to_owned))
        .collect();
    let review = review_source("src/candidate_registry.py", &source);

    assert_eq!(
        candidate_subjects(&review),
        NAMED
            .into_iter()
            .map(|token| format!("_{token}"))
            .chain(["Alpha", "Q", "Α"].map(str::to_owned))
            .collect::<Vec<_>>()
    );
    let unknown: Vec<_> = review
        .findings()
        .iter()
        .filter(|finding| finding.rule() == "identifier.unknown_token")
        .map(|finding| finding.subject())
        .collect();
    assert_eq!(unknown, ["_alphabeta"]);
    assert_eq!(identifier_count(&review), 29);
}

/// 审查单份内存源码（带词表扩展）并返回封存终态
fn review_source_with(
    path: &str,
    source: &str,
    extra_tokens: &[&str],
) -> csu::SealedReview {
    let mut authority: serde_json::Value =
        serde_json::from_slice(AUTHORITY).unwrap();
    for token in extra_tokens {
        authority["token_vocabulary"]
            .as_array_mut()
            .unwrap()
            .push(serde_json::json!(token));
    }
    let reviewer =
        compile_value(&authority).expect("extended Authority must compile");
    reviewed_source(&reviewer, path, source)
}

/// 断言无问题或仅有一条指定规则的问题
fn assert_single_rule(
    review: &csu::SealedReview,
    expected: Option<(&str, FindingGrade)>,
) {
    match expected {
        None => {
            assert!(review.findings().is_empty(), "{:#?}", review.findings())
        }
        Some((rule, grade)) => {
            let [finding] = review.findings() else {
                panic!("expects exactly one finding: {:#?}", review.findings())
            };
            assert_eq!(finding.rule(), rule);
            assert_eq!(finding.grade(), grade);
        }
    }
}

/// 验证 Self 仅在对应语言结构中视为固定名称
#[test]
fn self_spelling_is_profile_owned() {
    let native_source = concat!(
        "/**\n",
        " * 计算平均速度\n",
        " *\n",
        " * 参数：\n",
        " * - Self：       行进距离\n",
        " * - duration_s： 持续时间\n",
        " * 返回：\n",
        " * - 平均速度\n",
        " * 错误：\n",
        " * - duration_s不大于零时返回错误\n",
        " */\n",
        "double calculate_velocity(double Self, double duration_s);\n",
    );
    for (path, source, expected) in [
        (
            "src/self_identity.rs",
            concat!(
                "struct Velocity { distance_m: f64 }\n",
                "impl Velocity {\n",
                "    /// 构造速度值\n",
                "    fn calculate(distance_m: f64) -> Self { Velocity { distance_m } }\n",
                "    type Self = Velocity;\n",
                "}\n",
            ),
            None,
        ),
        (
            "src/self_identity.rs",
            "/// 计算持续时长\nfn calculate_duration() -> f64 { let Self = 1.0; 1.0 }\n",
            Some(HARD_CANONICAL),
        ),
        ("src/self_identity.py", "Self = 1\n", Some(HARD_CANONICAL)),
        ("src/self_identity.c", native_source, Some(HARD_CANONICAL)),
        (
            "include/self_identity.hpp",
            native_source,
            Some(HARD_CANONICAL),
        ),
    ] {
        assert_single_rule(&review_source(path, source), expected);
    }
}

/// 验证四语言别名声明的现代与经典形式
#[test]
fn alias_declarations_cover_four_language_forms() {
    let cases = [
        (
            "src/alias.py",
            "from typing import TypeAlias\ntype Vector = list[float]\nDistance: TypeAlias = dict\n",
        ),
        ("src/alias.rs", "type DistanceVector = Vec<f64>;\n"),
        ("src/alias.c", "typedef int distance_vector_t;\n"),
        ("include/alias.hpp", "using DistanceVector = int;\n"),
    ];
    for (path, source) in cases {
        let review = review_source_with(path, source, &["vector"]);
        assert_single_rule(&review, None);
    }
}

/// 验证 Rust 模式绑定受检且条件引用不新增声明
#[test]
fn rust_match_pattern_bindings_are_judged_but_guards_are_not() {
    let source = concat!(
        "/// 计算持续时长\n",
        "fn calculate_duration(duration_s: f64) -> f64 {\n",
        "    match duration_s {\n",
        "        phase if phase > 0.0 => phase,\n",
        "        _ => 0.0,\n",
        "    }\n",
        "}\n",
    );
    let review = review_source_with("src/match_guard.rs", source, &["phase"]);
    let [finding] = review.findings() else {
        panic!("expects exactly the pattern-binding finding")
    };
    assert_eq!(finding.rule(), "identifier.representation_suffix");
    assert_eq!(finding.subject(), "phase");
}

/// 验证下划线丢弃与普通绑定的精确区分
#[test]
fn underscore_discard_and_ordinary_binding_are_distinct() {
    for (path, source, expected) in [
        (
            "src/underscore.rs",
            concat!(
                "/// 计算持续时长\n",
                "fn calculate_duration() -> f64 {\n",
                "    let _ = 1.0;\n",
                "    match 1.0 { _ => {} }\n",
                "    1.0\n",
                "}\n",
            ),
            None,
        ),
        (
            "src/underscore.py",
            concat!(
                "def calculate_velocity(duration_s: float) -> float:\n",
                "    \"\"\"\n",
                "    计算平均速度\n",
                "\n",
                "    Args:\n",
                "        duration_s: 持续时间\n",
                "    Returns:\n",
                "        float: 平均速度\n",
                "    Raises:\n",
                "        无\n",
                "    \"\"\"\n",
                "    match duration_s:\n",
                "        case _:\n",
                "            return duration_s\n",
                "    return duration_s\n",
            ),
            None,
        ),
        (
            "src/underscore.py",
            "for _ in range(3):\n    pass\n",
            Some(HARD_CANONICAL),
        ),
        ("src/underscore.py", "_cache = {}\n", Some(UNKNOWN_REVIEW)),
        ("src/underscore.c", "int _;\n", Some(HARD_RESERVED)),
    ] {
        assert_single_rule(&review_source(path, source), expected);
    }
}

/// 验证 Python 固定拼写只在精确结构位置生效
#[test]
fn python_fixed_spellings_are_structural_only() {
    for (source, expected) in [
        ("__all__ = [\"calculate_velocity\"]\n", None),
        (
            "class _Velocity:\n    \"\"\"\n    速度值容器\n    \"\"\"\n    __slots__ = (\"distance_m\",)\n",
            None,
        ),
        (
            concat!(
                "def calculate_velocity() -> None:\n",
                "    \"\"\"\n    计算平均速度\n\n",
                "    Args:\n        无\n    Returns:\n        无\n",
                "    Raises:\n        无\n    \"\"\"\n",
                "    __all__ = []\n    return\n",
            ),
            Some(HARD_CANONICAL),
        ),
    ] {
        assert_single_rule(&review_source("src/fixed.py", source), expected);
    }
}

/// 验证 Python 带类型的可变参数具有稳定名称
#[test]
fn python_typed_splat_observes_stable_parameter_names() {
    let review = review_source_with(
        "src/splat.py",
        concat!(
            "def calculate_totals(*distance_m: float, **options: dict) -> float:\n",
            "    \"\"\"\n",
            "    计算合计值\n",
            "\n",
            "    Args:\n",
            "        distance_m: 距离序列\n",
            "        options:    附加选项\n",
            "    Returns:\n",
            "        float: 合计值\n",
            "    Raises:\n",
            "        无\n",
            "    \"\"\"\n",
            "    return 0.0\n",
        ),
        &["options", "totals"],
    );
    assert_single_rule(&review, None);
}

/// 验证外部协议名称只能通过精确注册获得有限处理
#[test]
fn external_owner_spellings_exempt_only_through_typed_rows() {
    let trait_source = concat!(
        "struct Velocity {\n",
        "    distance_m: f64,\n",
        "}\n",
        "\n",
        "impl fmt::Display for Velocity {\n",
        "    /// 计算展示文本\n",
        "    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {\n",
        "        formatter.write_str(\"velocity\")\n",
        "    }\n",
        "}\n",
    );
    let free_source = concat!(
        "/// 计算展示宽度\n",
        "fn fmt(distance_m: f64) -> f64 {\n",
        "    distance_m\n",
        "}\n",
    );
    let mut authority: serde_json::Value =
        serde_json::from_slice(AUTHORITY).unwrap();
    authority["token_vocabulary"]
        .as_array_mut()
        .unwrap()
        .push(serde_json::json!("formatter"));
    authority["external_fixed_identifiers"] = serde_json::json!([
        {"profile": "rust", "role": "function", "owner": "fmt::Display", "spelling": "fmt"},
        {"profile": "rust", "role": "function", "owner": "std::fmt::Display", "spelling": "fmt"},
        {"profile": "rust", "role": "function", "owner": "fmt::Display", "spelling": "x"},
        {"profile": "rust", "role": "function", "owner": "fmt::Display", "spelling": "BadName"},
        {"profile": "rust", "role": "function", "owner": "fmt::Display", "spelling": "r#type"},
    ]);
    let with_rows = compile_value(&authority).unwrap();
    let exempt =
        reviewed_source(&with_rows, "src/external_owner.rs", trait_source);
    assert_single_rule(&exempt, None);
    let free =
        reviewed_source(&with_rows, "src/external_owner.rs", free_source);
    assert_single_rule(&free, Some(UNKNOWN_REVIEW));
    let absent = review_source_with(
        "src/external_owner.rs",
        trait_source,
        &["formatter"],
    );
    assert_single_rule(&absent, Some(UNKNOWN_REVIEW));

    for (name, expected) in [
        ("x", ("identifier.candidate", FindingGrade::ReviewRequired)),
        ("BadName", HARD_CANONICAL),
        ("r#type", HARD_RESERVED),
    ] {
        let source = format!(
            "impl fmt::Display for Velocity {{\n    /// 计算展示文本\n    fn {name}(&self) {{}}\n}}\n"
        );
        let review =
            reviewed_source(&with_rows, "src/external_owner.rs", &source);
        assert_single_rule(&review, Some(expected));
    }

    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
    let self_reviewer = WorkspaceReviewer::compile(AuthorityInput::Directory(
        &root.join("docs/authority/csu-self"),
    ))
    .expect("CSU self Authority must compile");
    let free_review = reviewed_source(
        &self_reviewer,
        "src/authority.rs",
        concat!(
            "/// 处理格式化输入\n",
            "fn expecting(formatter: i32) {\n",
            "    let _ = formatter;\n",
            "}\n",
            "\n",
            "/// 访问映射输入\n",
            "fn visit_map(access: i32) {\n",
            "    let _ = access;\n",
            "}\n",
        ),
    );
    assert_eq!(
        free_review.findings().len(),
        2,
        "{:#?}",
        free_review.findings()
    );
    assert!(free_review.findings().iter().all(|finding| {
        finding.rule() == "identifier.unknown_token"
            && finding.grade() == FindingGrade::ReviewRequired
    }));
}
