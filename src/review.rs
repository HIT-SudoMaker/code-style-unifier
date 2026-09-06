use crate::authority::CompiledAuthority;
use crate::authority::DependencyProfileLaw;
use crate::authority::DocumentationCarrierLaw;
use crate::authority::DocumentationRole;
use crate::authority::ProfileLaw;
use crate::authority::QuantityNameDisposition;
use crate::authority::ReturnShape;
use crate::authority::ReviewRejection;
use crate::authority::RuleOperator;
use crate::authority::SourceProfile as Language;
use crate::authority::TokenDisposition;
use crate::authority::callable_is_reserved;
use crate::authority::narrative_law;
use crate::authority::normalize_relative_path;
use crate::authority::profile_law;
use crate::model::CompactCoverage;
use crate::model::FactFamilyState;
use crate::model::FamilyClosure;
use crate::model::FileCoverage;
use crate::model::Finding;
use crate::model::REVIEW_SCHEMA_VERSION;
use crate::model::ReviewFailure;
use crate::model::ReviewInput;
use crate::model::ReviewMetrics;
use crate::model::ReviewTerminal;
use crate::model::ReviewedScope;
use crate::model::SealedReview;
use std::collections::BTreeMap;
use std::collections::BTreeSet;
use std::fs;
use std::path::Path;
use tree_sitter::Language as TreeSitterLanguage;
use tree_sitter::Node;
use tree_sitter::Parser;
use walkdir::WalkDir;
#[derive(Clone, Debug)]
struct OwnedDocument {
    path: String,
    bytes: Vec<u8>,
    language: Language,
    capture_error: Option<String>,
}

/// 表示已确定路径和语言的源码输入
struct AdmittedSource {
    path: String,
    language: Language,
}

type CaptureResult = Result<
    (ReviewedScope, Vec<OwnedDocument>, ReviewMetrics),
    ReviewRejection,
>;

#[derive(Debug)]
struct FileResult {
    coverage: FileCoverage,
    findings: Vec<Finding>,
    snapshot_digest: [u8; 32],
    byte_sweeps: u64,
    structural_parses: u64,
}

#[derive(Clone, Debug)]
struct Callable {
    language: Language,
    name: String,
    line: usize,
    column: usize,
    named: bool,
    visibility: DocumentationVisibility,
    parameters: Vec<String>,
    parameters_complete: bool,
    template_parameters: Vec<String>,
    template_parameters_complete: bool,
    requires_template_parameters: bool,
    return_shape: ReturnShape,
    carrier: Option<String>,
    requires_safety: bool,
    requires_effect: bool,
    carrier_unresolved: bool,
}

/// 汇总一个 Rust 声明附着的属性事实
struct RustAttributeFacts<'tree> {
    documentation: Vec<String>,
    /// 是否观察到精确 macro_export 属性
    is_public: bool,
    nonliteral_documentation: bool,
    preceding: Option<Node<'tree>>,
    attachment_start: usize,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum DocumentationVisibility {
    Public,
    Internal,
    IdentityUnresolved,
    Unresolved,
}

#[derive(Clone, Debug)]
struct Declaration {
    name: String,
    line: usize,
    column: usize,
    value_like: bool,
    role: IdentifierRole,
    local_form: LocalIdentifierForm,
    reserved_scope: bool,
    owner: IdentifierOwner,
    external_owner: Option<String>,
}

/// 在一次遍历中拥有声明观察所需的稳定上下文与输出
struct DeclarationReview<'source> {
    language: Language,
    source: &'source [u8],
    output: Vec<Declaration>,
    callables: Vec<Callable>,
}

#[derive(Debug)]
struct LocalFacts {
    callables: Vec<Callable>,
    declarations: Vec<Declaration>,
    python_module_docstring: Option<(usize, usize)>,
    dependencies: DependencyFacts,
    trailing_comments: Vec<TrailingComment>,
}

/// 表示同一物理行中跟随代码的 comment token
#[derive(Debug)]
struct TrailingComment {
    line: usize,
    column: usize,
    end_row: usize,
}

#[derive(Debug)]
struct ParseEvidence {
    line: usize,
    column: usize,
    reason: &'static str,
}

/// 为同一源码路径构造可稳定排序的审查问题
struct FindingState<'path> {
    path: &'path str,
    findings: Vec<Finding>,
}

impl<'path> FindingState<'path> {
    /// 开始收集单个文件的审查问题
    fn new(path: &'path str) -> Self {
        Self {
            path,
            findings: Vec::new(),
        }
    }

    /// 根据固定规则目录追加一个源码问题
    fn push(
        &mut self,
        operator: RuleOperator,
        line: usize,
        column: usize,
        subject: &str,
        observation: &str,
    ) {
        let rule = operator.law();
        self.findings.push(Finding {
            rule: rule.identity.to_owned(),
            grade: rule.grade,
            path: self.path.to_owned(),
            line,
            column,
            subject: subject.to_owned(),
            observation: observation.to_owned(),
            question: rule.question.map(str::to_owned),
            message: rule.message.to_owned(),
        });
    }

    /// 返回本文件已收集的全部问题
    fn complete(self) -> Vec<Finding> {
        self.findings
    }
}

