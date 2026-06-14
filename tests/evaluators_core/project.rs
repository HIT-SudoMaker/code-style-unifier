use crate::support::{profile, store_from_source};
use unifier::core::evaluators::core::evaluate;
use unifier::core::evaluators::evaluate_all;
use unifier::core::evidence::{
    DependencyEdgeFact, DependencyGroup, EvidenceStore, FileUnitFact, HistoryHealthFact,
    ModuleUnitFact, PublicSurfaceFact, SymbolFact, SymbolKind, SymbolVisibility,
};
use unifier::core::issue::{IssueKind, Language, Scope};

#[test]
fn generated_c_family_file_suppresses_hard_public_style_rules() {
    let store = store_from_source(
        "jimsh0.c",
        r#"
/* This is single source file, bootstrap version of Jim Tcl */
#define JIM_VERSION 81
typedef struct Jim_Obj Jim_Obj;
"#,
    );

    let issues = evaluate_all(&store, &profile());

    assert!(
        !issues
            .iter()
            .any(|issue| issue.rule == "Core011" || issue.rule == "Core014"),
        "generated C-family files must not emit hard public documentation or naming findings"
    );
}

#[test]
fn missing_file_facts_still_emit_core011_and_core014() {
    let mut store = EvidenceStore::empty_for_tests();
    store.public_surfaces.push(PublicSurfaceFact {
        id: "surface:missing".to_string(),
        symbol_name: "public_api".to_string(),
        visibility: "public".to_string(),
        has_doc_region: false,
        file_id: "file:missing".to_string(),
        range: "1:1-1:1".to_string(),
    });
    store.symbols.push(SymbolFact {
        id: "symbol:missing".to_string(),
        file_id: "file:missing".to_string(),
        module_id: "module:missing".to_string(),
        name: "RunTask".to_string(),
        qualified_name: "RunTask".to_string(),
        kind: SymbolKind::Function,
        visibility: SymbolVisibility::Public,
        language: Language::Python,
        range: "2:1-2:1".to_string(),
        doc_region_id: None,
        return_annotation: None,
        missing_parameter_annotations: Vec::new(),
        type_text: None,
        is_async: false,
        is_unsafe: false,
        attributes: Vec::new(),
    });

    let issues = evaluate(&store, &profile());

    assert!(
        issues.iter().any(|issue| issue.rule == "Core011"),
        "missing file metadata must not suppress public-doc findings"
    );
    assert!(
        issues.iter().any(|issue| issue.rule == "Core014"),
        "missing file metadata must not suppress naming findings"
    );
}

