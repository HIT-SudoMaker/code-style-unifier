use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::Path;

use assert_cmd::Command;
use unifier::core::issue::{IssueKind, Scope};
use unifier::core::rules::{RuleCatalog, RuleDefinition};

#[test]
fn catalog_contains_continuous_core_rules_and_l022_review_rule() {
    let catalog = RuleCatalog::from_toml_str(include_str!("../rules/catalog.toml")).unwrap();

    let core_ids: Vec<_> = catalog
        .rules
        .iter()
        .filter(|rule| rule.id.starts_with("Core"))
        .map(|rule| rule.id.as_str())
        .collect();

    assert_eq!(core_ids.first(), Some(&"Core001"));
    assert_eq!(core_ids.last(), Some(&"Core028"));
    assert_eq!(core_ids.len(), 28);

    let language_review = catalog.get("Core027").unwrap();
    assert_eq!(language_review.kind, IssueKind::UnderReview);
    assert_eq!(language_review.scope, Scope::Text);
    assert_eq!(language_review.source_ids, vec!["L022"]);
}

#[test]
fn catalog_distinguishes_contract_evidence_types_from_issue_evidence_refs() {
    let catalog = RuleCatalog::from_toml_str(include_str!("../rules/catalog.toml")).unwrap();
    let term = catalog.get("Core026").unwrap();
    let review = catalog.get("Core027").unwrap();

    assert_eq!(term.evidence_types, vec!["text_span"]);
    assert_eq!(review.evidence_types, vec!["text_span", "comment_region"]);
}

#[test]
fn catalog_contains_all_rule_families() {
    let catalog = RuleCatalog::from_toml_str(include_str!("../rules/catalog.toml")).unwrap();

    assert_eq!(
        catalog
            .rules
            .iter()
            .filter(|rule| rule.id.starts_with("Core"))
            .count(),
        28
    );
    assert_eq!(
        catalog
            .rules
            .iter()
            .filter(|rule| rule.id.starts_with("Py"))
            .count(),
        8
    );
    assert_eq!(
        catalog
            .rules
            .iter()
            .filter(|rule| rule.id.starts_with("Rust"))
            .count(),
        10
    );
    assert_eq!(
        catalog
            .rules
            .iter()
            .filter(|rule| rule.id.starts_with("Cpp"))
            .count(),
        10
    );
}

#[test]
fn every_catalog_rule_has_a_per_rule_toml_file() {
    let catalog = RuleCatalog::from_toml_str(include_str!("../rules/catalog.toml")).unwrap();
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("rules");

    for rule in catalog.rules {
        let path = root
            .join(family_dir(&rule.id))
            .join(format!("{}.{}.toml", rule.id, rule.name));
        assert!(
            path.is_file(),
            "missing per-rule TOML file: {}",
            path.display()
        );
    }
}

#[test]
fn every_per_rule_definition_matches_catalog_contract_and_filename() {
    let catalog = RuleCatalog::from_toml_str(include_str!("../rules/catalog.toml")).unwrap();
    let catalog_by_id: BTreeMap<_, _> = catalog
        .rules
        .iter()
        .map(|rule| (rule.id.as_str(), rule))
        .collect();
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("rules");
    let mut definition_ids = BTreeSet::new();

    for family in ["core", "python", "rust", "cpp", "typescript"] {
        for entry in fs::read_dir(root.join(family)).unwrap() {
            let path = entry.unwrap().path();
            if path.extension().and_then(|extension| extension.to_str()) != Some("toml") {
                continue;
            }

            let input = fs::read_to_string(&path).unwrap();
            let definition = RuleDefinition::from_toml_str(&input).unwrap();
            let expected_filename = format!("{}.{}.toml", definition.id, definition.name);

            assert_eq!(
                path.file_name().and_then(|name| name.to_str()),
                Some(expected_filename.as_str())
            );
            assert_eq!(
                &definition.contract(),
                *catalog_by_id
                    .get(definition.id.as_str())
                    .unwrap_or_else(|| panic!(
                        "per-rule definition missing from catalog: {}",
                        definition.id
                    ))
            );
            assert!(
                definition_ids.insert(definition.id.clone()),
                "duplicate per-rule definition ID: {}",
                definition.id
            );
        }
    }

    let catalog_ids: BTreeSet<_> = catalog.rules.iter().map(|rule| rule.id.clone()).collect();
    assert_eq!(definition_ids, catalog_ids);
}

#[test]
fn per_rule_schema_rejects_unknown_fields() {
    let input = r#"
id = "Core026"
name = "text.term_policy"
kind = "hard_violation"
scope = "text"
domain = "style"
languages = ["python", "rust", "c", "cpp"]
default_enabled = true
origin = "new"
source_ids = []
evidence_types = ["text_span"]
message = "Text must follow deterministic term policy."
unexpected = "field"
"#;

    assert!(RuleDefinition::from_toml_str(input).is_err());
}

#[test]
fn catalog_rejects_invalid_contract_invariants() {
    let invalid_catalogs = [
        duplicate_id_catalog(),
        duplicate_name_catalog(),
        empty_languages_catalog(),
        empty_evidence_types_catalog(),
        core_missing_language_catalog(),
        py_wrong_language_catalog(),
        rust_wrong_language_catalog(),
        cpp_wrong_language_catalog(),
        malformed_core_id_catalog(),
        malformed_rust_id_catalog(),
    ];

    for input in invalid_catalogs {
        assert!(
            RuleCatalog::from_toml_str(&input).is_err(),
            "catalog should be invalid:\n{input}"
        );
    }
}