#[derive(Debug)]
enum StructuralObservation {
    Complete(LocalFacts),
    SourceRejected(ParseEvidence),
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum IdentifierRole {
    Value,
    Function,
    Type,
    Constant,
    Enumerator,
    Variant,
    Typedef,
    ModuleNamespace,
    Tag,
    Lifetime,
    Label,
    Alias,
    ModuleBinding,
}

/// 表示从语言结构识别的标识符归属
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum IdentifierOwner {
    /// 动态成员构造缺少可直接证明的声明角色
    Unresolved,
    /// 语法或语言身份固定拼写，例如 Rust 类型上下文 `Self`
    LanguageFixed,
    /// 语言结构确定的约定名称，例如 Python 首位接收者
    ProfileFixed,
    /// 语法证明的非绑定丢弃角色
    Discard,
    /// 作者选择，进入正常候选/词形/量纲判定
    AuthorChosen,
}

impl IdentifierRole {
    /// 返回声明角色对应的 Authority 拼写
    fn key(self) -> &'static str {
        match self {
            Self::Value => "value",
            Self::Function => "function",
            Self::Type => "type",
            Self::Constant => "constant",
            Self::Enumerator => "enumerator",
            Self::Variant => "variant",
            Self::Typedef => "typedef",
            Self::ModuleNamespace => "module_namespace",
            Self::Tag => "tag",
            Self::Lifetime => "lifetime",
            Self::Label => "label",
            Self::Alias => "alias",
            Self::ModuleBinding => "module_binding",
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum LocalIdentifierForm {
    Plain,
    PythonPrivate,
    PythonProtocol,
    PythonInvalidReceiver,
    RustRaw,
    RustLifetime,
    TypeDefinitionSuffix,
    CplusplusPrivateMember,
}

/// 审查输入源码并汇总各文件结果
pub(crate) fn review(
    authority: &CompiledAuthority,
    input: ReviewInput<'_>,
) -> ReviewTerminal {
    let (scope, documents, metrics) = match capture(authority, input) {
        Ok(value) => value,
        Err(rejection) => return ReviewTerminal::Rejected(rejection),
    };
    let mut results = Vec::with_capacity(documents.len());
    let mut run_metrics = metrics;
    for document in documents {
        match close_file(authority, &document) {
            Ok(result) => {
                run_metrics.byte_sweeps += result.byte_sweeps;
                run_metrics.structural_parses += result.structural_parses;
                results.push(result);
            }
            Err(failure) => return ReviewTerminal::Failed(failure),
        }
    }
    seal(authority, scope, results, run_metrics)
}

/// 读取审查输入并记录文件快照
fn capture(
    authority: &CompiledAuthority,
    input: ReviewInput<'_>,
) -> CaptureResult {
    match input {
        ReviewInput::Documents(set) => {
            if set.revision.is_empty() {
                return Err(ReviewRejection::new(
                    "request.revision",
                    "document revision must not be empty",
                ));
            }
            let mut paths = BTreeSet::new();
            let mut documents = Vec::with_capacity(set.documents.len());
            for document in set.documents {
                let Some(admitted) =
                    source_admission(authority, document.relative_path)?
                else {
                    return Err(ReviewRejection::new(
                        "request.language",
                        format!(
                            "document language is not governed: {}",
                            document.relative_path
                        ),
                    ));
                };
                if !paths.insert(admitted.path.clone()) {
                    return Err(ReviewRejection::new(
                        "request.path",
                        format!("duplicate document path {}", admitted.path),
                    ));
                }
                documents.push(OwnedDocument {
                    path: admitted.path,
                    bytes: document.bytes.to_vec(),
                    language: admitted.language,
                    capture_error: None,
                });
            }
            documents.sort_by(|left, right| left.path.cmp(&right.path));
            let files =
                documents.iter().map(|item| item.path.clone()).collect();
            let scope = ReviewedScope::Documents {
                revision: set.revision.to_owned(),
                files,
            };
            Ok((
                scope,
                documents,
                ReviewMetrics {
                    files_read: set.documents.len() as u64,
                    ..ReviewMetrics::default()
                },
            ))
        }
        ReviewInput::Workspace(root) => capture_workspace(authority, root),
    }
}

/// 遍历工作区并读取纳入审查的源码
fn capture_workspace(
    authority: &CompiledAuthority,
    root: &Path,
) -> CaptureResult {
    let canonical = root.canonicalize().map_err(|error| {
        ReviewRejection::new(
            "request.workspace",
            format!("cannot open workspace {}: {error}", root.display()),
        )
    })?;
    let scope_root = canonical.to_str().ok_or_else(|| {
        ReviewRejection::new(
            "request.workspace",
            "canonical workspace path is not valid Unicode",
        )
    })?;
    let mut admitted_sources = Vec::new();
    let mut admitted_paths = BTreeSet::new();
    for entry in WalkDir::new(&canonical)
        .follow_links(false)
        .sort_by_file_name()
    {
        let entry = entry.map_err(|error| {
            ReviewRejection::new("request.workspace", error.to_string())
        })?;
        if !entry.file_type().is_file() {
            continue;
        }
        let relative =
            entry.path().strip_prefix(&canonical).map_err(|_| {
                ReviewRejection::new(
                    "request.path",
                    "source file escaped workspace",
                )
            })?;
        let relative = relative.to_str().ok_or_else(|| {
            ReviewRejection::new(
                "request.path",
                "workspace source path is not valid Unicode",
            )
        })?;
        let Some(admitted) = source_admission(authority, relative)? else {
            continue;
        };
        if !admitted_paths.insert(admitted.path.clone()) {
            return Err(ReviewRejection::new(
                "request.path",
                "distinct source paths collide after normalization",
            ));
        }
        admitted_sources.push((
            admitted.path,
            entry.path().to_path_buf(),
            admitted.language,
        ));
    }
    let mut documents = Vec::with_capacity(admitted_sources.len());
    for (path, source_path, language) in admitted_sources {
        let (bytes, capture_error) = match fs::read(source_path) {
            Ok(bytes) => (bytes, None),
            Err(error) => (
                Vec::new(),
                Some(format!("cannot read admitted source {path}: {error}")),
            ),
        };
        documents.push(OwnedDocument {
            path,
            bytes,
            language,
            capture_error,
        });
    }
    documents.sort_by(|left, right| left.path.cmp(&right.path));
    let files = documents.iter().map(|item| item.path.clone()).collect();
    let files_read = documents
        .iter()
        .filter(|document| document.capture_error.is_none())
        .count() as u64;
    Ok((
        ReviewedScope::Workspace {
            root: scope_root.replace('\\', "/"),
            files,
        },
        documents,
        ReviewMetrics {
            files_read,
            ..ReviewMetrics::default()
        },
    ))
}

/// 根据已读取文档生成文件审查终态
fn close_file(
    authority: &CompiledAuthority,
    document: &OwnedDocument,
) -> Result<FileResult, ReviewFailure> {
    let snapshot_digest = *blake3::hash(&document.bytes).as_bytes();
    let (findings, closure, byte_sweeps, structural_parses) =
        if let Some(reason) = &document.capture_error {
            (
                Vec::new(),
                FamilyClosure::CaptureBlocked(reason.clone()),
                0,
                0,
            )
        } else {
            let physical_lines = if document.bytes.is_empty() {
                0
            } else {
                document.bytes.iter().filter(|byte| **byte == b'\n').count()
                    + usize::from(!document.bytes.ends_with(b"\n"))
            } as u32;
            let (observation, structural_parses) =
                observe_structure(document)?;
            let (findings, closure) = match observation {
                StructuralObservation::Complete(facts) => {
                    close_complete_source(
                        authority,
                        document,
                        physical_lines,
                        facts,
                    )
                }
                StructuralObservation::SourceRejected(evidence) => {
                    close_source_rejection(document, physical_lines, evidence)
                }
            };
            (findings, closure, 1, structural_parses)
        };
    Ok(FileResult {
        coverage: FileCoverage::close(document.path.clone(), closure),
        findings,
        snapshot_digest,
        byte_sweeps,
        structural_parses,
    })
}

/// 检查已提取的结构事实并记录各类结果
fn close_complete_source(
    authority: &CompiledAuthority,
    document: &OwnedDocument,
    physical_lines: u32,
    facts: LocalFacts,
) -> (Vec<Finding>, FamilyClosure) {
    let language = document.language;
    let LocalFacts {
        mut callables,
        declarations,
        python_module_docstring,
        dependencies,
        trailing_comments,
    } = facts;
    resolve_native_public_visibility(
        authority,
        &document.path,
        &mut callables,
    );
    reject_ambiguous_public_callable_identities(&mut callables);
    let mut findings = FindingState::new(&document.path);
    let documentation_block_reason =
        unresolved_documentation_reason(&callables);
    if let Some((line, column)) = python_module_docstring {
        findings.push(
            RuleOperator::DocumentationCarrier,
            line,
            column,
            "<module>",
            concat!(
                "observed a suite-first constant string expression at ",
                "Python module scope"
            ),
        );
    }
    for callable in &callables {
        if callable.carrier_unresolved {
            continue;
        }
        let Some(carrier) = &callable.carrier else {
            findings.push(
                RuleOperator::DocumentationCarrier,
                callable.line,
                callable.column,
                &callable.name,
                concat!(
                    "the declaration has no directly attached ",
                    "profile-recognized carrier"
                ),
            );
            continue;
        };
        let documented_lines = documentation_lines(callable.language, carrier);
        let profile = profile_law(callable.language.key());
        let summary = profile.documentation_summary(
            documented_lines.iter().map(|line| line.text),
        );
        if summary.is_none_or(|line| {
            profile.is_documentation_heading(line)
                || callable.language == Language::Rust
                    && rust_markdown_line_is_indented_code(line)
                || !contains_chinese_phrase(line)
        }) {
            findings.push(
                RuleOperator::DocumentationSummary,
                callable.line,
                callable.column,
                &callable.name,
                &format!(
                    "observed attached documentation for {}",
                    callable.name
                ),
            );
            continue;
        }
        let has_public_contract = callable.named
            && callable.visibility == DocumentationVisibility::Public;
        let signature_is_resolved = callable.parameters_complete
            && callable.template_parameters_complete
            && (callable.return_shape != ReturnShape::Unknown
                || !profile.return_surface.unknown_blocks_documentation);
        if controlled_line_has_terminator(
            callable.language,
            has_public_contract,
            callable.requires_safety,
            &documented_lines,
        ) {
            findings.push(
                RuleOperator::DocumentationTerminator,
                callable.line,
                callable.column,
                &callable.name,
                &format!(
                    "observed attached documentation for {}",
                    callable.name
                ),
            );
        }
        if has_public_contract
            && signature_is_resolved
            && let Err(defect) =
                public_contract_is_complete(callable, &documented_lines)
        {
            findings.push(
                RuleOperator::DocumentationPublicContract,
                callable.line,
                callable.column,
                &callable.name,
                &defect.observation(&callable.name),
            );
        }
        if callable.requires_safety
            && !rust_safety_contract_is_complete(&documented_lines)
        {
            findings.push(
                RuleOperator::DocumentationSafety,
                callable.line,
                callable.column,
                &callable.name,
                &format!(
                    "observed attached documentation for {}",
                    callable.name
                ),
            );
        }
    }
    for declaration in &declarations {
        if let Some(operator) =
            judge_identifier(authority, language, declaration)
        {
            findings.push(
                operator,
                declaration.line,
                declaration.column,
                &declaration.name,
                &format!(
                    "observed author-chosen declaration spelling {}",
                    declaration.name
                ),
            );
        }
    }
    let dependency_state =
        judge_dependencies(authority, language, &dependencies, &mut findings);
    for comment in &trailing_comments {
        findings.push(
            RuleOperator::SourceTrailingComment,
            comment.line,
            comment.column,
            "<comment>",
            "observed an ordinary comment sharing a physical line with code",
        );
    }
    let unresolved: Vec<_> = declarations
        .iter()
        .filter(|declaration| declaration.owner == IdentifierOwner::Unresolved)
        .map(|declaration| {
            format!(
                "{}@{}:{}",
                declaration.name, declaration.line, declaration.column
            )
        })
        .collect();
    let identifier_state = if unresolved.is_empty() {
        FactFamilyState::Complete(declarations.len() as u32)
    } else {
        FactFamilyState::Blocked(format!(
            "unresolved identifier roles: {}",
            unresolved.join(", ")
        ))
    };
    let documentation_state = if let Some(reason) = documentation_block_reason
    {
        FactFamilyState::Blocked(reason)
    } else {
        let subjects = callables.len() as u32
            + u32::from(python_module_docstring.is_some());
        FactFamilyState::Complete(subjects)
    };
    (
        findings.complete(),
        FamilyClosure::Observed {
            physical_lines,
            identifier: identifier_state,
            documentation: documentation_state,
            dependency: dependency_state,
        },
    )
}

/// 执行一次结构观察并返回 owned facts 或拒绝证据
fn observe_structure(
    document: &OwnedDocument,
) -> Result<(StructuralObservation, u64), ReviewFailure> {
    if let Err(error) = std::str::from_utf8(&document.bytes) {
        let (line, column) = document.bytes[..error.valid_up_to()]
            .iter()
            .fold((1, 1), |(line, column), byte| match byte {
                b'\n' => (line + 1, 1),
                _ => (line, column + 1),
            });
        return Ok((
            StructuralObservation::SourceRejected(ParseEvidence {
                line,
                column,
                reason: "source is not valid UTF-8",
            }),
            0,
        ));
    }
    let mut parser = Parser::new();
    parser
        .set_language(&tree_sitter_language(document.language))
        .map_err(|error| {
            ReviewFailure::new("parser.language", error.to_string())
        })?;
    let tree = parser.parse(&document.bytes, None).ok_or_else(|| {
        ReviewFailure::new("parser.cancelled", "parser returned no tree")
    })?;
    if tree.root_node().has_error() {
        let parse_error = first_parse_error(tree.root_node())
            .expect("has_error must contain an ERROR or MISSING node");
        let point = parse_error.start_position();
        return Ok((
            StructuralObservation::SourceRejected(ParseEvidence {
                line: point.row + 1,
                column: point.column + 1,
                reason: if parse_error.is_missing() {
                    "pinned grammar reported a MISSING node"
                } else {
                    "pinned grammar reported an ERROR node"
                },
            }),
            1,
        ));
    }
    let language = document.language;
    let (mut declarations, callables) = DeclarationReview::collect(
        language,
        tree.root_node(),
        &document.bytes,
    );
    declarations.sort_by(|left, right| {
        (left.line, left.column, &left.name).cmp(&(
            right.line,
            right.column,
            &right.name,
        ))
    });
    declarations.dedup_by(|left, right| {
        left.line == right.line
            && left.column == right.column
            && left.name == right.name
    });
    let python_module_docstring = if language == Language::Python {
        python_module_docstring(tree.root_node(), &document.bytes).map(
            |docstring| {
                let point = docstring.start_position();
                (point.row + 1, point.column + 1)
            },
        )
    } else {
        None
    };
    let dependencies =
        observe_dependencies(language, tree.root_node(), &document.bytes);
    let profile = profile_law(language.key());
    let mut trailing_comments = Vec::new();
    let mut candidate_comments = Vec::new();
    let mut last_code_row = None;
    collect_trailing_comments(
        profile,
        language,
        tree.root_node(),
        &document.bytes,
        &mut last_code_row,
        &mut candidate_comments,
        &mut trailing_comments,
    );
    drop(tree);
    Ok((
        StructuralObservation::Complete(LocalFacts {
            callables,
            declarations,
            python_module_docstring,
            dependencies,
            trailing_comments,
        }),
        1,
    ))
}

/// 收集由 CST 证明且与代码共享物理行的普通 comment token
fn collect_trailing_comments(
    profile: &ProfileLaw,
    language: Language,
    node: Node<'_>,
    source: &[u8],
    last_code_row: &mut Option<usize>,
    candidate_comments: &mut Vec<TrailingComment>,
    output: &mut Vec<TrailingComment>,
) {
    let comment = node.kind() == "comment"
        || language == Language::Rust
            && matches!(node.kind(), "line_comment" | "block_comment");
    if comment {
        let point = node.start_position();
        let text =
            std::str::from_utf8(&source[node.start_byte()..node.end_byte()])
                .expect("accepted source is valid UTF-8");
        let end_row = node
            .end_position()
            .row
            .saturating_sub(usize::from(text.ends_with('\n')));
        let observation = TrailingComment {
            line: point.row + 1,
            column: point.column + 1,
            end_row,
        };
        if *last_code_row == Some(point.row) && !profile.is_directive(text) {
            output.push(observation);
        } else {
            candidate_comments.push(observation);
        }
        return;
    }
    if node.child_count() == 0 {
        let start_row = node.start_position().row;
        output.extend(
            candidate_comments
                .drain(..)
                .filter(|comment| comment.end_row == start_row),
        );
        *last_code_row = Some(node.end_position().row);
        return;
    }
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        collect_trailing_comments(
            profile,
            language,
            child,
            source,
            last_code_row,
            candidate_comments,
            output,
        );
    }
}

/// 按源码顺序返回最早的 ERROR 或 MISSING 节点
fn first_parse_error(root: Node<'_>) -> Option<Node<'_>> {
    let mut children = vec![root];
    while let Some(node) = children.pop() {
        if node.is_error() || node.is_missing() {
            return Some(node);
        }
        for index in (0..node.child_count()).rev() {
            if let Some(child) = node.child(index as u32)
                && (child.has_error()
                    || child.is_error()
                    || child.is_missing())
            {
                children.push(child);
            }
        }
    }
    None
}

/// 汇总函数文档缺少的必要事实
fn unresolved_documentation_reason(callables: &[Callable]) -> Option<String> {
    let mut subjects = Vec::new();
    for callable in callables {
        let mut categories = Vec::with_capacity(5);
        if callable.visibility == DocumentationVisibility::IdentityUnresolved {
            categories.push("identity");
        } else if callable.visibility == DocumentationVisibility::Unresolved {
            categories.push("tier");
        }
        if callable.carrier_unresolved {
            categories.push("carrier");
        }
        if callable.named
            && callable.visibility == DocumentationVisibility::Public
        {
            if !callable.parameters_complete {
                categories.push("parameters");
            }
            if !callable.template_parameters_complete {
                categories.push("template");
            }
            if callable.return_shape == ReturnShape::Unknown
                && profile_law(callable.language.key())
                    .return_surface
                    .unknown_blocks_documentation
            {
                categories.push("return");
            }
        }
        if !categories.is_empty() {
            subjects.push(format!(
                "{}@{}:{}[{}]",
                callable.name,
                callable.line,
                callable.column,
                categories.join(","),
            ));
        }
    }
    subjects.sort();
    subjects.dedup();
    (!subjects.is_empty()).then(|| {
        format!(
            "unresolved callable documentation facts: {}",
            subjects.join("; ")
        )
    })
}

/// 将 C/C++ 同名公开函数标记为归属不明确
///
/// 歧义只统计具名 callable：class 等 unnamed subject 不与它的
/// constructor 同名碰撞；真正的同名重载保持保守 Unresolved
fn reject_ambiguous_public_callable_identities(callables: &mut [Callable]) {
    let mut counts = BTreeMap::new();
    for callable in callables.iter() {
        if callable.named
            && matches!(
                callable.language,
                Language::ProceduralSource | Language::Cplusplus
            )
            && callable.visibility == DocumentationVisibility::Public
        {
            *counts.entry(callable.name.clone()).or_insert(0_u32) += 1;
        }
    }
    for callable in callables {
        if callable.named
            && matches!(
                callable.language,
                Language::ProceduralSource | Language::Cplusplus
            )
            && counts.get(&callable.name).is_some_and(|count| *count > 1)
        {
            callable.visibility = DocumentationVisibility::Unresolved;
        }
    }
}

#[derive(Clone, Debug)]
struct DependencyDeclaration {
    key: String,
    line: usize,
    column: usize,
    start_byte: usize,
    end_byte: usize,
    group_identity: u32,
    preceding_blank_lines: usize,
    wildcard: bool,
    complex_order: bool,
    module_placement_valid: bool,
}

#[derive(Debug)]
struct DependencyFacts {
    declarations: Vec<DependencyDeclaration>,
    python_has_unhandled_import: bool,
}

/// 从语法树提取依赖事实，返回不借用语法节点的数据
fn observe_dependencies(
    language: Language,
    root: Node<'_>,
    source: &[u8],
) -> DependencyFacts {
    let mut declarations = Vec::new();
    match language {
        Language::Python => collect_python_dependency_declarations(
            root,
            source,
            &mut declarations,
        ),
        Language::Rust => {
            let mut next_group = 0;
            collect_rust_dependency_declarations(
                root,
                source,
                &mut next_group,
                &mut declarations,
            );
        }
        Language::ProceduralSource | Language::Cplusplus => {
            collect_native_dependency_declarations(
                language,
                root,
                source,
                &mut declarations,
            );
        }
    }
    if language == Language::Cplusplus {
        collect_cplusplus_module_declarations(root, source, &mut declarations);
    }
    let python_has_unhandled_import = language == Language::Python
        && has_unhandled_python_import(root, &declarations);
    for index in 1..declarations.len() {
        if declarations[index - 1].group_identity
            == declarations[index].group_identity
        {
            declarations[index].preceding_blank_lines = blank_lines_between(
                source,
                declarations[index - 1].end_byte,
                declarations[index].start_byte,
            );
        }
    }
    DependencyFacts {
        declarations,
        python_has_unhandled_import,
    }
}

/// 检查依赖声明并记录违规或缺失事实
fn judge_dependencies(
    authority: &CompiledAuthority,
    language: Language,
    facts: &DependencyFacts,
    findings: &mut FindingState<'_>,
) -> FactFamilyState {
    let declarations = &facts.declarations;
    let law = &profile_law(language.key()).dependency;
    for declaration in declarations {
        if declaration.wildcard
            && matches!(
                law,
                DependencyProfileLaw::Python { .. }
                    | DependencyProfileLaw::Rust { .. }
            )
        {
            findings.push(
                RuleOperator::DependencyWildcard,
                declaration.line,
                declaration.column,
                &declaration.key,
                &format!(
                    "observed direct dependency declaration {}",
                    declaration.key
                ),
            );
        }
        if !declaration.module_placement_valid
            && matches!(law, DependencyProfileLaw::Cplusplus { .. })
        {
            findings.push(
                RuleOperator::DependencyModulePlacement,
                declaration.line,
                declaration.column,
                &declaration.key,
                &format!(
                    "observed direct dependency declaration {}",
                    declaration.key
                ),
            );
        }
    }
    let blocked = match law {
        DependencyProfileLaw::Python {
            scope_blocked,
            multi_import_blocked,
            classification_blocked,
            ..
        } => {
            let reason = if facts.python_has_unhandled_import {
                Some(*scope_blocked)
            } else if declarations.iter().any(|item| item.complex_order) {
                Some(*multi_import_blocked)
            } else if declarations.iter().any(|item| {
                authority.python_dependency_tier(&item.key).is_none()
            }) {
                Some(*classification_blocked)
            } else {
                None
            };
            reason.map(str::to_owned)
        }
        DependencyProfileLaw::Rust {
            nested_use_blocked, ..
        } => declarations
            .iter()
            .any(|item| item.complex_order)
            .then(|| (*nested_use_blocked).to_owned()),
        DependencyProfileLaw::Procedural {
            unavailable_blocked,
        }
        | DependencyProfileLaw::Cplusplus {
            unavailable_blocked,
            ..
        } => (!declarations.is_empty())
            .then(|| (*unavailable_blocked).to_owned()),
    };
    if blocked.is_none() {
        match law {
            DependencyProfileLaw::Python {
                within_tier_blank_lines,
                cross_tier_blank_lines,
                ..
            } => {
                if authority.dependency_reorder_safe(law) {
                    check_python_dependency_order(
                        authority,
                        declarations,
                        *within_tier_blank_lines,
                        *cross_tier_blank_lines,
                        findings,
                    );
                }
            }
            DependencyProfileLaw::Rust {
                within_group_blank_lines,
                ..
            } => {
                if authority.dependency_reorder_safe(law) {
                    check_rust_dependency_order(
                        declarations,
                        *within_group_blank_lines,
                        findings,
                    );
                }
            }
            DependencyProfileLaw::Procedural { .. }
            | DependencyProfileLaw::Cplusplus { .. } => {}
        }
    }
    blocked.map_or_else(
        || FactFamilyState::Complete(declarations.len() as u32),
        FactFamilyState::Blocked,
    )
}

/// 查找尚未记录的 Python 导入语句
fn has_unhandled_python_import(
    node: Node<'_>,
    handled: &[DependencyDeclaration],
) -> bool {
    if matches!(node.kind(), "import_statement" | "import_from_statement") {
        return !handled
            .iter()
            .any(|declaration| declaration.start_byte == node.start_byte());
    }
    let mut cursor = node.walk();
    node.named_children(&mut cursor)
        .any(|child| has_unhandled_python_import(child, handled))
}

/// 按连续分组收集 Python 模块级导入
fn collect_python_dependency_declarations(
    root: Node<'_>,
    source: &[u8],
    output: &mut Vec<DependencyDeclaration>,
) {
    let mut next_group = 0_u32;
    let mut current_group = None;
    let mut cursor = root.walk();
    for child in root.named_children(&mut cursor) {
        if matches!(child.kind(), "import_statement" | "import_from_statement")
        {
            let group = *current_group
                .get_or_insert_with(|| take_group(&mut next_group));
            push_dependency_declaration(
                Language::Python,
                child,
                source,
                group,
                output,
            );
            continue;
        }
        current_group = None;
        if child.kind() != "if_statement" {
            continue;
        }
        let exact_type_checking = child
            .child_by_field_name("condition")
            .and_then(|condition| condition.utf8_text(source).ok())
            .is_some_and(|condition| condition.trim() == "TYPE_CHECKING");
        if !exact_type_checking {
            continue;
        }
        let Some(consequence) = child.child_by_field_name("consequence")
        else {
            continue;
        };
        let mut consequence_group = None;
        let mut consequence_cursor = consequence.walk();
        for statement in consequence.named_children(&mut consequence_cursor) {
            if matches!(
                statement.kind(),
                "import_statement" | "import_from_statement"
            ) {
                let group = *consequence_group
                    .get_or_insert_with(|| take_group(&mut next_group));
                push_dependency_declaration(
                    Language::Python,
                    statement,
                    source,
                    group,
                    output,
                );
            } else {
                consequence_group = None;
            }
        }
    }
}

/// 分配下一个依赖分组编号
fn take_group(next_group: &mut u32) -> u32 {
    let group = *next_group;
    *next_group += 1;
    group
}

/// 按作用域收集连续的 Rust 导入分组
fn collect_rust_dependency_declarations(
    scope: Node<'_>,
    source: &[u8],
    next_group: &mut u32,
    output: &mut Vec<DependencyDeclaration>,
) {
    let mut current_group = None;
    let mut cursor = scope.walk();
    for child in scope.named_children(&mut cursor) {
        if child.kind() == "use_declaration" {
            let group =
                *current_group.get_or_insert_with(|| take_group(next_group));
            push_dependency_declaration(
                Language::Rust,
                child,
                source,
                group,
                output,
            );
            continue;
        }
        current_group = None;
        collect_rust_dependency_declarations(
            child, source, next_group, output,
        );
    }
}

/// 从语法树收集 C/C++ 头文件包含语句
fn collect_native_dependency_declarations(
    language: Language,
    node: Node<'_>,
    source: &[u8],
    output: &mut Vec<DependencyDeclaration>,
) {
    if node.kind() == "preproc_include" {
        push_dependency_declaration(language, node, source, 0, output);
        return;
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        collect_native_dependency_declarations(
            language, child, source, output,
        );
    }
}

/// 记录依赖声明的内容、位置和分组
fn push_dependency_declaration(
    language: Language,
    node: Node<'_>,
    source: &[u8],
    group_identity: u32,
    output: &mut Vec<DependencyDeclaration>,
) {
    let key = dependency_key(language, node, source).unwrap_or_default();
    let point = node.start_position();
    output.push(DependencyDeclaration {
        key,
        line: point.row + 1,
        column: point.column + 1,
        start_byte: node.start_byte(),
        end_byte: node.end_byte(),
        group_identity,
        preceding_blank_lines: 0,
        wildcard: dependency_node_has_token(node, "*"),
        complex_order: match language {
            Language::Python => {
                node.kind() == "import_statement"
                    && dependency_node_has_token(node, ",")
            }
            Language::Rust => dependency_node_has_token(node, "{"),
            Language::ProceduralSource | Language::Cplusplus => false,
        },
        module_placement_valid: true,
    });
}

/// 判断依赖声明的具体语法 token 是否存在
fn dependency_node_has_token(node: Node<'_>, token: &str) -> bool {
    if node.kind() == token {
        return true;
    }
    let mut cursor = node.walk();
    node.children(&mut cursor)
        .any(|child| dependency_node_has_token(child, token))
}

/// 收集 C++ 模块导入并判断其位置是否合法
fn collect_cplusplus_module_declarations(
    root: Node<'_>,
    source: &[u8],
    output: &mut Vec<DependencyDeclaration>,
) {
    let mut ordinary_declaration_seen = false;
    let mut inside_global_module_fragment = false;
    let mut cursor = root.walk();
    for child in root.named_children(&mut cursor) {
        match cplusplus_module_node(child) {
            CplusplusModuleNode::GlobalFragment => {
                inside_global_module_fragment = true
            }
            CplusplusModuleNode::ModuleDeclaration => {
                inside_global_module_fragment = false
            }
            CplusplusModuleNode::Import(import) => {
                push_cplusplus_module_import(
                    import,
                    source,
                    !ordinary_declaration_seen
                        && !inside_global_module_fragment,
                    output,
                )
            }
            CplusplusModuleNode::Other
                if child.kind().starts_with("preproc_") => {}
            CplusplusModuleNode::Other => {
                collect_nested_cplusplus_imports(child, source, output);
                ordinary_declaration_seen = true;
            }
        }
    }
}

#[derive(Clone, Copy)]
enum CplusplusModuleNode<'tree> {
    GlobalFragment,
    ModuleDeclaration,
    Import(Node<'tree>),
    Other,
}

/// 识别 C++ 模块声明、导入和其他节点
fn cplusplus_module_node(node: Node<'_>) -> CplusplusModuleNode<'_> {
    match node.kind() {
        "global_module_fragment_declaration" => {
            CplusplusModuleNode::GlobalFragment
        }
        "module_declaration" => CplusplusModuleNode::ModuleDeclaration,
        "import_declaration" => CplusplusModuleNode::Import(node),
        "export_declaration" => {
            let Some(child) = node.named_child(0) else {
                return CplusplusModuleNode::Other;
            };
            match child.kind() {
                "module_declaration" => CplusplusModuleNode::ModuleDeclaration,
                "import_declaration" => CplusplusModuleNode::Import(child),
                _ => CplusplusModuleNode::Other,
            }
        }
        _ => CplusplusModuleNode::Other,
    }
}

/// 收集不在顶层的 C++ 模块导入
fn collect_nested_cplusplus_imports(
    node: Node<'_>,
    source: &[u8],
    output: &mut Vec<DependencyDeclaration>,
) {
    if node.kind() == "import_declaration" {
        push_cplusplus_module_import(node, source, false, output);
        return;
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        collect_nested_cplusplus_imports(child, source, output);
    }
}

/// 记录 C++ 模块导入及其位置检查结果
fn push_cplusplus_module_import(
    node: Node<'_>,
    source: &[u8],
    placement_valid: bool,
    output: &mut Vec<DependencyDeclaration>,
) {
    let point = node.start_position();
    output.push(DependencyDeclaration {
        key: node.utf8_text(source).unwrap_or_default().trim().to_owned(),
        line: point.row + 1,
        column: point.column + 1,
        start_byte: node.start_byte(),
        end_byte: node.end_byte(),
        group_identity: 0,
        preceding_blank_lines: 0,
        wildcard: false,
        complex_order: false,
        module_placement_valid: placement_valid,
    });
}

/// 提取依赖声明用于排序的文本
fn dependency_key(
    language: Language,
    node: Node<'_>,
    source: &[u8],
) -> Option<String> {
    let key = match language {
        Language::Python if node.kind() == "import_from_statement" => {
            node.child_by_field_name("module_name")
        }
        Language::Python => node
            .child_by_field_name("name")
            .map(|name| name.child_by_field_name("name").unwrap_or(name)),
        Language::Rust => node.child_by_field_name("argument"),
        Language::ProceduralSource | Language::Cplusplus => Some(node),
    }?;
    key.utf8_text(source)
        .ok()
        .map(|text| text.trim().to_owned())
}

/// 按依赖类别检查 Python 导入顺序和空行
fn check_python_dependency_order(
    authority: &CompiledAuthority,
    declarations: &[DependencyDeclaration],
    within_tier_blank_lines: usize,
    cross_tier_blank_lines: usize,
    findings: &mut FindingState<'_>,
) {
    for pair in declarations.windows(2) {
        let left = &pair[0];
        let right = &pair[1];
        if left.group_identity != right.group_identity {
            continue;
        }
        let left_tier = authority.python_dependency_tier(&left.key);
        let right_tier = authority.python_dependency_tier(&right.key);
        let out_of_order = left_tier > right_tier
            || (left_tier == right_tier && left.key > right.key);
        let tier_changed = left_tier != right_tier;
        let spacing_invalid = if tier_changed {
            right.preceding_blank_lines != cross_tier_blank_lines
        } else {
            right.preceding_blank_lines != within_tier_blank_lines
        };
        if out_of_order || spacing_invalid {
            findings.push(
                RuleOperator::DependencyOrder,
                right.line,
                right.column,
                &right.key,
                &format!(
                    "observed direct dependency declaration {}",
                    right.key
                ),
            );
        }
    }
}

/// 检查同组 Rust 导入的顺序和空行
fn check_rust_dependency_order(
    declarations: &[DependencyDeclaration],
    within_group_blank_lines: usize,
    findings: &mut FindingState<'_>,
) {
    for pair in declarations.windows(2) {
        let left = &pair[0];
        let right = &pair[1];
        if left.group_identity == right.group_identity
            && (right.preceding_blank_lines != within_group_blank_lines
                || rust_dependency_compare(&left.key, &right.key).is_gt())
        {
            findings.push(
                RuleOperator::DependencyOrder,
                right.line,
                right.column,
                &right.key,
                &format!(
                    "observed direct dependency declaration {}",
                    right.key
                ),
            );
        }
    }
}

/// 按路径来源和数字段比较 Rust 导入顺序
fn rust_dependency_compare(left: &str, right: &str) -> std::cmp::Ordering {
    /// 返回 Rust 导入路径来源的排序编号
    fn root_rank(path: &str) -> u8 {
        match path.split("::").next().unwrap_or(path) {
            "self" => 0,
            "super" => 1,
            "crate" => 2,
            _ => 3,
        }
    }
    root_rank(left)
        .cmp(&root_rank(right))
        .then_with(|| version_compare(left, right))
        .then_with(|| left.cmp(right))
}

/// 统计两个源码位置之间的空行数
fn blank_lines_between(
    source: &[u8],
    end_byte: usize,
    start_byte: usize,
) -> usize {
    source
        .get(end_byte..start_byte)
        .map(|gap| {
            gap.iter()
                .filter(|byte| **byte == b'\n')
                .count()
                .saturating_sub(1)
        })
        .unwrap_or(0)
}

/// 按字符和数字段比较文本顺序
fn version_compare(left: &str, right: &str) -> std::cmp::Ordering {
    let mut left = left.chars().peekable();
    let mut right = right.chars().peekable();
    loop {
        match (left.peek(), right.peek()) {
            (None, None) => return std::cmp::Ordering::Equal,
            (None, Some(_)) => return std::cmp::Ordering::Less,
            (Some(_), None) => return std::cmp::Ordering::Greater,
            (Some(left_digit), Some(right_digit))
                if left_digit.is_ascii_digit()
                    && right_digit.is_ascii_digit() =>
            {
                let left_number = take_digits(&mut left);
                let right_number = take_digits(&mut right);
                let ordering = left_number
                    .len()
                    .cmp(&right_number.len())
                    .then_with(|| left_number.cmp(&right_number));
                if !ordering.is_eq() {
                    return ordering;
                }
            }
            (Some(_), Some(_)) => {
                let ordering = left.next().cmp(&right.next());
                if !ordering.is_eq() {
                    return ordering;
                }
            }
        }
    }
}

/// 读取连续数字并去除多余的前导零
fn take_digits(
    iterator: &mut std::iter::Peekable<std::str::Chars<'_>>,
) -> String {
    let mut digits = String::new();
    while iterator.peek().is_some_and(char::is_ascii_digit) {
        digits.push(iterator.next().expect("peeked digit must exist"));
    }
    let trimmed = digits.trim_start_matches('0');
    if trimmed.is_empty() {
        "0".to_owned()
    } else {
        trimmed.to_owned()
    }
}

impl<'source> DeclarationReview<'source> {
    /// 观察一棵语法树中的全部声明主体
    fn collect(
        language: Language,
        root: Node<'_>,
        source: &'source [u8],
    ) -> (Vec<Declaration>, Vec<Callable>) {
        let mut review = Self {
            language,
            source,
            output: Vec::new(),
            callables: Vec::new(),
        };
        review.collect_node(root, false);
        (review.output, review.callables)
    }

    /// 执行一个声明节点及其后代的深度优先观察
    fn collect_node(&mut self, node: Node<'_>, nested: bool) {
        let child_nested = observe_callable(
            self.language,
            node,
            self.source,
            nested,
            &mut self.callables,
        );
        match self.language {
            Language::Python => match node.kind() {
                "function_definition" | "class_definition" => {
                    let role = if node.kind() == "function_definition" {
                        if python_variant_member_decorator(node, self.source)
                            == Some(true)
                        {
                            IdentifierRole::Constant
                        } else {
                            IdentifierRole::Function
                        }
                    } else {
                        IdentifierRole::Type
                    };
                    self.push_named_declaration(
                        node.child_by_field_name("name"),
                        role,
                    );
                    if node.kind() == "function_definition"
                        && python_variant_member_decorator(node, self.source)
                            .is_none()
                        && let Some(declaration) = self.output.last_mut()
                    {
                        declaration.owner = IdentifierOwner::Unresolved;
                    }
                    if let Some(parameters) =
                        node.child_by_field_name("type_parameters")
                    {
                        self.push_python_type_parameters(parameters);
                    }
                    if let Some(parameters) =
                        node.child_by_field_name("parameters")
                    {
                        self.push_python_parameter_identifiers(
                            parameters,
                            python_receiver_spelling(node, self.source),
                        );
                    }
                }
                "assignment" | "augmented_assignment" => {
                    if let Some(left) = node.child_by_field_name("left") {
                        let role = if node.kind() == "assignment"
                            && node.child_by_field_name("right").is_some()
                            && python_variant_class(node, self.source)
                                .is_some()
                        {
                            if python_assignment_identity(node, self.source)
                                .as_deref()
                                == Some("enum.nonmember")
                            {
                                IdentifierRole::Value
                            } else {
                                IdentifierRole::Constant
                            }
                        } else if node.kind() == "assignment"
                            && python_type_parameter_assignment(
                                node,
                                self.source,
                            )
                        {
                            IdentifierRole::Type
                        } else if node.kind() == "assignment"
                            && python_type_alias_assignment(node, self.source)
                        {
                            IdentifierRole::Alias
                        } else if node.kind() == "assignment"
                            && python_is_module_assignment(node)
                        {
                            IdentifierRole::ModuleBinding
                        } else {
                            IdentifierRole::Value
                        };
                        let before = self.output.len();
                        self.push_python_binding_target(left, role);
                        if role == IdentifierRole::Constant
                            && !python_variant_member_is_resolved(
                                node,
                                self.source,
                            )
                        {
                            for declaration in &mut self.output[before..] {
                                declaration.owner =
                                    IdentifierOwner::Unresolved;
                            }
                        }
                        // 固定名称仍保留声明记录，只按已证明的归属排除命名检查
                        if self.output.len() == before + 1
                            && left.kind() == "identifier"
                            && let Some(binding) = self.output.last()
                            && let Some(fixed) = python_fixed_binding_owner(
                                node,
                                &binding.name,
                                self.source,
                            )
                            && let Some(last) = self.output.last_mut()
                        {
                            last.owner = fixed;
                        }
                    }
                }
                "for_statement" | "for_in_clause" => {
                    if let Some(left) = node.child_by_field_name("left") {
                        self.push_python_binding_target(
                            left,
                            IdentifierRole::Value,
                        );
                    }
                }
                "as_pattern_target" => {
                    let mut cursor = node.walk();
                    let name = node
                        .named_children(&mut cursor)
                        .find(|child| child.kind() == "identifier");
                    self.push_named_declaration(name, IdentifierRole::Value);
                }
                "named_expression" => {
                    self.push_named_declaration(
                        node.child_by_field_name("name"),
                        IdentifierRole::Value,
                    );
                }
                "aliased_import" => {
                    self.push_named_declaration(
                        node.child_by_field_name("alias"),
                        IdentifierRole::Alias,
                    );
                }
                "case_pattern" => self.push_python_case_bindings(node),
                "lambda" => {
                    if let Some(parameters) =
                        node.child_by_field_name("parameters")
                    {
                        self.push_python_parameter_identifiers(
                            parameters, None,
                        );
                    }
                }
                "type_alias_statement" => {
                    if let Some(left) = node.child_by_field_name("left") {
                        self.push_python_type_alias(left);
                    }
                }
                _ => {}
            },
            Language::Rust => match node.kind() {
                "function_item"
                | "struct_item"
                | "enum_item"
                | "trait_item"
                | "type_item"
                | "mod_item"
                | "const_item"
                | "static_item"
                | "union_item"
                | "function_signature_item"
                | "associated_type"
                | "macro_definition" => {
                    let role = match node.kind() {
                        "function_item"
                        | "function_signature_item"
                        | "macro_definition" => IdentifierRole::Function,
                        "struct_item" | "enum_item" | "trait_item"
                        | "type_item" | "union_item" | "associated_type" => {
                            IdentifierRole::Type
                        }
                        "const_item" | "static_item" => {
                            IdentifierRole::Constant
                        }
                        "mod_item" => IdentifierRole::ModuleNamespace,
                        _ => unreachable!("closed Rust item role"),
                    };
                    if matches!(
                        node.kind(),
                        "function_item" | "function_signature_item"
                    ) {
                        let before = self.output.len();
                        self.push_named_declaration(
                            node.child_by_field_name("name"),
                            role,
                        );
                        // 记录 impl 中直接写出的 trait 名称作为外部归属
                        // 不解析导入、别名或类型
                        if self.output.len() != before
                            && let Some(surface) =
                                rust_trait_surface(node, self.source)
                            && let Some(last) = self.output.last_mut()
                        {
                            last.external_owner = Some(surface);
                        }
                    } else {
                        self.push_named_declaration(
                            node.child_by_field_name("name"),
                            role,
                        );
                    }
                    if matches!(
                        node.kind(),
                        "function_item" | "function_signature_item"
                    ) && let Some(parameters) =
                        node.child_by_field_name("parameters")
                    {
                        self.push_rust_parameter_identifiers(parameters);
                    }
                }
                "field_declaration" => {
                    self.push_named_declaration(
                        node.child_by_field_name("name"),
                        IdentifierRole::Value,
                    );
                }
                "enum_variant" => {
                    self.push_named_declaration(
                        node.child_by_field_name("name"),
                        IdentifierRole::Variant,
                    );
                }
                "type_parameter" => {
                    self.push_named_declaration(
                        node.child_by_field_name("name"),
                        IdentifierRole::Type,
                    );
                }
                "const_parameter" => {
                    self.push_named_declaration(
                        node.child_by_field_name("name"),
                        IdentifierRole::Constant,
                    );
                }
                "lifetime_parameter" => {
                    self.push_named_declaration(
                        node.child_by_field_name("name"),
                        IdentifierRole::Lifetime,
                    );
                }
                "use_as_clause" => {
                    self.push_named_declaration(
                        node.child_by_field_name("alias"),
                        IdentifierRole::Alias,
                    );
                }
                "extern_crate_declaration" => {
                    self.push_named_declaration(
                        node.child_by_field_name("alias"),
                        IdentifierRole::ModuleNamespace,
                    );
                }
                "label"
                    if node.parent().is_some_and(|parent| {
                        !matches!(
                            parent.kind(),
                            "break_expression" | "continue_expression"
                        )
                    }) =>
                {
                    self.push_named_declaration(
                        Some(node),
                        IdentifierRole::Label,
                    );
                }
                "let_declaration" => {
                    if let Some(pattern) = node.child_by_field_name("pattern")
                    {
                        self.push_rust_binding_pattern(pattern);
                    }
                }
                "let_condition" | "for_expression" => {
                    if let Some(pattern) = node.child_by_field_name("pattern")
                    {
                        self.push_rust_binding_pattern(pattern);
                    }
                }
                "match_arm" => {
                    if let Some(pattern) = node.child_by_field_name("pattern")
                    {
                        self.push_rust_binding_pattern(pattern);
                    }
                }
                "closure_expression" => {
                    if let Some(parameters) =
                        node.child_by_field_name("parameters")
                    {
                        let mut cursor = parameters.walk();
                        for parameter in parameters.named_children(&mut cursor)
                        {
                            let pattern = parameter
                                .child_by_field_name("pattern")
                                .unwrap_or(parameter);
                            self.push_rust_binding_pattern(pattern);
                        }
                    }
                }
                _ => {}
            },
            Language::ProceduralSource | Language::Cplusplus => {
                match node.kind() {
                    "preproc_def" => {
                        self.push_named_declaration(
                            node.child_by_field_name("name"),
                            IdentifierRole::Constant,
                        );
                    }
                    "preproc_function_def" => {
                        self.push_named_declaration(
                            node.child_by_field_name("name"),
                            IdentifierRole::Constant,
                        );
                        if let Some(parameters) =
                            node.child_by_field_name("parameters")
                        {
                            let mut cursor = parameters.walk();
                            for parameter in
                                parameters.named_children(&mut cursor)
                            {
                                if parameter.kind() == "identifier" {
                                    self.push_named_declaration(
                                        Some(parameter),
                                        IdentifierRole::Value,
                                    );
                                }
                            }
                        }
                    }
                    "struct_specifier" | "union_specifier"
                    | "enum_specifier" | "class_specifier" => {
                        let name = node
                            .child_by_field_name("name")
                            .and_then(find_declaration_identifier);
                        let role = if self.language == Language::Cplusplus {
                            IdentifierRole::Type
                        } else {
                            IdentifierRole::Tag
                        };
                        self.push_named_declaration(name, role);
                    }
                    "type_definition" => {
                        self.push_native_family_field_declarators(
                            node,
                            "declarator",
                            IdentifierRole::Typedef,
                        );
                    }
                    "enumerator" => {
                        self.push_named_declaration(
                            node.child_by_field_name("name"),
                            IdentifierRole::Enumerator,
                        );
                    }
                    "labeled_statement"
                        if self.language == Language::ProceduralSource =>
                    {
                        self.push_named_declaration(
                            node.child_by_field_name("label"),
                            IdentifierRole::Label,
                        );
                    }
                    "namespace_definition"
                        if self.language == Language::Cplusplus =>
                    {
                        if let Some(name) = node.child_by_field_name("name") {
                            self.push_cplusplus_namespace_names(name);
                        }
                    }
                    "namespace_alias_definition"
                        if self.language == Language::Cplusplus =>
                    {
                        self.push_named_declaration(
                            node.child_by_field_name("name"),
                            IdentifierRole::ModuleNamespace,
                        );
                    }
                    "alias_declaration"
                        if self.language == Language::Cplusplus =>
                    {
                        self.push_named_declaration(
                            node.child_by_field_name("name"),
                            IdentifierRole::Type,
                        );
                    }
                    "type_parameter_declaration"
                    | "optional_type_parameter_declaration"
                    | "variadic_type_parameter_declaration"
                        if self.language == Language::Cplusplus =>
                    {
                        let mut cursor = node.walk();
                        let name = node
                            .named_children(&mut cursor)
                            .find(|child| child.kind() == "type_identifier");
                        self.push_named_declaration(
                            name,
                            IdentifierRole::Type,
                        );
                    }
                    "parameter_declaration"
                    | "optional_parameter_declaration"
                    | "variadic_parameter_declaration" => {
                        let name = parameter_binding(self.language, node);
                        let role = if node.parent().is_some_and(|parent| {
                            parent.kind() == "template_parameter_list"
                        }) {
                            IdentifierRole::Constant
                        } else {
                            IdentifierRole::Value
                        };
                        self.push_named_declaration(name, role);
                    }
                    "lambda_capture_initializer"
                        if self.language == Language::Cplusplus =>
                    {
                        self.push_named_declaration(
                            node.child_by_field_name("left"),
                            IdentifierRole::Value,
                        );
                    }
                    "function_definition"
                    | "declaration"
                    | "field_declaration"
                    | "for_range_loop" => {
                        self.push_native_family_value_declarations(node);
                    }
                    _ => {}
                }
            }
        }
        let mut cursor = node.walk();
        for child in node.named_children(&mut cursor) {
            self.collect_node(child, child_nested);
        }
    }
}

/// 返回 Rust 函数直接所属 impl 的书面 trait 面文本
fn rust_trait_surface(node: Node<'_>, source: &[u8]) -> Option<String> {
    let surface = node
        .parent()
        .filter(|body| body.kind() == "declaration_list")
        .and_then(|body| body.parent())
        .filter(|implementation| implementation.kind() == "impl_item")
        .and_then(|implementation| implementation.child_by_field_name("trait"))
        .and_then(|implemented_trait| {
            implemented_trait.utf8_text(source).ok()
        })?;
    Some(surface.split_whitespace().collect::<Vec<_>>().join(" "))
}

impl DeclarationReview<'_> {
    /// 提取 Python 模式匹配中的绑定名称
    fn push_python_case_bindings(&mut self, node: Node<'_>) {
        match node.kind() {
            // match 通配 `_` 是语法性丢弃，不是值绑定
            "case_pattern"
                if node.utf8_text(self.source).ok() == Some("_") =>
            {
                let before = self.output.len();
                self.push_named_declaration(Some(node), IdentifierRole::Value);
                if self.output.len() != before
                    && let Some(last) = self.output.last_mut()
                {
                    last.owner = IdentifierOwner::Discard;
                }
            }
            "dotted_name" => {
                let Ok(name) = node.utf8_text(self.source) else {
                    return;
                };
                if !name.contains('.') {
                    self.push_named_declaration(
                        first_descendant_identifier(node),
                        IdentifierRole::Value,
                    );
                }
            }
            "class_pattern" => {
                let mut cursor = node.walk();
                for child in node.named_children(&mut cursor) {
                    if child.kind() == "case_pattern" {
                        self.push_python_case_bindings(child);
                    }
                }
            }
            "dict_pattern" => {
                for index in 0..node.child_count() {
                    let index = index as u32;
                    let Some(child) = node.child(index) else {
                        continue;
                    };
                    if node.field_name_for_child(index) == Some("value")
                        || child.kind() == "splat_pattern"
                    {
                        self.push_python_case_bindings(child);
                    }
                }
            }
            "keyword_pattern" => {
                let mut cursor = node.walk();
                for child in node.named_children(&mut cursor) {
                    if child.kind() != "identifier" {
                        self.push_python_case_bindings(child);
                    }
                }
            }
            "as_pattern_target" => {
                self.push_named_declaration(
                    first_descendant_identifier(node),
                    IdentifierRole::Value,
                );
            }
            "identifier" => {
                self.push_named_declaration(Some(node), IdentifierRole::Value)
            }
            _ => {
                let mut cursor = node.walk();
                for child in node.named_children(&mut cursor) {
                    self.push_python_case_bindings(child);
                }
            }
        }
    }

    /// 提取 Python 类型别名及其类型参数
    fn push_python_type_alias(&mut self, node: Node<'_>) {
        let Some(generic) = descendant_of_kind(node, "generic_type") else {
            self.push_named_declaration(
                first_descendant_identifier(node),
                IdentifierRole::Type,
            );
            return;
        };
        let mut cursor = generic.walk();
        for child in generic.named_children(&mut cursor) {
            match child.kind() {
                "identifier" => self
                    .push_named_declaration(Some(child), IdentifierRole::Type),
                "type_parameter" => self.push_python_type_parameters(child),
                _ => {}
            }
        }
    }

    /// 提取 Python 类型参数的名称
    fn push_python_type_parameters(&mut self, parameters: Node<'_>) {
        let mut cursor = parameters.walk();
        for parameter in parameters.named_children(&mut cursor) {
            self.push_named_declaration(
                first_descendant_identifier(parameter),
                IdentifierRole::Type,
            );
        }
    }
}

/// 查找节点内的第一个标识符
fn first_descendant_identifier(node: Node<'_>) -> Option<Node<'_>> {
    if node.kind() == "identifier" {
        return Some(node);
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        if let Some(identifier) = first_descendant_identifier(child) {
            return Some(identifier);
        }
    }
    None
}

impl DeclarationReview<'_> {
    /// 收集 C++ 命名空间的名称
    fn push_cplusplus_namespace_names(&mut self, node: Node<'_>) {
        if node.kind() == "namespace_identifier" {
            self.push_named_declaration(
                Some(node),
                IdentifierRole::ModuleNamespace,
            );
            return;
        }
        let mut cursor = node.walk();
        for child in node.named_children(&mut cursor) {
            self.push_cplusplus_namespace_names(child);
        }
    }

    /// 从 C/C++ 指定语法字段提取声明名称
    fn push_native_family_field_declarators(
        &mut self,
        node: Node<'_>,
        field: &str,
        role: IdentifierRole,
    ) {
        for index in 0..node.child_count() {
            let index = index as u32;
            if node.field_name_for_child(index) != Some(field) {
                continue;
            }
            let Some(declarator) = node.child(index) else {
                continue;
            };
            self.push_named_declaration(
                find_declaration_identifier(declarator),
                role,
            );
        }
    }
}

/// 查找声明中的变量、字段或类型名称
fn find_declaration_identifier(node: Node<'_>) -> Option<Node<'_>> {
    if matches!(
        node.kind(),
        "identifier" | "field_identifier" | "type_identifier"
    ) {
        return Some(node);
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        if let Some(identifier) = find_declaration_identifier(child) {
            return Some(identifier);
        }
    }
    None
}

/// 判断 Python 赋值是否直接位于模块内
fn python_is_module_assignment(node: Node<'_>) -> bool {
    let statement = node
        .parent()
        .filter(|parent| parent.kind() == "expression_statement")
        .unwrap_or(node);
    statement
        .parent()
        .is_some_and(|parent| parent.kind() == "module")
}

/// 识别 Python 经典 TypeAlias 注解赋值
fn python_type_alias_assignment(node: Node<'_>, source: &[u8]) -> bool {
    node.child_by_field_name("type")
        .and_then(|carrier| carrier.named_child(0))
        .and_then(|reference| python_import_identity(reference, source))
        .as_deref()
        == Some("typing.TypeAlias")
}

/// 返回直接调用工厂的导入身份
fn python_assignment_identity(
    node: Node<'_>,
    source: &[u8],
) -> Option<String> {
    node.child_by_field_name("right")
        .filter(|value| value.kind() == "call")
        .and_then(|value| value.child_by_field_name("function"))
        .and_then(|function| python_import_identity(function, source))
}

/// 返回声明直接所属的原生枚举类
fn python_variant_class<'tree>(
    node: Node<'tree>,
    source: &[u8],
) -> Option<Node<'tree>> {
    let statement = node
        .parent()
        .filter(|parent| {
            matches!(
                parent.kind(),
                "expression_statement" | "decorated_definition"
            )
        })
        .unwrap_or(node);
    statement
        .parent()
        .filter(|body| body.kind() == "block")
        .and_then(|body| body.parent())
        .filter(|class| class.kind() == "class_definition")
        .filter(|class| {
            python_class_has_native_base(
                *class,
                source,
                &[
                    "enum.Enum",
                    "enum.IntEnum",
                    "enum.StrEnum",
                    "enum.Flag",
                    "enum.IntFlag",
                ],
            )
        })
}

/// 识别由直接原生成员装饰器建立的枚举声明
fn python_variant_member_decorator(
    node: Node<'_>,
    source: &[u8],
) -> Option<bool> {
    let Some(class) = python_variant_class(node, source) else {
        return Some(false);
    };
    if class.child_by_field_name("body").is_some_and(|body| {
        python_statement_contains_binding(body, source, "_ignore_")
    }) {
        return None;
    }
    let Some(wrapper) = node
        .parent()
        .filter(|parent| parent.kind() == "decorated_definition")
    else {
        return Some(false);
    };
    let mut cursor = wrapper.walk();
    let reference = wrapper
        .named_children(&mut cursor)
        .filter(|child| child.kind() == "decorator")
        .filter_map(|decorator| decorator.named_child(0))
        .next()?;
    match python_import_identity(reference, source).as_deref() {
        Some("enum.member") => Some(true),
        Some(
            "enum.nonmember"
            | "builtins.staticmethod"
            | "builtins.classmethod"
            | "builtins.property",
        ) => Some(false),
        _ => None,
    }
}

/// 返回赋值直接所属的 Python 类
fn python_assignment_class(node: Node<'_>) -> Option<Node<'_>> {
    node.parent()
        .filter(|statement| statement.kind() == "expression_statement")
        .and_then(|statement| statement.parent())
        .filter(|body| body.kind() == "block")
        .and_then(|body| body.parent())
        .filter(|owner| owner.kind() == "class_definition")
}

/// 识别直接导入工厂创建的 Python 类型参数
fn python_type_parameter_assignment(node: Node<'_>, source: &[u8]) -> bool {
    node.child_by_field_name("left")
        .is_some_and(|left| left.kind() == "identifier")
        && python_assignment_identity(node, source).is_some_and(|identity| {
            matches!(
                identity.as_str(),
                "typing.TypeVar" | "typing.ParamSpec" | "typing.TypeVarTuple"
            )
        })
}

/// 判断 Python 类是否直接继承已导入的原生基类
fn python_class_has_native_base(
    class: Node<'_>,
    source: &[u8],
    identities: &[&str],
) -> bool {
    let Some(base_arguments) = class.child_by_field_name("superclasses")
    else {
        return false;
    };
    let mut cursor = base_arguments.walk();
    base_arguments.named_children(&mut cursor).any(|base| {
        python_import_identity(base, source)
            .is_some_and(|identity| identities.contains(&identity.as_str()))
    })
}

/// 证明枚举赋值产生普通数据成员而不是未知的描述器或被忽略名称
fn python_variant_member_is_resolved(node: Node<'_>, source: &[u8]) -> bool {
    let has_excluded_names = python_assignment_class(node)
        .and_then(|class| class.child_by_field_name("body"))
        .is_some_and(|body| {
            python_statement_contains_binding(body, source, "_ignore_")
        });
    if has_excluded_names
        || node
            .child_by_field_name("left")
            .is_none_or(|left| left.kind() != "identifier")
    {
        return false;
    }
    node.child_by_field_name("right")
        .is_some_and(|value| match value.kind() {
            "integer"
            | "float"
            | "string"
            | "concatenated_string"
            | "true"
            | "false"
            | "none"
            | "tuple"
            | "list"
            | "dictionary"
            | "set" => true,
            "unary_operator" => value.named_child(0).is_some_and(|argument| {
                matches!(argument.kind(), "integer" | "float")
            }),
            "call" => value
                .child_by_field_name("function")
                .and_then(|function| python_import_identity(function, source))
                .is_some_and(|identity| {
                    matches!(identity.as_str(), "enum.auto" | "enum.member")
                }),
            _ => false,
        })
}

/// 从直接导入和之前的绑定确定一个 Python 引用的来源
///
/// 只沿模块和类体查找，函数局部、条件导入及赋值别名不展开
fn python_import_identity(
    reference: Node<'_>,
    source: &[u8],
) -> Option<String> {
    let (binding, member) = match reference.kind() {
        "identifier" => (reference.utf8_text(source).ok()?, None),
        "attribute" => (
            reference
                .child_by_field_name("object")?
                .utf8_text(source)
                .ok()?,
            Some(
                reference
                    .child_by_field_name("attribute")?
                    .utf8_text(source)
                    .ok()?,
            ),
        ),
        _ => return None,
    };
    let mut item = reference;
    while let Some(parent) = item.parent() {
        if matches!(parent.kind(), "function_definition" | "lambda") {
            return None;
        }
        if parent.kind() == "block"
            && parent
                .parent()
                .is_none_or(|owner| owner.kind() != "class_definition")
        {
            return None;
        }
        if parent.kind() == "module"
            || parent.kind() == "block"
                && parent
                    .parent()
                    .is_some_and(|owner| owner.kind() == "class_definition")
        {
            let mut preceding = item.prev_named_sibling();
            while let Some(statement) = preceding {
                if matches!(
                    statement.kind(),
                    "import_statement" | "import_from_statement"
                ) {
                    if let Some(identity) = python_direct_import_binding(
                        statement, source, binding,
                    ) {
                        return identity.map(|identity| {
                            member.map_or_else(
                                || identity.clone(),
                                |member| format!("{identity}.{member}"),
                            )
                        });
                    }
                } else if python_statement_contains_binding(
                    statement, source, binding,
                ) || member.is_some_and(|member| {
                    python_statement_contains_binding(
                        statement,
                        source,
                        &format!("{binding}.{member}"),
                    )
                }) {
                    return None;
                }
                preceding = statement.prev_named_sibling();
            }
        }
        item = parent;
    }
    // 只有查完可证明的词法作用域且没有绑定时，才能回退到内置装饰器。
    (member.is_none()
        && matches!(binding, "staticmethod" | "classmethod" | "property"))
    .then(|| format!("builtins.{binding}"))
}

/// 读取一条直接导入对指定本地名称建立的来源
///
/// 外层空值表示未绑定，内层空值表示通配导入使来源不确定
fn python_direct_import_binding(
    node: Node<'_>,
    source: &[u8],
    binding: &str,
) -> Option<Option<String>> {
    let module = node
        .child_by_field_name("module_name")
        .and_then(|module| module.utf8_text(source).ok());
    let mut cursor = node.walk();
    for declaration in node.children_by_field_name("name", &mut cursor) {
        let name = declaration
            .child_by_field_name("name")
            .unwrap_or(declaration)
            .utf8_text(source)
            .ok()?;
        let local = declaration
            .child_by_field_name("alias")
            .and_then(|alias| alias.utf8_text(source).ok())
            .unwrap_or_else(|| name.split('.').next().unwrap_or(name));
        if local == binding {
            let identity = module.map_or_else(
                || name.to_owned(),
                |module| format!("{module}.{name}"),
            );
            return Some(Some(identity));
        }
    }
    let mut cursor = node.walk();
    node.named_children(&mut cursor)
        .any(|child| child.kind() == "wildcard_import")
        .then_some(None)
}

/// 判断语句是否可能遮蔽一个直接导入的名称
fn python_statement_contains_binding(
    node: Node<'_>,
    source: &[u8],
    binding: &str,
) -> bool {
    let target = match node.kind() {
        "function_definition" | "class_definition" => {
            return node.child_by_field_name("name").is_some_and(|name| {
                name.utf8_text(source).ok() == Some(binding)
            });
        }
        "import_statement" | "import_from_statement" => {
            return python_direct_import_binding(node, source, binding)
                .is_some();
        }
        "assignment"
        | "augmented_assignment"
        | "for_statement"
        | "for_in_clause" => node.child_by_field_name("left"),
        "named_expression" => node.child_by_field_name("name"),
        "as_pattern_target" | "delete_statement" | "case_pattern" => {
            Some(node)
        }
        "type_alias_statement" => node.child_by_field_name("left"),
        _ => None,
    };
    if target.is_some_and(|target| {
        python_target_contains_binding(target, source, binding)
    }) {
        return true;
    }
    let mut cursor = node.walk();
    node.named_children(&mut cursor)
        .any(|child| python_statement_contains_binding(child, source, binding))
}

/// 检查 Python 绑定模式是否包含指定名称或精确的属性写入
fn python_target_contains_binding(
    node: Node<'_>,
    source: &[u8],
    binding: &str,
) -> bool {
    match node.kind() {
        "identifier" => node.utf8_text(source).ok() == Some(binding),
        "attribute" => {
            binding.split_once('.').is_some_and(|(object, member)| {
                node.child_by_field_name("object").is_some_and(|name| {
                    name.utf8_text(source).ok() == Some(object)
                }) && node.child_by_field_name("attribute").is_some_and(
                    |name| name.utf8_text(source).ok() == Some(member),
                )
            })
        }
        "subscript" => false,
        _ => {
            let mut cursor = node.walk();
            node.named_children(&mut cursor).any(|child| {
                python_target_contains_binding(child, source, binding)
            })
        }
    }
}

/// 返回 Python 精确结构固定绑定的归属
fn python_fixed_binding_owner(
    node: Node<'_>,
    name: &str,
    source: &[u8],
) -> Option<IdentifierOwner> {
    let statement = node
        .parent()
        .filter(|parent| parent.kind() == "expression_statement")
        .unwrap_or(node);
    let body = statement.parent()?;
    match (name, body.kind()) {
        ("__all__", "module") => Some(IdentifierOwner::LanguageFixed),
        ("__slots__", "block")
            if body
                .parent()
                .is_some_and(|owner| owner.kind() == "class_definition") =>
        {
            Some(IdentifierOwner::LanguageFixed)
        }
        ("_fields_", "block")
            if python_assignment_class(node).is_some_and(|class| {
                python_class_has_native_base(
                    class,
                    source,
                    &["ctypes.Structure", "ctypes.Union"],
                )
            }) =>
        {
            Some(IdentifierOwner::LanguageFixed)
        }
        ("_ignore_" | "_order_", "block")
            if python_variant_class(node, source).is_some() =>
        {
            Some(IdentifierOwner::LanguageFixed)
        }
        _ => None,
    }
}

impl DeclarationReview<'_> {
    /// 提取 Python 赋值目标中的绑定名称
    fn push_python_binding_target(
        &mut self,
        node: Node<'_>,
        role: IdentifierRole,
    ) {
        match node.kind() {
            "identifier" => self.push_named_declaration(Some(node), role),
            "attribute" => {
                let is_owned_field = node
                    .child_by_field_name("object")
                    .and_then(|object| object.utf8_text(self.source).ok())
                    .is_some_and(|object| matches!(object, "self" | "cls"));
                if is_owned_field {
                    self.push_named_declaration(
                        node.child_by_field_name("attribute"),
                        IdentifierRole::Value,
                    );
                }
            }
            "subscript" => {}
            _ => {
                let mut cursor = node.walk();
                for child in node.named_children(&mut cursor) {
                    self.push_python_binding_target(child, role);
                }
            }
        }
    }

    /// 提取 Python 参数名称并校验首位接收者
    fn push_python_parameter_identifiers(
        &mut self,
        parameters: Node<'_>,
        excluded_receiver: Option<&str>,
    ) {
        let mut cursor = parameters.walk();
        let mut first_parameter = true;
        for parameter in parameters.named_children(&mut cursor) {
            if parameter_is_fixed(parameter) {
                continue;
            }
            let name = parameter_binding(self.language, parameter);
            if first_parameter {
                first_parameter = false;
                if let Some(expected) = excluded_receiver {
                    let observed = name.and_then(|identifier| {
                        identifier.utf8_text(self.source).ok()
                    });
                    if observed == Some(expected) {
                        // 仅将结构已证明的首位参数认作接收者
                        let before = self.output.len();
                        self.push_named_declaration(
                            name,
                            IdentifierRole::Value,
                        );
                        if self.output.len() != before
                            && let Some(last) = self.output.last_mut()
                        {
                            last.owner = IdentifierOwner::ProfileFixed;
                        }
                        continue;
                    }
                    let before = self.output.len();
                    self.push_named_declaration(name, IdentifierRole::Value);
                    if self.output.len() != before {
                        self.output
                            .last_mut()
                            .expect("new receiver declaration must be last")
                            .local_form =
                            LocalIdentifierForm::PythonInvalidReceiver;
                    }
                    continue;
                }
            }
            self.push_named_declaration(name, IdentifierRole::Value);
        }
    }
}

/// 返回 Python 参数节点内的稳定标识符
///
/// 类型化 splat（`*values_m: float`、`**options: dict`）的稳定名
/// 位于 list/dictionary_splat_pattern 内部的 identifier
fn python_parameter_identifier(parameter: Node<'_>) -> Option<Node<'_>> {
    match parameter.kind() {
        "identifier" => Some(parameter),
        "default_parameter" | "typed_default_parameter" => parameter
            .child_by_field_name("name")
            .filter(|name| name.kind() == "identifier"),
        "typed_parameter" => {
            let direct = single_identifier_child(parameter);
            if direct.is_some() {
                return direct;
            }
            let mut cursor = parameter.walk();
            let children: Vec<_> =
                parameter.named_children(&mut cursor).collect();
            children
                .iter()
                .find(|child| {
                    matches!(
                        child.kind(),
                        "list_splat_pattern" | "dictionary_splat_pattern"
                    )
                })
                .and_then(|splat| single_identifier_child(*splat))
        }
        "list_splat_pattern" | "dictionary_splat_pattern" => {
            single_identifier_child(parameter)
        }
        _ => None,
    }
}

/// 根据方法位置和装饰器确定 Python 接收者名称
fn python_receiver_spelling<'source>(
    node: Node<'_>,
    source: &'source [u8],
) -> Option<&'source str> {
    if python_variant_member_decorator(node, source) != Some(false) {
        return None;
    }
    let wrapper = node
        .parent()
        .filter(|parent| parent.kind() == "decorated_definition");
    let item = wrapper.unwrap_or(node);
    let direct_class_member = item
        .parent()
        .and_then(|block| block.parent())
        .is_some_and(|parent| parent.kind() == "class_definition");
    if !direct_class_member {
        return None;
    }
    let mut cursor = item.walk();
    let mut decorators = Vec::new();
    for decorator in item
        .named_children(&mut cursor)
        .filter(|child| child.kind() == "decorator")
    {
        let reference = decorator.named_child(0)?;
        let identity = python_import_identity(reference, source);
        if reference.utf8_text(source).is_ok_and(|name| {
            matches!(name, "staticmethod" | "classmethod" | "property")
                && identity.as_deref()
                    != Some(format!("builtins.{name}").as_str())
        }) {
            return None;
        }
        decorators.extend(identity);
    }
    if decorators
        .iter()
        .any(|identity| identity == "builtins.classmethod")
    {
        Some("cls")
    } else if decorators
        .iter()
        .any(|identity| identity == "builtins.staticmethod")
    {
        None
    } else if node
        .child_by_field_name("name")
        .and_then(|name| name.utf8_text(source).ok())
        .is_some_and(|name| {
            matches!(name, "__init_subclass__" | "__class_getitem__")
        })
    {
        Some("cls")
    } else {
        Some("self")
    }
}

impl DeclarationReview<'_> {
    /// 记录声明名称、源码位置和语言形式
    fn push_named_declaration(
        &mut self,
        node: Option<Node<'_>>,
        role: IdentifierRole,
    ) {
        let Some(node) = node else {
            return;
        };
        let Ok(name) = node.utf8_text(self.source) else {
            return;
        };
        let point = node.start_position();
        let local_form = match self.language {
            Language::Python
                if role == IdentifierRole::Function
                    && node.parent().is_some_and(|definition| {
                        python_protocol_method(definition, self.source)
                    }) =>
            {
                LocalIdentifierForm::PythonProtocol
            }
            Language::Python if name.starts_with('_') => {
                LocalIdentifierForm::PythonPrivate
            }
            Language::Rust if name.starts_with("r#") => {
                LocalIdentifierForm::RustRaw
            }
            Language::Rust if name.starts_with('\'') => {
                LocalIdentifierForm::RustLifetime
            }
            Language::ProceduralSource
                if role == IdentifierRole::Typedef && name.ends_with("_t") =>
            {
                LocalIdentifierForm::TypeDefinitionSuffix
            }
            _ => LocalIdentifierForm::Plain,
        };
        // Rust `Self` 只在类型上下文是语言固定拼写；其他语言同名照常判定
        let owner = match (self.language, name, role) {
            (Language::Rust, "Self", IdentifierRole::Type) => {
                IdentifierOwner::LanguageFixed
            }
            _ => IdentifierOwner::AuthorChosen,
        };
        self.output.push(Declaration {
            name: name.to_owned(),
            line: point.row + 1,
            column: point.column + 1,
            value_like: matches!(
                role,
                IdentifierRole::Value
                    | IdentifierRole::Constant
                    | IdentifierRole::Enumerator
                    | IdentifierRole::ModuleBinding
            ),
            role,
            local_form,
            reserved_scope: declaration_is_file_or_global_scope(node),
            owner,
            external_owner: None,
        });
    }