#[test]
fn core_project_file_and_dependency_rules_emit_expected_findings() {
    let mut store = EvidenceStore::empty_for_tests();
    store.history_health = Some(HistoryHealthFact {
        run_count: 31,
        oldest_run_age_days: 15,
        total_bytes: 536_870_913,
    });
    store.file_units.push(FileUnitFact {
        id: "file:py".to_string(),
        path: "utils.py".to_string(),
        language: Language::Python,
        generated: false,
        excluded: false,
        fingerprint: "hash:py".to_string(),
    });
    store.file_units.push(FileUnitFact {
        id: "file:rs".to_string(),
        path: "src/lib.rs".to_string(),
        language: Language::Rust,
        generated: false,
        excluded: false,
        fingerprint: "hash:rs".to_string(),
    });
    store.module_units.push(ModuleUnitFact {
        id: "module:py".to_string(),
        file_id: "file:py".to_string(),
        language: Language::Python,
        path: "utils.py".to_string(),
        range: "1:1-20:1".to_string(),
        has_module_doc_region: false,
        is_header: false,
        include_guard: None,
        pragma_once: false,
    });
    store.dependency_edges.push(DependencyEdgeFact {
        id: "dep:1".to_string(),
        file_id: "file:py".to_string(),
        module_id: "module:py".to_string(),
        group: DependencyGroup::Local,
        source: "b".to_string(),
        imported: "b".to_string(),
        alias: None,
        range: "1:1-1:9".to_string(),
        block_id: "module".to_string(),
        is_glob: false,
        is_public: false,
        is_relative: false,
        is_deferred: false,
        is_type_checking: false,
        is_conditional: false,
    });
    store.dependency_edges.push(DependencyEdgeFact {
        id: "dep:3".to_string(),
        file_id: "file:py".to_string(),
        module_id: "b".to_string(),
        group: DependencyGroup::Local,
        source: "module:py".to_string(),
        imported: "module:py".to_string(),
        alias: None,
        range: "3:1-3:18".to_string(),
        block_id: "module".to_string(),
        is_glob: false,
        is_public: false,
        is_relative: false,
        is_deferred: false,
        is_type_checking: false,
        is_conditional: false,
    });
    store.dependency_edges.push(DependencyEdgeFact {
        id: "dep:4".to_string(),
        file_id: "file:py".to_string(),
        module_id: "module:py".to_string(),
        group: DependencyGroup::Local,
        source: "..parent".to_string(),
        imported: "parent".to_string(),
        alias: None,
        range: "4:1-4:20".to_string(),
        block_id: "module".to_string(),
        is_glob: false,
        is_public: false,
        is_relative: true,
        is_deferred: false,
        is_type_checking: false,
        is_conditional: false,
    });
    store.dependency_edges.push(DependencyEdgeFact {
        id: "dep:2".to_string(),
        file_id: "file:py".to_string(),
        module_id: "module:py".to_string(),
        group: DependencyGroup::Local,
        source: "a".to_string(),
        imported: "*".to_string(),
        alias: None,
        range: "2:1-2:16".to_string(),
        block_id: "module".to_string(),
        is_glob: true,
        is_public: false,
        is_relative: false,
        is_deferred: false,
        is_type_checking: false,
        is_conditional: false,
    });

    let issues = evaluate(&store, &profile());
    let rules = issues
        .iter()
        .map(|issue| issue.rule.as_str())
        .collect::<Vec<_>>();

    assert!(rules.contains(&"Core001"));
    assert!(rules.contains(&"Core003"));
    assert!(rules.contains(&"Core004"));
    assert!(rules.contains(&"Core005"));
    assert!(rules.contains(&"Core006"));
    assert!(rules.contains(&"Core009"));
    assert!(rules.contains(&"Core010"));
    assert!(issues
        .iter()
        .any(|issue| { issue.rule == "Core010" && issue.kind == IssueKind::HardViolation }));
    assert!(issues
        .iter()
        .any(|issue| issue.rule == "Core003" && issue.scope == Scope::Project));
    assert!(issues
        .iter()
        .any(|issue| issue.rule == "Core004" && issue.scope == Scope::Project));
    assert!(issues
        .iter()
        .any(|issue| issue.rule == "Core005" && issue.kind == IssueKind::SoftFriction));
}

#[test]
fn core009_sorts_only_within_same_python_import_block() {
    let store = store_from_source(
        "module.py",
        concat!(
            "from zeta import Zeta\n",
            "\n",
            "def build_runtime():\n",
            "    from alpha import Alpha\n",
            "    return Alpha\n",
        ),
    );

    let issues = evaluate_all(&store, &profile());

    assert!(
        !issues.iter().any(|issue| issue.rule == "Core009"),
        "deferred imports must not be sorted against top-level imports"
    );
}

#[test]
fn core009_ignores_python_type_checking_import_boundary() {
    let store = store_from_source(
        "module.py",
        concat!(
            "from zeta import Zeta\n",
            "from typing import TYPE_CHECKING\n",
            "\n",
            "if TYPE_CHECKING:\n",
            "    from alpha import Alpha\n",
        ),
    );

    let issues = evaluate_all(&store, &profile());

    assert!(
        !issues.iter().any(|issue| issue.rule == "Core009"),
        "TYPE_CHECKING imports must not be sorted against runtime imports"
    );
}

#[test]
fn core009_still_reports_unsorted_python_imports_in_same_block() {
    let store = store_from_source(
        "module.py",
        "from zeta import Zeta\n\
from alpha import Alpha\n",
    );

    let issues = evaluate_all(&store, &profile());

    assert!(
        issues.iter().any(|issue| issue.rule == "Core009"),
        "imports in the same block remain subject to deterministic sorting"
    );
}

#[test]
fn file_name_rules_ignore_excluded_or_generated_files() {
    let mut store = EvidenceStore::empty_for_tests();
    store.file_units.push(FileUnitFact {
        id: "file:excluded".to_string(),
        path: "utils.py".to_string(),
        language: Language::Python,
        generated: false,
        excluded: true,
        fingerprint: "hash:excluded".to_string(),
    });
    store.file_units.push(FileUnitFact {
        id: "file:generated".to_string(),
        path: "helpers.rs".to_string(),
        language: Language::Rust,
        generated: true,
        excluded: false,
        fingerprint: "hash:generated".to_string(),
    });

    let issues = evaluate(&store, &profile());

    assert!(!issues.iter().any(|issue| issue.rule == "Core006"));
}
