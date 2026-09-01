use csu::AuthorityDocument;
use csu::AuthorityInput;
use csu::DocumentSet;
use csu::FactFamily;
use csu::FactFamilyState;
use csu::ReviewInput;
use csu::ReviewTerminal;
use csu::SourceDocument;
use csu::WorkspaceReviewer;

const AUTHORITY: &[u8] =
    include_bytes!("../docs/fixtures/core/authority.json");

/// 审查单份内存源码并返回封存终态
fn review_source<'source>(
    path: &'source str,
    source: &'source str,
) -> csu::SealedReview {
    let authority = [AuthorityDocument {
        relative_path: "authority.json",
        bytes: AUTHORITY,
    }];
    let reviewer =
        WorkspaceReviewer::compile(AuthorityInput::Documents(&authority))
            .expect("frozen Authority must compile");
    let documents = [SourceDocument {
        relative_path: path,
        bytes: source.as_bytes(),
    }];
    let ReviewTerminal::Sealed(review) =
        reviewer.review(ReviewInput::Documents(DocumentSet {
            revision: "identifier-subjects",
            documents: &documents,
        }))
    else {
        panic!("valid direct source must seal");
    };
    review
}

/// 收集 Candidate Finding 主体
fn candidate_subjects(review: &csu::SealedReview) -> Vec<String> {
    review
        .findings()
        .iter()
        .filter(|finding| finding.rule() == "identifier.candidate")
        .map(|finding| finding.subject().to_owned())
        .collect()
}

/// 统计标识符 Finding
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

/// 验证标识符主体证据场景
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
    assert_eq!(identifier_count(&review), 11);
}

/// 验证标识符主体证据场景
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
    assert_eq!(identifier_count(&review), 11);
}

/// 验证标识符主体证据场景
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

/// 验证标识符主体证据场景
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

/// 验证标识符主体证据场景
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

/// 验证标识符主体证据场景
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

/// 验证标识符主体证据场景
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

/// 验证标识符主体证据场景
#[test]
fn candidate_registry_matches_frozen_latin_and_greek_forms() {
    let source = r#"Q = 1
q = Q
alpha = q
Alpha = alpha
Α = Alpha
α = Α
φ = α
ϕ = φ
"#;
    let review = review_source("src/candidate_registry.py", source);

    assert_eq!(
        candidate_subjects(&review),
        ["Q", "q", "alpha", "Alpha", "Α", "α", "φ", "ϕ"]
    );
    assert_eq!(identifier_count(&review), 8);
}