    /// 记录 C++ 私有数据成员的名称形式
    fn push_cplusplus_private_member_declaration(
        &mut self,
        node: Option<Node<'_>>,
    ) {
        let before = self.output.len();
        self.push_named_declaration(node, IdentifierRole::Value);
        if self.output.len() != before {
            self.output
                .last_mut()
                .expect("new declaration must be last")
                .local_form = LocalIdentifierForm::CplusplusPrivateMember;
        }
    }
}

/// 判断声明是否位于文件或全局作用域
fn declaration_is_file_or_global_scope(node: Node<'_>) -> bool {
    let mut ancestor = node.parent();
    while let Some(parent) = ancestor {
        if matches!(
            parent.kind(),
            "function_definition"
                | "compound_statement"
                | "field_declaration_list"
                | "parameter_list"
                | "namespace_definition"
        ) {
            return false;
        }
        ancestor = parent.parent();
    }
    true
}

impl DeclarationReview<'_> {
    /// 收集节点内的变量和字段名称
    fn push_identifier_descendants(
        &mut self,
        node: Node<'_>,
        role: IdentifierRole,
    ) {
        if matches!(node.kind(), "identifier" | "field_identifier") {
            self.push_named_declaration(Some(node), role);
            return;
        }
        let mut cursor = node.walk();
        for child in node.named_children(&mut cursor) {
            self.push_identifier_descendants(child, role);
        }
    }

    /// 提取 Rust 非接收者参数中的绑定名称
    fn push_rust_parameter_identifiers(&mut self, parameters: Node<'_>) {
        let mut cursor = parameters.walk();
        for parameter in parameters.named_children(&mut cursor) {
            if let Some(pattern) = parameter_binding(self.language, parameter)
            {
                self.push_rust_binding_pattern(pattern);
            }
        }
    }

    /// 提取 Rust 模式中的绑定并识别丢弃位置
    fn push_rust_binding_pattern(&mut self, node: Node<'_>) {
        match node.kind() {
            "identifier" | "shorthand_field_identifier" => {
                if node.kind() == "identifier"
                    && node.utf8_text(self.source).ok() == Some("None")
                {
                    return;
                }
                self.push_named_declaration(Some(node), IdentifierRole::Value);
            }
            "struct_pattern" | "tuple_struct_pattern" => {
                let excluded_type =
                    node.child_by_field_name("type").map(|child| child.id());
                let mut cursor = node.walk();
                for child in node.named_children(&mut cursor) {
                    if Some(child.id()) != excluded_type {
                        self.push_rust_binding_pattern(child);
                    }
                }
            }
            "field_pattern" => {
                if let Some(pattern) = node.child_by_field_name("pattern") {
                    self.push_rust_binding_pattern(pattern);
                } else {
                    self.push_named_declaration(
                        node.child_by_field_name("name"),
                        IdentifierRole::Value,
                    );
                }
            }
            "scoped_identifier"
            | "scoped_type_identifier"
            | "type_identifier"
            | "remaining_field_pattern" => {}
            // `_` 通配 token 是语法性丢弃，不是作者命名
            "_" => self.push_rust_discard_declaration(node),
            // 裸 `_` match 通配没有命名子节点，按整体文本识别为丢弃
            "match_pattern"
                if node.utf8_text(self.source).ok() == Some("_") =>
            {
                self.push_rust_discard_declaration(node);
            }
            // match_pattern 把 guard 表达式并入同一节点；只提取首个命名
            // 子节点（真实模式），guard 里的标识符不是绑定声明
            "match_pattern" => {
                let mut cursor = node.walk();
                let pattern = node.named_children(&mut cursor).next();
                if let Some(pattern) = pattern {
                    self.push_rust_binding_pattern(pattern);
                }
            }
            _ => {
                let mut cursor = node.walk();
                for child in node.named_children(&mut cursor) {
                    self.push_rust_binding_pattern(child);
                }
            }
        }
    }

    /// 记录 Rust 语法性丢弃 `_` 通配
    fn push_rust_discard_declaration(&mut self, node: Node<'_>) {
        let before = self.output.len();
        self.push_named_declaration(Some(node), IdentifierRole::Value);
        if self.output.len() != before
            && let Some(last) = self.output.last_mut()
        {
            last.owner = IdentifierOwner::Discard;
        }
    }
}

