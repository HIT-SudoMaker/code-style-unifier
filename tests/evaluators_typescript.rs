mod support;

use std::fs;

use support::{profile, store_from_source};
use tempfile::tempdir;
use unifier::core::evaluators::evaluate_all;
use unifier::core::evidence::{DependencyGroup, EvidenceStore, SymbolKind, SymbolVisibility};
use unifier::core::frontend::extract_text_evidence;
use unifier::core::issue::Language;
use unifier::core::scanner::scan_workspace;

// 在临时工作区写入多个文件后提取证据，用于跨文件漂移规则测试
fn store_from_files(files: &[(&str, &str)]) -> EvidenceStore {
    let dir = tempdir().unwrap();
    for (path, source) in files {
        let full = dir.path().join(path);
        if let Some(parent) = full.parent() {
            fs::create_dir_all(parent).unwrap();
        }
        fs::write(full, source).unwrap();
    }
    let state = scan_workspace(dir.path(), &[]).unwrap();
    extract_text_evidence(&state).unwrap()
}

#[test]
fn typescript_extraction_emits_symbols_imports_and_docs() {
    let store = store_from_source(
        "widget.tsx",
        "import { useState } from \"react\";\n\
         import { db } from \"@/lib/db\";\n\
         import type { Foo } from \"./foo\";\n\
         \n\
         /** Returns the greeting. */\n\
         export function getGreeting(name: string): string {\n\
         \treturn name;\n\
         }\n\
         \n\
         export interface FooProps {\n\
         \tid: number;\n\
         }\n",
    );

    let greeting = store
        .symbols
        .iter()
        .find(|symbol| symbol.name == "getGreeting")
        .expect("getGreeting symbol");
    assert_eq!(greeting.kind, SymbolKind::Function);
    assert_eq!(greeting.visibility, SymbolVisibility::Public);
    assert_eq!(greeting.language, Language::Typescript);
    assert!(greeting.doc_region_id.is_some(), "TSDoc should bind to the symbol");

    let props = store
        .symbols
        .iter()
        .find(|symbol| symbol.name == "FooProps")
        .expect("FooProps symbol");
    assert_eq!(props.kind, SymbolKind::TypeAlias);
    assert!(props.attributes.iter().any(|a| a == "interface"));

    let react = store
        .dependency_edges
        .iter()
        .find(|edge| edge.source == "react")
        .expect("react import edge");
    assert_eq!(react.group, DependencyGroup::ThirdParty);

    let local = store
        .dependency_edges
        .iter()
        .find(|edge| edge.source == "@/lib/db")
        .expect("alias import edge");
    assert_eq!(local.group, DependencyGroup::Local);
    assert!(local.is_relative);

    let type_import = store
        .dependency_edges
        .iter()
        .find(|edge| edge.source == "./foo")
        .expect("type-only import edge");
    assert!(type_import.is_type_checking, "import type sets is_type_checking");

    // The exported, documented function carries a public surface with a doc region.
    assert!(store
        .public_surfaces
        .iter()
        .any(|surface| surface.symbol_name == "getGreeting" && surface.has_doc_region));
}

#[test]
fn core014_allows_idiomatic_typescript_names() {
    let store = store_from_source(
        "ok.tsx",
        "export function getGreeting(): string {\n\treturn \"\";\n}\n\
         export const useCounter = () => 0;\n\
         export function UserCard(): null {\n\treturn null;\n}\n\
         export const MAX_USERS = 100;\n\
         export interface UserProps {\n\tid: number;\n}\n\
         export async function GET(): Promise<void> {}\n",
    );

    let issues = evaluate_all(&store, &profile());
    let core014: Vec<_> = issues
        .iter()
        .filter(|issue| issue.rule == "Core014")
        .collect();
    assert!(
        core014.is_empty(),
        "idiomatic TS/React names must not trigger Core014, got: {:?}",
        core014.iter().map(|i| &i.range).collect::<Vec<_>>()
    );
}

#[test]
fn core014_flags_snake_case_typescript_function() {
    let store = store_from_source(
        "bad.ts",
        "export function bad_name(): void {}\n",
    );

    let issues = evaluate_all(&store, &profile());
    assert!(
        issues
            .iter()
            .any(|issue| issue.rule == "Core014" && issue.kind.blocks()),
        "snake_case TS function must be a Core014 hard violation"
    );
}

#[test]
fn typescript_export_style_drift_reports_ts001() {
    let store = store_from_files(&[
        ("widget/Alpha.tsx", "export default function Alpha() { return null; }\n"),
        ("widget/Beta.tsx", "export function Beta() { return null; }\n"),
        ("widget/Gamma.tsx", "export function Gamma() { return null; }\n"),
    ]);

    let issues = evaluate_all(&store, &profile());
    let ts001: Vec<_> = issues.iter().filter(|i| i.rule == "Ts001").collect();
    assert_eq!(ts001.len(), 1, "minority default-export file should be flagged once");
    assert!(ts001[0].path.as_deref().unwrap().ends_with("Alpha.tsx"));
}

#[test]
fn typescript_props_style_drift_reports_ts003() {
    let store = store_from_source(
        "types.ts",
        "export interface AProps { id: number }\n\
         export interface BProps { id: number }\n\
         export type CProps = { id: number };\n",
    );

    let issues = evaluate_all(&store, &profile());
    let ts003: Vec<_> = issues.iter().filter(|i| i.rule == "Ts003").collect();
    assert_eq!(ts003.len(), 1, "minority `type` Props should be flagged");
}

#[test]
fn typescript_comment_language_drift_reports_ts002() {
    let store = store_from_source(
        "mixed.ts",
        "// first english comment line\n\
         // second english comment line\n\
         // third english comment line\n\
         // fourth english comment line\n\
         // 这是一个需要审查的中文注释\n\
         export const value = 1;\n",
    );

    let issues = evaluate_all(&store, &profile());
    let ts002: Vec<_> = issues.iter().filter(|i| i.rule == "Ts002").collect();
    assert_eq!(ts002.len(), 1, "minority-language comment should be flagged once");
}
