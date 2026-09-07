use crate::model::FindingGrade;
use crate::model::PresentationCell;
use crate::model::PresentationChapter;
use crate::model::PresentationPlan;
use crate::model::ReviewInput;
use crate::model::ReviewTerminal;
use crate::review;
use serde::Deserialize;
use serde::Serialize;
use std::collections::BTreeMap;
use std::collections::BTreeSet;
use std::fmt;
use std::fs;
use std::path::Path;
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
    /// 根据错误代码和说明创建拒绝结果
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
    /// - input： Authority 的读取来源
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
        let bundle: AuthorityBundle =
            serde_json::from_slice(&bytes).map_err(&invalid)?;
        let authority = CompiledAuthority::compile(bundle)?;
        Ok(Self { authority })
    }
    /// 对输入快照执行一次完整审查
    ///
    /// # Arguments
    /// - input： 待审查的工作区或内存文档快照
    /// # Returns
    /// - 已封存或带错误的终态
    /// # Errors
    /// - 无
    pub fn review(&self, input: ReviewInput<'_>) -> ReviewTerminal {
        review::review(&self.authority, input)
    }
}
/// 确认内存输入只包含一份 authority.json
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
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct AuthorityBundle {
    schema_version: u32,
    #[serde(default, deserialize_with = "deserialize_unique_key_map")]
    public_callables: BTreeMap<String, Vec<String>>,
    #[serde(default)]
    token_vocabulary: Vec<String>,
    #[serde(default, deserialize_with = "deserialize_unique_key_map")]
    quantity_concepts: BTreeMap<String, Vec<String>>,
    #[serde(default, deserialize_with = "deserialize_unique_key_map")]
    header_languages: BTreeMap<String, String>,
    #[serde(default)]
    external_fixed_identifiers: Vec<ExternalFixedIdentity>,
    #[serde(default)]
    dependency_authority: Option<DependencyAuthorityInput>,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
#[repr(u8)]
pub(crate) enum RuleOperator {
    SourceParseability,
    SourceTrailingComment,
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
}
impl RuleOperator {
    /// 返回操作符对应的完整规则条目
    pub(crate) fn law(self) -> &'static RuleLaw {
        STANDARD_LAW
            .rules
            .iter()
            .find(|rule| rule.operator == self)
            .expect("Standard Law catalog must contain every Rule operator")
    }
}
#[derive(Clone, Copy, Debug, Serialize)]
pub(crate) struct RuleLaw {
    operator: RuleOperator,
    pub(crate) identity: &'static str,
    pub(crate) grade: FindingGrade,
    pub(crate) message: &'static str,
    pub(crate) question: Option<&'static str>,
    semantic_revision: u16,
    #[serde(skip)]
    chapter: &'static str,
    #[serde(skip)]
    presentation_contract: &'static str,
    #[serde(skip)]
    rank: u8,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
enum DirectiveArgumentForm {
    Exact,
    BracketedCodes,
    ParenthesizedCodes,
    ColonCodes,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
/// 注释的精确起止标记
struct DirectiveCarrier(&'static str, &'static str);
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
/// 指令头与允许的参数格式
struct DirectiveLaw(&'static str, DirectiveArgumentForm);
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
/// 指令代码列表允许的字符和分隔符
struct DirectiveCodeLaw {
    separator: char,
    allow_ascii_alphanumeric: bool,
    punctuation: &'static str,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
pub(crate) enum DocumentationRole {
    TemplateParameters,
    Arguments,
    Returns,
    Failures,
    Effect,
    Panics,
    Safety,
    Ownership,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
pub(crate) enum ReturnShape {
    NoValue,
    Never,
    Value,
    Unknown,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
pub(crate) enum DocumentationCarrierLaw {
    PythonSuite,
    RustOuter,
    NativeAdjacent,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
enum SummaryLocation {
    FirstLine,
    FirstNonempty,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
pub(crate) struct HeadingLaw(
    pub(crate) &'static str,
    pub(crate) DocumentationRole,
);
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
pub(crate) struct StructuredFieldLaw {
    pub(crate) roles: &'static [DocumentationRole],
    pub(crate) prefix: &'static str,
    pub(crate) delimiter: char,
    pub(crate) padding: char,
    pub(crate) alignment_gap: usize,
    pub(crate) exact_identity: bool,
    pub(crate) require_description: bool,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
pub(crate) struct DocumentationLaw {
    pub(crate) carrier: DocumentationCarrierLaw,
    summary: SummaryLocation,
    pub(crate) headings: &'static [HeadingLaw],
    heading_prefix: Option<&'static str>,
    pub(crate) empty_role: &'static str,
    pub(crate) fields: StructuredFieldLaw,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
pub(crate) struct ReturnSurfaceLaw {
    pub(crate) no_value: &'static [&'static str],
    pub(crate) never: &'static [&'static str],
    pub(crate) never_attribute: Option<&'static str>,
    pub(crate) unknown_blocks_documentation: bool,
    pub(crate) never_documentation: Option<&'static str>,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
pub(crate) struct NarrativeLaw {
    cjk_ranges: [(char, char); 2],
    pub(crate) minimum_cjk_run: u8,
    pub(crate) blank_lines_after_summary: usize,
    pub(crate) forbidden_terminators: [char; 2],
}
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
pub(crate) enum DependencyProfileLaw {
    Python {
        scope_revision: u16,
        order_revision: u16,
        within_tier_blank_lines: usize,
        cross_tier_blank_lines: usize,
        scope_blocked: &'static str,
        multi_import_blocked: &'static str,
        classification_blocked: &'static str,
    },
    Rust {
        scope_revision: u16,
        order_revision: u16,
        within_group_blank_lines: usize,
        unknown_use_blocked: &'static str,
    },
    Procedural {
        unavailable_blocked: &'static str,
    },
    Cplusplus {
        scope_revision: u16,
        module_placement_revision: u16,
        unavailable_blocked: &'static str,
    },
}
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
pub(crate) struct ProfileLaw {
    identity: &'static str,
    /// 标识所用语法、节点种类和事实提取方法
    pub observation_method: &'static str,
    pub(crate) documentation: DocumentationLaw,
    pub(crate) return_surface: ReturnSurfaceLaw,
    pub(crate) dependency: DependencyProfileLaw,
    directive_carriers: &'static [DirectiveCarrier],
    directives: &'static [DirectiveLaw],
}
impl DirectiveLaw {
    /// 精确匹配指令头及其参数格式
    fn matches(self, body: &str, code_law: DirectiveCodeLaw) -> bool {
        let Self(head, arguments) = self;
        if body == head {
            return true;
        }
        let codes = match arguments {
            DirectiveArgumentForm::Exact => return false,
            DirectiveArgumentForm::BracketedCodes => body
                .strip_prefix(head)
                .and_then(|tail| tail.strip_prefix('['))
                .and_then(|codes| codes.strip_suffix(']')),
            DirectiveArgumentForm::ParenthesizedCodes => body
                .strip_prefix(head)
                .and_then(|tail| tail.strip_prefix('('))
                .and_then(|codes| codes.strip_suffix(')')),
            DirectiveArgumentForm::ColonCodes => body
                .strip_prefix(head)
                .and_then(|tail| tail.strip_prefix(':'))
                .map(str::trim),
        };
        codes.is_some_and(|codes| {
            !codes.is_empty()
                && codes.split(code_law.separator).all(|code| {
                    let code = code.trim();
                    !code.is_empty()
                        && code.chars().all(|character| {
                            code_law.allow_ascii_alphanumeric
                                && character.is_ascii_alphanumeric()
                                || code_law.punctuation.contains(character)
                        })
                })
        })
    }
}
impl ProfileLaw {
    /// 判断完整注释是否为当前语言允许的指令
    pub(crate) fn is_directive(&self, comment: &str) -> bool {
        self.directive_carriers
            .iter()
            .find_map(|carrier| {
                comment
                    .strip_prefix(carrier.0)
                    .and_then(|body| body.strip_suffix(carrier.1))
            })
            .map(str::trim)
            .is_some_and(|body| {
                self.directives.iter().any(|directive| {
                    directive.matches(body, STANDARD_LAW.directive_codes)
                })
            })
    }
    /// 判断文档行是否为当前语言识别的标题
    pub(crate) fn is_documentation_heading(&self, line: &str) -> bool {
        self.documentation
            .heading_prefix
            .is_some_and(|prefix| line.starts_with(prefix))
            || self
                .documentation
                .headings
                .iter()
                .any(|heading| line == heading.0)
    }
    /// 按当前语言要求读取摘要行
    pub(crate) fn documentation_summary<'line>(
        &self,
        mut lines: impl Iterator<Item = &'line str>,
    ) -> Option<&'line str> {
        match self.documentation.summary {
            SummaryLocation::FirstLine => lines.next(),
            SummaryLocation::FirstNonempty => {
                lines.find(|line| !line.is_empty())
            }
        }
    }
}
impl NarrativeLaw {
    /// 判断字符是否属于规定的中日韩统一表意文字范围
    pub(crate) fn is_cjk(&self, character: char) -> bool {
        self.cjk_ranges
            .iter()
            .any(|(start, end)| (*start..=*end).contains(&character))
    }
}
/// 逐项读取映射并拒绝重复原始键的访问器
struct UniqueKeyVisitor<Value>(std::marker::PhantomData<Value>);
impl<'input, Value> serde::de::Visitor<'input> for UniqueKeyVisitor<Value>
where
    Value: Deserialize<'input>,
{
    type Value = BTreeMap<String, Value>;
    /// 说明访问器要求的输入格式
    fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("a map with unique raw keys")
    }
    /// 逐项读取映射并在首个重复原始键处拒绝
    fn visit_map<Access>(
        self,
        mut access: Access,
    ) -> Result<Self::Value, Access::Error>
    where
        Access: serde::de::MapAccess<'input>,
    {
        let mut map = BTreeMap::new();
        while let Some((key, value)) = access.next_entry::<String, Value>()? {
            if map.insert(key, value).is_some() {
                return Err(serde::de::Error::custom(
                    "duplicate raw key in typed Authority map",
                ));
            }
        }
        Ok(map)
    }
}
/// 读取映射时拒绝完全相同的原始键
///
/// 在路径归一化之前检查原始键是否重复
/// 不允许后写覆盖，也不先转为通用 JSON 值
fn deserialize_unique_key_map<'input, Deserializer, Value>(
    deserializer: Deserializer,
) -> Result<BTreeMap<String, Value>, Deserializer::Error>
where
    Deserializer: serde::Deserializer<'input>,
    Value: Deserialize<'input>,
{
    deserializer.deserialize_map(UniqueKeyVisitor(std::marker::PhantomData))
}
#[derive(Debug, Default, Deserialize)]
#[serde(deny_unknown_fields)]
struct DependencyAuthorityInput {
    /// 已登记的 Python 标准库名称
    #[serde(default)]
    python_standard_library: Vec<String>,
    /// 已登记的 Python 第三方依赖名称
    #[serde(default)]
    python_third_party: Vec<String>,
    /// 已登记的 Python 项目顶层包名称
    #[serde(default)]
    python_project_roots: Vec<String>,
    /// Python 导入是否允许自动重排
    #[serde(default)]
    python_reorder_safe: bool,
    /// Rust 导入是否允许自动重排
    #[serde(default)]
    rust_reorder_safe: bool,
}
/// 表示一条已校验的外部协议固定名称记录
#[derive(
    Clone, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize,
)]
#[serde(deny_unknown_fields)]
pub(crate) struct ExternalFixedIdentity {
    /// 记录所属语言，固定为 rust
    profile: String,
    /// 声明角色，固定为 function
    role: String,
    /// 声明中直接写出的外部归属名称
    owner: String,
    /// 被证明固定的精确拼写
    spelling: String,
}
/// 表示源码检查支持的语言
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[repr(usize)]
pub(crate) enum SourceProfile {
    /// Python 源码
    #[serde(rename = "python")]
    Python,
    /// Rust 源码
    #[serde(rename = "rust")]
    Rust,
    /// C 源码或头文件
    #[serde(rename = "c")]
    ProceduralSource,
    /// C++ 源码或头文件
    #[serde(rename = "cpp")]
    Cplusplus,
}
impl SourceProfile {
    /// 返回语言的规范拼写
    pub(crate) fn key(self) -> &'static str {
        match self {
            Self::Python => "python",
            Self::Rust => "rust",
            Self::ProceduralSource => "c",
            Self::Cplusplus => "cpp",
        }
    }
}
/// 表示已准入的项目依赖事实
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub(crate) struct DependencyProjectFacts {
    python_standard_library: BTreeSet<String>,
    python_third_party: BTreeSet<String>,
    python_project_roots: BTreeSet<String>,
    python_reorder_safe: bool,
    rust_reorder_safe: bool,
}
/// 项目唯一拥有的可注册语义事实
///
/// 序列化布局是身份协议：字段顺序、枚举拼写、集合顺序或省略行为的
/// 任何改变都是协议变更，需要新的黄金摘要
#[derive(Clone, Debug, Serialize)]
struct ProjectFacts {
    public_callables: BTreeMap<String, BTreeSet<String>>,
    token_vocabulary: BTreeSet<String>,
    quantity_concepts: BTreeMap<String, BTreeSet<String>>,
    header_languages: BTreeMap<String, SourceProfile>,
    external_fixed: BTreeSet<ExternalFixedIdentity>,
    dependency: DependencyProjectFacts,
}
/// 完整词元的候选判定规则
#[derive(Serialize)]
struct CandidateLaw {
    matching: &'static str,
    named_tokens: [&'static str; 24],
    single_character: bool,
}
/// 语义角色前缀的接纳与拒绝规则
#[derive(Serialize)]
struct PrefixLaw {
    allowed: [&'static str; 9],
    forbidden: [&'static str; 2],
    allow_compound: bool,
}
#[derive(Clone, Copy, Serialize)]
#[serde(rename_all = "snake_case")]
enum QuantitySegmentLaw {
    AsciiLowercase,
    AsciiLowercaseThenDigits,
}
#[derive(Serialize)]
struct AdmissionLaw {
    fixed_source_profiles: [(&'static str, &'static str); 10],
    reserved_callables: [(&'static str, &'static str); 3],
    forbidden_rust_raw_callables: &'static str,
    cplusplus_conversion_types: &'static str,
    external_fixed_profile: &'static str,
    external_fixed_role: &'static str,
    concept_segments: QuantitySegmentLaw,
    suffix_segments: QuantitySegmentLaw,
    require_unique_nonempty_suffixes: bool,
}
/// 共享的可执行规则与固定算法的语义修订身份
#[derive(Serialize)]
struct StandardLaw {
    admission: AdmissionLaw,
    /// 项目事实准入与效应协议的修订号，不是运行期规则开关
    project_fact_revision: u16,
    candidate: CandidateLaw,
    prefix: PrefixLaw,
    narrative: NarrativeLaw,
    directive_codes: DirectiveCodeLaw,
    profiles: [ProfileLaw; 4],
    rules: [RuleLaw; 15],
}
/// 标准规则与项目事实的联合语义身份
#[derive(Serialize)]
struct SemanticLaw<'facts> {
    standard: &'static StandardLaw,
    project: &'facts ProjectFacts,
}
/// 从规则和项目事实派生的单次审查索引
///
/// 保存按长度降序排列的标记和精确量值名称表
/// 更换索引表示不得改变语义摘要或封存摘要
#[derive(Clone, Debug)]
struct AuthorityIndexes {
    /// 语义角色前缀，按长度降序排列
    role_prefixes: Vec<String>,
    /// 带前导下划线的表示后缀，采用同一排序方式
    suffix_markers: Vec<String>,
    /// 量值名称及其带后缀拼写的精确判定表
    quantity_names: BTreeMap<String, QuantityNameDisposition>,
}
impl AuthorityIndexes {
    /// 从项目事实和固定规则构建查询索引
    ///
    /// 量值名称拆分冲突在读取源码前返回 authority.quantity
    fn derive(facts: &ProjectFacts) -> Result<Self, ReviewRejection> {
        let representation_suffixes: BTreeSet<_> = facts
            .quantity_concepts
            .values()
            .flatten()
            .cloned()
            .collect();
        let mut quantity_names = BTreeMap::new();
        let mut insert = |spelling: String, disposition| {
            for name in [spelling.to_ascii_uppercase(), spelling] {
                if quantity_names.insert(name, disposition).is_some() {
                    return Err(ReviewRejection::new(
                        "authority.quantity",
                        "quantity spelling has multiple decompositions",
                    ));
                }
            }
            Ok(())
        };
        for (concept, allowed) in &facts.quantity_concepts {
            insert(concept.clone(), QuantityNameDisposition::MissingSuffix)?;
            for suffix in &representation_suffixes {
                let disposition = if allowed.contains(suffix) {
                    QuantityNameDisposition::Valid
                } else {
                    QuantityNameDisposition::InvalidSuffix
                };
                insert(format!("{concept}_{suffix}"), disposition)?;
            }
        }
        Ok(Self {
            role_prefixes: ordered_markers(
                STANDARD_LAW
                    .prefix
                    .allowed
                    .into_iter()
                    .chain(STANDARD_LAW.prefix.forbidden)
                    .flat_map(|marker| {
                        [marker.to_owned(), marker.to_ascii_uppercase()]
                    }),
            ),
            suffix_markers: ordered_markers(
                representation_suffixes.iter().flat_map(|suffix| {
                    [
                        format!("_{suffix}"),
                        format!("_{}", suffix.to_ascii_uppercase()),
                    ]
                }),
            ),
            quantity_names,
        })
    }
}
/// 按最长优先、字典序平局排序标记集
fn ordered_markers(markers: impl Iterator<Item = String>) -> Vec<String> {
    let mut markers: Vec<String> = markers.collect();
    markers.sort_by(|left, right| {
        right.len().cmp(&left.len()).then(left.cmp(right))
    });
    markers
}
/// 向审查代码统一提供已校验的 Authority 查询
#[derive(Clone, Debug)]
pub(crate) struct CompiledAuthority {
    /// 项目唯一拥有的注册事实
    facts: ProjectFacts,
    /// 一次性派生的运行期索引
    indexes: AuthorityIndexes,
    /// 不参与语义身份计算的展示关系
    presentation: PresentationPlan,
    /// 通过 BLAKE3 derive-key 计算的规则和事实摘要
    semantic_digest: [u8; 32],
}
/// 表示 quantity 拼写在精确闭表中的处置
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum QuantityNameDisposition {
    /// 精确 Concept 携带该 Concept 允许的 Representation Suffix
    Valid,
    /// 裸精确 Concept 缺少唯一表示后缀
    MissingSuffix,
    /// 拼写携带了已声明但未被该 Concept 允许的后缀
    InvalidSuffix,
}
/// 表示完整词元在标识符词法法则下的处置
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum TokenDisposition {
    /// 单字符或已登记候选，需要项目负责人复核
    Candidate,
    /// 已登记的普通词元
    Vocabulary,
    /// 尚未登记的词元
    Unknown,
}
impl CompiledAuthority {
    /// 校验项目事实并生成查询索引和摘要
    ///
    /// 一次完整解构输入，新增字段遗漏时触发编译错误
    /// 各字段必须进入语义计算、展示或显式拒绝处理
    fn compile(bundle: AuthorityBundle) -> Result<Self, ReviewRejection> {
        let AuthorityBundle {
            schema_version,
            public_callables: public_callable_rows,
            token_vocabulary,
            quantity_concepts,
            header_languages: header_language_rows,
            external_fixed_identifiers,
            dependency_authority,
        } = bundle;
        if schema_version != 4 {
            return Err(ReviewRejection::new(
                "authority.version",
                "only schema_version 4 is supported",
            ));
        }
        let dependency = compile_dependency_law(dependency_authority)?;
        let external_fixed = compile_external_fixed(
            external_fixed_identifiers,
            &STANDARD_LAW.admission,
        )?;
        let mut header_languages = BTreeMap::new();
        for (path, language) in header_language_rows {
            let profile = match language.as_str() {
                "c" => SourceProfile::ProceduralSource,
                "cpp" => SourceProfile::Cplusplus,
                _ => {
                    return Err(ReviewRejection::new(
                        "authority.header_language",
                        format!(
                            "header {path} has invalid language {language}"
                        ),
                    ));
                }
            };
            let path = normalize_relative_path(&path)?;
            if Path::new(&path)
                .extension()
                .and_then(|value| value.to_str())
                != Some("h")
            {
                return Err(ReviewRejection::new(
                    "authority.header_language",
                    format!("header fact targets a non-header path: {path}"),
                ));
            }
            if header_languages.insert(path, profile).is_some() {
                return Err(ReviewRejection::new(
                    "authority.header_language",
                    "distinct header paths collide after normalization",
                ));
            }
        }
        let mut public_callables = BTreeMap::new();
        for (path, names) in public_callable_rows {
            let path = normalize_relative_path(&path)?;
            let extension = Path::new(&path)
                .extension()
                .and_then(|value| value.to_str());
            let profile = extension
                .and_then(standard_source_profile)
                .and_then(|profile| match profile {
                    "header" => header_languages.get(&path).copied(),
                    "c" => Some(SourceProfile::ProceduralSource),
                    "cpp" => Some(SourceProfile::Cplusplus),
                    _ => None,
                });
            let Some(profile) = profile else {
                return Err(ReviewRejection::new(
                    "authority.public_callable",
                    format!(
                        "public callable fact targets non-native source: {path}"
                    ),
                ));
            };
            let count = names.len();
            let names: BTreeSet<_> = names.into_iter().collect();
            if names.is_empty()
                || names.len() != count
                || names.iter().any(|name| {
                    !native_callable_spelling_is_valid(profile, name)
                })
            {
                return Err(ReviewRejection::new(
                    "authority.public_callable",
                    format!(
                        "public callable identities are invalid for {path}"
                    ),
                ));
            }
            if public_callables.insert(path, names).is_some() {
                return Err(ReviewRejection::new(
                    "authority.public_callable",
                    "distinct public callable paths collide after normalization",
                ));
            }
        }
        let quantity_concepts = compile_quantity_facts(
            quantity_concepts,
            &STANDARD_LAW.admission,
        )?;
        let token_vocabulary = compile_token_facts(token_vocabulary)?;
        let facts = ProjectFacts {
            public_callables,
            token_vocabulary,
            quantity_concepts,
            header_languages,
            external_fixed,
            dependency,
        };
        // 在名称归一化后、索引展开前拒绝拆分冲突；此时尚未访问源码
        let indexes = AuthorityIndexes::derive(&facts)?;
        let presentation = standard_presentation();
        let semantic_digest = law_digest(&facts)?;
        Ok(Self {
            facts,
            indexes,
            presentation,
            semantic_digest,
        })
    }
    /// 按语言判断项目是否允许依赖重排
    pub(crate) fn dependency_reorder_safe(
        &self,
        law: &DependencyProfileLaw,
    ) -> bool {
        match law {
            DependencyProfileLaw::Python { .. } => {
                self.facts.dependency.python_reorder_safe
            }
            DependencyProfileLaw::Rust { .. } => {
                self.facts.dependency.rust_reorder_safe
            }
            DependencyProfileLaw::Procedural { .. }
            | DependencyProfileLaw::Cplusplus { .. } => false,
        }
    }
    /// 返回 Python 顶层模块根所属的项目分类层
    pub(crate) fn python_dependency_tier(&self, key: &str) -> Option<u8> {
        if key.starts_with('.') {
            return Some(2);
        }
        let root = key.split('.').next().unwrap_or(key);
        [
            (&self.facts.dependency.python_standard_library, 0_u8),
            (&self.facts.dependency.python_third_party, 1),
            (&self.facts.dependency.python_project_roots, 2),
        ]
        .into_iter()
        .find(|(group, _)| group.contains(root))
        .map(|(_, tier)| tier)
    }
    /// 按语言、角色、归属和拼写精确匹配外部协议名称
    ///
    /// 直接借用各字段比较，避免为查询构造字符串键
    pub(crate) fn external_fixed_contains(
        &self,
        profile: &str,
        role: &str,
        owner: &str,
        spelling: &str,
    ) -> bool {
        self.facts.external_fixed.iter().any(|identity| {
            identity.profile == profile
                && identity.role == role
                && identity.owner == owner
                && identity.spelling == spelling
        })
    }
    /// 根据固定扩展名规则和已登记头文件事实确定语言
    pub(crate) fn source_profile(
        &self,
        extension: &str,
        path: &str,
    ) -> Result<Option<SourceProfile>, ReviewRejection> {
        let profile = match standard_source_profile(extension) {
            Some("header") => self
                .facts
                .header_languages
                .get(path)
                .copied()
                .ok_or_else(|| {
                ReviewRejection::new(
                    "request.language",
                    format!("ambiguous header lacks Profile fact: {path}"),
                )
            })?,
            Some("python") => SourceProfile::Python,
            Some("rust") => SourceProfile::Rust,
            Some("c") => SourceProfile::ProceduralSource,
            Some("cpp") => SourceProfile::Cplusplus,
            Some(_) => unreachable!("Standard Law fixed Profile is closed"),
            None => return Ok(None),
        };
        Ok(Some(profile))
    }
    /// 统一判断完整词元是否为候选、已注册词元或未知词元
    ///
    /// 原始单字符词元直接判为候选
    /// 其他词元先统一转为小写，再查询候选表和普通词表
    /// 与注册输入共用 str::to_lowercase，不做大小写折叠、字形或转写归一
    pub(crate) fn identifier_token_disposition(
        &self,
        token: &str,
    ) -> TokenDisposition {
        if STANDARD_LAW.candidate.single_character
            && token.chars().count() == 1
        {
            return TokenDisposition::Candidate;
        }
        let normalized = lowercase_token(token);
        if STANDARD_LAW
            .candidate
            .named_tokens
            .binary_search(&normalized.as_str())
            .is_ok()
        {
            return TokenDisposition::Candidate;
        }
        if self.facts.token_vocabulary.contains(normalized.as_str()) {
            return TokenDisposition::Vocabulary;
        }
        TokenDisposition::Unknown
    }
    /// 检查名称前缀和量值后缀，并提取基础名称
    ///
    /// 返回前缀是否非法、量值判定结果及去除表示后缀的名称
    pub(crate) fn identifier_name_disposition<'name>(
        &self,
        name: &'name str,
    ) -> (bool, Option<QuantityNameDisposition>, &'name str) {
        let match_prefix = |subject: &'name str| {
            self.indexes.role_prefixes.iter().find_map(|prefix| {
                subject
                    .strip_prefix(prefix)
                    .and_then(|rest| rest.strip_prefix('_'))
                    .map(|remainder| (prefix.as_str(), remainder))
            })
        };
        let (invalid_prefix, base_name) = match match_prefix(name) {
            None => (false, name),
            Some((prefix, remainder))
                if STANDARD_LAW.prefix.forbidden.iter().any(|forbidden| {
                    prefix.eq_ignore_ascii_case(forbidden)
                }) =>
            {
                (true, remainder)
            }
            Some((_, remainder)) => match match_prefix(remainder) {
                Some((_, compound)) if !STANDARD_LAW.prefix.allow_compound => {
                    (true, compound)
                }
                _ => (false, remainder),
            },
        };
        let Some(quantity) =
            self.indexes.quantity_names.get(base_name).copied()
        else {
            return (invalid_prefix, None, base_name);
        };
        for marker in &self.indexes.suffix_markers {
            if let Some(remainder) = base_name.strip_suffix(marker.as_str()) {
                return (invalid_prefix, Some(quantity), remainder);
            }
        }
        (invalid_prefix, Some(quantity), base_name)
    }
    /// 返回指定路径已登记的公开函数名称
    pub(crate) fn public_names(
        &self,
        path: &str,
    ) -> Option<&BTreeSet<String>> {
        self.facts.public_callables.get(path)
    }
    /// 返回规则和项目事实的语义摘要
    pub(crate) fn semantic_digest(&self) -> [u8; 32] {
        self.semantic_digest
    }
    /// 返回章节与规则的展示关系
    pub(crate) fn presentation(&self) -> &PresentationPlan {
        &self.presentation
    }
}
/// 根据固定扩展名规则确定语言
fn standard_source_profile(extension: &str) -> Option<&'static str> {
    STANDARD_LAW
        .admission
        .fixed_source_profiles
        .iter()
        .find(|(candidate, _)| *candidate == extension)
        .map(|(_, profile)| *profile)
}
/// 校验注册表中的完整词元并去重
fn compile_token_facts(
    tokens: Vec<String>,
) -> Result<BTreeSet<String>, ReviewRejection> {
    let mut compiled = BTreeSet::new();
    for token in tokens {
        let normalized = lowercase_token(&token);
        let mut characters = normalized.chars();
        let valid = characters.next().is_some_and(char::is_alphabetic)
            && characters.clone().next().is_some()
            && characters.all(char::is_alphanumeric)
            && STANDARD_LAW
                .candidate
                .named_tokens
                .binary_search(&normalized.as_str())
                .is_err();
        if !valid || !compiled.insert(normalized) {
            return Err(ReviewRejection::new(
                "authority.token_vocabulary",
                "token registrations must be unique effective complete tokens",
            ));
        }
    }
    Ok(compiled)
}
/// 校验并编译项目依赖事实
///
/// 缺席与显式空对象含义相同；填写实际内容才启用依赖事实
fn compile_dependency_law(
    input: Option<DependencyAuthorityInput>,
) -> Result<DependencyProjectFacts, ReviewRejection> {
    let input = input.unwrap_or_default();
    let mut seen = BTreeSet::new();
    for name in input
        .python_standard_library
        .iter()
        .chain(&input.python_third_party)
        .chain(&input.python_project_roots)
    {
        if !ascii_identifier_is_valid(name) || !seen.insert(name) {
            return Err(ReviewRejection::new(
                "authority.dependency",
                "Python dependency classes must be exact top-level module roots and disjoint",
            ));
        }
    }
    Ok(DependencyProjectFacts {
        python_standard_library: input
            .python_standard_library
            .into_iter()
            .collect(),
        python_third_party: input.python_third_party.into_iter().collect(),
        python_project_roots: input.python_project_roots.into_iter().collect(),
        python_reorder_safe: input.python_reorder_safe,
        rust_reorder_safe: input.rust_reorder_safe,
    })
}
/// 校验外部协议固定名称记录的适用条件和唯一性
/// 输入类型与字段格式由反序列化检查负责
fn compile_external_fixed(
    rows: Vec<ExternalFixedIdentity>,
    law: &AdmissionLaw,
) -> Result<BTreeSet<ExternalFixedIdentity>, ReviewRejection> {
    let mut compiled = BTreeSet::new();
    for row in rows {
        let ExternalFixedIdentity {
            profile,
            role,
            owner,
            spelling,
        } = &row;
        if profile != law.external_fixed_profile
            || role != law.external_fixed_role
        {
            return Err(ReviewRejection::new(
                "authority.external_fixed",
                "external fixed row uses an unsupported seam",
            ));
        }
        if !rust_trait_surface_is_valid(owner)
            || !rust_callable_spelling_is_valid(spelling)
        {
            return Err(ReviewRejection::new(
                "authority.external_fixed",
                "external fixed fields must match observable Rust identities",
            ));
        }
        if !compiled.insert(row) {
            return Err(ReviewRejection::new(
                "authority.external_fixed",
                "external fixed rows must be unique",
            ));
        }
    }
    Ok(compiled)
}

/// 判断函数名称是否符合结构提取支持的拼写
fn native_callable_spelling_is_valid(
    profile: SourceProfile,
    spelling: &str,
) -> bool {
    const OPERATORS: &str = "== != < > <= >= <=> + - * / % ^ & | ~ ! = += -= *= /= %= ^= &= |= << >> <<= >>= ++ -- , ->* -> () []";
    let identifier = ascii_identifier_is_valid(spelling)
        && !callable_is_reserved(profile, spelling);
    match profile {
        SourceProfile::ProceduralSource => identifier,
        SourceProfile::Cplusplus => {
            identifier
                || spelling.strip_prefix('~').is_some_and(|name| {
                    ascii_identifier_is_valid(name)
                        && !callable_is_reserved(profile, name)
                })
                || spelling.strip_prefix("operator").is_some_and(|operator| {
                    OPERATORS
                        .split_ascii_whitespace()
                        .any(|item| item == operator)
                        || operator
                            .strip_prefix(' ')
                            .and_then(|item| item.strip_suffix("()"))
                            .is_some_and(cplusplus_conversion_type_is_valid)
                })
        }
        SourceProfile::Python | SourceProfile::Rust => false,
    }
}

/// 判断 ExternalFixed callable 是否为可观察 Rust identifier
fn rust_callable_spelling_is_valid(spelling: &str) -> bool {
    let raw = spelling.strip_prefix("r#");
    let semantic = raw.unwrap_or(spelling);
    ascii_identifier_is_valid(semantic)
        && raw.map_or_else(
            || !callable_is_reserved(SourceProfile::Rust, semantic),
            |_| {
                !STANDARD_LAW
                    .admission
                    .forbidden_rust_raw_callables
                    .split_ascii_whitespace()
                    .any(|value| value == semantic)
            },
        )
}

/// 判断 Rust trait 名称是否为路径或带单个生命周期参数的路径
fn rust_trait_surface_is_valid(surface: &str) -> bool {
    let Some((path, generic)) = surface.split_once('<') else {
        return rust_trait_path_is_valid(surface);
    };
    rust_trait_path_is_valid(path)
        && generic
            .strip_suffix('>')
            .and_then(|item| item.strip_prefix('\''))
            .is_some_and(ascii_identifier_is_valid)
}

/// 判断 Rust trait 路径是否符合语法树提取范围
fn rust_trait_path_is_valid(path: &str) -> bool {
    let mut segments = path.split("::");
    let Some(first) = segments.next() else {
        return false;
    };
    let first_valid = if matches!(first, "crate" | "self" | "super" | "Self") {
        segments.next().is_some_and(rust_callable_spelling_is_valid)
    } else {
        rust_callable_spelling_is_valid(first)
    };
    first_valid && segments.all(rust_callable_spelling_is_valid)
}

/// 判断 C++ 转换目标是否属于当前支持的类型拼写
fn cplusplus_conversion_type_is_valid(surface: &str) -> bool {
    STANDARD_LAW
        .admission
        .cplusplus_conversion_types
        .split_ascii_whitespace()
        .any(|value| value == surface)
        || surface.split("::").all(|segment| {
            ascii_identifier_is_valid(segment)
                && !callable_is_reserved(SourceProfile::Cplusplus, segment)
        })
}

/// 判断拼写是否为 C/C++ 与 Rust 共享的 ASCII identifier
fn ascii_identifier_is_valid(spelling: &str) -> bool {
    let mut characters = spelling.chars();
    characters.next().is_some_and(|character| {
        character.is_ascii_alphabetic() || character == '_'
    }) && characters
        .all(|character| character.is_ascii_alphanumeric() || character == '_')
}
/// 判断函数名称是否为当前语言的固定关键字
pub(crate) fn callable_is_reserved(
    profile: SourceProfile,
    spelling: &str,
) -> bool {
    STANDARD_LAW
        .admission
        .reserved_callables
        .iter()
        .find(|(key, _)| *key == profile.key())
        .is_some_and(|(_, values)| {
            values
                .split_ascii_whitespace()
                .any(|value| value == spelling)
        })
}
/// 校验原始 quantity 行后构造唯一的规范 Project Facts
fn compile_quantity_facts(
    concepts: BTreeMap<String, Vec<String>>,
    law: &AdmissionLaw,
) -> Result<BTreeMap<String, BTreeSet<String>>, ReviewRejection> {
    if concepts.iter().any(|(concept, suffixes)| {
        let mut seen = BTreeSet::new();
        !quantity_spelling_is_valid(concept, law.concept_segments)
            || law.require_unique_nonempty_suffixes && suffixes.is_empty()
            || suffixes.iter().any(|suffix| {
                !quantity_spelling_is_valid(suffix, law.suffix_segments)
                    || law.require_unique_nonempty_suffixes
                        && !seen.insert(suffix.as_str())
            })
    }) {
        return Err(ReviewRejection::new(
            "authority.quantity",
            "quantity registrations must be unique nonempty lower-snake rows",
        ));
    }
    Ok(concepts
        .into_iter()
        .map(|(concept, suffixes)| (concept, suffixes.into_iter().collect()))
        .collect())
}

/// 判断量值名称或后缀是否采用 ASCII 小写下划线形式
fn quantity_spelling_is_valid(
    spelling: &str,
    law: QuantitySegmentLaw,
) -> bool {
    spelling.split('_').all(|segment| {
        let digits = segment
            .trim_start_matches(|letter: char| letter.is_ascii_lowercase());
        digits.len() < segment.len()
            && (digits.is_empty()
                || matches!(law, QuantitySegmentLaw::AsciiLowercaseThenDigits)
                    && digits.bytes().all(|byte| byte.is_ascii_digit()))
    })
}
const PYTHON_DIRECTIVES: [DirectiveLaw; 5] = [
    DirectiveLaw("pragma: no cover", DirectiveArgumentForm::Exact),
    DirectiveLaw("fmt: skip", DirectiveArgumentForm::Exact),
    DirectiveLaw("type: ignore", DirectiveArgumentForm::BracketedCodes),
    DirectiveLaw("pyright: ignore", DirectiveArgumentForm::BracketedCodes),
    DirectiveLaw("noqa", DirectiveArgumentForm::ColonCodes),
];
const NATIVE_DIRECTIVES: [DirectiveLaw; 2] = [
    DirectiveLaw("IWYU pragma: keep", DirectiveArgumentForm::Exact),
    DirectiveLaw("NOLINT", DirectiveArgumentForm::ParenthesizedCodes),
];
const NATIVE_DIRECTIVE_CARRIERS: [DirectiveCarrier; 2] =
    [DirectiveCarrier("//", ""), DirectiveCarrier("/*", "*/")];
const PYTHON_HEADINGS: [HeadingLaw; 4] = [
    HeadingLaw("Args:", DocumentationRole::Arguments),
    HeadingLaw("Returns:", DocumentationRole::Returns),
    HeadingLaw("Raises:", DocumentationRole::Failures),
    HeadingLaw("Attributes:", DocumentationRole::Ownership),
];
const RUST_HEADINGS: [HeadingLaw; 5] = [
    HeadingLaw("# Arguments", DocumentationRole::Arguments),
    HeadingLaw("# Returns", DocumentationRole::Returns),
    HeadingLaw("# Errors", DocumentationRole::Failures),
    HeadingLaw("# Panics", DocumentationRole::Panics),
    HeadingLaw("# Safety", DocumentationRole::Safety),
];
const NATIVE_HEADINGS: [HeadingLaw; 6] = [
    HeadingLaw("模板参数：", DocumentationRole::TemplateParameters),
    HeadingLaw("参数：", DocumentationRole::Arguments),
    HeadingLaw("返回：", DocumentationRole::Returns),
    HeadingLaw("错误：", DocumentationRole::Failures),
    HeadingLaw("所有权：", DocumentationRole::Ownership),
    HeadingLaw("效果：", DocumentationRole::Effect),
];
const STANDARD_LAW: StandardLaw = StandardLaw {
    admission: AdmissionLaw {
        fixed_source_profiles: [
            ("py", "python"),
            ("rs", "rust"),
            ("c", "c"),
            ("h", "header"),
            ("cc", "cpp"),
            ("cpp", "cpp"),
            ("cxx", "cpp"),
            ("hpp", "cpp"),
            ("hh", "cpp"),
            ("hxx", "cpp"),
        ],
        reserved_callables: [
            (
                "c",
                "__alignof __alignof__ __asm __asm__ __attribute __attribute__ __based __cdecl __clrcall __declspec __except __extension__ __fastcall __finally __forceinline __inline __inline__ __leave __restrict __restrict__ __sptr __stdcall __thiscall __thread __try __unaligned __uptr __vectorcall __volatile__ _Alignas _alignof _Alignof _Atomic _Generic _Nonnull _Noreturn _unaligned alignas alignof asm auto bool break case char char16_t char32_t char64_t char8_t charptr_t const constexpr continue default defined do double else enum extern false FALSE float for goto if inline int int16_t int32_t int64_t int8_t intptr_t long max_align_t noreturn NULL nullptr nullptr_t offsetof ptrdiff_t register restrict return short signed size_t sizeof ssize_t static struct switch thread_local TRUE true typedef uint16_t uint32_t uint64_t uint8_t uintptr_t union unsigned void volatile while",
            ),
            (
                "cpp",
                "__alignof __alignof__ __asm __asm__ __attribute __attribute__ __based __cdecl __clrcall __declspec __except __extension__ __fastcall __finally __forceinline __inline __inline__ __leave __restrict __restrict__ __sptr __stdcall __thiscall __thread __try __unaligned __uptr __vectorcall __volatile__ _Alignas _Alignof _alignof _Atomic _Generic _Nonnull _Noreturn _unaligned alignas alignof and and_eq asm auto bitand bitor bool break case catch char char16_t char32_t char64_t char8_t charptr_t class co_await co_return co_yield compl concept const consteval constexpr constinit continue decltype default defined delete do double else enum explicit export extern FALSE false final float for friend goto if import inline int int16_t int32_t int64_t int8_t intptr_t long max_align_t module mutable namespace new noexcept noreturn not not_eq NULL nullptr nullptr_t offsetof operator or or_eq override private protected ptrdiff_t public register requires restrict return short signed size_t sizeof ssize_t static static_assert struct switch template this thread_local throw true TRUE try typedef typename uint16_t uint32_t uint64_t uint8_t uintptr_t union unsigned using virtual void volatile while xor xor_eq",
            ),
            (
                "rust",
                "as async await break const continue crate dyn else enum extern false fn for if impl in let loop match mod move mut pub ref return self Self static struct super trait true try type union unsafe use where while abstract become box do final macro override priv typeof unsized virtual yield",
            ),
        ],
        forbidden_rust_raw_callables: "_ crate self Self super",
        cplusplus_conversion_types: "bool char char8_t char16_t char32_t char64_t charptr_t double float int int8_t int16_t int32_t int64_t intptr_t long max_align_t nullptr_t ptrdiff_t short signed size_t ssize_t uint8_t uint16_t uint32_t uint64_t uintptr_t unsigned void",
        external_fixed_profile: "rust",
        external_fixed_role: "function",
        concept_segments: QuantitySegmentLaw::AsciiLowercase,
        suffix_segments: QuantitySegmentLaw::AsciiLowercaseThenDigits,
        require_unique_nonempty_suffixes: true,
    },
    project_fact_revision: 1,
    candidate: CandidateLaw {
        matching: "rust_unicode_lowercase_exact_token",
        named_tokens: [
            "alpha", "beta", "chi", "delta", "epsilon", "eta", "gamma",
            "iota", "kappa", "lambda", "mu", "nu", "omega", "omicron", "phi",
            "pi", "psi", "rho", "sigma", "tau", "theta", "upsilon", "xi",
            "zeta",
        ],
        single_character: true,
    },
    prefix: PrefixLaw {
        allowed: [
            "maximum", "minimum", "should", "lower", "needs", "upper", "can",
            "has", "is",
        ],
        forbidden: ["max", "min"],
        allow_compound: false,
    },
    narrative: NarrativeLaw {
        cjk_ranges: [('\u{3400}', '\u{4dbf}'), ('\u{4e00}', '\u{9fff}')],
        minimum_cjk_run: 2,
        blank_lines_after_summary: 1,
        forbidden_terminators: ['。', '.'],
    },
    directive_codes: DirectiveCodeLaw {
        separator: ',',
        allow_ascii_alphanumeric: true,
        punctuation: "_-.",
    },
    profiles: [
        ProfileLaw {
            identity: "python",
            observation_method: "tree-sitter-python@0.25.0+direct-source-facts",
            documentation: DocumentationLaw {
                carrier: DocumentationCarrierLaw::PythonSuite,
                summary: SummaryLocation::FirstLine,
                headings: &PYTHON_HEADINGS,
                heading_prefix: None,
                empty_role: "无",
                fields: StructuredFieldLaw {
                    roles: &[
                        DocumentationRole::Arguments,
                        DocumentationRole::Returns,
                        DocumentationRole::Failures,
                    ],
                    prefix: "",
                    delimiter: ':',
                    padding: ' ',
                    alignment_gap: 1,
                    exact_identity: true,
                    require_description: true,
                },
            },
            return_surface: ReturnSurfaceLaw {
                no_value: &["None"],
                never: &[
                    "Never",
                    "NoReturn",
                    "typing.Never",
                    "typing.NoReturn",
                ],
                never_attribute: None,
                unknown_blocks_documentation: true,
                never_documentation: None,
            },
            dependency: DependencyProfileLaw::Python {
                scope_revision: 2,
                order_revision: 3,
                within_tier_blank_lines: 0,
                cross_tier_blank_lines: 1,
                scope_blocked: "Python import outside module scope or exact TYPE_CHECKING block needs Authority",
                multi_import_blocked: "Python multi-module import statement needs per-module dependency facts",
                classification_blocked: "Python dependency classification is absent from Authority",
            },
            directive_carriers: &[DirectiveCarrier("#", "")],
            directives: &PYTHON_DIRECTIVES,
        },
        ProfileLaw {
            identity: "rust",
            observation_method: "tree-sitter-rust@0.24.2+direct-source-facts",
            documentation: DocumentationLaw {
                carrier: DocumentationCarrierLaw::RustOuter,
                summary: SummaryLocation::FirstNonempty,
                headings: &RUST_HEADINGS,
                heading_prefix: Some("# "),
                empty_role: "- 无",
                fields: StructuredFieldLaw {
                    roles: &[DocumentationRole::Arguments],
                    prefix: "- ",
                    delimiter: '：',
                    padding: ' ',
                    alignment_gap: 1,
                    exact_identity: true,
                    require_description: true,
                },
            },
            return_surface: ReturnSurfaceLaw {
                no_value: &["()"],
                never: &["!"],
                never_attribute: None,
                unknown_blocks_documentation: true,
                never_documentation: Some("- 不返回"),
            },
            dependency: DependencyProfileLaw::Rust {
                scope_revision: 1,
                order_revision: 3,
                within_group_blank_lines: 0,
                unknown_use_blocked: "Rust use-tree contains unsupported direct syntax",
            },
            directive_carriers: &[],
            directives: &[],
        },
        ProfileLaw {
            identity: "c",
            observation_method: "tree-sitter-c@0.24.2+direct-source-facts",
            documentation: DocumentationLaw {
                carrier: DocumentationCarrierLaw::NativeAdjacent,
                summary: SummaryLocation::FirstNonempty,
                headings: &NATIVE_HEADINGS,
                heading_prefix: None,
                empty_role: "- 无",
                fields: StructuredFieldLaw {
                    roles: &[DocumentationRole::Arguments],
                    prefix: "- ",
                    delimiter: '：',
                    padding: ' ',
                    alignment_gap: 1,
                    exact_identity: true,
                    require_description: true,
                },
            },
            return_surface: ReturnSurfaceLaw {
                no_value: &["void"],
                never: &["_Noreturn"],
                never_attribute: Some("noreturn"),
                unknown_blocks_documentation: true,
                never_documentation: None,
            },
            dependency: DependencyProfileLaw::Procedural {
                unavailable_blocked: "C/C++ dependency target or preprocessing capability is absent from Authority",
            },
            directive_carriers: &NATIVE_DIRECTIVE_CARRIERS,
            directives: &NATIVE_DIRECTIVES,
        },
        ProfileLaw {
            identity: "cpp",
            observation_method: "tree-sitter-cpp@8b5b49eb+direct-source-facts",
            documentation: DocumentationLaw {
                carrier: DocumentationCarrierLaw::NativeAdjacent,
                summary: SummaryLocation::FirstNonempty,
                headings: &NATIVE_HEADINGS,
                heading_prefix: None,
                empty_role: "- 无",
                fields: StructuredFieldLaw {
                    roles: &[
                        DocumentationRole::TemplateParameters,
                        DocumentationRole::Arguments,
                    ],
                    prefix: "- ",
                    delimiter: '：',
                    padding: ' ',
                    alignment_gap: 1,
                    exact_identity: true,
                    require_description: true,
                },
            },
            return_surface: ReturnSurfaceLaw {
                no_value: &["void"],
                never: &[],
                never_attribute: Some("noreturn"),
                unknown_blocks_documentation: true,
                never_documentation: None,
            },
            dependency: DependencyProfileLaw::Cplusplus {
                scope_revision: 2,
                module_placement_revision: 1,
                unavailable_blocked: "C/C++ dependency target or preprocessing capability is absent from Authority",
            },
            directive_carriers: &NATIVE_DIRECTIVE_CARRIERS,
            directives: &NATIVE_DIRECTIVES,
        },
    ],
    rules: [
        RuleLaw {
            operator: RuleOperator::SourceParseability,
            identity: "source.parseability",
            grade: FindingGrade::HardViolation,
            message: "managed source must satisfy its pinned Profile parseability contract",
            question: None,
            semantic_revision: 1,
            chapter: "Structure",
            presentation_contract: "source_structure",
            rank: 0,
        },
        RuleLaw {
            operator: RuleOperator::SourceTrailingComment,
            identity: "source.trailing_comment",
            grade: FindingGrade::HardViolation,
            message: "ordinary comments must not share a physical line with code",
            question: None,
            semantic_revision: 2,
            chapter: "Structure",
            presentation_contract: "source_structure",
            rank: 1,
        },
        RuleLaw {
            operator: RuleOperator::IdentifierCandidate,
            identity: "identifier.candidate",
            grade: FindingGrade::ReviewRequired,
            message: "candidate symbolic form requires an Authority-backed rename",
            question: Some("该符号对应哪个完整 Canonical Concept？"),
            semantic_revision: 4,
            chapter: "Name",
            presentation_contract: "identifier_declaration",
            rank: 5,
        },
        RuleLaw {
            operator: RuleOperator::IdentifierReserved,
            identity: "identifier.reserved",
            grade: FindingGrade::HardViolation,
            message: "project declaration uses a language-reserved identifier form",
            question: None,
            semantic_revision: 4,
            chapter: "Name",
            presentation_contract: "identifier_declaration",
            rank: 6,
        },
        RuleLaw {
            operator: RuleOperator::IdentifierCanonicalForm,
            identity: "identifier.canonical_form",
            grade: FindingGrade::HardViolation,
            message: "identifier does not satisfy its language-local canonical form",
            question: None,
            semantic_revision: 5,
            chapter: "Name",
            presentation_contract: "identifier_declaration",
            rank: 7,
        },
        RuleLaw {
            operator: RuleOperator::IdentifierRepresentationSuffix,
            identity: "identifier.representation_suffix",
            grade: FindingGrade::HardViolation,
            message: "quantity-bearing value must use its registered representation suffix",
            question: None,
            semantic_revision: 5,
            chapter: "Name",
            presentation_contract: "identifier_declaration",
            rank: 8,
        },
        RuleLaw {
            operator: RuleOperator::IdentifierUnknownToken,
            identity: "identifier.unknown_token",
            grade: FindingGrade::ReviewRequired,
            message: "identifier contains a token absent from the compiled vocabulary",
            question: Some("该 token 是否应先加入 Authority 并重新审查？"),
            semantic_revision: 4,
            chapter: "Name",
            presentation_contract: "identifier_declaration",
            rank: 9,
        },
        RuleLaw {
            operator: RuleOperator::DocumentationCarrier,
            identity: "documentation.carrier",
            grade: FindingGrade::HardViolation,
            message: "documentation subject has a missing or forbidden profile carrier",
            question: None,
            semantic_revision: 3,
            chapter: "Explain",
            presentation_contract: "callable_documentation",
            rank: 10,
        },
        RuleLaw {
            operator: RuleOperator::DocumentationSummary,
            identity: "documentation.summary",
            grade: FindingGrade::HardViolation,
            message: "documentation carrier must contain a non-empty summary",
            question: None,
            semantic_revision: 4,
            chapter: "Explain",
            presentation_contract: "callable_documentation",
            rank: 11,
        },
        RuleLaw {
            operator: RuleOperator::DocumentationTerminator,
            identity: "documentation.punctuation",
            grade: FindingGrade::HardViolation,
            message: "summary and controlled field descriptions must not end in a sentence terminator",
            question: None,
            semantic_revision: 4,
            chapter: "Explain",
            presentation_contract: "callable_documentation",
            rank: 12,
        },
        RuleLaw {
            operator: RuleOperator::DocumentationPublicContract,
            identity: "documentation.public_contract",
            grade: FindingGrade::HardViolation,
            message: "public callable must provide every structurally required controlled role in profile order",
            question: None,
            semantic_revision: 6,
            chapter: "Explain",
            presentation_contract: "callable_documentation",
            rank: 13,
        },
        RuleLaw {
            operator: RuleOperator::DocumentationSafety,
            identity: "documentation.safety",
            grade: FindingGrade::HardViolation,
            message: "unsafe Rust subject must provide a non-empty # Safety section",
            question: None,
            semantic_revision: 4,
            chapter: "Explain",
            presentation_contract: "callable_documentation",
            rank: 14,
        },
        RuleLaw {
            operator: RuleOperator::DependencyWildcard,
            identity: "dependency.wildcard",
            grade: FindingGrade::HardViolation,
            message: "wildcard dependency binding is forbidden",
            question: None,
            semantic_revision: 1,
            chapter: "Relate",
            presentation_contract: "dependency_declaration",
            rank: 2,
        },
        RuleLaw {
            operator: RuleOperator::DependencyModulePlacement,
            identity: "dependency.module_placement",
            grade: FindingGrade::HardViolation,
            message: "C++ module import must precede ordinary top-level declarations",
            question: None,
            semantic_revision: 1,
            chapter: "Relate",
            presentation_contract: "dependency_declaration",
            rank: 3,
        },
        RuleLaw {
            operator: RuleOperator::DependencyOrder,
            identity: "dependency.order",
            grade: FindingGrade::HardViolation,
            message: "dependencies must follow the language-local canonical order",
            question: None,
            semantic_revision: 1,
            chapter: "Relate",
            presentation_contract: "dependency_declaration",
            rank: 4,
        },
    ],
};
/// 构造不可由项目覆写的章节展示关系
fn standard_presentation() -> PresentationPlan {
    let mut rules: Vec<_> = STANDARD_LAW.rules.iter().collect();
    rules.sort_by_key(|rule| rule.rank);
    let chapters = rules
        .chunk_by(|left, right| {
            left.chapter == right.chapter
                && left.presentation_contract == right.presentation_contract
        })
        .map(|rules| {
            let first = rules[0];
            let profiles = ["c", "cpp", "python", "rust"]
                .into_iter()
                .map(|profile| {
                    let cell = PresentationCell::Supported {
                        contract: first.presentation_contract.to_owned(),
                    };
                    (profile.to_owned(), cell)
                })
                .collect();
            PresentationChapter {
                chapter: first.chapter.to_owned(),
                rules: rules
                    .iter()
                    .map(|rule| rule.identity.to_owned())
                    .collect(),
                profiles,
            }
        })
        .collect();
    PresentationPlan { chapters }
}

/// 计算标准规则和项目事实的语义摘要
///
/// 序列化布局本身是身份协议：字节直接喂给 BLAKE3 derive-key 模式，
/// 不附加手工前缀；序列化失败返回 authority.identity
fn law_digest(facts: &ProjectFacts) -> Result<[u8; 32], ReviewRejection> {
    let law = SemanticLaw {
        standard: &STANDARD_LAW,
        project: facts,
    };
    let bytes = serde_json::to_vec(&law).map_err(|error| {
        ReviewRejection::new(
            "authority.identity",
            format!("compiled Authority Law failed to serialize: {error}"),
        )
    })?;
    let mut hasher = blake3::Hasher::new_derive_key(
        "github.com/HIT-SudoMaker/CSU authority law semantic identity",
    );
    hasher.update(&bytes);
    Ok(*hasher.finalize().as_bytes())
}
/// 统一将完整词元转为小写
///
/// 准入与观察两侧共用本函数；它是 Rust 的 str::to_lowercase，
/// 不是大小写折叠，也不做字形、兼容性或转写归一
fn lowercase_token(token: &str) -> String {
    token.to_lowercase()
}
/// 返回指定语言的源码观察和文档规则
pub(crate) fn profile_law(language: &str) -> &'static ProfileLaw {
    STANDARD_LAW
        .profiles
        .iter()
        .find(|profile| profile.identity == language)
        .expect("captured source has one supported Profile")
}
/// 返回四语言共享的叙述区规则
pub(crate) fn narrative_law() -> &'static NarrativeLaw {
    &STANDARD_LAW.narrative
}
/// 统一相对路径分隔符并拒绝非法路径
pub(crate) fn normalize_relative_path(
    path: &str,
) -> Result<String, ReviewRejection> {
    let path = path.replace('\\', "/");
    let bytes = path.as_bytes();
    let has_platform_prefix = bytes.get(1) == Some(&b':')
        && bytes.first().is_some_and(u8::is_ascii_alphabetic);
    if path.is_empty()
        || path.starts_with('/')
        || has_platform_prefix
        || path.split('/').any(|part| matches!(part, "" | "." | ".."))
    {
        return Err(ReviewRejection::new(
            "request.path",
            format!("invalid relative path {path:?}"),
        ));
    }
    Ok(path)
}