/// 沿声明名称向外确定对象首先是函数还是指针等派生对象
fn native_family_function_declarator(node: Node<'_>) -> Option<Node<'_>> {
    let declarator = node.child_by_field_name("declarator").unwrap_or(node);
    let mut current = find_declarator_identifier(declarator)?;
    while current.id() != node.id() {
        let parent = current.parent()?;
        match parent.kind() {
            "function_declarator" => return Some(parent),
            "pointer_declarator"
            | "reference_declarator"
            | "array_declarator" => return None,
            _ => {}
        }
        current = parent;
    }
    None
}

/// 识别 C++ 构造、析构和运算符的固定名称
fn cplusplus_fixed_callable_spelling(
    name: Option<Node<'_>>,
    source: &[u8],
) -> bool {
    let Some(name) = name else {
        return false;
    };
    if matches!(
        name.kind(),
        "operator_name" | "operator_cast" | "destructor_name"
    ) {
        return true;
    }
    let Ok(spelling) = name.utf8_text(source) else {
        return false;
    };
    let mut ancestor = name.parent();
    while let Some(node) = ancestor {
        if node.kind() == "class_specifier" {
            return node
                .child_by_field_name("name")
                .and_then(|class_name| class_name.utf8_text(source).ok())
                == Some(spelling);
        }
        if node.kind() == "qualified_identifier" {
            let scope = node
                .child_by_field_name("scope")
                .and_then(|scope| scope.utf8_text(source).ok());
            if scope.is_some_and(|scope| {
                scope.rsplit("::").next() == Some(spelling)
            }) {
                return true;
            }
        }
        ancestor = node.parent();
    }
    false
}

impl DeclarationReview<'_> {
    /// 统一观察 C/C++ 函数、变量、常量及范围绑定
    fn push_native_family_value_declarations(
        &mut self,
        declaration: Node<'_>,
    ) {
        for index in 0..declaration.child_count() {
            let index = index as u32;
            let Some(child) = declaration.child(index) else {
                continue;
            };
            let is_declarator = declaration.field_name_for_child(index)
                == Some("declarator")
                || child.kind() == "init_declarator"
                || child.kind().ends_with("declarator");
            if !is_declarator {
                continue;
            }
            if let Some(binding) =
                descendant_of_kind(child, "structured_binding_declarator")
            {
                let constant = native_family_declaration_is_constant(
                    declaration,
                    child,
                    self.source,
                );
                let role = if constant {
                    IdentifierRole::Constant
                } else {
                    IdentifierRole::Value
                };
                let before = self.output.len();
                self.push_identifier_descendants(binding, role);
                if constant
                    && !cplusplus_constant_binding_is_proven(
                        declaration,
                        self.source,
                    )
                {
                    for declaration in &mut self.output[before..] {
                        declaration.owner = IdentifierOwner::Unresolved;
                    }
                }
                continue;
            }
            let name = find_declarator_identifier(child);
            if self.language == Language::Cplusplus
                && cplusplus_fixed_callable_spelling(name, self.source)
            {
                continue;
            }
            if native_family_function_declarator(child).is_some() {
                self.push_named_declaration(name, IdentifierRole::Function);
            } else if self.language == Language::Cplusplus
                && cplusplus_is_private_non_static_data_member(
                    declaration,
                    self.source,
                )
            {
                self.push_cplusplus_private_member_declaration(name);
            } else {
                let role = if native_family_declaration_is_constant(
                    declaration,
                    child,
                    self.source,
                ) {
                    IdentifierRole::Constant
                } else {
                    IdentifierRole::Value
                };
                self.push_named_declaration(name, role);
            }
        }
    }
}