#[test]
fn rule_catalog_does_not_frame_count_reduction_as_goal() {
    let catalog = RuleCatalog::from_toml_str(include_str!("../rules/catalog.toml")).unwrap();

    for rule in catalog.rules {
        for (field_name, field_value) in [
            ("id", rule.id.as_str()),
            ("name", rule.name.as_str()),
            ("message", rule.message.as_str()),
        ] {
            assert!(
                !catalog_field_contains_banned_count_wording(field_value),
                "{} {} must not describe count reduction as the goal",
                rule.id,
                field_name
            );
        }
    }
}

#[test]
fn catalog_count_wording_scan_matches_identifier_separated_phrases() {
    assert!(catalog_field_contains_banned_count_wording(
        "Policy has too many findings"
    ));
    assert!(catalog_field_contains_banned_count_wording(
        "Core999.reduce_findings"
    ));
    assert!(catalog_field_contains_banned_count_wording(
        "policy.findings.count.is.high"
    ));
}

#[test]
fn rules_json_marks_findings_count_as_non_goal() {
    let output = Command::cargo_bin("csu")
        .unwrap()
        .arg("rules")
        .arg("--format")
        .arg("json")
        .assert()
        .success()
        .get_output()
        .stdout
        .clone();
    let json: serde_json::Value = serde_json::from_slice(&output).unwrap();

    assert_eq!(
        json["findings_count_is_optimization_goal"],
        serde_json::json!(false)
    );
}

fn family_dir(id: &str) -> &'static str {
    if id.starts_with("Core") {
        "core"
    } else if id.starts_with("Py") {
        "python"
    } else if id.starts_with("Rust") {
        "rust"
    } else if id.starts_with("Cpp") {
        "cpp"
    } else if id.starts_with("Ts") {
        "typescript"
    } else {
        panic!("unknown rule family: {id}");
    }
}

fn duplicate_id_catalog() -> String {
    catalog_with_rules(&[
        core_rule(
            "Core001",
            "one",
            &["python", "rust", "c", "cpp"],
            &["workspace"],
        ),
        core_rule(
            "Core001",
            "two",
            &["python", "rust", "c", "cpp"],
            &["workspace"],
        ),
    ])
}

fn duplicate_name_catalog() -> String {
    catalog_with_rules(&[
        core_rule(
            "Core001",
            "same",
            &["python", "rust", "c", "cpp"],
            &["workspace"],
        ),
        core_rule(
            "Core002",
            "same",
            &["python", "rust", "c", "cpp"],
            &["workspace"],
        ),
    ])
}

fn empty_languages_catalog() -> String {
    catalog_with_rules(&[core_rule("Core001", "one", &[], &["workspace"])])
}

fn empty_evidence_types_catalog() -> String {
    catalog_with_rules(&[core_rule(
        "Core001",
        "one",
        &["python", "rust", "c", "cpp"],
        &[],
    )])
}

fn core_missing_language_catalog() -> String {
    catalog_with_rules(&[core_rule(
        "Core001",
        "one",
        &["python", "rust", "cpp"],
        &["workspace"],
    )])
}

fn py_wrong_language_catalog() -> String {
    catalog_with_rules(&[rule("Py001", "one", &["python", "rust"], &["module_unit"])])
}

fn rust_wrong_language_catalog() -> String {
    catalog_with_rules(&[rule("Rust001", "one", &["rust", "cpp"], &["workspace"])])
}

fn cpp_wrong_language_catalog() -> String {
    catalog_with_rules(&[rule("Cpp001", "one", &["python"], &["workspace"])])
}

fn malformed_core_id_catalog() -> String {
    catalog_with_rules(&[core_rule(
        "CoreXYZ",
        "one",
        &["python", "rust", "c", "cpp"],
        &["workspace"],
    )])
}

fn malformed_rust_id_catalog() -> String {
    catalog_with_rules(&[rule("Rust-old", "one", &["rust"], &["workspace"])])
}

fn catalog_with_rules(rules: &[String]) -> String {
    format!(
        "catalog_version = \"test\"\nrules = [\n{}\n]\n",
        rules.join(",\n")
    )
}

fn core_rule(id: &str, name: &str, languages: &[&str], evidence_types: &[&str]) -> String {
    rule(id, name, languages, evidence_types)
}

fn rule(id: &str, name: &str, languages: &[&str], evidence_types: &[&str]) -> String {
    format!(
        concat!(
            "  {{ id = {id:?}, name = {name:?}, kind = \"soft_friction\", ",
            "scope = \"project\", domain = \"project\", languages = {languages}, ",
            "default_enabled = true, origin = \"new\", source_ids = [], ",
            "evidence_types = {evidence_types}, message = \"message\" }}",
        ),
        id = id,
        name = name,
        languages = string_array(languages),
        evidence_types = string_array(evidence_types),
    )
}

fn string_array(items: &[&str]) -> String {
    let quoted = items
        .iter()
        .map(|item| format!("{item:?}"))
        .collect::<Vec<_>>()
        .join(", ");
    format!("[{quoted}]")
}

fn catalog_field_contains_banned_count_wording(field_value: &str) -> bool {
    let lowered = field_value.to_ascii_lowercase();
    let normalized = normalize_identifier_separators(&lowered);

    unifier::core::calibration::BANNED_COUNT_RATIONALES
        .iter()
        .any(|phrase| lowered.contains(phrase) || normalized.contains(phrase))
}

fn normalize_identifier_separators(text: &str) -> String {
    text.chars()
        .map(|character| {
            if character.is_ascii_alphanumeric() || !character.is_ascii() {
                character
            } else {
                ' '
            }
        })
        .collect::<String>()
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
}
