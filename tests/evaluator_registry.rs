use std::collections::BTreeSet;

use unifier::core::evaluators::{evaluate_all, implemented_rule_ids};
use unifier::core::evidence::EvidenceStore;
use unifier::core::profile::Profile;
use unifier::core::rules::RuleCatalog;

#[test]
fn every_catalog_rule_has_registered_evaluator() {
    let catalog = RuleCatalog::from_toml_str(include_str!("../rules/catalog.toml")).unwrap();
    let catalog_ids = catalog
        .rules
        .iter()
        .map(|rule| rule.id.as_str())
        .collect::<BTreeSet<_>>();
    let implemented = implemented_rule_ids().into_iter().collect::<BTreeSet<_>>();

    assert_eq!(implemented, catalog_ids);
}

#[test]
fn evaluate_all_respects_empty_evidence_without_panicking() {
    let profile = Profile::from_toml_str(include_str!("../profiles/default.toml")).unwrap();
    let store = EvidenceStore::empty_for_tests();

    let issues = evaluate_all(&store, &profile);

    assert!(issues.is_empty());
}