/// 只用紧邻同作用域的原生数组声明证明范围元素不含 tuple 或 mutable 成员
fn cplusplus_constant_binding_is_proven(
    node: Node<'_>,
    source: &[u8],
) -> bool {
    if node.kind() != "for_range_loop"
        || node.child_by_field_name("initializer").is_some()
        || node
            .parent()
            .is_none_or(|parent| parent.kind() != "compound_statement")
    {
        return false;
    }
    let Some(right) = node
        .child_by_field_name("right")
        .filter(|right| right.kind() == "identifier")
    else {
        return false;
    };
    let mut preceding = node.prev_named_sibling();
    while preceding.is_some_and(|node| node.kind() == "comment") {
        preceding = preceding.and_then(|node| node.prev_named_sibling());
    }
    let Some(declaration) =
        preceding.filter(|node| node.kind() == "declaration")
    else {
        return false;
    };
    if !declaration.child_by_field_name("type").is_some_and(|kind| {
        matches!(kind.kind(), "primitive_type" | "sized_type_specifier")
    }) {
        return false;
    }
    let mut cursor = declaration.walk();
    declaration
        .children_by_field_name("declarator", &mut cursor)
        .any(|declarator| {
            if find_declarator_identifier(declarator)
                .and_then(|name| name.utf8_text(source).ok())
                != right.utf8_text(source).ok()
            {
                return false;
            }
            let mut current = Some(declarator);
            let mut count = 0;
            while let Some(node) = current {
                match node.kind() {
                    "array_declarator" => count += 1,
                    "init_declarator" | "identifier" => {}
                    _ => return false,
                }
                current = node.child_by_field_name("declarator");
            }
            count >= 2
        })
}

/// 判断原生声明是否直接携带不可变对象说明符
fn native_family_declaration_is_constant(
    declaration: Node<'_>,
    declarator: Node<'_>,
    source: &[u8],
) -> bool {
    let matches_type_spelling = |node: Node<'_>, spelling| {
        let mut cursor = node.walk();
        node.named_children(&mut cursor).any(|child| {
            matches!(
                child.kind(),
                "type_qualifier" | "storage_class_specifier"
            ) && child.utf8_text(source).ok() == Some(spelling)
        })
    };
    if matches_type_spelling(declaration, "constexpr") {
        return true;
    }
    let mut current = find_declarator_identifier(declarator);
    while let Some(node) = current {
        match node.kind() {
            "pointer_declarator" => {
                return matches_type_spelling(node, "const");
            }
            "reference_declarator" => return false,
            _ => {}
        }
        if node.id() == declarator.id() {
            break;
        }
        current = node.parent();
    }
    matches_type_spelling(declaration, "const")
}

/// 判断 C++ 声明是否为私有非静态数据成员
fn cplusplus_is_private_non_static_data_member(
    declaration: Node<'_>,
    source: &[u8],
) -> bool {
    if declaration.kind() != "field_declaration"
        || native_family_function_declarator(declaration).is_some()
        || descendant_of_kind(declaration, "storage_class_specifier").is_some()
    {
        return false;
    }
    let Some(body) = declaration.parent() else {
        return false;
    };
    let Some(owner) = body.parent() else {
        return false;
    };
    let mut private = owner.kind() == "class_specifier";
    let mut cursor = body.walk();
    for sibling in body.named_children(&mut cursor) {
        if sibling.id() == declaration.id() {
            break;
        }
        if sibling.kind() == "access_specifier" {
            private = sibling
                .utf8_text(source)
                .ok()
                .is_some_and(|access| access.starts_with("private"));
        }
    }
    private
}

/// 按规则优先级检查标识符并返回首项问题
fn judge_identifier(
    authority: &CompiledAuthority,
    language: Language,
    declaration: &Declaration,
) -> Option<RuleOperator> {
    match declaration.owner {
        IdentifierOwner::Unresolved
        | IdentifierOwner::LanguageFixed
        | IdentifierOwner::ProfileFixed
        | IdentifierOwner::Discard => return None,
        IdentifierOwner::AuthorChosen => {}
    }
    let semantic_name = strip_language_form(declaration);
    let (invalid_prefix, quantity, remainder) =
        authority.identifier_name_disposition(semantic_name);
    // 通过 Authority 统一判断词元是否为候选或已注册名称
    // 单次遍历汇总结果，调用方不再自行分类
    let mut has_candidate = false;
    let mut vocabulary_complete = true;
    for token in split_identifier_tokens(remainder) {
        match authority.identifier_token_disposition(&token) {
            TokenDisposition::Candidate => has_candidate = true,
            TokenDisposition::Vocabulary => {}
            TokenDisposition::Unknown => vocabulary_complete = false,
        }
    }
    if has_candidate {
        return Some(RuleOperator::IdentifierCandidate);
    }
    if identifier_is_reserved(language, declaration) {
        return Some(RuleOperator::IdentifierReserved);
    }
    if invalid_prefix {
        return Some(RuleOperator::IdentifierCanonicalForm);
    }
    if !identifier_role_form_is_valid(declaration, semantic_name) {
        return Some(RuleOperator::IdentifierCanonicalForm);
    }
    // 表未命中即不做任何 quantity 推断；token 判定路径保持不变
    if declaration.value_like
        && let Some(disposition) = quantity
        && disposition != QuantityNameDisposition::Valid
    {
        return Some(RuleOperator::IdentifierRepresentationSuffix);
    }
    if !vocabulary_complete
        && !declaration.external_owner.as_deref().is_some_and(|owner| {
            authority.external_fixed_contains(
                language.key(),
                declaration.role.key(),
                owner,
                &declaration.name,
            )
        })
    {
        return Some(RuleOperator::IdentifierUnknownToken);
    }
    None
}

/// 去除标识符中已识别的语言专用前后缀
fn strip_language_form(declaration: &Declaration) -> &str {
    match declaration.local_form {
        LocalIdentifierForm::PythonPrivate => declaration
            .name
            .strip_prefix('_')
            .unwrap_or(&declaration.name),
        LocalIdentifierForm::PythonProtocol => declaration
            .name
            .strip_prefix("__")
            .and_then(|name| name.strip_suffix("__"))
            .unwrap_or(&declaration.name),
        LocalIdentifierForm::PythonInvalidReceiver => &declaration.name,
        LocalIdentifierForm::RustRaw => declaration
            .name
            .strip_prefix("r#")
            .unwrap_or(&declaration.name),
        LocalIdentifierForm::RustLifetime => declaration
            .name
            .strip_prefix('\'')
            .unwrap_or(&declaration.name),
        LocalIdentifierForm::TypeDefinitionSuffix => declaration
            .name
            .strip_suffix("_t")
            .unwrap_or(&declaration.name),
        LocalIdentifierForm::CplusplusPrivateMember => declaration
            .name
            .strip_suffix('_')
            .unwrap_or(&declaration.name),
        LocalIdentifierForm::Plain => &declaration.name,
    }
}

/// 判断标识符是否占用语言保留名称
fn identifier_is_reserved(
    language: Language,
    declaration: &Declaration,
) -> bool {
    if language == Language::Rust {
        return declaration.local_form == LocalIdentifierForm::RustRaw
            && callable_is_reserved(
                language,
                strip_language_form(declaration),
            );
    }
    if !matches!(language, Language::ProceduralSource | Language::Cplusplus) {
        return false;
    }
    let name = declaration.name.as_str();
    let underscore_upper = name
        .strip_prefix('_')
        .and_then(|suffix| suffix.chars().next())
        .is_some_and(|character| character.is_uppercase());
    let double_underscore = if language == Language::Cplusplus {
        name.contains("__")
    } else {
        name.starts_with("__")
    };
    double_underscore
        || underscore_upper
        || (declaration.reserved_scope && name.starts_with('_'))
}

/// 按声明用途检查标识符的命名形式
fn identifier_role_form_is_valid(
    declaration: &Declaration,
    semantic_name: &str,
) -> bool {
    if declaration.local_form == LocalIdentifierForm::PythonInvalidReceiver {
        return false;
    }
    match declaration.role {
        IdentifierRole::Value | IdentifierRole::Function => {
            let local_form_valid = match declaration.local_form {
                LocalIdentifierForm::CplusplusPrivateMember => {
                    declaration.name.ends_with('_')
                }
                _ => true,
            };
            local_form_valid && matches_lower_snake_case(semantic_name)
        }
        IdentifierRole::Type => is_pascal_case(semantic_name),
        IdentifierRole::Constant | IdentifierRole::Enumerator => {
            matches_upper_snake_case(semantic_name)
        }
        IdentifierRole::Variant => is_pascal_case(semantic_name),
        IdentifierRole::Typedef => {
            declaration.local_form == LocalIdentifierForm::TypeDefinitionSuffix
                && declaration.name.ends_with("_t")
                && matches_lower_snake_case(semantic_name)
        }
        IdentifierRole::ModuleNamespace
        | IdentifierRole::Tag
        | IdentifierRole::Lifetime
        | IdentifierRole::Label => matches_lower_snake_case(semantic_name),
        IdentifierRole::Alias => {
            matches_lower_snake_case(semantic_name)
                || is_pascal_case(semantic_name)
        }
        IdentifierRole::ModuleBinding => {
            matches_lower_snake_case(semantic_name)
                || matches_upper_snake_case(semantic_name)
        }
    }
}

/// 判断名称是否符合小写蛇形形式
fn matches_lower_snake_case(name: &str) -> bool {
    !name.is_empty()
        && !name.starts_with('_')
        && !name.ends_with('_')
        && name.split('_').all(|segment| {
            !segment.is_empty()
                && segment.chars().all(|character| {
                    character.is_ascii_lowercase()
                        || character.is_ascii_digit()
                })
        })
}

/// 判断名称是否符合大写蛇形形式
fn matches_upper_snake_case(name: &str) -> bool {
    !name.is_empty()
        && !name.starts_with('_')
        && !name.ends_with('_')
        && name.split('_').all(|segment| {
            !segment.is_empty()
                && segment.chars().all(|character| {
                    character.is_ascii_uppercase()
                        || character.is_ascii_digit()
                })
        })
}

/// 判断名称是否满足大驼峰拼写要求
fn is_pascal_case(name: &str) -> bool {
    name.chars()
        .next()
        .is_some_and(|character| character.is_ascii_uppercase())
        && !name.contains('_')
        && name
            .chars()
            .all(|character| character.is_ascii_alphanumeric())
        && name.chars().any(|character| character.is_ascii_lowercase())
}

/// 按下划线和大小写边界拆分名称
///
/// 只负责边界拆分；大小写归一化由 Authority 的词法法则查询统一拥有
fn split_identifier_tokens(name: &str) -> Vec<String> {
    let mut tokens = Vec::new();
    for segment in name.split('_').filter(|segment| !segment.is_empty()) {
        if segment.chars().all(|character| {
            !character.is_alphabetic() || character.is_uppercase()
        }) {
            tokens.push(segment.to_owned());
            continue;
        }
        let mut current = String::new();
        for character in segment.chars() {
            if character.is_uppercase() && !current.is_empty() {
                tokens.push(std::mem::take(&mut current));
            }
            current.push(character);
        }
        if !current.is_empty() {
            tokens.push(current);
        }
    }
    tokens
}

/// 选择对应语言的 Tree-sitter 语法
fn tree_sitter_language(language: Language) -> TreeSitterLanguage {
    match language {
        Language::Python => tree_sitter_python::LANGUAGE.into(),
        Language::Rust => tree_sitter_rust::LANGUAGE.into(),
        Language::ProceduralSource => tree_sitter_c::LANGUAGE.into(),
        Language::Cplusplus => tree_sitter_cpp::LANGUAGE.into(),
    }
}

/// 规范化相对路径并确定其源码语言
fn source_admission(
    authority: &CompiledAuthority,
    raw_path: &str,
) -> Result<Option<AdmittedSource>, ReviewRejection> {
    let path = normalize_relative_path(raw_path)?;
    let Some(extension) = Path::new(&path)
        .extension()
        .and_then(std::ffi::OsStr::to_str)
    else {
        return Ok(None);
    };
    let Some(language) = authority.source_profile(extension, &path)? else {
        return Ok(None);
    };
    Ok(Some(AdmittedSource { path, language }))
}

/// 从语法树收集需要文档的声明及其相关事实
#[allow(clippy::too_many_arguments)]
fn observe_callable(
    language: Language,
    node: Node<'_>,
    source: &[u8],
    nested: bool,
    output: &mut Vec<Callable>,
) -> bool {
    if matches!(language, Language::ProceduralSource | Language::Cplusplus)
        && matches!(node.kind(), "declaration" | "field_declaration")
    {
        let mut cursor = node.walk();
        let mut observed = false;
        for declarator in
            node.children_by_field_name("declarator", &mut cursor)
        {
            if native_family_function_declarator(declarator).is_some() {
                observe_callable_declaration(
                    language,
                    node,
                    Some(declarator),
                    source,
                    nested,
                    output,
                );
                observed = true;
            }
        }
        if observed {
            return nested;
        }
    }
    observe_callable_declaration(language, node, None, source, nested, output)
}

