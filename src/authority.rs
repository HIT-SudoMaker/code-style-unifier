use crate::model::FindingGrade;
use crate::model::PresentationCell;
use crate::model::PresentationChapter;
use crate::model::PresentationPlan;
use crate::model::ReviewInput;
use crate::model::ReviewTerminal;
use crate::review;
use serde::Deserialize;
use std::collections::BTreeMap;
use std::collections::BTreeSet;
use std::fmt;
use std::fs;
use std::path::Path;
use std::path::PathBuf;
/// 表示一份内存中的 Authority 文档
#[derive(Clone, Copy, Debug)]
pub struct AuthorityDocument<'document> {
    /// Authority 集合内的相对路径
    pub relative_path: &'document str,
    /// Authority 文档的原始字节
    pub bytes: &'document [u8],
}
/// 指定 Authority 的读取来源
#[derive(Clone, Copy, Debug)]
pub enum AuthorityInput<'authority> {
    /// 从目录读取 Authority
    Directory(&'authority Path),
    /// 从调用方提供的内存文档读取 Authority
    Documents(&'authority [AuthorityDocument<'authority>]),
}
/// 表示 Authority 编译前拒绝的原因
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReviewRejection {
    code: &'static str,
    message: String,
}
impl ReviewRejection {
    /// 执行 `new` 内部逻辑
    pub(crate) fn new(code: &'static str, message: impl Into<String>) -> Self {
        Self {
            code,
            message: message.into(),
        }
    }
    /// 返回稳定的拒绝代码
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 拒绝代码
    /// # Errors
    /// - 无
    pub fn code(&self) -> &str {
        self.code
    }
    /// 返回便于人工理解的拒绝说明
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 拒绝说明
    /// # Errors
    /// - 无
    pub fn message(&self) -> &str {
        &self.message
    }
}
impl fmt::Display for ReviewRejection {
    /// 将拒绝原因写入格式化器
    ///
    /// # Arguments
    /// - formatter：格式化输出目标
    /// # Returns
    /// - 格式化结果
    /// # Errors
    /// - 写入格式化器失败时返回错误
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{}: {}", self.code, self.message)
    }
}
impl std::error::Error for ReviewRejection {}
/// 提供已编译 Authority 驱动的一次性审查入口
#[derive(Clone, Debug)]
pub struct WorkspaceReviewer {
    pub(crate) authority: CompiledAuthority,
}
impl WorkspaceReviewer {
    /// 编译并验证 Authority
    ///
    /// # Arguments
    /// - input：Authority 的读取来源
    /// # Returns
    /// - 可执行审查的 Reviewer
    /// # Errors
    /// - Authority 缺失、不可读或不满足冻结契约时返回拒绝原因
    pub fn compile(
        input: AuthorityInput<'_>,
    ) -> Result<Self, ReviewRejection> {
        let bytes = match input {
            AuthorityInput::Documents(documents) => {
                let document = select_authority_document(documents)?;
                document.bytes.to_vec()
            }
            AuthorityInput::Directory(directory) => {
                let path = directory.join("authority.json");
                fs::read(&path).map_err(|error| {
                    ReviewRejection::new(
                        "authority.read",
                        format!("cannot read {}: {error}", path.display()),
                    )
                })?
            }
        };
        let invalid = |error: serde_json::Error| {
            ReviewRejection::new(
                "authority.syntax",
                format!("authority.json is invalid: {error}"),
            )
        };
        let source: serde_json::Value =
            serde_json::from_slice(&bytes).map_err(&invalid)?;
        let bundle: AuthorityBundle =
            serde_json::from_value(source.clone()).map_err(&invalid)?;
        let authority = CompiledAuthority::compile(bundle, source)?;
        Ok(Self { authority })
    }
    /// 对输入快照执行一次完整审查
    ///
    /// # Arguments
    /// - input：待审查的工作区或内存文档快照
    /// # Returns
    /// - 已封存或带错误的终态
    /// # Errors
    /// - 无
    pub fn review(&self, input: ReviewInput<'_>) -> ReviewTerminal {
        review::review(&self.authority, input)
    }
}
/// 执行 `select_authority_document` 内部逻辑
fn select_authority_document<'document>(
    documents: &'document [AuthorityDocument<'document>],
) -> Result<&'document AuthorityDocument<'document>, ReviewRejection> {
    if documents.len() != 1 || documents[0].relative_path != "authority.json" {
        return Err(ReviewRejection::new(
            "authority.membership",
            "in-memory Authority must contain exactly authority.json",
        ));
    }
    Ok(&documents[0])
}
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct AuthorityBundle {
    schema_version: u32,
    source_form: SourceForm,
    families: Vec<FamilyInput>,
    #[serde(default)]
    public_callables: BTreeMap<String, Vec<String>>,
    #[serde(default)]
    token_vocabulary: Vec<String>,
    #[serde(default)]
    candidate_tokens: Vec<String>,
    #[serde(default)]
    candidate_token_matching: String,
    #[serde(default)]
    quantity_concepts: BTreeMap<String, Vec<String>>,
    #[serde(default)]
    semantic_role_prefixes: Vec<String>,
    #[serde(default)]
    representation_suffixes: Vec<String>,
    #[serde(default)]
    profile_contracts: BTreeMap<String, ProfileContractInput>,
    rules: Vec<RuleInput>,
    #[serde(default)]
    header_languages: BTreeMap<String, String>,
    #[serde(default)]
    dependency_authority: Option<DependencyAuthorityInput>,
    presentation: Vec<PresentationChapter>,
}
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct RuleInput {
    #[serde(rename = "id")]
    identity: String,
    family: String,
    fact: String,
    operator: RuleOperator,
    grade: FindingGrade,
    message: String,
    #[serde(default)]
    question: Option<String>,
}
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd)]
#[serde(rename_all = "snake_case")]
#[repr(u8)]
pub(crate) enum RuleOperator {
    IdentifierCandidate,
    IdentifierReserved,
    IdentifierCanonicalForm,
    IdentifierRepresentationSuffix,
    IdentifierUnknownToken,
    DocumentationCarrier,
    DocumentationSummary,
    DocumentationTerminator,
    DocumentationPublicContract,
    DocumentationSafety,
    DependencyWildcard,
    DependencyModulePlacement,
    DependencyOrder,
    SourceForm,
}
impl RuleOperator {
    const COUNT: usize = Self::SourceForm as usize + 1;
    /// 返回 operator 唯一允许的事实族与事实类型
    fn contract(self) -> (&'static str, &'static str) {
        match self {
            Self::IdentifierCandidate
            | Self::IdentifierReserved
            | Self::IdentifierCanonicalForm
            | Self::IdentifierRepresentationSuffix
            | Self::IdentifierUnknownToken => {
                ("identifier", "declaration_name")
            }
            Self::DocumentationCarrier
            | Self::DocumentationSummary
            | Self::DocumentationTerminator
            | Self::DocumentationPublicContract
            | Self::DocumentationSafety => {
                ("documentation", "callable_documentation")
            }
            Self::DependencyWildcard
            | Self::DependencyModulePlacement
            | Self::DependencyOrder => {
                ("dependency", "dependency_declaration")
            }
            Self::SourceForm => ("structure", "source_parseability"),
        }
    }
    /// 返回 operator 唯一允许的 Finding 等级
    fn grade(self) -> FindingGrade {
        match self {
            Self::IdentifierCandidate | Self::IdentifierUnknownToken => {
                FindingGrade::ReviewRequired
            }
            _ => FindingGrade::HardViolation,
        }
    }
}
#[derive(Clone, Debug)]
pub(crate) struct RuleContract {
    pub(crate) identity: String,
    pub(crate) grade: FindingGrade,
    pub(crate) message: String,
    pub(crate) question: Option<String>,
}
type RuleCatalog = BTreeMap<RuleOperator, RuleContract>;
type CompiledRules = (RuleCatalog, BTreeSet<String>);
#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
#[serde(deny_unknown_fields)]
pub(crate) struct ProfileContractInput {
    /// 绑定 grammar、node vocabulary 与事实提取的观察方法身份
    pub observation_method: String,
    /// 语言要求的文档载体
    pub documentation_carrier: String,
    /// 参数章节标签
    pub arguments_label: String,
    /// 返回章节标签
    pub returns_label: String,
    /// 错误章节标签
    pub failures_label: String,
    /// 空章节的受控标记
    pub empty_role: String,
}
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct FamilyInput {
    name: String,
    operator: String,
    projections: BTreeMap<String, String>,
}
#[derive(Clone, Debug, Default, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct DependencyAuthorityInput {
    /// 是否启用依赖事实族
    #[serde(default)]
    pub enabled: bool,
    /// Python 标准库闭集
    #[serde(default)]
    pub python_standard_library: Vec<String>,
    /// Python 第三方依赖闭集
    #[serde(default)]
    pub python_third_party: Vec<String>,
    /// Python 项目内顶层包闭集
    #[serde(default)]
    pub python_project_roots: Vec<String>,
    /// Python 导入是否允许自动重排
    #[serde(default)]
    pub python_reorder_safe: bool,
    /// Rust 导入是否允许自动重排
    #[serde(default)]
    pub rust_reorder_safe: bool,
}
#[derive(Clone, Debug)]
pub(crate) struct CompiledAuthority {
    /// 排除认知展示关系的语义 Authority 摘要
    pub semantic_digest: [u8; 32],
    /// 整个 Review scope 的源码解析处置制度
    pub source_form: SourceForm,
    /// 不参与科学身份的认知展示关系
    pub presentation: PresentationPlan,
    /// 已启用事实族闭集
    pub families: BTreeSet<String>,
    /// 按语言冻结的事实族投影
    pub projections: BTreeMap<String, BTreeMap<String, ProjectionState>>,
    /// 按路径冻结的公开 callable 身份
    pub public_callables: BTreeMap<String, BTreeSet<String>>,
    /// 允许的标识符词元闭集
    pub token_vocabulary: BTreeSet<String>,
    /// 需要人工复核的候选词元闭集
    pub candidate_tokens: BTreeSet<String>,
    /// 量纲概念到表示后缀的映射
    pub quantity_concepts: BTreeMap<String, BTreeSet<String>>,
    /// 按最长优先排列的语义角色前缀
    pub semantic_role_prefixes: Vec<String>,
    /// 允许的表示后缀闭集
    pub representation_suffixes: BTreeSet<String>,
    /// 按语言冻结的文档契约
    pub profile_contracts: BTreeMap<String, ProfileContractInput>,
    /// 按封闭 operator 编译的规则目录
    rules: RuleCatalog,
    /// C 与 C++ 头文件的显式语言映射
    pub header_languages: BTreeMap<String, String>,
    /// 已编译的依赖规则 Authority
    pub dependency: DependencyAuthorityInput,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ProjectionState {
    Supported,
    NotApplicable,
    NeedsAuthority,
}
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq)]
#[serde(rename_all = "snake_case")]
pub(crate) enum SourceForm {
    Direct,
    External,
}
impl CompiledAuthority {
    /// 执行 `compile` 内部逻辑
    fn compile(
        bundle: AuthorityBundle,
        source: serde_json::Value,
    ) -> Result<Self, ReviewRejection> {
        if bundle.schema_version != 2 {
            return Err(ReviewRejection::new(
                "authority.version",
                "only schema_version 2 is supported",
            ));
        }
        let mut families = BTreeSet::new();
        let mut projections = BTreeMap::new();
        for family in &bundle.families {
            let expected_operator = match family.name.as_str() {
                "identifier" => "identifier_v1",
                "documentation" => "documentation_v1",
                "dependency" => "dependency_v1",
                _ => {
                    return Err(ReviewRejection::new(
                        "authority.family",
                        format!("unknown family {}", family.name),
                    ));
                }
            };
            if family.operator != expected_operator {
                return Err(ReviewRejection::new(
                    "authority.operator",
                    format!("unknown operator {}", family.operator),
                ));
            }
            if !families.insert(family.name.clone()) {
                return Err(ReviewRejection::new(
                    "authority.family",
                    format!("duplicate family {}", family.name),
                ));
            }
            validate_projections(family)?;
            projections.insert(
                family.name.clone(),
                family
                    .projections
                    .iter()
                    .map(|(language, state)| {
                        let state = match state.as_str() {
                            "supported" => ProjectionState::Supported,
                            "not_applicable" => ProjectionState::NotApplicable,
                            "needs_authority" => {
                                ProjectionState::NeedsAuthority
                            }
                            _ => unreachable!("projection was validated"),
                        };
                        (language.clone(), state)
                    })
                    .collect(),
            );
        }
        for required in ["identifier", "documentation"] {
            if !families.contains(required) {
                return Err(ReviewRejection::new(
                    "authority.family",
                    format!("missing required family {required}"),
                ));
            }
        }
        validate_operator_constants(&bundle)?;
        let (rules, rule_identities) = compile_rules(&bundle.rules)?;
        let dependency =
            bundle.dependency_authority.clone().unwrap_or_default();
        if families.contains("dependency") != dependency.enabled {
            return Err(ReviewRejection::new(
                "authority.dependency",
                concat!(
                    "dependency family selection and ",
                    "dependency_authority.enabled must agree"
                ),
            ));
        }
        validate_dependency_authority(&dependency)?;
        let mut semantic_role_prefixes = bundle.semantic_role_prefixes;
        semantic_role_prefixes
            .sort_by_key(|prefix| std::cmp::Reverse(prefix.len()));
        let representation_suffixes =
            bundle.representation_suffixes.into_iter().collect();
        let profile_contracts = bundle.profile_contracts;
        let presentation =
            compile_presentation(&bundle.presentation, &rule_identities)?;
        let semantic_digest = semantic_authority_digest(source);
        let public_callables = bundle
            .public_callables
            .into_iter()
            .map(|(path, names)| {
                let path = normalize_relative_path(&path)?;
                let names: BTreeSet<_> = names.into_iter().collect();
                if names.is_empty()
                    || names.iter().any(|name| name.trim().is_empty())
                {
                    return Err(ReviewRejection::new(
                        "authority.public_callable",
                        format!(
                            "public callable identity list is empty for {path}"
                        ),
                    ));
                }
                Ok((path, names))
            })
            .collect::<Result<BTreeMap<_, _>, _>>()?;
        let header_languages = bundle
            .header_languages
            .into_iter()
            .map(|(path, language)| {
                if !matches!(language.as_str(), "c" | "cpp") {
                    return Err(ReviewRejection::new(
                        "authority.header_language",
                        format!(
                            "header {path} has invalid language {language}"
                        ),
                    ));
                }
                Ok((normalize_relative_path(&path)?, language))
            })
            .collect::<Result<BTreeMap<_, _>, _>>()?;
        Ok(Self {
            semantic_digest,
            source_form: bundle.source_form,
            presentation,
            families,
            projections,
            public_callables,
            token_vocabulary: bundle.token_vocabulary.into_iter().collect(),
            candidate_tokens: bundle
                .candidate_tokens
                .into_iter()
                .map(|token| token.to_lowercase())
                .collect(),
            quantity_concepts: bundle
                .quantity_concepts
                .into_iter()
                .map(|(concept, suffixes)| {
                    (concept, suffixes.into_iter().collect())
                })
                .collect(),
            semantic_role_prefixes,
            representation_suffixes,
            profile_contracts,
            rules,
            header_languages,
            dependency,
        })
    }
    /// 执行 `projection` 内部逻辑
    pub(crate) fn projection(
        &self,
        family: &str,
        language: &str,
    ) -> ProjectionState {
        self.projections[family][language]
    }
    /// 返回绑定到封闭 operator 的唯一 Authority 规则
    pub(crate) fn rule(&self, operator: RuleOperator) -> &RuleContract {
        &self.rules[&operator]
    }
    /// 执行 `profile_contract` 内部逻辑
    pub(crate) fn profile_contract(
        &self,
        language: &str,
    ) -> &ProfileContractInput {
        &self.profile_contracts[language]
    }
}
/// 执行 `validate_dependency_authority` 内部逻辑
fn validate_dependency_authority(
    dependency: &DependencyAuthorityInput,
) -> Result<(), ReviewRejection> {
    let groups = [
        &dependency.python_standard_library,
        &dependency.python_third_party,
        &dependency.python_project_roots,
    ];
    let mut seen = BTreeSet::new();
    for group in groups {
        for name in group {
            if name.trim().is_empty() || !seen.insert(name) {
                return Err(ReviewRejection::new(
                    "authority.dependency",
                    "Python dependency classes must be non-empty and disjoint",
                ));
            }
        }
    }
    Ok(())
}
/// 执行 `validate_operator_constants` 内部逻辑
fn validate_operator_constants(
    bundle: &AuthorityBundle,
) -> Result<(), ReviewRejection> {
    let matching = &bundle.candidate_token_matching;
    if matching != "unicode_case_fold_exact_token" {
        return Err(ReviewRejection::new(
            "authority.identifier",
            format!("unsupported candidate matching {matching}"),
        ));
    }
    validate_candidate_registry(&bundle.candidate_tokens)?;
    let prefixes = &bundle.semantic_role_prefixes;
    let actual: BTreeSet<_> = prefixes.iter().map(String::as_str).collect();
    let expected: BTreeSet<_> = [
        "is", "has", "can", "should", "needs", "lower", "upper", "minimum",
        "maximum",
    ]
    .into_iter()
    .collect();
    if actual != expected {
        return Err(ReviewRejection::new(
            "authority.identifier",
            "semantic_role_prefixes do not match identifier_v1",
        ));
    }
    let suffixes = &bundle.representation_suffixes;
    let declared: BTreeSet<_> = suffixes.iter().map(String::as_str).collect();
    let used: BTreeSet<_> = bundle
        .quantity_concepts
        .values()
        .flat_map(|items| items.iter().map(String::as_str))
        .collect();
    if !used.is_subset(&declared) {
        return Err(ReviewRejection::new(
            "authority.identifier",
            "quantity concept references an undeclared representation suffix",
        ));
    }
    let contracts = &bundle.profile_contracts;
    let expected = expected_profile_contracts();
    if contracts != &expected {
        return Err(ReviewRejection::new(
            "authority.documentation",
            "profile_contracts do not match documentation_v1",
        ));
    }
    Ok(())
}
/// 编译由 Authority 唯一拥有的规则目录
fn compile_rules(
    inputs: &[RuleInput],
) -> Result<CompiledRules, ReviewRejection> {
    let mut rules = RuleCatalog::new();
    let mut identities = BTreeSet::new();
    for input in inputs {
        if input.identity.trim().is_empty()
            || input.message.trim().is_empty()
            || input
                .question
                .as_ref()
                .is_some_and(|question| question.trim().is_empty())
            || !identities.insert(input.identity.clone())
        {
            return Err(ReviewRejection::new(
                "authority.rule_catalog",
                "Rule identities and evidence text must be non-empty and unique",
            ));
        }
        if input.operator.contract()
            != (input.family.as_str(), input.fact.as_str())
            || input.operator.grade() != input.grade
        {
            return Err(ReviewRejection::new(
                "authority.rule_catalog",
                format!(
                    "Rule {} does not match its operator fact contract",
                    input.identity
                ),
            ));
        }
        if rules
            .insert(
                input.operator,
                RuleContract {
                    identity: input.identity.clone(),
                    grade: input.grade,
                    message: input.message.clone(),
                    question: input.question.clone(),
                },
            )
            .is_some()
        {
            return Err(ReviewRejection::new(
                "authority.rule_catalog",
                "each closed operator must own exactly one Rule",
            ));
        }
    }
    if rules.len() != RuleOperator::COUNT {
        return Err(ReviewRejection::new(
            "authority.rule_catalog",
            "Rule catalog must cover every closed operator",
        ));
    }
    Ok((rules, identities))
}
/// 编译规则与认知章节之间的唯一展示关系
fn compile_presentation(
    inputs: &[PresentationChapter],
    rule_identities: &BTreeSet<String>,
) -> Result<PresentationPlan, ReviewRejection> {
    const CHAPTERS: [&str; 9] = [
        "Admit",
        "Structure",
        "Relate",
        "Expose",
        "Name",
        "Explain",
        "Shape",
        "Behave",
        "Close",
    ];
    const PROFILES: [&str; 4] = ["python", "rust", "c", "cpp"];
    if inputs.len() != CHAPTERS.len() {
        return Err(invalid_presentation(
            "presentation must contain every Cognitive Chapter exactly once",
        ));
    }
    let mut seen_rules = BTreeSet::new();
    let mut chapters = Vec::with_capacity(inputs.len());
    for (chapter_rank, (input, expected_chapter)) in
        inputs.iter().zip(CHAPTERS).enumerate()
    {
        if input.chapter != expected_chapter {
            return Err(invalid_presentation(format!(
                "expected Cognitive Chapter {expected_chapter} at position {}",
                chapter_rank + 1
            )));
        }
        if input.profiles.len() != PROFILES.len()
            || PROFILES
                .iter()
                .any(|profile| !input.profiles.contains_key(*profile))
            || input.profiles.values().any(|cell| match cell {
                PresentationCell::Supported { contract: evidence }
                | PresentationCell::NotApplicable { reason: evidence }
                | PresentationCell::NeedsAuthority {
                    capability: evidence,
                } => evidence.trim().is_empty(),
            })
        {
            return Err(invalid_presentation(format!(
                "Cognitive Chapter {} requires four valid profile cells",
                input.chapter
            )));
        }
        for rule in &input.rules {
            if !rule_identities.contains(rule)
                || !seen_rules.insert(rule.clone())
            {
                return Err(invalid_presentation(format!(
                    "presentation contains a duplicate or unknown Rule {rule}"
                )));
            }
        }
        chapters.push(PresentationChapter {
            chapter: input.chapter.clone(),
            rules: input.rules.clone(),
            profiles: input.profiles.clone(),
        });
    }
    if seen_rules != *rule_identities {
        return Err(invalid_presentation(
            "presentation must place every Rule exactly once",
        ));
    }
    Ok(PresentationPlan { chapters })
}
/// 构造认知展示编译拒绝
fn invalid_presentation(message: impl Into<String>) -> ReviewRejection {
    ReviewRejection::new("authority.presentation", message)
}
/// 计算排除认知展示字段的规范语义摘要
fn semantic_authority_digest(mut source: serde_json::Value) -> [u8; 32] {
    let object = source
        .as_object_mut()
        .expect("typed Authority source must be an object");
    object.remove("presentation");
    object["rules"]
        .as_array_mut()
        .expect("typed Rule catalog must be an array")
        .sort_by(|left, right| left["id"].as_str().cmp(&right["id"].as_str()));
    *blake3::hash(source.to_string().as_bytes()).as_bytes()
}
/// 执行 `validate_candidate_registry` 内部逻辑
fn validate_candidate_registry(
    tokens: &[String],
) -> Result<(), ReviewRejection> {
    let actual: BTreeSet<_> = tokens.iter().cloned().collect();
    let mut required: BTreeSet<String> = ('a'..='z')
        .chain('A'..='Z')
        .map(|letter| letter.to_string())
        .collect();
    required.extend(
        [
            "alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta",
            "theta", "iota", "kappa", "lambda", "mu", "nu", "xi", "omicron",
            "pi", "rho", "sigma", "tau", "upsilon", "phi", "chi", "psi",
            "omega",
        ]
        .into_iter()
        .map(str::to_owned),
    );
    required.extend(
        "αΑβΒγΓδΔεΕζΖηΗθΘιΙκΚλΛμΜνΝξΞοΟπΠρΡσΣτΤυΥφΦχΧψΨωΩϕϑϵϖϱς"
            .chars()
            .map(|letter| letter.to_string()),
    );
    if !required.is_subset(&actual) {
        return Err(ReviewRejection::new(
            "authority.candidate_registry",
            "candidate registry lacks the frozen Latin or Greek minimum",
        ));
    }
    Ok(())
}
/// 执行 `expected_profile_contracts` 内部逻辑
fn expected_profile_contracts() -> BTreeMap<String, ProfileContractInput> {
    [
        (
            "python",
            "tree-sitter-python@0.25.0+direct-source-facts-v1",
            "suite_first_triple_double_quoted_string",
            "Args:",
            "Returns:",
            "Raises:",
            "无",
        ),
        (
            "rust",
            "tree-sitter-rust@0.24.2+direct-source-facts-v1",
            "outer_rustdoc",
            "# Arguments",
            "# Returns",
            "# Errors",
            "- 无",
        ),
        (
            "c",
            "tree-sitter-c@0.24.2+direct-source-facts-v1",
            "controlled_adjacent_block",
            "参数：",
            "返回：",
            "错误：",
            "- 无",
        ),
        (
            "cpp",
            "tree-sitter-cpp@8b5b49eb+direct-source-facts-v1",
            "controlled_adjacent_block",
            "参数：",
            "返回：",
            "错误：",
            "- 无",
        ),
    ]
    .into_iter()
    .map(
        |(
            language,
            observation_method,
            carrier,
            arguments,
            returns,
            failures,
            empty,
        )| {
            (
                language.to_owned(),
                ProfileContractInput {
                    observation_method: observation_method.to_owned(),
                    documentation_carrier: carrier.to_owned(),
                    arguments_label: arguments.to_owned(),
                    returns_label: returns.to_owned(),
                    failures_label: failures.to_owned(),
                    empty_role: empty.to_owned(),
                },
            )
        },
    )
    .collect()
}
/// 执行 `validate_projections` 内部逻辑
fn validate_projections(family: &FamilyInput) -> Result<(), ReviewRejection> {
    const LANGUAGES: [&str; 4] = ["python", "rust", "c", "cpp"];
    if family.projections.len() != LANGUAGES.len() {
        return Err(ReviewRejection::new(
            "authority.projection",
            format!(
                "family {} must have exactly four projections",
                family.name
            ),
        ));
    }
    for language in LANGUAGES {
        let Some(state) = family.projections.get(language) else {
            return Err(ReviewRejection::new(
                "authority.projection",
                format!("family {} is missing {language}", family.name),
            ));
        };
        if !matches!(
            state.as_str(),
            "supported" | "not_applicable" | "needs_authority"
        ) {
            return Err(ReviewRejection::new(
                "authority.projection",
                format!("invalid {language} projection {state}"),
            ));
        }
    }
    Ok(())
}
/// 执行 `normalize_relative_path` 内部逻辑
pub(crate) fn normalize_relative_path(
    path: &str,
) -> Result<String, ReviewRejection> {
    let path = path.replace('\\', "/");
    let candidate = PathBuf::from(&path);
    if path.is_empty()
        || candidate.is_absolute()
        || path.split('/').any(|part| part.is_empty() || part == "..")
    {
        return Err(ReviewRejection::new(
            "request.path",
            format!("invalid relative path {path:?}"),
        ));
    }
    Ok(path)
}
