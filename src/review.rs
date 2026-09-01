use crate::authority::CompiledAuthority;
use crate::authority::ProjectionState;
use crate::authority::ReviewRejection;
use crate::authority::RuleOperator;
use crate::authority::SourceForm;
use crate::authority::normalize_relative_path;
use crate::model::CompactCoverage;
use crate::model::Completion;
use crate::model::FactFamily;
use crate::model::FactFamilyState;
use crate::model::FileCoverage;
use crate::model::Finding;
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
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Language {
    Python,
    Rust,
    ProceduralSource,
    Cplusplus,
}

impl Language {
    /// 执行 `key` 内部逻辑
    fn key(self) -> &'static str {
        match self {
            Self::Python => "python",
            Self::Rust => "rust",
            Self::ProceduralSource => "c",
            Self::Cplusplus => "cpp",
        }
    }
}

#[derive(Clone, Debug)]
struct OwnedDocument {
    path: String,
    bytes: Vec<u8>,
    language: Language,
    capture_error: Option<String>,
}

type CaptureResult = Result<
    (ReviewedScope, Vec<OwnedDocument>, ReviewMetrics),
    ReviewRejection,
>;

#[derive(Debug)]
struct FileResult {
    path: String,
    findings: Vec<Finding>,
    required_mask: u8,
    families: [FactFamilyState; 7],
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

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum DocumentationVisibility {
    Public,
    Internal,
    Unresolved,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum DocumentationRole {
    TemplateParameters,
    Arguments,
    Returns,
    Failures,
    Effect,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ReturnShape {
    NoValue,
    Never,
    Value,
    Unknown,
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
}

#[derive(Debug)]
struct LocalFacts {
    callables: Vec<Callable>,
    declarations: Vec<Declaration>,
    python_module_docstring: Option<(usize, usize)>,
    dependencies: DependencyFacts,
}

#[derive(Debug)]
struct ParseEvidence {
    line: usize,
    column: usize,
    reason: &'static str,
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

/// 执行 `review` 内部逻辑
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

/// 执行 `capture` 内部逻辑
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
                let path = normalize_relative_path(document.relative_path)?;
                if !paths.insert(path.clone()) {
                    return Err(ReviewRejection::new(
                        "request.path",
                        format!("duplicate document path {path}"),
                    ));
                }
                let Some(language) = language_for_document(authority, &path)?
                else {
                    return Err(ReviewRejection::new(
                        "request.language",
                        format!("document language is not governed: {path}"),
                    ));
                };
                documents.push(OwnedDocument {
                    path,
                    bytes: document.bytes.to_vec(),
                    language,
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

/// 执行 `capture_workspace` 内部逻辑
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
    let inventory_path = canonical.join(".csu-inventory.json");
    if inventory_path.is_file() {
        return capture_manifest_workspace(&canonical, &inventory_path);
    }
    let mut inventory = Vec::new();
    for entry in WalkDir::new(&canonical)
        .follow_links(false)
        .sort_by_file_name()
    {
        let entry = entry.map_err(|error| {
            ReviewRejection::new("request.inventory", error.to_string())
        })?;
        if !entry.file_type().is_file() {
            continue;
        }
        let relative =
            entry.path().strip_prefix(&canonical).map_err(|_| {
                ReviewRejection::new(
                    "request.path",
                    "inventoried file escaped workspace",
                )
            })?;
        let path = normalize_relative_path(&relative.to_string_lossy())?;
        let language = match language_for_document(authority, &path) {
            Ok(Some(language)) => language,
            Ok(None) => continue,
            Err(rejection) => return Err(rejection),
        };
        inventory.push((path, entry.path().to_path_buf(), language));
    }
    inventory.sort_by(|left, right| left.0.cmp(&right.0));
    let mut documents = Vec::with_capacity(inventory.len());
    for (path, source_path, language) in inventory {
        documents.push(read_document(
            path,
            language,
            Some(&source_path),
            None,
        ));
    }
    close_workspace_capture(&canonical, documents)
}

#[derive(serde::Deserialize)]
struct WorkspaceInventory {
    schema_version: u32,
    entries: Vec<WorkspaceInventoryEntry>,
}

#[derive(serde::Deserialize)]
struct WorkspaceInventoryEntry {
    path: String,
    language: String,
}

/// 执行 `capture_manifest_workspace` 内部逻辑
fn capture_manifest_workspace(
    root: &Path,
    inventory_path: &Path,
) -> CaptureResult {
    let inventory_bytes = fs::read(inventory_path).map_err(|error| {
        ReviewRejection::new(
            "request.inventory",
            format!("cannot read {}: {error}", inventory_path.display()),
        )
    })?;
    let inventory: WorkspaceInventory =
        serde_json::from_slice(&inventory_bytes).map_err(|error| {
            ReviewRejection::new(
                "request.inventory",
                format!("invalid .csu-inventory.json: {error}"),
            )
        })?;
    if inventory.schema_version != 1 {
        return Err(ReviewRejection::new(
            "request.inventory",
            "only workspace inventory schema_version 1 is supported",
        ));
    }
    let mut seen = BTreeSet::new();
    let mut admitted = Vec::with_capacity(inventory.entries.len());
    for entry in inventory.entries {
        let path = normalize_relative_path(&entry.path)?;
        if !seen.insert(path.clone()) {
            return Err(ReviewRejection::new(
                "request.inventory",
                format!("duplicate inventory path {path}"),
            ));
        }
        let language = parse_language(&entry.language)?;
        let source_path = root.join(Path::new(&path));
        admitted.push((path, language, source_path));
    }
    admitted.sort_by(|left, right| left.0.cmp(&right.0));

    let mut prepared = Vec::with_capacity(admitted.len());
    for (path, language, source_path) in admitted {
        let (canonical_source, capture_error) = match source_path
            .canonicalize()
        {
            Ok(canonical_source) if !canonical_source.starts_with(root) => {
                return Err(ReviewRejection::new(
                    "request.path",
                    format!("inventoried source escapes workspace: {path}"),
                ));
            }
            Ok(canonical_source) => (Some(canonical_source), None),
            Err(error) => (
                None,
                Some(format!(
                    "cannot open inventoried source {path}: {error}"
                )),
            ),
        };
        prepared.push((path, language, canonical_source, capture_error));
    }

    let mut documents = Vec::with_capacity(prepared.len());
    for (path, language, canonical_source, prior_error) in prepared {
        documents.push(read_document(
            path,
            language,
            canonical_source.as_deref(),
            prior_error,
        ));
    }
    close_workspace_capture(root, documents)
}

/// 捕获一个已准入文档，保留可审计的读取失败
fn read_document(
    path: String,
    language: Language,
    source_path: Option<&Path>,
    prior_error: Option<String>,
) -> OwnedDocument {
    let (bytes, capture_error) = match source_path {
        Some(source_path) => match fs::read(source_path) {
            Ok(bytes) => (bytes, None),
            Err(error) => (
                Vec::new(),
                Some(format!(
                    "cannot read inventoried source {path}: {error}"
                )),
            ),
        },
        None => (Vec::new(), prior_error),
    };
    OwnedDocument {
        path,
        bytes,
        language,
        capture_error,
    }
}

/// 以唯一顺序封闭工作区捕获范围与读取计数
fn close_workspace_capture(
    root: &Path,
    mut documents: Vec<OwnedDocument>,
) -> CaptureResult {
    documents.sort_by(|left, right| left.path.cmp(&right.path));
    let files = documents.iter().map(|item| item.path.clone()).collect();
    let files_read = documents
        .iter()
        .filter(|document| document.capture_error.is_none())
        .count() as u64;
    Ok((
        ReviewedScope::Workspace {
            root: root.to_string_lossy().replace('\\', "/"),
            files,
        },
        documents,
        ReviewMetrics {
            files_read,
            ..ReviewMetrics::default()
        },
    ))
}

/// 将 captured document 构造为完整文件终态
fn close_file(
    authority: &CompiledAuthority,
    document: &OwnedDocument,
) -> Result<FileResult, ReviewFailure> {
    let snapshot_digest = *blake3::hash(&document.bytes).as_bytes();
    let language = document.language;
    let required_mask = required_family_mask(authority, language);
    let (findings, families, byte_sweeps, structural_parses) =
        if let Some(reason) = &document.capture_error {
            let blocked = || FactFamilyState::Blocked(reason.clone());
            let projection = |family| match authority
                .projection(family, language.key())
            {
                ProjectionState::NotApplicable => FactFamilyState::NotRequired,
                ProjectionState::Supported
                | ProjectionState::NeedsAuthority => blocked(),
            };
            (
                Vec::new(),
                [
                    blocked(),
                    blocked(),
                    blocked(),
                    projection("identifier"),
                    projection("documentation"),
                    if authority.families.contains("dependency") {
                        projection("dependency")
                    } else {
                        FactFamilyState::NotRequired
                    },
                    FactFamilyState::NotRequired,
                ],
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
            let (findings, families) = match observation {
                StructuralObservation::Complete(facts) => {
                    close_complete_source(
                        authority,
                        document,
                        physical_lines,
                        facts,
                    )
                }
                StructuralObservation::SourceRejected(evidence) => {
                    close_source_rejection(
                        authority,
                        document,
                        physical_lines,
                        evidence,
                    )
                }
            };
            (findings, families, 1, structural_parses)
        };
    Ok(FileResult {
        path: document.path.clone(),
        findings,
        required_mask,
        families,
        snapshot_digest,
        byte_sweeps,
        structural_parses,
    })
}

/// 对已接受的结构事实执行可满足 Judgment 并闭合事实族
fn close_complete_source(
    authority: &CompiledAuthority,
    document: &OwnedDocument,
    physical_lines: u32,
    facts: LocalFacts,
) -> (Vec<Finding>, [FactFamilyState; 7]) {
    let language = document.language;
    let LocalFacts {
        mut callables,
        declarations,
        python_module_docstring,
        dependencies,
    } = facts;
    resolve_native_public_visibility(
        authority,
        &document.path,
        &mut callables,
    );
    reject_ambiguous_public_callable_identities(&mut callables);
    let documentation_projection =
        authority.projection("documentation", language.key());
    let identifier_projection =
        authority.projection("identifier", language.key());
    let mut findings = Vec::new();
    if let Some((line, column)) = python_module_docstring {
        push_rule_findings(
            authority,
            RuleOperator::DocumentationCarrier,
            &document.path,
            line,
            column,
            "<module>",
            concat!(
                "observed a suite-first constant string expression at ",
                "Python module scope"
            ),
            &mut findings,
        );
    }
    let documentation_block_reason =
        unresolved_documentation_reason(&callables);
    if documentation_projection == ProjectionState::Supported {
        for callable in &callables {
            if callable.carrier_unresolved {
                continue;
            }
            let Some(carrier) = &callable.carrier else {
                push_rule_findings(
                    authority,
                    RuleOperator::DocumentationCarrier,
                    &document.path,
                    callable.line,
                    callable.column,
                    &callable.name,
                    concat!(
                        "the declaration has no directly attached ",
                        "profile-recognized carrier"
                    ),
                    &mut findings,
                );
                continue;
            };
            let lines = documentation_lines(callable.language, carrier);
            if !documentation_has_summary(authority, callable.language, &lines)
            {
                push_documentation_findings(
                    authority,
                    document,
                    callable,
                    RuleOperator::DocumentationSummary,
                    &mut findings,
                );
                continue;
            }
            let has_public_contract = callable.named
                && callable.visibility == DocumentationVisibility::Public;
            let signature_is_resolved = callable.parameters_complete
                && callable.template_parameters_complete
                && callable.return_shape != ReturnShape::Unknown;
            if controlled_line_has_terminator(
                authority,
                callable.language,
                has_public_contract,
                callable.requires_safety,
                &lines,
            ) {
                push_documentation_findings(
                    authority,
                    document,
                    callable,
                    RuleOperator::DocumentationTerminator,
                    &mut findings,
                );
            }
            if has_public_contract
                && signature_is_resolved
                && !public_contract_is_complete(authority, callable, &lines)
            {
                push_documentation_findings(
                    authority,
                    document,
                    callable,
                    RuleOperator::DocumentationPublicContract,
                    &mut findings,
                );
            }
            if callable.requires_safety
                && !rust_safety_contract_is_complete(&lines)
            {
                push_documentation_findings(
                    authority,
                    document,
                    callable,
                    RuleOperator::DocumentationSafety,
                    &mut findings,
                );
            }
        }
    }
    if identifier_projection == ProjectionState::Supported {
        for declaration in &declarations {
            if let Some(operator) =
                judge_identifier(authority, language, declaration)
            {
                push_identifier_findings(
                    authority,
                    document,
                    declaration,
                    operator,
                    &mut findings,
                );
            }
        }
    }
    let dependency =
        judge_dependencies(authority, language, &dependencies, document);
    findings.extend(dependency.findings);
    findings.sort_by(finding_order);
    let identifier_subjects = declarations.len() as u32;
    let identifier_state = match identifier_projection {
        ProjectionState::Supported => {
            FactFamilyState::Complete(identifier_subjects)
        }
        ProjectionState::NotApplicable => FactFamilyState::NotRequired,
        ProjectionState::NeedsAuthority => FactFamilyState::Blocked(
            "Identifier projection requires Authority capability".to_owned(),
        ),
    };
    let documentation_state = if documentation_projection
        == ProjectionState::Supported
        && let Some(reason) = documentation_block_reason
    {
        FactFamilyState::Blocked(reason)
    } else {
        let subjects = callables.len() as u32
            + u32::from(python_module_docstring.is_some());
        match documentation_projection {
            ProjectionState::Supported => FactFamilyState::Complete(subjects),
            ProjectionState::NotApplicable => FactFamilyState::NotRequired,
            ProjectionState::NeedsAuthority => FactFamilyState::Blocked(
                "Documentation projection requires Authority capability"
                    .to_owned(),
            ),
        }
    };
    (
        findings,
        [
            FactFamilyState::Complete(1),
            FactFamilyState::Complete(physical_lines),
            FactFamilyState::Complete(identifier_subjects),
            identifier_state,
            documentation_state,
            dependency.state,
            FactFamilyState::NotRequired,
        ],
    )
}

/// 执行一次结构观察并返回 owned facts 或拒绝证据
fn observe_structure(
    document: &OwnedDocument,
) -> Result<(StructuralObservation, u64), ReviewFailure> {
    if let Err(error) = std::str::from_utf8(&document.bytes) {
        let (line, column) =
            source_line_column(&document.bytes, error.valid_up_to());
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
    let mut callables = Vec::new();
    collect_callables(
        language,
        tree.root_node(),
        &document.bytes,
        false,
        &mut callables,
    );
    let mut declarations = Vec::new();
    collect_declarations(
        language,
        tree.root_node(),
        &document.bytes,
        &mut declarations,
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
    drop(tree);
    Ok((
        StructuralObservation::Complete(LocalFacts {
            callables,
            declarations,
            python_module_docstring,
            dependencies,
        }),
        1,
    ))
}

/// 返回 byte offset 对应的一基源码位置
fn source_line_column(bytes: &[u8], offset: usize) -> (usize, usize) {
    let prefix = &bytes[..offset.min(bytes.len())];
    let line = prefix.iter().filter(|byte| **byte == b'\n').count() + 1;
    let column = prefix
        .iter()
        .rposition(|byte| *byte == b'\n')
        .map_or(prefix.len() + 1, |index| prefix.len() - index);
    (line, column)
}

/// 返回最早 source-order ERROR 或 MISSING node
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

/// 汇总无法闭合的 callable Documentation 事实
fn unresolved_documentation_reason(callables: &[Callable]) -> Option<String> {
    let mut subjects = Vec::new();
    for callable in callables {
        let mut categories = Vec::with_capacity(5);
        if callable.visibility == DocumentationVisibility::Unresolved {
            categories.push("tier");
        }
        if callable.carrier_unresolved {
            categories.push("carrier");
        }
        if callable.named
            && callable.visibility == DocumentationVisibility::Public
            && callable.carrier.is_some()
        {
            if !callable.parameters_complete {
                categories.push("parameters");
            }
            if !callable.template_parameters_complete {
                categories.push("template");
            }
            if callable.return_shape == ReturnShape::Unknown {
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

/// 执行 `reject_ambiguous_public_callable_identities` 内部逻辑
fn reject_ambiguous_public_callable_identities(callables: &mut [Callable]) {
    let mut counts = BTreeMap::new();
    for callable in callables.iter() {
        if matches!(
            callable.language,
            Language::ProceduralSource | Language::Cplusplus
        ) && callable.visibility == DocumentationVisibility::Public
        {
            *counts.entry(callable.name.clone()).or_insert(0_u32) += 1;
        }
    }
    for callable in callables {
        if matches!(
            callable.language,
            Language::ProceduralSource | Language::Cplusplus
        ) && counts.get(&callable.name).is_some_and(|count| *count > 1)
        {
            callable.visibility = DocumentationVisibility::Unresolved;
        }
    }
}

#[derive(Debug)]
struct DependencyResult {
    state: FactFamilyState,
    findings: Vec<Finding>,
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

/// 读取一次 CST 并返回完全自有的依赖事实
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
            collect_dependency_declarations(
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

/// 执行 `judge_dependencies` 内部逻辑
fn judge_dependencies(
    authority: &CompiledAuthority,
    language: Language,
    facts: &DependencyFacts,
    document: &OwnedDocument,
) -> DependencyResult {
    if !authority.families.contains("dependency")
        || !authority.dependency.enabled
    {
        return DependencyResult {
            state: FactFamilyState::NotRequired,
            findings: Vec::new(),
        };
    }
    match authority.projection("dependency", language.key()) {
        ProjectionState::NotApplicable => {
            return DependencyResult {
                state: FactFamilyState::NotRequired,
                findings: Vec::new(),
            };
        }
        ProjectionState::NeedsAuthority => {
            return DependencyResult {
                state: FactFamilyState::Blocked(
                    "Dependency projection requires Authority capability"
                        .to_owned(),
                ),
                findings: Vec::new(),
            };
        }
        ProjectionState::Supported => {}
    }
    let declarations = &facts.declarations;
    let mut findings = Vec::new();
    for declaration in declarations {
        if declaration.wildcard
            && matches!(language, Language::Python | Language::Rust)
        {
            push_dependency_findings(
                authority,
                document,
                declaration,
                RuleOperator::DependencyWildcard,
                &mut findings,
            );
        }
        if !declaration.module_placement_valid {
            push_dependency_findings(
                authority,
                document,
                declaration,
                RuleOperator::DependencyModulePlacement,
                &mut findings,
            );
        }
    }
    let blocked = match language {
        Language::Python if facts.python_has_unhandled_import => Some(
            concat!(
                "Python import outside module scope or exact TYPE_CHECKING ",
                "block needs Authority"
            )
            .to_owned(),
        ),
        Language::Python
            if declarations.iter().any(|item| item.complex_order) =>
        {
            Some(
                concat!(
                    "Python multi-module import statement needs per-module ",
                    "dependency facts"
                )
                .to_owned(),
            )
        }
        Language::Python
            if declarations.iter().any(|item| {
                classify_python_dependency(authority, &item.key).is_none()
            }) =>
        {
            Some(
                "Python dependency classification is absent from Authority"
                    .to_owned(),
            )
        }
        Language::Python => {
            if authority.dependency.python_reorder_safe {
                check_python_dependency_order(
                    authority,
                    declarations,
                    document,
                    &mut findings,
                );
            }
            None
        }
        Language::Rust
            if declarations.iter().any(|item| item.complex_order) =>
        {
            Some(
                concat!(
                    "Rust nested use-list ordering needs a frozen comparator ",
                    "capability"
                )
                .to_owned(),
            )
        }
        Language::Rust => {
            if authority.dependency.rust_reorder_safe {
                check_rust_dependency_order(
                    authority,
                    declarations,
                    document,
                    &mut findings,
                );
            }
            None
        }
        Language::ProceduralSource | Language::Cplusplus
            if !declarations.is_empty() =>
        {
            Some(
                concat!(
                    "C/C++ dependency target or preprocessing capability is ",
                    "absent from Authority"
                )
                .to_owned(),
            )
        }
        Language::ProceduralSource | Language::Cplusplus => None,
    };
    DependencyResult {
        state: blocked.map_or_else(
            || FactFamilyState::Complete(declarations.len() as u32),
            FactFamilyState::Blocked,
        ),
        findings,
    }
}

/// 执行 `has_unhandled_python_import` 内部逻辑
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

/// 执行 `collect_python_dependency_declarations` 内部逻辑
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

/// 执行 `take_group` 内部逻辑
fn take_group(next_group: &mut u32) -> u32 {
    let group = *next_group;
    *next_group += 1;
    group
}

/// 执行 `collect_rust_dependency_declarations` 内部逻辑
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

/// 执行 `collect_dependency_declarations` 内部逻辑
fn collect_dependency_declarations(
    language: Language,
    node: Node<'_>,
    source: &[u8],
    output: &mut Vec<DependencyDeclaration>,
) {
    let relevant = match language {
        Language::Python => {
            matches!(node.kind(), "import_statement" | "import_from_statement")
        }
        Language::Rust => node.kind() == "use_declaration",
        Language::ProceduralSource | Language::Cplusplus => {
            node.kind() == "preproc_include"
        }
    };
    if relevant {
        push_dependency_declaration(language, node, source, 0, output);
        return;
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        collect_dependency_declarations(language, child, source, output);
    }
}

/// 执行 `push_dependency_declaration` 内部逻辑
fn push_dependency_declaration(
    language: Language,
    node: Node<'_>,
    source: &[u8],
    group_identity: u32,
    output: &mut Vec<DependencyDeclaration>,
) {
    let Ok(text) = node.utf8_text(source) else {
        return;
    };
    let key = dependency_key(language, text);
    let point = node.start_position();
    output.push(DependencyDeclaration {
        key,
        line: point.row + 1,
        column: point.column + 1,
        start_byte: node.start_byte(),
        end_byte: node.end_byte(),
        group_identity,
        preceding_blank_lines: 0,
        wildcard: match language {
            Language::Python | Language::Rust => {
                dependency_node_has_token(node, "*")
            }
            Language::ProceduralSource | Language::Cplusplus => false,
        },
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

/// 执行 `collect_cplusplus_module_declarations` 内部逻辑
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

/// 执行 `cplusplus_module_node` 内部逻辑
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

/// 执行 `collect_nested_cplusplus_imports` 内部逻辑
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

/// 执行 `push_cplusplus_module_import` 内部逻辑
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

/// 执行 `dependency_key` 内部逻辑
fn dependency_key(language: Language, text: &str) -> String {
    let text = text.trim();
    match language {
        Language::Python => {
            if let Some(rest) = text.strip_prefix("from ") {
                rest.split_whitespace()
                    .next()
                    .unwrap_or_default()
                    .to_owned()
            } else {
                text.strip_prefix("import ")
                    .unwrap_or(text)
                    .split([',', ' '])
                    .next()
                    .unwrap_or_default()
                    .to_owned()
            }
        }
        Language::Rust => text
            .strip_prefix("pub ")
            .unwrap_or(text)
            .strip_prefix("use ")
            .unwrap_or(text)
            .trim_end_matches(';')
            .to_owned(),
        Language::ProceduralSource | Language::Cplusplus => text.to_owned(),
    }
}

/// 执行 `classify_python_dependency` 内部逻辑
fn classify_python_dependency(
    authority: &CompiledAuthority,
    key: &str,
) -> Option<u8> {
    let root = key.split('.').next().unwrap_or(key);
    if authority
        .dependency
        .python_standard_library
        .iter()
        .any(|module| module == root)
    {
        Some(0)
    } else if authority
        .dependency
        .python_third_party
        .iter()
        .any(|module| module == root)
    {
        Some(1)
    } else if authority
        .dependency
        .python_project_roots
        .iter()
        .any(|module| module == root)
    {
        Some(2)
    } else {
        None
    }
}

/// 执行 `check_python_dependency_order` 内部逻辑
fn check_python_dependency_order(
    authority: &CompiledAuthority,
    declarations: &[DependencyDeclaration],
    document: &OwnedDocument,
    findings: &mut Vec<Finding>,
) {
    for pair in declarations.windows(2) {
        let left = &pair[0];
        let right = &pair[1];
        if left.group_identity != right.group_identity {
            continue;
        }
        let left_tier = classify_python_dependency(authority, &left.key);
        let right_tier = classify_python_dependency(authority, &right.key);
        let out_of_order = left_tier > right_tier
            || (left_tier == right_tier && left.key > right.key);
        let tier_changed = left_tier != right_tier;
        let spacing_invalid = if tier_changed {
            right.preceding_blank_lines != 1
        } else {
            right.preceding_blank_lines != 0
        };
        if out_of_order || spacing_invalid {
            push_dependency_findings(
                authority,
                document,
                right,
                RuleOperator::DependencyOrder,
                findings,
            );
        }
    }
}

/// 执行 `check_rust_dependency_order` 内部逻辑
fn check_rust_dependency_order(
    authority: &CompiledAuthority,
    declarations: &[DependencyDeclaration],
    document: &OwnedDocument,
    findings: &mut Vec<Finding>,
) {
    for pair in declarations.windows(2) {
        let left = &pair[0];
        let right = &pair[1];
        if left.group_identity == right.group_identity
            && (right.preceding_blank_lines != 0
                || rust_dependency_compare(&left.key, &right.key).is_gt())
        {
            push_dependency_findings(
                authority,
                document,
                right,
                RuleOperator::DependencyOrder,
                findings,
            );
        }
    }
}

/// 执行 `rust_dependency_compare` 内部逻辑
fn rust_dependency_compare(left: &str, right: &str) -> std::cmp::Ordering {
    /// 执行 `root_rank` 内部逻辑
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

/// 执行 `blank_lines_between` 内部逻辑
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

/// 执行 `version_compare` 内部逻辑
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

/// 执行 `take_digits` 内部逻辑
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

/// 将依赖判定映射为 Authority 拥有的 Finding
fn push_dependency_findings(
    authority: &CompiledAuthority,
    document: &OwnedDocument,
    declaration: &DependencyDeclaration,
    operator: RuleOperator,
    findings: &mut Vec<Finding>,
) {
    push_rule_findings(
        authority,
        operator,
        &document.path,
        declaration.line,
        declaration.column,
        &declaration.key,
        &format!("observed direct dependency declaration {}", declaration.key),
        findings,
    );
}

/// 执行 `collect_declarations` 内部逻辑
fn collect_declarations(
    language: Language,
    node: Node<'_>,
    source: &[u8],
    output: &mut Vec<Declaration>,
) {
    match language {
        Language::Python => match node.kind() {
            "function_definition" | "class_definition" => {
                let role = if node.kind() == "function_definition" {
                    IdentifierRole::Function
                } else {
                    IdentifierRole::Type
                };
                push_named_declaration(
                    Language::Python,
                    node.child_by_field_name("name"),
                    source,
                    role,
                    output,
                );
                if let Some(parameters) =
                    node.child_by_field_name("type_parameters")
                {
                    push_python_type_parameters(parameters, source, output);
                }
                if let Some(parameters) =
                    node.child_by_field_name("parameters")
                {
                    push_python_parameter_identifiers(
                        parameters,
                        source,
                        python_receiver_spelling(node, source),
                        output,
                    );
                }
            }
            "assignment" | "augmented_assignment" => {
                if let Some(left) = node.child_by_field_name("left") {
                    let role = if node.kind() == "assignment"
                        && python_is_module_assignment(node)
                    {
                        IdentifierRole::ModuleBinding
                    } else {
                        IdentifierRole::Value
                    };
                    push_python_binding_target(left, source, role, output);
                }
            }
            "for_statement" | "for_in_clause" => {
                if let Some(left) = node.child_by_field_name("left") {
                    push_python_binding_target(
                        left,
                        source,
                        IdentifierRole::Value,
                        output,
                    );
                }
            }
            "as_pattern_target" => {
                let mut cursor = node.walk();
                let name = node
                    .named_children(&mut cursor)
                    .find(|child| child.kind() == "identifier");
                push_named_declaration(
                    Language::Python,
                    name,
                    source,
                    IdentifierRole::Value,
                    output,
                );
            }
            "named_expression" => {
                push_named_declaration(
                    Language::Python,
                    node.child_by_field_name("name"),
                    source,
                    IdentifierRole::Value,
                    output,
                );
            }
            "aliased_import" => {
                push_named_declaration(
                    Language::Python,
                    node.child_by_field_name("alias"),
                    source,
                    IdentifierRole::Alias,
                    output,
                );
            }
            "case_pattern" => push_python_case_bindings(node, source, output),
            "lambda" => {
                if let Some(parameters) =
                    node.child_by_field_name("parameters")
                {
                    push_python_parameter_identifiers(
                        parameters, source, None, output,
                    );
                }
            }
            "type_alias_statement" => {
                if let Some(left) = node.child_by_field_name("left") {
                    push_python_type_alias(left, source, output);
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
                    "const_item" | "static_item" => IdentifierRole::Constant,
                    "mod_item" => IdentifierRole::ModuleNamespace,
                    _ => unreachable!("closed Rust item role"),
                };
                if !rust_external_trait_method_has_fixed_name(node, source) {
                    push_named_declaration(
                        Language::Rust,
                        node.child_by_field_name("name"),
                        source,
                        role,
                        output,
                    );
                }
                if matches!(
                    node.kind(),
                    "function_item" | "function_signature_item"
                ) && let Some(parameters) =
                    node.child_by_field_name("parameters")
                {
                    push_rust_parameter_identifiers(
                        parameters, source, output,
                    );
                }
            }
            "field_declaration" => {
                push_named_declaration(
                    Language::Rust,
                    node.child_by_field_name("name"),
                    source,
                    IdentifierRole::Value,
                    output,
                );
            }
            "enum_variant" => {
                push_named_declaration(
                    Language::Rust,
                    node.child_by_field_name("name"),
                    source,
                    IdentifierRole::Variant,
                    output,
                );
            }
            "type_parameter" => {
                push_named_declaration(
                    Language::Rust,
                    node.child_by_field_name("name"),
                    source,
                    IdentifierRole::Type,
                    output,
                );
            }
            "const_parameter" => {
                push_named_declaration(
                    Language::Rust,
                    node.child_by_field_name("name"),
                    source,
                    IdentifierRole::Constant,
                    output,
                );
            }
            "lifetime_parameter" => {
                push_named_declaration(
                    Language::Rust,
                    node.child_by_field_name("name"),
                    source,
                    IdentifierRole::Lifetime,
                    output,
                );
            }
            "use_as_clause" => {
                push_named_declaration(
                    Language::Rust,
                    node.child_by_field_name("alias"),
                    source,
                    IdentifierRole::Alias,
                    output,
                );
            }
            "extern_crate_declaration" => {
                push_named_declaration(
                    Language::Rust,
                    node.child_by_field_name("alias"),
                    source,
                    IdentifierRole::ModuleNamespace,
                    output,
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
                push_named_declaration(
                    Language::Rust,
                    Some(node),
                    source,
                    IdentifierRole::Label,
                    output,
                );
            }
            "let_declaration" => {
                if let Some(pattern) = node.child_by_field_name("pattern") {
                    push_rust_binding_pattern(pattern, source, output);
                }
            }
            "let_condition" | "for_expression" => {
                if let Some(pattern) = node.child_by_field_name("pattern") {
                    push_rust_binding_pattern(pattern, source, output);
                }
            }
            "match_arm" => {
                if let Some(pattern) = node.child_by_field_name("pattern") {
                    push_rust_binding_pattern(pattern, source, output);
                }
            }
            "closure_expression" => {
                if let Some(parameters) =
                    node.child_by_field_name("parameters")
                {
                    let mut cursor = parameters.walk();
                    for parameter in parameters.named_children(&mut cursor) {
                        let pattern = parameter
                            .child_by_field_name("pattern")
                            .unwrap_or(parameter);
                        push_rust_binding_pattern(pattern, source, output);
                    }
                }
            }
            _ => {}
        },
        Language::ProceduralSource | Language::Cplusplus => {
            match node.kind() {
                "preproc_def" => {
                    push_named_declaration(
                        language,
                        node.child_by_field_name("name"),
                        source,
                        IdentifierRole::Constant,
                        output,
                    );
                }
                "preproc_function_def" => {
                    push_named_declaration(
                        language,
                        node.child_by_field_name("name"),
                        source,
                        IdentifierRole::Constant,
                        output,
                    );
                    if let Some(parameters) =
                        node.child_by_field_name("parameters")
                    {
                        let mut cursor = parameters.walk();
                        for parameter in parameters.named_children(&mut cursor)
                        {
                            if parameter.kind() == "identifier" {
                                push_named_declaration(
                                    language,
                                    Some(parameter),
                                    source,
                                    IdentifierRole::Value,
                                    output,
                                );
                            }
                        }
                    }
                }
                "struct_specifier" | "union_specifier" | "enum_specifier"
                | "class_specifier" => {
                    let name = node
                        .child_by_field_name("name")
                        .and_then(find_declaration_identifier);
                    let role = if language == Language::Cplusplus {
                        IdentifierRole::Type
                    } else {
                        IdentifierRole::Tag
                    };
                    push_named_declaration(
                        language, name, source, role, output,
                    );
                }
                "type_definition" => {
                    push_native_family_field_declarators(
                        language,
                        node,
                        "declarator",
                        source,
                        IdentifierRole::Typedef,
                        output,
                    );
                }
                "enumerator" => {
                    push_named_declaration(
                        language,
                        node.child_by_field_name("name"),
                        source,
                        IdentifierRole::Enumerator,
                        output,
                    );
                }
                "labeled_statement"
                    if language == Language::ProceduralSource =>
                {
                    push_named_declaration(
                        language,
                        node.child_by_field_name("label"),
                        source,
                        IdentifierRole::Label,
                        output,
                    );
                }
                "namespace_definition" if language == Language::Cplusplus => {
                    if let Some(name) = node.child_by_field_name("name") {
                        push_cplusplus_namespace_names(name, source, output);
                    }
                }
                "namespace_alias_definition"
                    if language == Language::Cplusplus =>
                {
                    push_named_declaration(
                        language,
                        node.child_by_field_name("name"),
                        source,
                        IdentifierRole::ModuleNamespace,
                        output,
                    );
                }
                "alias_declaration" if language == Language::Cplusplus => {
                    push_named_declaration(
                        language,
                        node.child_by_field_name("name"),
                        source,
                        IdentifierRole::Type,
                        output,
                    );
                }
                "type_parameter_declaration"
                | "optional_type_parameter_declaration"
                | "variadic_type_parameter_declaration"
                    if language == Language::Cplusplus =>
                {
                    let mut cursor = node.walk();
                    let name = node
                        .named_children(&mut cursor)
                        .find(|child| child.kind() == "type_identifier");
                    push_named_declaration(
                        language,
                        name,
                        source,
                        IdentifierRole::Type,
                        output,
                    );
                }
                "parameter_declaration"
                | "optional_parameter_declaration"
                | "variadic_parameter_declaration" => {
                    let name = node
                        .child_by_field_name("declarator")
                        .and_then(find_declarator_identifier);
                    let role = if node.parent().is_some_and(|parent| {
                        parent.kind() == "template_parameter_list"
                    }) {
                        IdentifierRole::Constant
                    } else {
                        IdentifierRole::Value
                    };
                    push_named_declaration(
                        language, name, source, role, output,
                    );
                }
                "lambda_capture_initializer"
                    if language == Language::Cplusplus =>
                {
                    push_named_declaration(
                        language,
                        node.child_by_field_name("left"),
                        source,
                        IdentifierRole::Value,
                        output,
                    );
                }
                "function_definition" => {
                    if let Some(declarator) =
                        node.child_by_field_name("declarator")
                    {
                        push_native_family_callable_declarations(
                            language, declarator, source, output,
                        );
                    }
                }
                "declaration" | "field_declaration" => {
                    push_native_family_value_declarations(
                        language, node, source, output,
                    );
                    if descendant_of_kind(node, "function_declarator")
                        .is_some()
                    {
                        if let Some(declarator) =
                            node.child_by_field_name("declarator")
                        {
                            push_native_family_callable_declarations(
                                language, declarator, source, output,
                            );
                        } else {
                            let mut cursor = node.walk();
                            for child in node.named_children(&mut cursor) {
                                if child.kind().contains("declarator") {
                                    push_native_family_callable_declarations(
                                        language, child, source, output,
                                    );
                                }
                            }
                        }
                    }
                }
                _ => {}
            }
        }
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        collect_declarations(language, child, source, output);
    }
}

/// 判断 Rust 外部 trait 是否固定当前方法拼写
fn rust_external_trait_method_has_fixed_name(
    node: Node<'_>,
    source: &[u8],
) -> bool {
    if node.kind() != "function_item"
        || node
            .child_by_field_name("name")
            .and_then(|name| name.utf8_text(source).ok())
            != Some("fmt")
    {
        return false;
    }
    node.parent()
        .and_then(|body| body.parent())
        .filter(|implementation| implementation.kind() == "impl_item")
        .and_then(|implementation| implementation.child_by_field_name("trait"))
        .and_then(|implemented_trait| implemented_trait.utf8_text(source).ok())
        .is_some_and(|implemented_trait| {
            matches!(implemented_trait, "fmt::Display" | "std::fmt::Display")
        })
}

/// 执行 `push_python_case_bindings` 内部逻辑
fn push_python_case_bindings(
    node: Node<'_>,
    source: &[u8],
    output: &mut Vec<Declaration>,
) {
    match node.kind() {
        "dotted_name" => {
            let Ok(name) = node.utf8_text(source) else {
                return;
            };
            if !name.contains('.') {
                push_named_declaration(
                    Language::Python,
                    first_descendant_identifier(node),
                    source,
                    IdentifierRole::Value,
                    output,
                );
            }
        }
        "class_pattern" => {
            let mut cursor = node.walk();
            for child in node.named_children(&mut cursor) {
                if child.kind() == "case_pattern" {
                    push_python_case_bindings(child, source, output);
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
                    push_python_case_bindings(child, source, output);
                }
            }
        }
        "keyword_pattern" => {
            let mut cursor = node.walk();
            for child in node.named_children(&mut cursor) {
                if child.kind() != "identifier" {
                    push_python_case_bindings(child, source, output);
                }
            }
        }
        "as_pattern_target" => {
            push_named_declaration(
                Language::Python,
                first_descendant_identifier(node),
                source,
                IdentifierRole::Value,
                output,
            );
        }
        "identifier" => push_named_declaration(
            Language::Python,
            Some(node),
            source,
            IdentifierRole::Value,
            output,
        ),
        _ => {
            let mut cursor = node.walk();
            for child in node.named_children(&mut cursor) {
                push_python_case_bindings(child, source, output);
            }
        }
    }
}

/// 执行 `push_python_type_alias` 内部逻辑
fn push_python_type_alias(
    node: Node<'_>,
    source: &[u8],
    output: &mut Vec<Declaration>,
) {
    let Some(generic) = descendant_of_kind(node, "generic_type") else {
        push_named_declaration(
            Language::Python,
            first_descendant_identifier(node),
            source,
            IdentifierRole::Type,
            output,
        );
        return;
    };
    let mut cursor = generic.walk();
    for child in generic.named_children(&mut cursor) {
        match child.kind() {
            "identifier" => push_named_declaration(
                Language::Python,
                Some(child),
                source,
                IdentifierRole::Type,
                output,
            ),
            "type_parameter" => {
                push_python_type_parameters(child, source, output)
            }
            _ => {}
        }
    }
}

/// 执行 `push_python_type_parameters` 内部逻辑
fn push_python_type_parameters(
    parameters: Node<'_>,
    source: &[u8],
    output: &mut Vec<Declaration>,
) {
    let mut cursor = parameters.walk();
    for parameter in parameters.named_children(&mut cursor) {
        push_named_declaration(
            Language::Python,
            first_descendant_identifier(parameter),
            source,
            IdentifierRole::Type,
            output,
        );
    }
}

/// 执行 `first_descendant_identifier` 内部逻辑
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

/// 执行 `push_cplusplus_namespace_names` 内部逻辑
fn push_cplusplus_namespace_names(
    node: Node<'_>,
    source: &[u8],
    output: &mut Vec<Declaration>,
) {
    if node.kind() == "namespace_identifier" {
        push_named_declaration(
            Language::Cplusplus,
            Some(node),
            source,
            IdentifierRole::ModuleNamespace,
            output,
        );
        return;
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        push_cplusplus_namespace_names(child, source, output);
    }
}

/// 执行 `push_native_family_field_declarators` 内部逻辑
fn push_native_family_field_declarators(
    language: Language,
    node: Node<'_>,
    field: &str,
    source: &[u8],
    role: IdentifierRole,
    output: &mut Vec<Declaration>,
) {
    for index in 0..node.child_count() {
        let index = index as u32;
        if node.field_name_for_child(index) != Some(field) {
            continue;
        }
        let Some(declarator) = node.child(index) else {
            continue;
        };
        push_named_declaration(
            language,
            find_declaration_identifier(declarator),
            source,
            role,
            output,
        );
    }
}

/// 执行 `find_declaration_identifier` 内部逻辑
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

/// 执行 `python_is_module_assignment` 内部逻辑
fn python_is_module_assignment(node: Node<'_>) -> bool {
    let statement = node
        .parent()
        .filter(|parent| parent.kind() == "expression_statement")
        .unwrap_or(node);
    statement
        .parent()
        .is_some_and(|parent| parent.kind() == "module")
}

/// 执行 `push_python_binding_target` 内部逻辑
fn push_python_binding_target(
    node: Node<'_>,
    source: &[u8],
    role: IdentifierRole,
    output: &mut Vec<Declaration>,
) {
    match node.kind() {
        "identifier" => push_named_declaration(
            Language::Python,
            Some(node),
            source,
            role,
            output,
        ),
        "attribute" => {
            let is_owned_field = node
                .child_by_field_name("object")
                .and_then(|object| object.utf8_text(source).ok())
                .is_some_and(|object| matches!(object, "self" | "cls"));
            if is_owned_field {
                push_named_declaration(
                    Language::Python,
                    node.child_by_field_name("attribute"),
                    source,
                    IdentifierRole::Value,
                    output,
                );
            }
        }
        "subscript" => {}
        _ => {
            let mut cursor = node.walk();
            for child in node.named_children(&mut cursor) {
                push_python_binding_target(child, source, role, output);
            }
        }
    }
}

/// 执行 `push_python_parameter_identifiers` 内部逻辑
fn push_python_parameter_identifiers(
    parameters: Node<'_>,
    source: &[u8],
    excluded_receiver: Option<&str>,
    output: &mut Vec<Declaration>,
) {
    let mut cursor = parameters.walk();
    let mut first_parameter = true;
    for parameter in parameters.named_children(&mut cursor) {
        let name = if parameter.kind() == "identifier" {
            Some(parameter)
        } else {
            parameter.child_by_field_name("name").or_else(|| {
                let mut child_cursor = parameter.walk();
                parameter
                    .named_children(&mut child_cursor)
                    .find(|child| child.kind() == "identifier")
            })
        };
        if first_parameter {
            first_parameter = false;
            if let Some(expected) = excluded_receiver {
                let observed = name
                    .and_then(|identifier| identifier.utf8_text(source).ok());
                if observed == Some(expected) {
                    continue;
                }
                let before = output.len();
                push_named_declaration(
                    Language::Python,
                    name,
                    source,
                    IdentifierRole::Value,
                    output,
                );
                if output.len() != before {
                    output
                        .last_mut()
                        .expect("new receiver declaration must be last")
                        .local_form =
                        LocalIdentifierForm::PythonInvalidReceiver;
                }
                continue;
            }
        }
        push_named_declaration(
            Language::Python,
            name,
            source,
            IdentifierRole::Value,
            output,
        );
    }
}

/// 执行 `python_receiver_spelling` 内部逻辑
fn python_receiver_spelling<'source>(
    node: Node<'_>,
    source: &'source [u8],
) -> Option<&'source str> {
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
    let Some(wrapper) = wrapper else {
        return Some("self");
    };
    let mut cursor = wrapper.walk();
    let decorators: Vec<_> = wrapper
        .named_children(&mut cursor)
        .filter(|child| child.kind() == "decorator")
        .filter_map(|child| child.utf8_text(source).ok())
        .collect();
    if decorators.contains(&"@classmethod") {
        Some("cls")
    } else if decorators.contains(&"@staticmethod") {
        None
    } else {
        Some("self")
    }
}

/// 执行 `push_named_declaration` 内部逻辑
fn push_named_declaration(
    language: Language,
    node: Option<Node<'_>>,
    source: &[u8],
    role: IdentifierRole,
    output: &mut Vec<Declaration>,
) {
    let Some(node) = node else {
        return;
    };
    let Ok(name) = node.utf8_text(source) else {
        return;
    };
    let point = node.start_position();
    let local_form = match language {
        Language::Python
            if role == IdentifierRole::Function
                && name.starts_with("__")
                && name.ends_with("__") =>
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
    output.push(Declaration {
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
    });
}

/// 执行 `push_cplusplus_private_member_declaration` 内部逻辑
fn push_cplusplus_private_member_declaration(
    node: Option<Node<'_>>,
    source: &[u8],
    output: &mut Vec<Declaration>,
) {
    let before = output.len();
    push_named_declaration(
        Language::Cplusplus,
        node,
        source,
        IdentifierRole::Value,
        output,
    );
    if output.len() != before {
        output
            .last_mut()
            .expect("new declaration must be last")
            .local_form = LocalIdentifierForm::CplusplusPrivateMember;
    }
}

/// 执行 `declaration_is_file_or_global_scope` 内部逻辑
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

/// 执行 `push_identifier_descendants` 内部逻辑
fn push_identifier_descendants(
    language: Language,
    node: Node<'_>,
    source: &[u8],
    role: IdentifierRole,
    output: &mut Vec<Declaration>,
) {
    if matches!(node.kind(), "identifier" | "field_identifier") {
        push_named_declaration(language, Some(node), source, role, output);
        return;
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        push_identifier_descendants(language, child, source, role, output);
    }
}

/// 执行 `push_rust_parameter_identifiers` 内部逻辑
fn push_rust_parameter_identifiers(
    parameters: Node<'_>,
    source: &[u8],
    output: &mut Vec<Declaration>,
) {
    let mut cursor = parameters.walk();
    for parameter in parameters.named_children(&mut cursor) {
        if parameter.kind() == "self_parameter" {
            continue;
        }
        if let Some(pattern) = parameter.child_by_field_name("pattern") {
            push_rust_binding_pattern(pattern, source, output);
        }
    }
}

/// 执行 `push_rust_binding_pattern` 内部逻辑
fn push_rust_binding_pattern(
    node: Node<'_>,
    source: &[u8],
    output: &mut Vec<Declaration>,
) {
    match node.kind() {
        "identifier" | "shorthand_field_identifier" => {
            if node.kind() == "identifier"
                && node.utf8_text(source).ok() == Some("None")
            {
                return;
            }
            push_named_declaration(
                Language::Rust,
                Some(node),
                source,
                IdentifierRole::Value,
                output,
            );
        }
        "struct_pattern" | "tuple_struct_pattern" => {
            let excluded_type =
                node.child_by_field_name("type").map(|child| child.id());
            let mut cursor = node.walk();
            for child in node.named_children(&mut cursor) {
                if Some(child.id()) != excluded_type {
                    push_rust_binding_pattern(child, source, output);
                }
            }
        }
        "field_pattern" => {
            if let Some(pattern) = node.child_by_field_name("pattern") {
                push_rust_binding_pattern(pattern, source, output);
            } else {
                push_named_declaration(
                    Language::Rust,
                    node.child_by_field_name("name"),
                    source,
                    IdentifierRole::Value,
                    output,
                );
            }
        }
        "scoped_identifier"
        | "scoped_type_identifier"
        | "type_identifier"
        | "remaining_field_pattern"
        | "wildcard_pattern" => {}
        _ => {
            let mut cursor = node.walk();
            for child in node.named_children(&mut cursor) {
                push_rust_binding_pattern(child, source, output);
            }
        }
    }
}

/// 执行 `push_native_family_callable_declarations` 内部逻辑
fn push_native_family_callable_declarations(
    language: Language,
    declarator: Node<'_>,
    source: &[u8],
    output: &mut Vec<Declaration>,
) {
    if let Some(function) =
        descendant_of_kind(declarator, "function_declarator")
    {
        let name = function
            .child_by_field_name("declarator")
            .and_then(find_declarator_identifier);
        if language != Language::Cplusplus
            || !cplusplus_fixed_callable_spelling(name, source)
        {
            push_named_declaration(
                language,
                name,
                source,
                IdentifierRole::Function,
                output,
            );
        }
        if let Some(parameters) = function.child_by_field_name("parameters") {
            let mut cursor = parameters.walk();
            for parameter in parameters.named_children(&mut cursor) {
                if !matches!(
                    parameter.kind(),
                    "parameter_declaration" | "optional_parameter_declaration"
                ) {
                    continue;
                }
                let name = parameter
                    .child_by_field_name("declarator")
                    .and_then(find_declarator_identifier);
                push_named_declaration(
                    language,
                    name,
                    source,
                    IdentifierRole::Value,
                    output,
                );
            }
        }
    }
}

/// 执行 `cplusplus_fixed_callable_spelling` 内部逻辑
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

/// 执行 `push_native_family_value_declarations` 内部逻辑
fn push_native_family_value_declarations(
    language: Language,
    declaration: Node<'_>,
    source: &[u8],
    output: &mut Vec<Declaration>,
) {
    for index in 0..declaration.child_count() {
        let index = index as u32;
        let Some(child) = declaration.child(index) else {
            continue;
        };
        let is_declarator = declaration.field_name_for_child(index)
            == Some("declarator")
            || child.kind() == "init_declarator"
            || (child.kind().ends_with("declarator")
                && child.kind() != "function_declarator");
        if !is_declarator
            || descendant_of_kind(child, "function_declarator").is_some()
        {
            continue;
        }
        if let Some(binding) =
            descendant_of_kind(child, "structured_binding_declarator")
        {
            push_identifier_descendants(
                language,
                binding,
                source,
                IdentifierRole::Value,
                output,
            );
            continue;
        }
        let name = find_declarator_identifier(child);
        if language == Language::Cplusplus
            && cplusplus_is_private_non_static_data_member(declaration, source)
        {
            push_cplusplus_private_member_declaration(name, source, output);
        } else {
            push_named_declaration(
                language,
                name,
                source,
                IdentifierRole::Value,
                output,
            );
        }
    }
}

/// 执行 `cplusplus_is_private_non_static_data_member` 内部逻辑
fn cplusplus_is_private_non_static_data_member(
    declaration: Node<'_>,
    source: &[u8],
) -> bool {
    if declaration.kind() != "field_declaration"
        || descendant_of_kind(declaration, "function_declarator").is_some()
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

/// 执行 `judge_identifier` 内部逻辑
fn judge_identifier(
    authority: &CompiledAuthority,
    language: Language,
    declaration: &Declaration,
) -> Option<RuleOperator> {
    if declaration.name == "Self" {
        return None;
    }
    let semantic_name = strip_language_form(declaration);
    let (invalid_prefix, mut remainder) =
        strip_role_prefix(&authority.semantic_role_prefixes, semantic_name);
    let mut observed_suffix = None;
    let mut suffix_order: Vec<_> = authority
        .representation_suffixes
        .iter()
        .map(String::as_str)
        .collect();
    suffix_order.sort_by_key(|suffix| std::cmp::Reverse(suffix.len()));
    for suffix in suffix_order {
        let marker = format!("_{suffix}");
        if remainder.ends_with(&marker) {
            remainder = &remainder[..remainder.len() - marker.len()];
            observed_suffix = Some(suffix);
            break;
        }
    }
    let tokens = split_identifier_tokens(remainder);
    if tokens.iter().any(|token| {
        token.chars().count() == 1
            || authority.candidate_tokens.contains(token.as_str())
    }) {
        return Some(RuleOperator::IdentifierCandidate);
    }
    if identifier_is_reserved(language, declaration) {
        return Some(RuleOperator::IdentifierReserved);
    }
    if invalid_prefix {
        return Some(RuleOperator::IdentifierCanonicalForm);
    }
    let vocabulary_complete = tokens
        .iter()
        .all(|token| authority.token_vocabulary.contains(token.as_str()));
    if vocabulary_complete
        && !identifier_role_form_is_valid(declaration, semantic_name)
    {
        return Some(RuleOperator::IdentifierCanonicalForm);
    }
    if declaration.value_like
        && let Some(allowed) = authority.quantity_concepts.get(remainder)
    {
        match observed_suffix {
            Some(suffix) if allowed.contains(suffix) => {}
            _ => {
                return Some(RuleOperator::IdentifierRepresentationSuffix);
            }
        }
    }
    if declaration.value_like
        && observed_suffix.is_none()
        && authority
            .quantity_concepts
            .keys()
            .any(|concept| remainder.starts_with(&format!("{concept}_")))
    {
        return Some(RuleOperator::IdentifierRepresentationSuffix);
    }
    if tokens
        .iter()
        .any(|token| !authority.token_vocabulary.contains(token.as_str()))
    {
        return Some(RuleOperator::IdentifierUnknownToken);
    }
    None
}

/// 执行 `strip_language_form` 内部逻辑
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

/// 执行 `identifier_is_reserved` 内部逻辑
fn identifier_is_reserved(
    language: Language,
    declaration: &Declaration,
) -> bool {
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

/// 执行 `identifier_role_form_is_valid` 内部逻辑
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

/// 执行 `is_pascal_case` 内部逻辑
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

/// 执行 `strip_role_prefix` 内部逻辑
fn strip_role_prefix<'identifier>(
    prefixes: &[String],
    name: &'identifier str,
) -> (bool, &'identifier str) {
    if let Some(remainder) = name
        .strip_prefix("min_")
        .or_else(|| name.strip_prefix("max_"))
    {
        return (true, remainder);
    }
    for prefix in prefixes {
        let marker = format!("{prefix}_");
        if let Some(remainder) = name.strip_prefix(&marker) {
            if prefixes
                .iter()
                .any(|other| remainder.starts_with(&format!("{other}_")))
            {
                let remainder = prefixes
                    .iter()
                    .find_map(|other| {
                        remainder.strip_prefix(&format!("{other}_"))
                    })
                    .unwrap_or(remainder);
                return (true, remainder);
            }
            return (false, remainder);
        }
    }
    (false, name)
}

/// 执行 `split_identifier_tokens` 内部逻辑
fn split_identifier_tokens(name: &str) -> Vec<String> {
    let mut tokens = Vec::new();
    for segment in name.split('_').filter(|segment| !segment.is_empty()) {
        if segment.chars().all(|character| {
            !character.is_alphabetic() || character.is_uppercase()
        }) {
            tokens.push(segment.to_lowercase());
            continue;
        }
        let mut current = String::new();
        for character in segment.chars() {
            if character.is_uppercase() && !current.is_empty() {
                tokens.push(current.to_lowercase());
                current.clear();
            }
            current.extend(character.to_lowercase());
        }
        if !current.is_empty() {
            tokens.push(current);
        }
    }
    tokens
}

/// 将标识符判定映射为 Authority 拥有的 Finding
fn push_identifier_findings(
    authority: &CompiledAuthority,
    document: &OwnedDocument,
    declaration: &Declaration,
    operator: RuleOperator,
    findings: &mut Vec<Finding>,
) {
    push_rule_findings(
        authority,
        operator,
        &document.path,
        declaration.line,
        declaration.column,
        &declaration.name,
        &format!(
            "observed author-chosen declaration spelling {}",
            declaration.name
        ),
        findings,
    );
}

/// 执行 `tree_sitter_language` 内部逻辑
fn tree_sitter_language(language: Language) -> TreeSitterLanguage {
    match language {
        Language::Python => tree_sitter_python::LANGUAGE.into(),
        Language::Rust => tree_sitter_rust::LANGUAGE.into(),
        Language::ProceduralSource => tree_sitter_c::LANGUAGE.into(),
        Language::Cplusplus => tree_sitter_cpp::LANGUAGE.into(),
    }
}

/// 执行 `language_for_document` 内部逻辑
fn language_for_document(
    authority: &CompiledAuthority,
    path: &str,
) -> Result<Option<Language>, ReviewRejection> {
    let path_object = Path::new(path);
    if path_object
        .extension()
        .and_then(|extension| extension.to_str())
        == Some("h")
    {
        return match authority.header_languages.get(path) {
            Some(language) => parse_language(language).map(Some),
            None => Err(ReviewRejection::new(
                "request.language",
                format!(
                    "ambiguous .h source lacks header_languages entry: {path}"
                ),
            )),
        };
    }
    Ok(language_for_path(path_object))
}

/// 执行 `language_for_path` 内部逻辑
fn language_for_path(path: &Path) -> Option<Language> {
    match path.extension().and_then(|extension| extension.to_str()) {
        Some("py") => Some(Language::Python),
        Some("rs") => Some(Language::Rust),
        Some("c") => Some(Language::ProceduralSource),
        Some("cc" | "cpp" | "cxx" | "hpp" | "hh" | "hxx") => {
            Some(Language::Cplusplus)
        }
        _ => None,
    }
}

/// 执行 `parse_language` 内部逻辑
fn parse_language(language: &str) -> Result<Language, ReviewRejection> {
    match language {
        "python" => Ok(Language::Python),
        "rust" => Ok(Language::Rust),
        "c" => Ok(Language::ProceduralSource),
        "cpp" => Ok(Language::Cplusplus),
        _ => Err(ReviewRejection::new(
            "request.language",
            format!("unknown language {language}"),
        )),
    }
}

/// 执行 `collect_callables` 内部逻辑
#[allow(clippy::too_many_arguments)]
fn collect_callables(
    language: Language,
    node: Node<'_>,
    source: &[u8],
    nested: bool,
    output: &mut Vec<Callable>,
) {
    let is_named_callable = match language {
        Language::Python => node.kind() == "function_definition",
        Language::Rust => {
            matches!(node.kind(), "function_item" | "function_signature_item")
        }
        Language::ProceduralSource | Language::Cplusplus => {
            node.kind() == "function_definition"
                || (matches!(node.kind(), "declaration" | "field_declaration")
                    && descendant_of_kind(node, "function_declarator")
                        .is_some())
        }
    };
    let is_python_class =
        language == Language::Python && node.kind() == "class_definition";
    let is_rust_public_item = language == Language::Rust
        && rust_public_documentation_item(node, source);
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
        let name = documentation_subject_name(language, node, source)
            .unwrap_or_else(|| "<unknown>".to_owned());
        let point = node.start_position();
        let decorated_visibility = (language == Language::Python
            && is_named_callable)
            .then(|| observe_python_decorated_visibility(node, source, &name))
            .flatten();
        let visibility = if is_native_family_unresolved_item {
            DocumentationVisibility::Unresolved
        } else if let Some(decorated_visibility) = decorated_visibility {
            decorated_visibility
        } else {
            observe_documentation_visibility(
                language, node, source, nested, &name,
            )
        };
        let carrier = documentation_carrier(language, node, source);
        let (parameters, parameters_complete) =
            callable_parameters(language, node, source);
        let (
            template_parameters,
            template_parameters_complete,
            requires_template_parameters,
        ) = cplusplus_template_parameters(language, node, source);
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
            return_shape: callable_return_shape(language, node, source),
            carrier,
            requires_safety: language == Language::Rust
                && rust_requires_safety(node),
            requires_effect: language == Language::Cplusplus
                && cplusplus_requires_effect(node, source),
            carrier_unresolved: language == Language::Rust
                && rust_has_nonliteral_documentation_attribute(node, source),
        });
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        collect_callables(language, child, source, child_nested, output);
    }
}

/// 执行 `rust_public_documentation_item` 内部逻辑
fn rust_public_documentation_item(node: Node<'_>, source: &[u8]) -> bool {
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
        "macro_definition" => rust_has_attribute(node, source, "macro_export"),
        _ => false,
    }
}

/// 执行 `rust_requires_safety` 内部逻辑
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

/// 执行 `rust_has_attribute` 内部逻辑
fn rust_has_attribute(
    node: Node<'_>,
    source: &[u8],
    attribute_name: &str,
) -> bool {
    let marker = format!("#[{attribute_name}");
    let mut cursor = node.walk();
    if node.named_children(&mut cursor).any(|child| {
        child.kind() == "attribute_item"
            && child
                .utf8_text(source)
                .is_ok_and(|text| text.trim().starts_with(&marker))
    }) {
        return true;
    }
    let mut sibling = node.prev_named_sibling();
    while let Some(attribute) = sibling {
        if attribute.kind() != "attribute_item" {
            break;
        }
        if attribute
            .utf8_text(source)
            .is_ok_and(|text| text.trim().starts_with(&marker))
        {
            return true;
        }
        sibling = attribute.prev_named_sibling();
    }
    false
}

/// 执行 `rust_has_nonliteral_documentation_attribute` 内部逻辑
fn rust_has_nonliteral_documentation_attribute(
    node: Node<'_>,
    source: &[u8],
) -> bool {
    let mut cursor = node.walk();
    if node.named_children(&mut cursor).any(|child| {
        child.kind() == "attribute_item"
            && child
                .utf8_text(source)
                .is_ok_and(|text| text.trim().starts_with("#[doc"))
            && parse_rust_documentation_attribute(child, source).is_none()
    }) {
        return true;
    }
    let mut sibling = node.prev_named_sibling();
    while let Some(attribute) = sibling {
        if attribute.kind() != "attribute_item" {
            break;
        }
        if attribute
            .utf8_text(source)
            .is_ok_and(|text| text.trim().starts_with("#[doc"))
            && parse_rust_documentation_attribute(attribute, source).is_none()
        {
            return true;
        }
        sibling = attribute.prev_named_sibling();
    }
    false
}

/// 执行 `rust_leading_attribute_start` 内部逻辑
fn rust_leading_attribute_start(node: Node<'_>) -> usize {
    let mut start = node.start_byte();
    let mut sibling = node.prev_named_sibling();
    while let Some(attribute) = sibling {
        if attribute.kind() != "attribute_item" {
            break;
        }
        start = attribute.start_byte();
        sibling = attribute.prev_named_sibling();
    }
    start
}

/// 执行 `rust_has_unrestricted_public_visibility` 内部逻辑
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

/// 执行 `rust_public_ancestor` 内部逻辑
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

/// 执行 `native_family_documentation_capability_needed` 内部逻辑
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
        && descendant_of_kind(node, "function_declarator").is_none())
}

/// 执行 `documentation_subject_name` 内部逻辑
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

/// 执行 `callable_parameters` 内部逻辑
fn callable_parameters(
    language: Language,
    node: Node<'_>,
    source: &[u8],
) -> (Vec<String>, bool) {
    let parameters = match language {
        Language::Python | Language::Rust => {
            node.child_by_field_name("parameters")
        }
        Language::ProceduralSource | Language::Cplusplus => node
            .child_by_field_name("declarator")
            .and_then(|declarator| {
                descendant_of_kind(declarator, "parameter_list")
            })
            .or_else(|| descendant_of_kind(node, "parameter_list")),
    };
    let Some(parameters) = parameters else {
        return (Vec::new(), false);
    };
    let mut names = Vec::new();
    let complete = match language {
        Language::Python => {
            python_parameter_names(parameters, source, &mut names)
        }
        Language::Rust => rust_parameter_names(parameters, source, &mut names),
        Language::ProceduralSource | Language::Cplusplus => {
            native_family_parameter_names(
                language, parameters, source, &mut names,
            )
        }
    };
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
    source: &[u8],
) -> (Vec<String>, bool, bool) {
    if language != Language::Cplusplus {
        return (Vec::new(), true, false);
    }
    let has_abbreviated_parameter =
        cplusplus_has_placeholder_auto_parameter(node);
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
    let items: Vec<_> = parameters.named_children(&mut cursor).collect();
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

/// 提取可稳定命名的 Python 参数
fn python_parameter_names(
    parameters: Node<'_>,
    source: &[u8],
    names: &mut Vec<String>,
) -> bool {
    let mut complete = true;
    let mut cursor = parameters.walk();
    for parameter in parameters.named_children(&mut cursor) {
        if matches!(
            parameter.kind(),
            "keyword_separator" | "positional_separator"
        ) {
            continue;
        }
        let candidate = match parameter.kind() {
            "identifier" => Some(parameter),
            "default_parameter" | "typed_default_parameter" => parameter
                .child_by_field_name("name")
                .filter(|name| name.kind() == "identifier"),
            "typed_parameter" => single_identifier_child(parameter),
            "list_splat_pattern" | "dictionary_splat_pattern" => {
                single_identifier_child(parameter)
            }
            _ => None,
        };
        if let Some(identifier) = candidate
            && let Ok(text) = identifier.utf8_text(source)
        {
            names.push(text.to_owned());
        } else {
            complete = false;
        }
    }
    complete
}

/// 提取可稳定命名的 Rust 参数
fn rust_parameter_names(
    parameters: Node<'_>,
    source: &[u8],
    names: &mut Vec<String>,
) -> bool {
    let mut complete = true;
    let mut cursor = parameters.walk();
    for parameter in parameters.named_children(&mut cursor) {
        match parameter.kind() {
            "self_parameter" | "attribute_item" => {}
            "parameter" => {
                let candidate = parameter
                    .child_by_field_name("pattern")
                    .filter(|pattern| pattern.kind() == "identifier");
                if let Some(identifier) = candidate
                    && let Ok(text) = identifier.utf8_text(source)
                {
                    names.push(text.to_owned());
                } else {
                    complete = false;
                }
            }
            _ => complete = false,
        }
    }
    complete
}

/// 提取可稳定命名的 C 家族参数
fn native_family_parameter_names(
    language: Language,
    parameters: Node<'_>,
    source: &[u8],
    names: &mut Vec<String>,
) -> bool {
    let mut cursor = parameters.walk();
    let items: Vec<_> = parameters.named_children(&mut cursor).collect();
    if items.is_empty() {
        return language == Language::Cplusplus;
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
    let mut complete = parameters
        .utf8_text(source)
        .is_ok_and(|text| !text.contains("..."));
    for parameter in items {
        if !matches!(
            parameter.kind(),
            "parameter_declaration" | "optional_parameter_declaration"
        ) {
            complete = false;
            continue;
        }
        let candidate = parameter
            .child_by_field_name("declarator")
            .and_then(find_declarator_identifier);
        if let Some(identifier) = candidate
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
        Language::Rust => rust_return_shape(node),
        Language::ProceduralSource | Language::Cplusplus => {
            native_family_return_shape(language, node, source)
        }
    }
}

/// 提取 Python 可由直接语法证明的返回值形状
fn python_return_shape(node: Node<'_>, source: &[u8]) -> ReturnShape {
    let Some(kind) = node.child_by_field_name("return_type") else {
        return ReturnShape::Unknown;
    };
    let kind = if kind.kind() == "type" && kind.named_child_count() == 1 {
        kind.named_child(0).unwrap_or(kind)
    } else {
        kind
    };
    let Ok(spelling) = kind.utf8_text(source) else {
        return ReturnShape::Unknown;
    };
    if kind.kind() == "none" || spelling == "None" {
        return ReturnShape::NoValue;
    }
    if kind.kind() == "identifier"
        && matches!(
            spelling,
            "bool"
                | "bytearray"
                | "bytes"
                | "complex"
                | "dict"
                | "float"
                | "frozenset"
                | "int"
                | "list"
                | "object"
                | "range"
                | "set"
                | "str"
                | "tuple"
        )
    {
        ReturnShape::Value
    } else {
        ReturnShape::Unknown
    }
}

/// 提取 Rust 可由直接语法证明的返回值形状
fn rust_return_shape(node: Node<'_>) -> ReturnShape {
    let Some(kind) = node.child_by_field_name("return_type") else {
        return ReturnShape::NoValue;
    };
    match kind.kind() {
        "unit_type" => ReturnShape::NoValue,
        "never_type" => ReturnShape::Never,
        "macro_invocation" | "metavariable" => ReturnShape::Unknown,
        _ => ReturnShape::Value,
    }
}

/// 提取 C 家族 callable 的返回值形状
fn native_family_return_shape(
    language: Language,
    node: Node<'_>,
    source: &[u8],
) -> ReturnShape {
    let function_declarator = descendant_of_kind(node, "function_declarator");
    if language == Language::Cplusplus
        && let Some(trailing) = function_declarator.and_then(|declarator| {
            direct_child_of_kind(declarator, "trailing_return_type")
        })
        && let Some(descriptor) = trailing.named_child(0)
        && let Some(kind) = descriptor.child_by_field_name("type")
    {
        return native_family_type_shape(
            kind,
            descriptor.child_by_field_name("declarator"),
            source,
        );
    }
    let Some(kind) = node.child_by_field_name("type") else {
        return if language == Language::Cplusplus
            && cplusplus_constructor_or_destructor(node, source)
        {
            ReturnShape::NoValue
        } else {
            ReturnShape::Unknown
        };
    };
    let result_declarator = function_declarator
        .and_then(|declarator| declarator.child_by_field_name("declarator"));
    native_family_type_shape(kind, result_declarator, source)
}

/// 提取 C 家族直接类型节点的返回值形状
fn native_family_type_shape(
    kind: Node<'_>,
    declarator: Option<Node<'_>>,
    source: &[u8],
) -> ReturnShape {
    if declarator.is_some_and(declarator_proves_return_value) {
        return ReturnShape::Value;
    }
    match kind.kind() {
        "primitive_type" => kind.utf8_text(source).ok().map(str::trim).map_or(
            ReturnShape::Unknown,
            |spelling| {
                if spelling == "void" {
                    ReturnShape::NoValue
                } else {
                    ReturnShape::Value
                }
            },
        ),
        "sized_type_specifier" => {
            if descendant_of_kind(kind, "type_identifier").is_some() {
                ReturnShape::Unknown
            } else {
                ReturnShape::Value
            }
        }
        "class_specifier" | "enum_specifier" | "struct_specifier"
        | "union_specifier" => ReturnShape::Value,
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
    if matches!(
        node.kind(),
        "pointer_declarator"
            | "reference_declarator"
            | "abstract_reference_declarator"
    ) {
        return true;
    }
    let mut cursor = node.walk();
    node.named_children(&mut cursor)
        .any(declarator_proves_return_value)
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

/// 执行 `callable_name` 内部逻辑
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

/// 执行 `find_declarator_identifier` 内部逻辑
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

/// 执行 `descendant_of_kind` 内部逻辑
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

/// 执行 `observe_documentation_visibility` 内部逻辑
fn observe_documentation_visibility(
    language: Language,
    node: Node<'_>,
    source: &[u8],
    nested: bool,
    name: &str,
) -> DocumentationVisibility {
    match language {
        Language::Python => {
            if python_protocol_method(node, source)
                || (!nested && !name.starts_with('_'))
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
                || rust_public_documentation_item(node, source)
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
    let Some(public_names) = authority.public_callables.get(path) else {
        return;
    };
    for callable in callables {
        if matches!(
            callable.language,
            Language::ProceduralSource | Language::Cplusplus
        ) && public_names.contains(&callable.name)
        {
            callable.visibility = DocumentationVisibility::Public;
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
    let [decorator] = decorators.as_slice() else {
        return Some(DocumentationVisibility::Unresolved);
    };
    let direct_class = python_direct_class_body(node);
    if matches!(decorator.as_str(), "@classmethod" | "@staticmethod") {
        return direct_class
            .is_none()
            .then_some(DocumentationVisibility::Unresolved);
    }
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
            && matches!(accessor, "setter" | "deleter")
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

/// 执行 `python_protocol_method` 内部逻辑
fn python_protocol_method(node: Node<'_>, source: &[u8]) -> bool {
    if node.kind() != "function_definition" {
        return false;
    }
    node.child_by_field_name("name")
        .and_then(|name| name.utf8_text(source).ok())
        .is_some_and(|name| {
            name.len() > 4 && name.starts_with("__") && name.ends_with("__")
        })
}

/// 执行 `native_family_callable_is_proven_internal` 内部逻辑
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

/// 执行 `documentation_carrier` 内部逻辑
fn documentation_carrier(
    language: Language,
    node: Node<'_>,
    source: &[u8],
) -> Option<String> {
    match language {
        Language::Python => python_docstring(node, source),
        Language::Rust => rust_documentation_attribute(node, source)
            .or_else(|| preceding_rustdoc(node, source)),
        Language::ProceduralSource => preceding_controlled_block(node, source),
        Language::Cplusplus => preceding_controlled_block(
            cplusplus_template_declaration(node).unwrap_or(node),
            source,
        ),
    }
}

/// 执行 `rust_documentation_attribute` 内部逻辑
fn rust_documentation_attribute(
    node: Node<'_>,
    source: &[u8],
) -> Option<String> {
    let mut lines = Vec::new();
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        if child.kind() == "attribute_item"
            && let Some(line) =
                parse_rust_documentation_attribute(child, source)
        {
            lines.push(line);
        }
    }
    if lines.is_empty() {
        let mut sibling = node.prev_named_sibling();
        while let Some(attribute) = sibling {
            if attribute.kind() != "attribute_item" {
                break;
            }
            if let Some(line) =
                parse_rust_documentation_attribute(attribute, source)
            {
                lines.push(line);
            }
            sibling = attribute.prev_named_sibling();
        }
        lines.reverse();
    }
    (!lines.is_empty()).then(|| lines.join("\n"))
}

/// 执行 `parse_rust_documentation_attribute` 内部逻辑
fn parse_rust_documentation_attribute(
    node: Node<'_>,
    source: &[u8],
) -> Option<String> {
    let text = node.utf8_text(source).ok()?.trim();
    let value = text
        .strip_prefix("#[doc")?
        .strip_suffix(']')?
        .trim()
        .strip_prefix('=')?
        .trim();
    serde_json::from_str(value).ok()
}

/// 执行 `python_docstring` 内部逻辑
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

/// 执行 `python_module_docstring` 内部逻辑
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
/// 执行 `preceding_rustdoc` 内部逻辑
fn preceding_rustdoc(node: Node<'_>, source: &[u8]) -> Option<String> {
    let mut attachment_start = rust_leading_attribute_start(node);
    let mut sibling = node.prev_named_sibling();
    while let Some(attribute) = sibling {
        if attribute.kind() != "attribute_item" {
            break;
        }
        attachment_start = attribute.start_byte();
        sibling = attribute.prev_named_sibling();
    }
    let candidate = sibling?;
    if !source_gap_is_whitespace(
        candidate.end_byte(),
        attachment_start,
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
    sibling = candidate.prev_named_sibling();
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
/// 执行 `preceding_controlled_block` 内部逻辑
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
/// 执行 `documentation_lines` 内部逻辑
fn documentation_lines(language: Language, carrier: &str) -> Vec<String> {
    if language == Language::Rust {
        return rust_documentation_lines(carrier);
    }
    if matches!(language, Language::ProceduralSource | Language::Cplusplus) {
        return native_family_documentation_lines(carrier);
    }
    carrier
        .lines()
        .filter_map(|line| {
            let normalized = match language {
                Language::Python => line.trim(),
                Language::Rust => unreachable!(),
                Language::ProceduralSource | Language::Cplusplus => {
                    unreachable!()
                }
            };
            if matches!(normalized, "\"\"\"" | "/**" | "*/" | "/") {
                None
            } else {
                Some(normalized.to_owned())
            }
        })
        .collect()
}
/// 规范化 C 家族受控文档块的逐行正文
fn native_family_documentation_lines(carrier: &str) -> Vec<String> {
    carrier
        .lines()
        .filter_map(|line| {
            let normalized =
                line.trim().strip_prefix('*').unwrap_or(line.trim()).trim();
            if matches!(normalized, "/**" | "*/" | "/") {
                None
            } else {
                Some(normalized.to_owned())
            }
        })
        .collect()
}
/// 规范化 Rust outer rustdoc 的逐行正文
fn rust_documentation_lines(carrier: &str) -> Vec<String> {
    if let Some(body) = carrier
        .strip_prefix("/**")
        .and_then(|body| body.strip_suffix("*/"))
    {
        let body = body.strip_prefix(' ').unwrap_or(body);
        let body = body.strip_suffix(' ').unwrap_or(body);
        return body
            .lines()
            .map(|line| {
                let decoration = line.trim_start_matches([' ', '\t']);
                let content = decoration
                    .strip_prefix('*')
                    .map(|content| {
                        content.strip_prefix(' ').unwrap_or(content)
                    })
                    .unwrap_or(line);
                content.to_owned()
            })
            .collect();
    }
    carrier
        .lines()
        .map(|line| {
            let content = line.strip_prefix("///").unwrap_or(line);
            content.strip_prefix(' ').unwrap_or(content).to_owned()
        })
        .collect()
}
/// 执行 `documentation_has_summary` 内部逻辑
fn documentation_has_summary(
    authority: &CompiledAuthority,
    language: Language,
    lines: &[String],
) -> bool {
    let summary = if language == Language::Python {
        lines.first().filter(|line| !line.is_empty())
    } else {
        lines.iter().find(|line| !line.is_empty())
    };
    let Some(summary) = summary else {
        return false;
    };
    if language == Language::Rust
        && rust_markdown_line_is_indented_code(summary)
    {
        return false;
    }
    let contract = authority.profile_contract(language.key());
    !([
        contract.arguments_label.as_str(),
        contract.returns_label.as_str(),
        contract.failures_label.as_str(),
    ]
    .contains(&summary.as_str())
        || language == Language::Cplusplus
            && documentation_heading(Language::Cplusplus, summary))
        && contains_chinese_phrase(summary)
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
/// 判断受控字段正文是否可作为 Markdown 内容
fn controlled_field_body_is_markdown_content(
    language: Language,
    lines: &[String],
) -> bool {
    language != Language::Rust
        || lines
            .iter()
            .all(|line| !rust_markdown_line_is_indented_code(line))
}
/// 判断文本是否含有至少两个连续中文字符
fn contains_chinese_phrase(text: &str) -> bool {
    let mut consecutive = 0_u8;
    for character in text.chars() {
        if matches!(
            character,
            '\u{3400}'..='\u{4dbf}' | '\u{4e00}'..='\u{9fff}'
        ) {
            consecutive += 1;
            if consecutive >= 2 {
                return true;
            }
        } else {
            consecutive = 0;
        }
    }
    false
}
/// 执行 `public_contract_is_complete` 内部逻辑
fn public_contract_is_complete(
    authority: &CompiledAuthority,
    callable: &Callable,
    lines: &[String],
) -> bool {
    if callable.language == Language::Rust
        && !rust_controlled_headings_are_valid(lines)
    {
        return false;
    }
    let contract = authority.profile_contract(callable.language.key());
    let mut headings = Vec::with_capacity(5);
    if callable.language == Language::Cplusplus
        && callable.requires_template_parameters
    {
        headings.push(("模板参数：", DocumentationRole::TemplateParameters));
    }
    headings.extend([
        (
            contract.arguments_label.as_str(),
            DocumentationRole::Arguments,
        ),
        (contract.returns_label.as_str(), DocumentationRole::Returns),
        (
            contract.failures_label.as_str(),
            DocumentationRole::Failures,
        ),
    ]);
    if callable.language == Language::Cplusplus && callable.requires_effect {
        headings.push(("效果：", DocumentationRole::Effect));
    }
    if callable.language == Language::Cplusplus {
        let observed: Vec<_> = lines
            .iter()
            .filter(|line| documentation_heading(Language::Cplusplus, line))
            .map(String::as_str)
            .collect();
        let expected: Vec<_> =
            headings.iter().map(|(heading, _)| *heading).collect();
        if observed != expected {
            return false;
        }
    }
    let empty_role = contract.empty_role.as_str();
    let mut indices = Vec::with_capacity(headings.len());
    for (heading, role) in headings {
        let matches: Vec<_> = lines
            .iter()
            .enumerate()
            .filter_map(|(index, line)| (line == heading).then_some(index))
            .collect();
        let [index] = matches.as_slice() else {
            return false;
        };
        if indices.last().is_some_and(|(prior, _)| index <= prior) {
            return false;
        }
        indices.push((*index, role));
    }
    let Some(summary_index) = lines.iter().position(|line| !line.is_empty())
    else {
        return false;
    };
    if indices[0].0 != summary_index + 2
        || !lines[summary_index + 1].is_empty()
    {
        return false;
    }
    for (start, role) in indices.iter().copied() {
        let end = lines
            .iter()
            .enumerate()
            .skip(start + 1)
            .find_map(|(index, line)| {
                documentation_heading(callable.language, line).then_some(index)
            })
            .unwrap_or(lines.len());
        let body = &lines[start + 1..end];
        let content: Vec<_> =
            body.iter().filter(|line| !line.is_empty()).collect();
        if content.is_empty() {
            return false;
        }
        if !documentation_role_is_complete(
            callable, role, &content, empty_role,
        ) {
            return false;
        }
    }
    true
}
/// 判断单个公开文档字段是否与结构事实闭合
fn documentation_role_is_complete(
    callable: &Callable,
    role: DocumentationRole,
    content: &[&String],
    empty_role: &str,
) -> bool {
    let is_empty = |line: &str| {
        controlled_field_line_equals(callable.language, line, empty_role)
    };
    let is_valid =
        |line: &str| documentation_role_line_is_valid(callable.language, line);
    let has_empty = content.iter().any(|line| is_empty(line));
    let single_empty = content.len() == 1 && is_empty(content[0]);
    if has_empty && !single_empty {
        return false;
    }
    match role {
        DocumentationRole::TemplateParameters => {
            !has_empty
                && documented_names_match(
                    Language::Cplusplus,
                    content,
                    &callable.template_parameters,
                )
        }
        DocumentationRole::Arguments if callable.parameters.is_empty() => {
            single_empty
        }
        DocumentationRole::Arguments => {
            !has_empty
                && documented_names_match(
                    callable.language,
                    content,
                    &callable.parameters,
                )
        }
        DocumentationRole::Returns => match callable.return_shape {
            ReturnShape::NoValue => single_empty,
            ReturnShape::Never => {
                callable.language == Language::Rust
                    && content.len() == 1
                    && controlled_field_line_equals(
                        callable.language,
                        content[0],
                        "- 不返回",
                    )
            }
            ReturnShape::Value => {
                !has_empty && content.iter().all(|line| is_valid(line))
            }
            ReturnShape::Unknown => false,
        },
        DocumentationRole::Failures => {
            content.iter().all(|line| is_empty(line) || is_valid(line))
        }
        DocumentationRole::Effect => {
            !has_empty && content.iter().all(|line| is_valid(line))
        }
    }
}
/// 比较受控字段行与规范文本
fn controlled_field_line_equals(
    language: Language,
    line: &str,
    expected: &str,
) -> bool {
    let line = if language == Language::Rust {
        line.trim_start_matches([' ', '\t'])
    } else {
        line
    };
    line == expected
}
/// 判断文档字段是否逐一且仅逐一覆盖结构化名称
fn documented_names_match(
    language: Language,
    content: &[&String],
    expected: &[String],
) -> bool {
    if content.len() != expected.len() {
        return false;
    }
    let mut observed = BTreeSet::new();
    for line in content {
        let Some(name) = documented_parameter_name(language, line) else {
            return false;
        };
        if !expected.iter().any(|item| item == name) || !observed.insert(name)
        {
            return false;
        }
    }
    observed.len() == expected.len()
}
/// 执行 `rust_safety_contract_is_complete` 内部逻辑
fn rust_safety_contract_is_complete(lines: &[String]) -> bool {
    if !rust_controlled_headings_are_valid(lines) {
        return false;
    }
    let safety_indices: Vec<_> = lines
        .iter()
        .enumerate()
        .filter_map(|(index, line)| (line == "# Safety").then_some(index))
        .collect();
    let [start] = safety_indices.as_slice() else {
        return false;
    };
    if lines
        .iter()
        .position(|line| line == "# Errors")
        .is_some_and(|errors| *start <= errors)
        || lines
            .iter()
            .position(|line| line == "# Panics")
            .is_some_and(|panics| panics >= *start)
    {
        return false;
    }
    lines[start + 1..]
        .iter()
        .take_while(|line| !documentation_heading(Language::Rust, line))
        .any(|line| !line.is_empty())
}
/// 执行 `documented_parameter_name` 内部逻辑
fn documented_parameter_name(language: Language, line: &str) -> Option<&str> {
    if language == Language::Rust && rust_markdown_line_is_indented_code(line)
    {
        return None;
    }
    let entry = match language {
        Language::Python => line.trim(),
        Language::Rust | Language::ProceduralSource | Language::Cplusplus => {
            line.trim().strip_prefix('-')?.trim_start()
        }
    };
    let (separator, separator_width) = entry
        .find(':')
        .map(|index| (index, ':'.len_utf8()))
        .or_else(|| entry.find('：').map(|index| (index, '：'.len_utf8())))?;
    let name = entry[..separator].trim();
    let description = entry[separator + separator_width..].trim();
    (!name.is_empty()
        && !description.is_empty()
        && contains_chinese_phrase(description))
    .then_some(name)
}
/// 执行 `documentation_role_line_is_valid` 内部逻辑
fn documentation_role_line_is_valid(language: Language, line: &str) -> bool {
    if language == Language::Rust && rust_markdown_line_is_indented_code(line)
    {
        return false;
    }
    match language {
        Language::Python => {
            let Some(separator) = line.find(':') else {
                return false;
            };
            !line[..separator].trim().is_empty()
                && !line[separator + 1..].trim().is_empty()
                && contains_chinese_phrase(&line[separator + 1..])
        }
        Language::Rust | Language::ProceduralSource | Language::Cplusplus => {
            line.trim().strip_prefix('-').is_some_and(|description| {
                !description.trim().is_empty()
                    && contains_chinese_phrase(description)
            })
        }
    }
}
/// 执行 `documentation_heading` 内部逻辑
fn documentation_heading(language: Language, line: &str) -> bool {
    match language {
        Language::Python => {
            matches!(line, "Args:" | "Returns:" | "Raises:" | "Attributes:")
        }
        Language::Rust => line.starts_with("# "),
        Language::ProceduralSource | Language::Cplusplus => matches!(
            line,
            "模板参数："
                | "参数："
                | "返回："
                | "错误："
                | "所有权："
                | "效果："
        ),
    }
}
/// 执行 `rust_controlled_headings_are_valid` 内部逻辑
fn rust_controlled_headings_are_valid(lines: &[String]) -> bool {
    const HEADINGS: [&str; 5] = [
        "# Arguments",
        "# Returns",
        "# Errors",
        "# Panics",
        "# Safety",
    ];
    let mut seen = BTreeSet::new();
    let mut previous = None;
    for (index, line) in lines.iter().enumerate() {
        let Some(rank) = HEADINGS.iter().position(|heading| line == heading)
        else {
            continue;
        };
        if !seen.insert(rank)
            || previous.is_some_and(|previous_rank| rank <= previous_rank)
        {
            return false;
        }
        previous = Some(rank);
        let end = lines[index + 1..]
            .iter()
            .position(|candidate| candidate.starts_with("# "))
            .map(|offset| index + 1 + offset)
            .unwrap_or(lines.len());
        let body = &lines[index + 1..end];
        if !controlled_field_body_is_markdown_content(Language::Rust, body) {
            return false;
        }
        if rank < 3 {
            continue;
        }
        let content: Vec<_> = body
            .iter()
            .filter(|candidate| !candidate.is_empty())
            .collect();
        if content.is_empty()
            || !content.iter().all(|candidate| {
                documentation_role_line_is_valid(Language::Rust, candidate)
            })
        {
            return false;
        }
    }
    true
}
/// 执行 `controlled_line_has_terminator` 内部逻辑
fn controlled_line_has_terminator(
    authority: &CompiledAuthority,
    language: Language,
    public: bool,
    requires_safety: bool,
    lines: &[String],
) -> bool {
    let summary = lines.iter().find(|line| !line.is_empty());
    if summary.is_some_and(|line| ends_in_sentence_terminator(line)) {
        return true;
    }
    let has_controlled_contract =
        public || (language == Language::Rust && requires_safety);
    if !has_controlled_contract {
        return false;
    }
    let contract = authority.profile_contract(language.key());
    let headings = [
        contract.arguments_label.as_str(),
        contract.returns_label.as_str(),
        contract.failures_label.as_str(),
    ];
    let mut controlled = false;
    lines.iter().any(|line| {
        if headings.contains(&line.as_str())
            || (language == Language::Cplusplus
                && documentation_heading(Language::Cplusplus, line))
            || (language == Language::Rust
                && requires_safety
                && line == "# Safety")
        {
            controlled = true;
            return false;
        }
        controlled
            && documentation_role_line_is_valid(language, line)
            && ends_in_sentence_terminator(line)
    })
}
/// 执行 `ends_in_sentence_terminator` 内部逻辑
fn ends_in_sentence_terminator(line: &str) -> bool {
    line.trim_end().ends_with(['。', '.'])
}
/// 将文档判定映射为 Authority 拥有的 Finding
fn push_documentation_findings(
    authority: &CompiledAuthority,
    document: &OwnedDocument,
    callable: &Callable,
    operator: RuleOperator,
    findings: &mut Vec<Finding>,
) {
    push_rule_findings(
        authority,
        operator,
        &document.path,
        callable.line,
        callable.column,
        &callable.name,
        &format!("observed attached documentation for {}", callable.name),
        findings,
    );
}

/// 从单一规则目录构造稳定 Finding
#[allow(clippy::too_many_arguments)]
fn push_rule_findings(
    authority: &CompiledAuthority,
    operator: RuleOperator,
    path: &str,
    line: usize,
    column: usize,
    subject: &str,
    observation: &str,
    findings: &mut Vec<Finding>,
) {
    let rule = authority.rule(operator);
    findings.push(Finding {
        rule: rule.identity.clone(),
        grade: rule.grade,
        path: path.to_owned(),
        line,
        column,
        subject: subject.to_owned(),
        observation: observation.to_owned(),
        question: rule.question.clone(),
        message: rule.message.clone(),
    });
}
/// 将 source rejection 投影为 Authority Finding 与 family blocker
fn close_source_rejection(
    authority: &CompiledAuthority,
    document: &OwnedDocument,
    physical_lines: u32,
    evidence: ParseEvidence,
) -> (Vec<Finding>, [FactFamilyState; 7]) {
    let method = &authority
        .profile_contract(document.language.key())
        .observation_method;
    let reason = format!(
        "observation method {method} rejected source at {}:{}: {}",
        evidence.line, evidence.column, evidence.reason
    );
    let mut findings = Vec::new();
    if authority.source_form == SourceForm::Direct {
        push_rule_findings(
            authority,
            RuleOperator::SourceForm,
            &document.path,
            evidence.line,
            evidence.column,
            "<source>",
            &reason,
            &mut findings,
        );
    }
    let blocked = || FactFamilyState::Blocked(reason.to_owned());
    let projection =
        |family| match authority.projection(family, document.language.key()) {
            ProjectionState::NotApplicable => FactFamilyState::NotRequired,
            ProjectionState::Supported | ProjectionState::NeedsAuthority => {
                blocked()
            }
        };
    (
        findings,
        [
            FactFamilyState::Complete(1),
            FactFamilyState::Complete(physical_lines),
            blocked(),
            projection("identifier"),
            projection("documentation"),
            if authority.families.contains("dependency") {
                projection("dependency")
            } else {
                FactFamilyState::NotRequired
            },
            FactFamilyState::NotRequired,
        ],
    )
}
/// 执行 `required_family_mask` 内部逻辑
fn required_family_mask(
    authority: &CompiledAuthority,
    language: Language,
) -> u8 {
    let mut mask = (1 << FactFamily::Capture as u8)
        | (1 << FactFamily::PhysicalLines as u8)
        | (1 << FactFamily::Structure as u8);
    for (family_name, family) in [
        ("identifier", FactFamily::Identifier),
        ("documentation", FactFamily::Documentation),
        ("dependency", FactFamily::DependencyDeclaration),
    ] {
        if authority.families.contains(family_name)
            && authority.projection(family_name, language.key())
                != ProjectionState::NotApplicable
        {
            mask |= 1 << family as u8;
        }
    }
    mask
}
impl FactFamily {
    /// 执行 `all` 内部逻辑
    fn all() -> [Self; 7] {
        [
            Self::Capture,
            Self::PhysicalLines,
            Self::Structure,
            Self::Identifier,
            Self::Documentation,
            Self::DependencyDeclaration,
            Self::DeclarationOrder,
        ]
    }
}
/// 执行 `finding_order` 内部逻辑
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
/// 执行 `seal` 内部逻辑
fn seal(
    authority: &CompiledAuthority,
    scope: ReviewedScope,
    results: Vec<FileResult>,
    metrics: ReviewMetrics,
) -> ReviewTerminal {
    for result in &results {
        if let Err(failure) = validate_family_closure(
            &result.path,
            result.required_mask,
            &result.families,
        ) {
            return ReviewTerminal::Failed(failure);
        }
    }
    let completion = if results
        .iter()
        .flat_map(|result| &result.families)
        .any(|state| matches!(state, FactFamilyState::Blocked(_)))
    {
        Completion::Incomplete
    } else {
        Completion::Complete
    };
    let mut snapshot_hasher = blake3::Hasher::new();
    let mut findings = Vec::new();
    let mut files = Vec::new();
    for result in results {
        snapshot_hasher.update(result.path.as_bytes());
        snapshot_hasher.update(&[0]);
        snapshot_hasher.update(&result.snapshot_digest);
        findings.extend(result.findings);
        let executed_mask = executed_mask(&result.families);
        let families =
            FactFamily::all().into_iter().zip(result.families).collect();
        files.push(FileCoverage {
            path: result.path,
            required_mask: result.required_mask,
            executed_mask,
            families,
        });
    }
    findings.sort_by(finding_order);
    let snapshot_digest = snapshot_hasher.finalize().to_hex().to_string();
    let semantic_authority_digest =
        blake3::Hash::from_bytes(authority.semantic_digest)
            .to_hex()
            .to_string();
    let coverage = CompactCoverage { files };
    let seal = compute_seal(
        &semantic_authority_digest,
        &snapshot_digest,
        &scope,
        completion,
        &coverage,
        &findings,
    );
    ReviewTerminal::Sealed(SealedReview {
        schema_version: 2,
        scope,
        completion,
        coverage,
        findings,
        metrics,
        semantic_authority_digest,
        snapshot_digest,
        seal,
        presentation: authority.presentation.clone(),
    })
}
/// 执行 `executed_mask` 内部逻辑
fn executed_mask(families: &[FactFamilyState; 7]) -> u8 {
    let mut executed = 0_u8;
    for (family, state) in FactFamily::all().into_iter().zip(families) {
        let bit = 1 << family as u8;
        if !matches!(state, FactFamilyState::NotRequired) {
            executed |= bit;
        }
    }
    executed
}
/// 执行 `validate_family_closure` 内部逻辑
fn validate_family_closure(
    path: &str,
    required: u8,
    families: &[FactFamilyState; 7],
) -> Result<(), ReviewFailure> {
    let executed = executed_mask(families);
    if required != executed {
        return Err(ReviewFailure::new(
            "closure.mask",
            format!(
                "{path} required mask {required:#04x} differs from executed mask {executed:#04x}"
            ),
        ));
    }
    Ok(())
}
/// 执行 `compute_seal` 内部逻辑
fn compute_seal(
    semantic_authority_digest: &str,
    snapshot_digest: &str,
    scope: &ReviewedScope,
    completion: Completion,
    coverage: &CompactCoverage,
    findings: &[Finding],
) -> String {
    let mut hasher = blake3::Hasher::new();
    hasher.update(b"csu-seal-v1\0");
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
    hasher.update(&[completion as u8]);
    hasher.update(&(coverage.files.len() as u64).to_le_bytes());
    for file in &coverage.files {
        hash_string(&mut hasher, &file.path);
        hasher.update(&[file.required_mask, file.executed_mask]);
        hasher.update(&(file.families.len() as u64).to_le_bytes());
        for (family, state) in &file.families {
            hasher.update(&[*family as u8]);
            match state {
                FactFamilyState::NotRequired => {
                    hasher.update(&[0]);
                }
                FactFamilyState::Complete(count) => {
                    hasher.update(&[1]);
                    hasher.update(&count.to_le_bytes());
                }
                FactFamilyState::Blocked(reason) => {
                    hasher.update(&[2]);
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
/// 执行 `hash_strings` 内部逻辑
fn hash_strings(hasher: &mut blake3::Hasher, values: &[String]) {
    hasher.update(&(values.len() as u64).to_le_bytes());
    for value in values {
        hash_string(hasher, value);
    }
}
/// 执行 `hash_string` 内部逻辑
fn hash_string(hasher: &mut blake3::Hasher, value: &str) {
    hasher.update(&(value.len() as u64).to_le_bytes());
    hasher.update(value.as_bytes());
}