/// 按独立 declarator 收集函数事实并保留共同声明的文档归属
fn observe_callable_declaration(
    language: Language,
    node: Node<'_>,
    declarator: Option<Node<'_>>,
    source: &[u8],
    nested: bool,
    output: &mut Vec<Callable>,
) -> bool {
    let subject = declarator.unwrap_or(node);
    let is_named_callable = match language {
        Language::Python => node.kind() == "function_definition",
        Language::Rust => {
            matches!(node.kind(), "function_item" | "function_signature_item")
        }
        Language::ProceduralSource | Language::Cplusplus => {
            node.kind() == "function_definition" || declarator.is_some()
        }
    };
    let is_python_class =
        language == Language::Python && node.kind() == "class_definition";
    let mut rust_attribute = (language == Language::Rust
        && node.kind() == "macro_definition")
        .then(|| observe_rust_attribute(node, source));
    let is_rust_public_item = language == Language::Rust
        && rust_public_documentation_item(
            node,
            source,
            rust_attribute.as_ref(),
        );
    let is_native_family_unresolved_item =
        matches!(language, Language::ProceduralSource | Language::Cplusplus)
            && native_family_documentation_capability_needed(node);
    let is_subject = is_named_callable
        || is_python_class
        || is_rust_public_item
        || is_native_family_unresolved_item;
    let child_nested = nested
        || (is_named_callable
            && !matches!(node.kind(), "function_signature_item"));
    if is_subject {
        if language == Language::Rust && rust_attribute.is_none() {
            rust_attribute = Some(observe_rust_attribute(node, source));
        }
        let name = documentation_subject_name(language, subject, source);
        let identity_unresolved = name.is_none();
        let name = name.unwrap_or_else(|| "<unknown>".to_owned());
        let point = subject.start_position();
        let decorated_visibility = (language == Language::Python
            && is_named_callable)
            .then(|| observe_python_decorated_visibility(node, source, &name))
            .flatten();
        let visibility = if identity_unresolved {
            DocumentationVisibility::IdentityUnresolved
        } else if is_native_family_unresolved_item && !is_named_callable {
            DocumentationVisibility::Internal
        } else if is_native_family_unresolved_item {
            DocumentationVisibility::Unresolved
        } else if let Some(decorated_visibility) = decorated_visibility {
            decorated_visibility
        } else {
            observe_documentation_visibility(
                language,
                node,
                source,
                nested,
                &name,
                rust_attribute.as_ref(),
            )
        };
        let carrier = documentation_carrier(
            language,
            node,
            source,
            rust_attribute.as_ref(),
        );
        let (parameters, parameters_complete) =
            callable_parameters(language, subject, source);
        let (
            template_parameters,
            template_parameters_complete,
            requires_template_parameters,
        ) = cplusplus_template_parameters(language, node, subject, source);
        output.push(Callable {
            language,
            name,
            line: point.row + 1,
            column: point.column + 1,
            named: is_named_callable,
            visibility,
            parameters,
            parameters_complete,
            template_parameters,
            template_parameters_complete,
            requires_template_parameters,
            return_shape: if declarator.is_some() {
                native_family_return_shape(language, node, declarator, source)
            } else {
                callable_return_shape(language, node, source)
            },
            carrier,
            requires_safety: language == Language::Rust
                && rust_requires_safety(node),
            requires_effect: language == Language::Cplusplus
                && cplusplus_requires_effect(subject, source),
            carrier_unresolved: rust_attribute
                .as_ref()
                .is_some_and(|facts| facts.nonliteral_documentation),
        });
    }
    child_nested
}

/// 判断 Rust 非函数声明是否需要文档
fn rust_public_documentation_item(
    node: Node<'_>,
    source: &[u8],
    attribute: Option<&RustAttributeFacts<'_>>,
) -> bool {
    match node.kind() {
        "mod_item" | "struct_item" | "union_item" | "enum_item"
        | "type_item" | "const_item" | "static_item" | "use_declaration" => {
            rust_has_unrestricted_public_visibility(node, source)
        }
        "trait_item" => {
            rust_has_unrestricted_public_visibility(node, source)
                || rust_requires_safety(node)
        }
        "field_declaration" => {
            rust_has_unrestricted_public_visibility(node, source)
        }
        "enum_variant" => rust_public_ancestor(node, source, "enum_item"),
        "macro_definition" => attribute.is_some_and(|facts| facts.is_public),
        _ => false,
    }
}

/// 判断 Rust 声明是否需要安全说明
fn rust_requires_safety(node: Node<'_>) -> bool {
    if !matches!(
        node.kind(),
        "function_item" | "function_signature_item" | "trait_item"
    ) {
        return false;
    }
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        if child.kind() == "unsafe" {
            return true;
        }
        if child.kind() == "function_modifiers" {
            let mut modifier_cursor = child.walk();
            if child
                .children(&mut modifier_cursor)
                .any(|modifier| modifier.kind() == "unsafe")
            {
                return true;
            }
        }
    }
    false
}

/// 一次观察 Rust 属性链的精确身份与文档事实
fn observe_rust_attribute<'tree>(
    node: Node<'tree>,
    source: &[u8],
) -> RustAttributeFacts<'tree> {
    let mut items = Vec::new();
    let mut cursor = node.walk();
    items.extend(
        node.named_children(&mut cursor)
            .filter(|child| child.kind() == "attribute_item"),
    );
    let mut preceding = node.prev_named_sibling();
    let mut attachment_start = node.start_byte();
    while let Some(attribute) = preceding {
        if attribute.kind() != "attribute_item" {
            break;
        }
        attachment_start = attribute.start_byte();
        items.push(attribute);
        preceding = attribute.prev_named_sibling();
    }
    items.sort_unstable_by_key(Node::start_byte);
    let mut facts = RustAttributeFacts {
        documentation: Vec::new(),
        is_public: false,
        nonliteral_documentation: false,
        preceding,
        attachment_start,
    };
    for item in items {
        let Some(attribute) = item.named_child(0) else {
            continue;
        };
        let Some(path) = attribute.named_child(0) else {
            continue;
        };
        if path.kind() != "identifier" {
            continue;
        }
        match path.utf8_text(source).ok() {
            Some("macro_export") => facts.is_public = true,
            Some("doc") => {
                let literal = attribute
                    .child_by_field_name("value")
                    .and_then(|value| value.utf8_text(source).ok())
                    .and_then(|value| serde_json::from_str(value).ok());
                if let Some(line) = literal {
                    facts.documentation.push(line);
                } else {
                    facts.nonliteral_documentation = true;
                }
            }
            _ => {}
        }
    }
    facts
}

/// 判断 Rust 声明是否具有不受限的公开可见性
fn rust_has_unrestricted_public_visibility(
    node: Node<'_>,
    source: &[u8],
) -> bool {
    let mut cursor = node.walk();
    node.named_children(&mut cursor).any(|child| {
        child.kind() == "visibility_modifier"
            && child
                .utf8_text(source)
                .is_ok_and(|text| text.trim() == "pub")
    })
}

/// 判断指定类型的 Rust 上层声明是否公开
fn rust_public_ancestor(node: Node<'_>, source: &[u8], kind: &str) -> bool {
    let mut ancestor = node.parent();
    while let Some(current) = ancestor {
        if current.kind() == kind {
            return rust_has_unrestricted_public_visibility(current, source);
        }
        ancestor = current.parent();
    }
    false
}

/// 识别需要文档的 C/C++ 非函数声明
fn native_family_documentation_capability_needed(node: Node<'_>) -> bool {
    matches!(
        node.kind(),
        "struct_specifier"
            | "union_specifier"
            | "enum_specifier"
            | "class_specifier"
            | "enumerator"
            | "preproc_def"
            | "preproc_function_def"
    ) || (node.kind() == "field_declaration"
        && native_family_function_declarator(node).is_none())
}

/// 提取文档所属声明的名称
fn documentation_subject_name(
    language: Language,
    node: Node<'_>,
    source: &[u8],
) -> Option<String> {
    if language == Language::Rust && node.kind() == "use_declaration" {
        return node
            .utf8_text(source)
            .ok()
            .map(str::trim)
            .map(str::to_owned);
    }
    callable_name(language, node, source).or_else(|| {
        node.child_by_field_name("name")
            .and_then(find_declaration_identifier)
            .and_then(|name| name.utf8_text(source).ok())
            .map(str::to_owned)
    })
}

/// 提取参数名称并判断信息是否完整且无重复
fn callable_parameters(
    language: Language,
    node: Node<'_>,
    source: &[u8],
) -> (Vec<String>, bool) {
    let parameters = match language {
        Language::Python | Language::Rust => {
            node.child_by_field_name("parameters")
        }
        Language::ProceduralSource | Language::Cplusplus => {
            native_family_function_declarator(node)
                .and_then(|declarator| {
                    declarator.child_by_field_name("parameters")
                })
                .or_else(|| {
                    node.child_by_field_name("declarator")
                        .filter(|declarator| {
                            declarator.kind() == "operator_cast"
                        })
                        .and_then(|declarator| {
                            descendant_of_kind(declarator, "parameter_list")
                        })
                })
        }
    };
    let Some(parameters) = parameters else {
        return (Vec::new(), false);
    };
    let mut names = Vec::new();
    let complete =
        observe_parameter_names(language, parameters, source, &mut names);
    if language == Language::Python
        && let Some(receiver) = python_receiver_spelling(node, source)
        && names.first().is_some_and(|name| name == receiver)
    {
        names.remove(0);
    }
    let original_count = names.len();
    names.sort();
    names.dedup();
    let names_are_unique = original_count == names.len();
    (names, complete && names_are_unique)
}

/// 提取 C++ callable 直属模板声明中的模板参数
fn cplusplus_template_parameters(
    language: Language,
    node: Node<'_>,
    subject: Node<'_>,
    source: &[u8],
) -> (Vec<String>, bool, bool) {
    if language != Language::Cplusplus {
        return (Vec::new(), true, false);
    }
    let has_abbreviated_parameter =
        cplusplus_has_placeholder_auto_parameter(subject);
    let Some(template) = cplusplus_template_declaration(node) else {
        return (
            Vec::new(),
            !has_abbreviated_parameter,
            has_abbreviated_parameter,
        );
    };
    let Some(parameters) = template.child_by_field_name("parameters") else {
        return (Vec::new(), false, true);
    };
    let mut cursor = parameters.walk();
    let items: Vec<_> = parameters
        .named_children(&mut cursor)
        .filter(|child| child.kind() != "comment")
        .collect();
    if items.is_empty() {
        return (Vec::new(), false, true);
    }
    let mut names = Vec::with_capacity(items.len());
    for parameter in items {
        let Some(name) = cplusplus_template_parameter_name(parameter) else {
            return (Vec::new(), false, true);
        };
        let Ok(name) = name.utf8_text(source) else {
            return (Vec::new(), false, true);
        };
        names.push(name.to_owned());
    }
    let original_count = names.len();
    names.sort();
    names.dedup();
    let names_are_unique = original_count == names.len();
    (names, names_are_unique && !has_abbreviated_parameter, true)
}

/// 判断 callable 参数中是否有 C++ abbreviated-template placeholder auto
fn cplusplus_has_placeholder_auto_parameter(node: Node<'_>) -> bool {
    let Some(parameters) = descendant_of_kind(node, "function_declarator")
        .and_then(|declarator| declarator.child_by_field_name("parameters"))
    else {
        return false;
    };
    let mut cursor = parameters.walk();
    parameters.named_children(&mut cursor).any(|parameter| {
        parameter.child_by_field_name("type").is_some_and(|kind| {
            kind.kind() == "placeholder_type_specifier"
                && direct_child_of_kind(kind, "auto").is_some()
        })
    })
}

/// 返回 callable 直接所属的 C++ template declaration
fn cplusplus_template_declaration(node: Node<'_>) -> Option<Node<'_>> {
    node.parent()
        .filter(|parent| parent.kind() == "template_declaration")
}

/// 返回一个直接 C++ template parameter 的稳定名称
fn cplusplus_template_parameter_name(parameter: Node<'_>) -> Option<Node<'_>> {
    match parameter.kind() {
        "type_parameter_declaration"
        | "optional_type_parameter_declaration"
        | "variadic_type_parameter_declaration" => {
            if let Some(name) = parameter.child_by_field_name("name") {
                return Some(name);
            }
            let mut cursor = parameter.walk();
            parameter
                .named_children(&mut cursor)
                .find(|child| child.kind() == "type_identifier")
        }
        "parameter_declaration"
        | "optional_parameter_declaration"
        | "variadic_parameter_declaration" => parameter
            .child_by_field_name("declarator")
            .and_then(find_declarator_identifier),
        "template_template_parameter_declaration" => {
            let mut cursor = parameter.walk();
            parameter
                .named_children(&mut cursor)
                .find(|child| {
                    matches!(
                        child.kind(),
                        "type_parameter_declaration"
                            | "optional_type_parameter_declaration"
                            | "variadic_type_parameter_declaration"
                    )
                })
                .and_then(cplusplus_template_parameter_name)
        }
        _ => None,
    }
}

/// 统一排除参数表中不产生作者绑定的位置
fn parameter_is_fixed(parameter: Node<'_>) -> bool {
    matches!(
        parameter.kind(),
        "keyword_separator"
            | "positional_separator"
            | "self_parameter"
            | "attribute_item"
            | "comment"
            | "line_comment"
            | "block_comment"
    )
}

/// 统一提供原生参数的绑定事实，保留 Rust 模式与稳定参数名的区别
fn parameter_binding(
    language: Language,
    parameter: Node<'_>,
) -> Option<Node<'_>> {
    match language {
        Language::Python => python_parameter_identifier(parameter),
        Language::Rust => parameter.child_by_field_name("pattern"),
        Language::ProceduralSource | Language::Cplusplus => parameter
            .child_by_field_name("declarator")
            .and_then(find_declarator_identifier),
    }
}

/// 从同一参数绑定来源派生文档名称与单调的完整性
fn observe_parameter_names(
    language: Language,
    parameters: Node<'_>,
    source: &[u8],
    names: &mut Vec<String>,
) -> bool {
    let mut cursor = parameters.walk();
    let items: Vec<_> = parameters
        .named_children(&mut cursor)
        .filter(|child| !parameter_is_fixed(*child))
        .collect();
    if items.is_empty() {
        // C 空括号没有原型信息；C++ 空括号以及 Python/Rust 空参数表有
        // 完整含义，裸变参仍由下方的匿名 token 检查保留缺口
        let mut cursor = parameters.walk();
        return language != Language::ProceduralSource
            && !parameters
                .children(&mut cursor)
                .any(|child| child.kind() == "...");
    }
    if items.len() == 1
        && items[0].kind() == "parameter_declaration"
        && items[0].child_by_field_name("declarator").is_none()
        && items[0]
            .child_by_field_name("type")
            .and_then(|kind| kind.utf8_text(source).ok())
            .is_some_and(|kind| kind.trim() == "void")
    {
        return true;
    }
    // 裸 `...` 在 C 家族参数表里是参数表的直接匿名节点，不会出现在
    // 命名子节点中；命名参数包的 `...` 藏在命名声明内部，不受影响
    let mut complete = {
        let mut cursor = parameters.walk();
        !parameters
            .children(&mut cursor)
            .any(|child| child.kind() == "...")
    };
    for parameter in items {
        if let Some(identifier) = parameter_binding(language, parameter)
            .filter(|binding| {
                matches!(binding.kind(), "identifier" | "field_identifier")
            })
            && let Ok(text) = identifier.utf8_text(source)
        {
            names.push(text.to_owned());
        } else {
            complete = false;
        }
    }
    complete
}

/// 返回节点唯一的直接标识符子节点
fn single_identifier_child(node: Node<'_>) -> Option<Node<'_>> {
    let mut cursor = node.walk();
    let identifiers: Vec<_> = node
        .named_children(&mut cursor)
        .filter(|child| child.kind() == "identifier")
        .collect();
    let [identifier] = identifiers.as_slice() else {
        return None;
    };
    Some(*identifier)
}

/// 提取 callable 的返回值形状
fn callable_return_shape(
    language: Language,
    node: Node<'_>,
    source: &[u8],
) -> ReturnShape {
    match language {
        Language::Python => python_return_shape(node, source),
        Language::Rust => rust_return_shape(node, source),
        Language::ProceduralSource | Language::Cplusplus => {
            native_family_return_shape(
                language,
                node,
                node.child_by_field_name("declarator"),
                source,
            )
        }
    }
}

/// 提取 Python 可由直接语法证明的返回值形状
///
/// 直接注解 `None` 判为 NoValue
/// 精确注解 `Never`、`NoReturn`、`typing.Never` 和 `typing.NoReturn` 判为 Never
/// 其他完整注解判为 Value，不解析别名；缺失注解保持 Unknown
fn python_return_shape(node: Node<'_>, source: &[u8]) -> ReturnShape {
    let Some(kind) = node.child_by_field_name("return_type") else {
        return ReturnShape::Unknown;
    };
    let kind = if kind.kind() == "type" && kind.named_child_count() == 1 {
        kind.named_child(0).unwrap_or(kind)
    } else {
        kind
    };
    direct_return_shape(Language::Python, kind, source)
}

/// 提取 Rust 可由直接语法证明的返回值形状
fn rust_return_shape(node: Node<'_>, source: &[u8]) -> ReturnShape {
    let Some(kind) = node.child_by_field_name("return_type") else {
        return ReturnShape::NoValue;
    };
    match kind.kind() {
        "macro_invocation" | "metavariable" => ReturnShape::Unknown,
        _ => direct_return_shape(Language::Rust, kind, source),
    }
}

/// 根据语言规则将直接返回类型归入四种返回状态
fn direct_return_shape(
    language: Language,
    kind: Node<'_>,
    source: &[u8],
) -> ReturnShape {
    let Ok(spelling) = kind.utf8_text(source).map(str::trim) else {
        return ReturnShape::Unknown;
    };
    let law = &profile_law(language.key()).return_surface;
    if law.no_value.contains(&spelling) {
        ReturnShape::NoValue
    } else if law.never.contains(&spelling) {
        ReturnShape::Never
    } else {
        ReturnShape::Value
    }
}

/// 提取 C/C++ 函数的返回状态
///
/// 优先识别不会返回的声明：C 的 `_Noreturn` 说明符
/// 或 C/C++ 声明及其声明结构上无前缀的 `[[noreturn]]` 属性判为 Never
/// 其余按直接类型判断；构造、析构及直接或后置 void 返回类型判为 NoValue
fn native_family_return_shape(
    language: Language,
    node: Node<'_>,
    declarator: Option<Node<'_>>,
    source: &[u8],
) -> ReturnShape {
    if native_family_proves_never(language, node, declarator, source) {
        return ReturnShape::Never;
    }
    let subject = declarator.unwrap_or(node);
    let function_declarator = native_family_function_declarator(subject);
    if language == Language::Cplusplus
        && let Some(trailing) = function_declarator.and_then(|declarator| {
            direct_child_of_kind(declarator, "trailing_return_type")
        })
        && let Some(descriptor) = trailing.named_child(0)
        && let Some(kind) = descriptor.child_by_field_name("type")
    {
        return native_family_type_shape(
            language,
            kind,
            descriptor.child_by_field_name("declarator"),
            source,
        );
    }
    if language == Language::Cplusplus
        && let Some(target) = descendant_of_kind(subject, "operator_cast")
        && let Some(kind) = target.child_by_field_name("type")
    {
        return native_family_type_shape(language, kind, None, source);
    }
    let Some(kind) = node.child_by_field_name("type") else {
        return if language == Language::Cplusplus
            && cplusplus_constructor_or_destructor(subject, source)
        {
            ReturnShape::NoValue
        } else {
            ReturnShape::Unknown
        };
    };
    native_family_type_shape(language, kind, declarator, source)
}

/// 判断 C/C++ 声明是否直接标明不会返回
///
/// C 支持 `_Noreturn` 说明符
/// 两种语言均支持声明或其声明结构上无前缀的 `[[noreturn]]` 属性
/// 不解释裸 `noreturn` 或 `__attribute__` 等其他形式，仍按返回类型判断
fn native_family_proves_never(
    language: Language,
    node: Node<'_>,
    declarator: Option<Node<'_>>,
    source: &[u8],
) -> bool {
    let law = &profile_law(language.key()).return_surface;
    let mut surface = Some(node);
    let mut declaration = true;
    while let Some(current) = surface {
        let mut nested = current.walk();
        for candidate in current.named_children(&mut nested) {
            if candidate.kind() == "attribute_declaration"
                && attribute_declaration_is_never(
                    candidate,
                    source,
                    law.never_attribute,
                )
            {
                return true;
            }
            if declaration
                && language == Language::ProceduralSource
                && candidate.kind() == "type_qualifier"
                && candidate
                    .utf8_text(source)
                    .is_ok_and(|text| law.never.contains(&text.trim()))
            {
                return true;
            }
        }
        surface = if declaration {
            declarator
        } else {
            current.child_by_field_name("declarator")
        };
        declaration = false;
    }
    false
}

/// 判断 attribute_declaration 是否恰为无前缀的 noreturn 属性
fn attribute_declaration_is_never(
    node: Node<'_>,
    source: &[u8],
    expected: Option<&str>,
) -> bool {
    let mut cursor = node.walk();
    node.named_children(&mut cursor)
        .filter(|child| child.kind() == "attribute")
        .any(|attribute| {
            attribute.named_child_count() == 1
                && attribute.child_by_field_name("prefix").is_none()
                && attribute
                    .child_by_field_name("name")
                    .and_then(|name| name.utf8_text(source).ok())
                    .is_some_and(|name| Some(name) == expected)
        })
}

/// 根据 C/C++ 直接类型节点判断返回状态
///
/// 完整具名类型判为 Value，包括长度修饰后的类型、限定名和模板类型
/// 未推导的 `auto`、`decltype(auto)` 及宏等无法确定的类型保持 Unknown
/// 不从函数体或别名定义推导类型
fn native_family_type_shape(
    language: Language,
    kind: Node<'_>,
    declarator: Option<Node<'_>>,
    source: &[u8],
) -> ReturnShape {
    if declarator.is_some_and(declarator_proves_return_value) {
        return ReturnShape::Value;
    }
    match kind.kind() {
        "primitive_type" => direct_return_shape(language, kind, source),
        "sized_type_specifier"
        | "class_specifier"
        | "enum_specifier"
        | "struct_specifier"
        | "union_specifier" => ReturnShape::Value,
        "type_identifier"
        | "scoped_type_identifier"
        | "qualified_identifier"
        | "template_type" => ReturnShape::Value,
        _ => ReturnShape::Unknown,
    }
}

/// 返回指定种类的直接命名子节点
fn direct_child_of_kind<'tree>(
    node: Node<'tree>,
    kind: &str,
) -> Option<Node<'tree>> {
    let mut cursor = node.walk();
    node.named_children(&mut cursor)
        .find(|child| child.kind() == kind)
}

/// 判断 declarator 是否直接保证返回一个指针或引用值
fn declarator_proves_return_value(node: Node<'_>) -> bool {
    matches!(
        node.kind(),
        "pointer_declarator"
            | "reference_declarator"
            | "abstract_reference_declarator"
    ) || node
        .child_by_field_name("declarator")
        .is_some_and(declarator_proves_return_value)
}

/// 判断 C++ callable 是否为可证明的构造或析构函数
fn cplusplus_constructor_or_destructor(node: Node<'_>, source: &[u8]) -> bool {
    let Some(name) = descendant_of_kind(node, "function_declarator")
        .and_then(|declarator| declarator.child_by_field_name("declarator"))
        .and_then(find_declarator_identifier)
    else {
        return false;
    };
    if name.kind() == "destructor_name" {
        return true;
    }
    let Ok(name) = name.utf8_text(source) else {
        return false;
    };
    let mut ancestor = node.parent();
    while let Some(parent) = ancestor {
        if parent.kind() == "class_specifier" {
            return parent
                .child_by_field_name("name")
                .and_then(|class_name| class_name.utf8_text(source).ok())
                .is_some_and(|class_name| class_name == name);
        }
        ancestor = parent.parent();
    }
    false
}

/// 判断 C++ callable 是否需要公开的效果字段
fn cplusplus_requires_effect(node: Node<'_>, source: &[u8]) -> bool {
    if cplusplus_constructor_or_destructor(node, source) {
        return true;
    }
    descendant_of_kind(node, "function_declarator")
        .and_then(|declarator| declarator.child_by_field_name("declarator"))
        .and_then(find_declarator_identifier)
        .is_some_and(|name| {
            matches!(name.kind(), "operator_name" | "operator_cast")
        })
}

/// 从函数声明中读取名称
fn callable_name(
    language: Language,
    node: Node<'_>,
    source: &[u8],
) -> Option<String> {
    let name = match language {
        Language::Python | Language::Rust => node.child_by_field_name("name"),
        Language::ProceduralSource | Language::Cplusplus => node
            .child_by_field_name("declarator")
            .and_then(find_declarator_identifier)
            .or_else(|| descendant_of_kind(node, "function_declarator"))
            .and_then(find_declarator_identifier),
    }?;
    name.utf8_text(source).ok().map(str::to_owned)
}

/// 沿声明结构查找函数名称节点
fn find_declarator_identifier(node: Node<'_>) -> Option<Node<'_>> {
    if matches!(
        node.kind(),
        "identifier"
            | "field_identifier"
            | "operator_name"
            | "operator_cast"
            | "destructor_name"
    ) {
        return Some(node);
    }
    if let Some(declarator) = node.child_by_field_name("declarator")
        && let Some(identifier) = find_declarator_identifier(declarator)
    {
        return Some(identifier);
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        if let Some(identifier) = find_declarator_identifier(child) {
            return Some(identifier);
        }
    }
    None
}

/// 递归查找指定类型的语法节点
fn descendant_of_kind<'tree>(
    node: Node<'tree>,
    kind: &str,
) -> Option<Node<'tree>> {
    if node.kind() == kind {
        return Some(node);
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        if let Some(found) = descendant_of_kind(child, kind) {
            return Some(found);
        }
    }
    None
}

/// 根据源码结构判断文档应采用公开或内部要求
fn observe_documentation_visibility(
    language: Language,
    node: Node<'_>,
    source: &[u8],
    nested: bool,
    name: &str,
    rust_attribute: Option<&RustAttributeFacts<'_>>,
) -> DocumentationVisibility {
    match language {
        Language::Python => {
            if !nested
                && (python_protocol_method(node, source)
                    || !name.starts_with('_'))
            {
                DocumentationVisibility::Public
            } else {
                DocumentationVisibility::Internal
            }
        }
        Language::Rust => {
            if (!nested
                && rust_has_unrestricted_public_visibility(node, source))
                || (node.kind() == "function_signature_item"
                    && rust_public_ancestor(node, source, "trait_item"))
                || rust_public_documentation_item(node, source, rust_attribute)
            {
                DocumentationVisibility::Public
            } else {
                DocumentationVisibility::Internal
            }
        }
        Language::ProceduralSource | Language::Cplusplus
            if nested
                || native_family_callable_is_proven_internal(node, source) =>
        {
            DocumentationVisibility::Internal
        }
        Language::ProceduralSource | Language::Cplusplus => {
            DocumentationVisibility::Unresolved
        }
    }
}

/// 在 CST 释放后应用 Authority 拥有的原生公开身份
fn resolve_native_public_visibility(
    authority: &CompiledAuthority,
    path: &str,
    callables: &mut [Callable],
) {
    let Some(public_names) = authority.public_names(path) else {
        return;
    };
    for callable in callables {
        if matches!(
            callable.language,
            Language::ProceduralSource | Language::Cplusplus
        ) {
            if public_names.contains(&callable.name) {
                callable.visibility = DocumentationVisibility::Public;
            } else if callable.visibility
                == DocumentationVisibility::Unresolved
            {
                callable.visibility = DocumentationVisibility::Internal;
            }
        }
    }
}

/// 确定 Python decorated callable 的结构化文档层级
fn observe_python_decorated_visibility(
    node: Node<'_>,
    source: &[u8],
    name: &str,
) -> Option<DocumentationVisibility> {
    let decorators = python_decorator_texts(node, source);
    if decorators.is_empty() {
        return None;
    }
    let property_decorator = |decorator: &str| {
        decorator == "@property"
            || python_property_accessor(decorator).is_some()
    };
    let [decorator] = decorators.as_slice() else {
        return decorators
            .iter()
            .any(|decorator| property_decorator(decorator))
            .then_some(DocumentationVisibility::Unresolved);
    };
    if !property_decorator(decorator) {
        return None;
    }
    let direct_class = python_direct_class_body(node);
    let Some((class_body, class)) = direct_class else {
        return Some(DocumentationVisibility::Unresolved);
    };
    let relation_is_valid = if decorator == "@property" {
        python_direct_property_getter_count(class_body, source, name) == 1
    } else {
        let Some((owner, accessor)) = python_property_accessor(decorator)
        else {
            return Some(DocumentationVisibility::Unresolved);
        };
        owner == name
            && matches!(accessor, "setter" | "getter" | "deleter")
            && python_direct_property_getter_count(class_body, source, name)
                == 1
    };
    if !relation_is_valid {
        return Some(DocumentationVisibility::Unresolved);
    }
    let class_is_public = class
        .child_by_field_name("name")
        .and_then(|item| item.utf8_text(source).ok())
        .is_some_and(|class_name| !class_name.starts_with('_'));
    Some(if class_is_public && !name.starts_with('_') {
        DocumentationVisibility::Public
    } else {
        DocumentationVisibility::Internal
    })
}

/// 读取 Python decorated definition 的直接 decorator 文本
fn python_decorator_texts(node: Node<'_>, source: &[u8]) -> Vec<String> {
    let Some(wrapper) = node
        .parent()
        .filter(|parent| parent.kind() == "decorated_definition")
    else {
        return Vec::new();
    };
    let mut cursor = wrapper.walk();
    wrapper
        .named_children(&mut cursor)
        .filter(|child| child.kind() == "decorator")
        .filter_map(|child| child.utf8_text(source).ok())
        .map(|decorator| decorator.trim().to_owned())
        .collect()
}

/// 定位 Python callable 直接所属的 class body
fn python_direct_class_body(node: Node<'_>) -> Option<(Node<'_>, Node<'_>)> {
    let item = node
        .parent()
        .filter(|parent| parent.kind() == "decorated_definition")
        .unwrap_or(node);
    let body = item.parent().filter(|parent| parent.kind() == "block")?;
    let class = body
        .parent()
        .filter(|parent| parent.kind() == "class_definition")?;
    Some((body, class))
}

/// 计算同一 Python class body 中同名的直接 property getter
fn python_direct_property_getter_count(
    class_body: Node<'_>,
    source: &[u8],
    name: &str,
) -> usize {
    let mut cursor = class_body.walk();
    class_body
        .named_children(&mut cursor)
        .filter(|child| child.kind() == "decorated_definition")
        .filter(|wrapper| {
            let mut wrapper_cursor = wrapper.walk();
            let children: Vec<_> =
                wrapper.named_children(&mut wrapper_cursor).collect();
            let decorators: Vec<_> = children
                .iter()
                .filter(|child| child.kind() == "decorator")
                .filter_map(|child| child.utf8_text(source).ok())
                .map(str::trim)
                .collect();
            let getter = children
                .iter()
                .find(|child| child.kind() == "function_definition");
            decorators == ["@property"]
                && getter
                    .and_then(|function| function.child_by_field_name("name"))
                    .and_then(|item| item.utf8_text(source).ok())
                    == Some(name)
        })
        .count()
}

/// 解析受支持的 Python property accessor decorator
fn python_property_accessor(decorator: &str) -> Option<(&str, &str)> {
    let (owner, accessor) = decorator.strip_prefix('@')?.split_once('.')?;
    (!owner.is_empty()
        && owner
            .chars()
            .all(|character| character == '_' || character.is_alphanumeric())
        && matches!(accessor, "setter" | "getter" | "deleter"))
    .then_some((owner, accessor))
}

/// 判断 Python 类方法是否使用双下划线协议名称
fn python_protocol_method(node: Node<'_>, source: &[u8]) -> bool {
    if node.kind() != "function_definition"
        || python_direct_class_body(node).is_none()
    {
        return false;
    }
    node.child_by_field_name("name")
        .and_then(|name| name.utf8_text(source).ok())
        .is_some_and(|name| {
            name.len() > 4 && name.starts_with("__") && name.ends_with("__")
        })
}

/// 判断 C/C++ 函数是否由源码证明为内部函数
fn native_family_callable_is_proven_internal(
    node: Node<'_>,
    source: &[u8],
) -> bool {
    let mut ancestor = Some(node);
    while let Some(current) = ancestor {
        if current.kind() == "namespace_definition"
            && current.child_by_field_name("name").is_none()
        {
            return true;
        }
        ancestor = current.parent();
    }
    descendant_of_kind(node, "storage_class_specifier")
        .and_then(|specifier| specifier.utf8_text(source).ok())
        .is_some_and(|specifier| specifier.trim() == "static")
}

/// 按语言读取声明附带的原生文档
fn documentation_carrier(
    language: Language,
    node: Node<'_>,
    source: &[u8],
    rust_attribute: Option<&RustAttributeFacts<'_>>,
) -> Option<String> {
    match profile_law(language.key()).documentation.carrier {
        DocumentationCarrierLaw::PythonSuite => python_docstring(node, source),
        DocumentationCarrierLaw::RustOuter => {
            let attribute = rust_attribute?;
            (!attribute.documentation.is_empty())
                .then(|| attribute.documentation.join("\n"))
                .or_else(|| preceding_rustdoc(source, attribute))
        }
        DocumentationCarrierLaw::NativeAdjacent => {
            let node = if language == Language::Cplusplus {
                cplusplus_template_declaration(node).unwrap_or(node)
            } else {
                node
            };
            preceding_controlled_block(node, source)
        }
    }
}

/// 读取 Python 函数或类的首条文档字符串
fn python_docstring(node: Node<'_>, source: &[u8]) -> Option<String> {
    let string = python_suite_first_docstring(node, source)?;
    let text = string.utf8_text(source).ok()?;
    Some(text.to_owned())
}

/// 判断 Python 字符串闭引号后是否只有行尾空白
fn python_string_ends_physical_line(string: Node<'_>, source: &[u8]) -> bool {
    source
        .get(string.end_byte()..)
        .and_then(|tail| tail.split(|byte| *byte == b'\n').next())
        .is_some_and(|tail| tail.iter().all(u8::is_ascii_whitespace))
}

/// 识别 Python 模块首条语句中的文档字符串
fn python_module_docstring<'tree>(
    node: Node<'tree>,
    source: &[u8],
) -> Option<Node<'tree>> {
    if node.kind() != "module" {
        return None;
    }
    let expression = python_suite_first_expression(node)?;
    python_language_string_expression(expression, source).then_some(expression)
}

/// 返回 suite 第一条受支持的三双引号常量字符串表达式
fn python_suite_first_docstring<'tree>(
    node: Node<'tree>,
    source: &[u8],
) -> Option<Node<'tree>> {
    let expression = python_suite_first_expression(node)?;
    if expression.kind() != "string" {
        return None;
    }
    let text = expression.utf8_text(source).ok()?;
    let lines: Vec<_> = text.lines().collect();
    (lines.len() >= 3
        && lines.first().is_some_and(|line| line.trim() == "\"\"\"")
        && lines.last().is_some_and(|line| line.trim() == "\"\"\"")
        && python_string_ends_physical_line(expression, source))
    .then_some(expression)
}
/// 返回 suite 第一条 statement 的唯一根表达式
fn python_suite_first_expression(node: Node<'_>) -> Option<Node<'_>> {
    let body = if node.kind() == "module" {
        node
    } else {
        node.child_by_field_name("body")?
    };
    let mut body_cursor = body.walk();
    let first = body.named_children(&mut body_cursor).next()?;
    if first.kind() != "expression_statement" {
        return None;
    }
    let mut expression_cursor = first.walk();
    let mut expressions = first.named_children(&mut expression_cursor);
    let expression = expressions.next()?;
    if expressions.next().is_some() {
        return None;
    }
    Some(expression)
}
/// 判断表达式是否为 Python 语言级常量字符串
fn python_language_string_expression(node: Node<'_>, source: &[u8]) -> bool {
    match node.kind() {
        "string" => python_string_literal_is_text(node, source),
        "concatenated_string" => {
            let mut cursor = node.walk();
            let children: Vec<_> = node.named_children(&mut cursor).collect();
            !children.is_empty()
                && children.iter().all(|child| {
                    child.kind() == "string"
                        && python_string_literal_is_text(*child, source)
                })
        }
        "parenthesized_expression" => {
            let mut cursor = node.walk();
            let mut children = node.named_children(&mut cursor);
            let Some(child) = children.next() else {
                return false;
            };
            children.next().is_none()
                && python_language_string_expression(child, source)
        }
        _ => false,
    }
}
/// 判断 Python string token 是否产生 str 而非 bytes 或 f-string
fn python_string_literal_is_text(node: Node<'_>, source: &[u8]) -> bool {
    let Ok(text) = node.utf8_text(source) else {
        return false;
    };
    let prefix = text
        .trim_start()
        .chars()
        .take_while(|character| !matches!(character, '\'' | '"'))
        .collect::<String>()
        .to_ascii_lowercase();
    !prefix.contains(['b', 'f'])
}
/// 读取紧邻 Rust 声明的外层文档注释
fn preceding_rustdoc(
    source: &[u8],
    attribute: &RustAttributeFacts<'_>,
) -> Option<String> {
    let candidate = attribute.preceding?;
    if !source_gap_is_whitespace(
        candidate.end_byte(),
        attribute.attachment_start,
        source,
    ) {
        return None;
    }
    let text = candidate.utf8_text(source).ok()?;
    if candidate.kind() == "block_comment" {
        return rust_outer_block_documentation_opener_is_exact(text)
            .then(|| text.to_owned());
    }
    if candidate.kind() != "line_comment"
        || !text.starts_with("///")
        || text.starts_with("////")
    {
        return None;
    }
    let mut comments = vec![text.trim_end_matches(['\r', '\n']).to_owned()];
    let mut next_start = candidate.start_byte();
    let mut sibling = candidate.prev_named_sibling();
    while let Some(comment) = sibling {
        let Ok(text) = comment.utf8_text(source) else {
            break;
        };
        if comment.kind() != "line_comment"
            || !text.starts_with("///")
            || text.starts_with("////")
            || !source_gap_is_whitespace(
                comment.end_byte(),
                next_start,
                source,
            )
        {
            break;
        }
        comments.push(text.trim_end_matches(['\r', '\n']).to_owned());
        next_start = comment.start_byte();
        sibling = comment.prev_named_sibling();
    }
    comments.reverse();
    Some(comments.join("\n"))
}
/// 判断 Rust outer block rustdoc 是否使用精确开头
fn rust_outer_block_documentation_opener_is_exact(text: &str) -> bool {
    text.strip_prefix("/**")
        .is_some_and(|body| !body.starts_with(['*', '/']))
}
/// 判断两个 CST token 之间是否只有空白
fn source_gap_is_whitespace(start: usize, end: usize, source: &[u8]) -> bool {
    source
        .get(start..end)
        .is_some_and(|gap| gap.iter().all(u8::is_ascii_whitespace))
}
/// 读取紧邻 C/C++ 声明的规范文档块
fn preceding_controlled_block(
    node: Node<'_>,
    source: &[u8],
) -> Option<String> {
    let candidate = node.prev_named_sibling()?;
    if candidate.kind() != "comment"
        || !source_gap_is_whitespace(
            candidate.end_byte(),
            node.start_byte(),
            source,
        )
    {
        return None;
    }
    let carrier = candidate.utf8_text(source).ok()?;
    let lines: Vec<_> = carrier.lines().collect();
    if lines.len() < 3
        || lines.first().is_none_or(|line| line.trim() != "/**")
        || lines.last().is_none_or(|line| line.trim() != "*/")
    {
        return None;
    }
    Some(carrier.to_owned())
}
/// 保存去除 carrier decoration 后的正文及其原始缩进前缀
struct DocumentationLine<'carrier> {
    text: &'carrier str,
    left_padding: &'carrier str,
}

/// 分离有效正文的首尾空白与 carrier-relative 缩进
fn documentation_line(line: &str) -> Option<DocumentationLine<'_>> {
    let text = line.trim();
    (!matches!(text, "\"\"\"" | "/**" | "*/" | "/")).then_some(
        DocumentationLine {
            text,
            left_padding: &line[..line.len() - line.trim_start().len()],
        },
    )
}

/// 返回保留 carrier-relative 缩进的文档正文行
fn documentation_lines(
    language: Language,
    carrier: &str,
) -> Vec<DocumentationLine<'_>> {
    match profile_law(language.key()).documentation.carrier {
        DocumentationCarrierLaw::PythonSuite => {
            carrier.lines().filter_map(documentation_line).collect()
        }
        DocumentationCarrierLaw::RustOuter => {
            rust_documentation_lines(carrier)
        }
        DocumentationCarrierLaw::NativeAdjacent => {
            native_family_documentation_lines(carrier)
        }
    }
}
/// 去除 C 家族 carrier decoration 并保留正文缩进
fn native_family_documentation_lines(
    carrier: &str,
) -> Vec<DocumentationLine<'_>> {
    carrier
        .lines()
        .filter_map(|line| {
            let decoration = line.trim_start();
            let content = decoration.strip_prefix('*').unwrap_or(decoration);
            let content = content.strip_prefix(' ').unwrap_or(content);
            documentation_line(content)
        })
        .collect()
}
/// 去除 Rust outer rustdoc decoration 并保留正文缩进
fn rust_documentation_lines(carrier: &str) -> Vec<DocumentationLine<'_>> {
    if let Some(body) = carrier
        .strip_prefix("/**")
        .and_then(|body| body.strip_suffix("*/"))
    {
        let body = body.strip_prefix(' ').unwrap_or(body);
        let body = body.strip_suffix(' ').unwrap_or(body);
        return body
            .lines()
            .filter_map(|line| {
                let decoration = line.trim_start_matches([' ', '\t']);
                let content = decoration
                    .strip_prefix('*')
                    .map(|content| {
                        content.strip_prefix(' ').unwrap_or(content)
                    })
                    .unwrap_or(line);
                documentation_line(content)
            })
            .collect();
    }
    carrier
        .lines()
        .filter_map(|line| {
            let content = line.strip_prefix("///").unwrap_or(line);
            documentation_line(content.strip_prefix(' ').unwrap_or(content))
        })
        .collect()
}
/// 判断 Rust Markdown 行是否属于缩进代码块
fn rust_markdown_line_is_indented_code(line: &str) -> bool {
    let mut column = 0_usize;
    for byte in line.bytes() {
        match byte {
            b' ' => column += 1,
            b'\t' => column += 4 - column % 4,
            _ => break,
        }
        if column >= 4 {
            return true;
        }
    }
    false
}
/// 判断文本是否含有至少两个连续中文字符
fn contains_chinese_phrase(text: &str) -> bool {
    let mut consecutive = 0_u8;
    let law = narrative_law();
    for character in text.chars() {
        if law.is_cjk(character) {
            consecutive += 1;
            if consecutive >= law.minimum_cjk_run {
                return true;
            }
        } else {
            consecutive = 0;
        }
    }
    false
}
/// 公开契约内部缺陷种类（私有诊断，不进入公共接口）
enum PublicContractDefect {
    /// 摘要之后缺少规定的空行
    Narrative,
    /// 受控标题多重、失序或存在未归属标题
    RoleOrder,
    /// 角色正文与结构事实不符
    RoleContent { role: &'static str },
    /// 结构化字段的分隔符或填充不符合语言要求
    Delimiter { role: &'static str },
    /// 结构化字段未对齐到规范 identity 与 description 列
    Alignment { role: &'static str },
}

impl PublicContractDefect {
    /// 生成文档违规的具体说明
    fn observation(&self, subject: &str) -> String {
        match self {
            Self::Narrative => format!(
                "observed documentation for {subject} without the mandatory blank line after Summary"
            ),
            Self::RoleOrder => format!(
                "observed controlled headings for {subject} that are duplicated, out of profile order, or unaccounted"
            ),
            Self::RoleContent { role } => format!(
                "observed {role} content for {subject} that does not close against the declared signature"
            ),
            Self::Delimiter { role } => format!(
                "observed {role} structured fields for {subject} whose delimiter or padding violates the profile grammar"
            ),
            Self::Alignment { role } => format!(
                "observed {role} structured fields for {subject} that do not share the canonical identity and description columns"
            ),
        }
    }
}

/// 按语言格式读取字段名称、填充和描述
struct StructuredField<'text> {
    identity: &'text str,
    padding: &'text str,
    description: &'text str,
}

/// 校验一个结构化角色的分隔符邻接与最短规范对齐
///
/// 在此统一切分字段；空值与 Rust `- 不返回` 不参与对齐
fn structured_field_defect(
    callable: &Callable,
    role: DocumentationRole,
    role_label: &'static str,
    content: &[&DocumentationLine<'_>],
    empty_role: &str,
) -> Option<PublicContractDefect> {
    let law = &profile_law(callable.language.key()).documentation.fields;
    if !law.roles.contains(&role)
        || content.len() == 1 && content[0].text == empty_role
    {
        return None;
    }
    if content
        .windows(2)
        .any(|pair| pair[0].left_padding != pair[1].left_padding)
    {
        return Some(PublicContractDefect::Alignment { role: role_label });
    }
    let delimiter_defect =
        || PublicContractDefect::Delimiter { role: role_label };
    let mut fields = Vec::with_capacity(content.len());
    for line in content {
        let Some((entry, delimiter_index)) =
            line.text.strip_prefix(law.prefix).and_then(|entry| {
                entry.find(law.delimiter).map(|index| (entry, index))
            })
        else {
            return Some(delimiter_defect());
        };
        let identity = &entry[..delimiter_index];
        let tail = &entry[delimiter_index + law.delimiter.len_utf8()..];
        let padding_end = tail
            .find(|character: char| !character.is_whitespace())
            .unwrap_or(tail.len());
        let field = StructuredField {
            identity,
            padding: &tail[..padding_end],
            description: &tail[padding_end..],
        };
        if law.exact_identity
            && (field.identity.is_empty()
                || field.identity.trim() != field.identity)
            || field.padding.is_empty()
            || !field
                .padding
                .chars()
                .all(|character| character == law.padding)
            || law.require_description && field.description.is_empty()
        {
            return Some(delimiter_defect());
        }
        if !contains_chinese_phrase(field.description) {
            return Some(PublicContractDefect::RoleContent {
                role: role_label,
            });
        }
        fields.push(field);
    }
    let expected_names: &[String] = match role {
        DocumentationRole::TemplateParameters => &callable.template_parameters,
        DocumentationRole::Arguments => &callable.parameters,
        _ => &[],
    };
    if !expected_names.is_empty() {
        let observed: BTreeSet<_> =
            fields.iter().map(|field| field.identity).collect();
        if fields.len() != expected_names.len()
            || observed.len() != expected_names.len()
            || expected_names
                .iter()
                .any(|name| !observed.contains(name.as_str()))
        {
            return Some(PublicContractDefect::RoleContent {
                role: role_label,
            });
        }
    }
    let target_width = fields
        .iter()
        .map(|field| field.identity.chars().count())
        .max()?
        + law.alignment_gap;
    fields.into_iter().find_map(|field| {
        let expected = target_width - field.identity.chars().count();
        let observed = field.padding.chars().count();
        (expected != observed)
            .then_some(PublicContractDefect::Alignment { role: role_label })
    })
}

/// 检查公开文档的标题、布局和字段内容
fn public_contract_is_complete(
    callable: &Callable,
    lines: &[DocumentationLine<'_>],
) -> Result<(), PublicContractDefect> {
    let profile = profile_law(callable.language.key());
    let contract = &profile.documentation;
    // 按当前函数的要求逐项核对标题及其顺序
    // 未知标题不能因位于叙述区或文档尾部而跳过检查
    // Rust 的 # Panics 可选，# Safety 按函数安全要求判断
    // 其他语言使用各自固定的标题
    let required = |heading: &&crate::authority::HeadingLaw| match heading.1 {
        DocumentationRole::Arguments
        | DocumentationRole::Returns
        | DocumentationRole::Failures => true,
        DocumentationRole::TemplateParameters => {
            callable.requires_template_parameters
        }
        DocumentationRole::Effect => callable.requires_effect,
        DocumentationRole::Panics => {
            lines.iter().any(|line| line.text == heading.0)
        }
        DocumentationRole::Safety => {
            callable.requires_safety
                && lines.iter().any(|line| line.text == heading.0)
        }
        DocumentationRole::Ownership => false,
    };
    let empty_role = contract.empty_role;
    let mut expected = contract.headings.iter().filter(required);
    let mut sections = Vec::new();
    for (index, line) in lines
        .iter()
        .enumerate()
        .filter(|(_, line)| profile.is_documentation_heading(line.text))
    {
        let Some(heading) = expected.next() else {
            return Err(PublicContractDefect::RoleOrder);
        };
        if line.text != heading.0 {
            return Err(PublicContractDefect::RoleOrder);
        }
        sections.push((index, heading.0, heading.1));
    }
    if expected.next().is_some() {
        return Err(PublicContractDefect::RoleOrder);
    }
    let Some(summary) = lines.iter().position(|line| !line.text.is_empty())
    else {
        return Err(PublicContractDefect::RoleContent { role: "Summary" });
    };
    let gap = narrative_law().blank_lines_after_summary;
    let observed_gap = lines[summary + 1..]
        .iter()
        .take_while(|line| line.text.is_empty())
        .count();
    if observed_gap != gap {
        return Err(PublicContractDefect::Narrative);
    }
    // 摘要后的规定空行与首个标题之间不检查中文、句号和对齐
    // 其中被识别为标题的行仍由上方标题检查处理
    // 不能用叙述区隐藏不允许的标题
    for (position, &(start, label, role)) in sections.iter().enumerate() {
        let end = sections
            .get(position + 1)
            .map_or(lines.len(), |section| section.0);
        let body = &lines[start + 1..end];
        let content: Vec<_> =
            body.iter().filter(|line| !line.text.is_empty()).collect();
        if content.is_empty() {
            return Err(PublicContractDefect::RoleContent { role: label });
        }
        if let Some(defect) = structured_field_defect(
            callable, role, label, &content, empty_role,
        ) {
            return Err(defect);
        }
        if !documentation_role_is_complete(
            callable, role, &content, empty_role,
        ) {
            return Err(PublicContractDefect::RoleContent { role: label });
        }
    }
    Ok(())
}
/// 根据声明事实检查单个公开文档字段
fn documentation_role_is_complete(
    callable: &Callable,
    role: DocumentationRole,
    content: &[&DocumentationLine<'_>],
    empty_role: &str,
) -> bool {
    let profile = profile_law(callable.language.key());
    let return_law = &profile.return_surface;
    let structured = profile.documentation.fields.roles.contains(&role);
    let is_valid = |line: &str| {
        structured
            || controlled_description(callable.language, line)
                .is_some_and(contains_chinese_phrase)
    };
    let has_empty = content.iter().any(|line| line.text == empty_role);
    let single_empty = content.len() == 1 && content[0].text == empty_role;
    if has_empty && !single_empty {
        return false;
    }
    match role {
        DocumentationRole::Arguments if callable.parameters.is_empty() => {
            single_empty
        }
        DocumentationRole::TemplateParameters
        | DocumentationRole::Arguments => !has_empty,
        DocumentationRole::Returns => match callable.return_shape {
            ReturnShape::NoValue => single_empty,
            ReturnShape::Never => {
                return_law.never_documentation.is_some_and(|expected| {
                    content.len() == 1 && content[0].text == expected
                })
            }
            ReturnShape::Value => {
                !has_empty && content.iter().all(|line| is_valid(line.text))
            }
            ReturnShape::Unknown => !return_law.unknown_blocks_documentation,
        },
        DocumentationRole::Failures => content
            .iter()
            .all(|line| line.text == empty_role || is_valid(line.text)),
        DocumentationRole::Effect
        | DocumentationRole::Panics
        | DocumentationRole::Safety => {
            !has_empty && content.iter().all(|line| is_valid(line.text))
        }
        DocumentationRole::Ownership => false,
    }
}
/// 检查 Rust 安全文档的标题顺序和正文
fn rust_safety_contract_is_complete(lines: &[DocumentationLine<'_>]) -> bool {
    let profile = profile_law(Language::Rust.key());
    let mut previous = None;
    let mut safety = None;
    for (index, line) in lines.iter().enumerate() {
        if !profile.is_documentation_heading(line.text) {
            continue;
        }
        let Some((rank, heading)) = profile
            .documentation
            .headings
            .iter()
            .enumerate()
            .find(|(_, heading)| line.text == heading.0)
        else {
            return false;
        };
        if previous.is_some_and(|prior| rank <= prior) {
            return false;
        }
        previous = Some(rank);
        if heading.1 == DocumentationRole::Safety {
            safety = Some(index);
        }
    }
    let Some(start) = safety else { return false };
    let mut body = lines[start + 1..]
        .iter()
        .take_while(|line| !profile.is_documentation_heading(line.text))
        .filter(|line| !line.text.is_empty());
    body.clone().next().is_some()
        && body.all(|line| {
            controlled_description(Language::Rust, line.text)
                .is_some_and(contains_chinese_phrase)
        })
}
/// 提取受控描述列表的正文
fn controlled_description(language: Language, line: &str) -> Option<&str> {
    if language == Language::Rust && rust_markdown_line_is_indented_code(line)
    {
        return None;
    }
    let law = &profile_law(language.key()).documentation.fields;
    line.strip_prefix(law.prefix)
        .filter(|description| !description.contains(law.delimiter))
}
/// 检查摘要及受控字段是否以禁用句号结束
fn controlled_line_has_terminator(
    language: Language,
    public: bool,
    requires_safety: bool,
    lines: &[DocumentationLine<'_>],
) -> bool {
    let profile = profile_law(language.key());
    let summary =
        profile.documentation_summary(lines.iter().map(|line| line.text));
    if summary.is_some_and(|line| {
        !(profile.is_documentation_heading(line)
            || language == Language::Rust
                && rust_markdown_line_is_indented_code(line))
            && ends_in_sentence_terminator(line)
    }) {
        return true;
    }
    if !(public || language == Language::Rust && requires_safety) {
        return false;
    }
    let mut controlled = None;
    lines.iter().any(|line| {
        if profile.is_documentation_heading(line.text) {
            controlled = profile
                .documentation
                .headings
                .iter()
                .find(|heading| line.text == heading.0)
                .map(|heading| heading.1)
                .filter(|role| {
                    public
                        || requires_safety
                            && *role == DocumentationRole::Safety
                });
            return false;
        }
        controlled.is_some_and(|role| {
            let law = &profile.documentation.fields;
            let is_controlled = if law.roles.contains(&role) {
                !(language == Language::Rust
                    && rust_markdown_line_is_indented_code(line.text))
                    && line.text.starts_with(law.prefix)
                    && line.text.contains(law.delimiter)
            } else {
                controlled_description(language, line.text).is_some()
            };
            is_controlled && ends_in_sentence_terminator(line.text)
        })
    })
}
/// 判断文本末尾是否为禁用句号
fn ends_in_sentence_terminator(line: &str) -> bool {
    line.trim_end()
        .ends_with(narrative_law().forbidden_terminators)
}
/// 将源码拒绝原因记录为规则问题和相关事实类别的受阻原因
fn close_source_rejection(
    document: &OwnedDocument,
    physical_lines: u32,
    evidence: ParseEvidence,
) -> (Vec<Finding>, FamilyClosure) {
    let method = &profile_law(document.language.key()).observation_method;
    let reason = format!(
        "observation method {method} rejected source at {}:{}: {}",
        evidence.line, evidence.column, evidence.reason
    );
    let mut findings = FindingState::new(&document.path);
    findings.push(
        RuleOperator::SourceParseability,
        evidence.line,
        evidence.column,
        "<source>",
        &reason,
    );
    (
        findings.complete(),
        FamilyClosure::SourceRejected {
            physical_lines,
            reason,
        },
    )
}
/// 按等级、位置和规则比较审查问题的顺序
fn finding_order(left: &Finding, right: &Finding) -> std::cmp::Ordering {
    (
        left.grade,
        &left.path,
        left.line,
        left.column,
        &left.rule,
        &left.subject,
    )
        .cmp(&(
            right.grade,
            &right.path,
            right.line,
            right.column,
            &right.rule,
            &right.subject,
        ))
}
/// 汇总文件证据并封存审查结果
fn seal(
    authority: &CompiledAuthority,
    scope: ReviewedScope,
    results: Vec<FileResult>,
    metrics: ReviewMetrics,
) -> ReviewTerminal {
    let mut snapshot_hasher = blake3::Hasher::new();
    let mut findings = Vec::new();
    let mut files = Vec::new();
    for result in results {
        snapshot_hasher.update(result.coverage.path.as_bytes());
        snapshot_hasher.update(&[0]);
        snapshot_hasher.update(&result.snapshot_digest);
        findings.extend(result.findings);
        files.push(result.coverage);
    }
    findings.sort_by(finding_order);
    let snapshot_digest = snapshot_hasher.finalize().to_hex().to_string();
    let semantic_authority_digest =
        blake3::Hash::from_bytes(authority.semantic_digest())
            .to_hex()
            .to_string();
    let coverage = CompactCoverage { files };
    let seal = compute_seal(
        &semantic_authority_digest,
        &snapshot_digest,
        &scope,
        &coverage,
        &findings,
    );
    ReviewTerminal::Sealed(SealedReview {
        scope,
        coverage,
        findings,
        metrics,
        semantic_authority_digest,
        snapshot_digest,
        seal,
        presentation: authority.presentation().clone(),
    })
}
/// 根据输入身份和审查证据计算封存摘要
fn compute_seal(
    semantic_authority_digest: &str,
    snapshot_digest: &str,
    scope: &ReviewedScope,
    coverage: &CompactCoverage,
    findings: &[Finding],
) -> String {
    let mut hasher = blake3::Hasher::new();
    hasher.update(b"csu-seal-standard-law\0");
    hasher.update(&REVIEW_SCHEMA_VERSION.to_le_bytes());
    hash_string(&mut hasher, semantic_authority_digest);
    hash_string(&mut hasher, snapshot_digest);
    match scope {
        ReviewedScope::Documents { revision, files } => {
            hasher.update(&[0]);
            hash_string(&mut hasher, revision);
            hash_strings(&mut hasher, files);
        }
        ReviewedScope::Workspace { root, files } => {
            hasher.update(&[1]);
            hash_string(&mut hasher, root);
            hash_strings(&mut hasher, files);
        }
    }
    hasher.update(&[coverage.completion() as u8]);
    hasher.update(&(coverage.files.len() as u64).to_le_bytes());
    for file in &coverage.files {
        hash_string(&mut hasher, &file.path);
        hasher.update(&(file.families.len() as u64).to_le_bytes());
        for (family, state) in &file.families {
            hasher.update(&[*family as u8]);
            match state {
                FactFamilyState::Complete(count) => {
                    hasher.update(&[0]);
                    hasher.update(&count.to_le_bytes());
                }
                FactFamilyState::Blocked(reason) => {
                    hasher.update(&[1]);
                    hash_string(&mut hasher, reason)
                }
            };
        }
    }
    hasher.update(&(findings.len() as u64).to_le_bytes());
    for finding in findings {
        hash_string(&mut hasher, &finding.rule);
        hasher.update(&[finding.grade as u8]);
        hash_string(&mut hasher, &finding.path);
        hasher.update(&(finding.line as u64).to_le_bytes());
        hasher.update(&(finding.column as u64).to_le_bytes());
        hash_string(&mut hasher, &finding.subject);
        hash_string(&mut hasher, &finding.observation);
        match &finding.question {
            Some(question) => {
                hasher.update(&[1]);
                hash_string(&mut hasher, question);
            }
            None => {
                hasher.update(&[0]);
            }
        }
        hash_string(&mut hasher, &finding.message);
    }
    hasher.finalize().to_hex().to_string()
}
/// 将字符串数量和各项内容写入摘要计算
fn hash_strings(hasher: &mut blake3::Hasher, values: &[String]) {
    hasher.update(&(values.len() as u64).to_le_bytes());
    for value in values {
        hash_string(hasher, value);
    }
}
/// 将字符串长度和字节写入摘要计算
fn hash_string(hasher: &mut blake3::Hasher, value: &str) {
    hasher.update(&(value.len() as u64).to_le_bytes());
    hasher.update(value.as_bytes());
}
