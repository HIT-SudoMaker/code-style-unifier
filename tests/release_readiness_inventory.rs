use serde_json::Value;

const SAMPLE_ISSUES: &str =
    include_str!("fixtures/release_readiness/self_check_sample_issues.json");

#[test]
fn release_readiness_sample_contains_all_blocking_paths() {
    let value: Value = serde_json::from_str(SAMPLE_ISSUES).unwrap();
    let issues = value["issues"].as_array().unwrap();
    let rules = issues
        .iter()
        .map(|issue| issue["rule"].as_str().unwrap())
        .collect::<std::collections::BTreeSet<_>>();

    for rule in ["Core011", "Core015", "Core018", "Core019"] {
        assert!(rules.contains(rule), "missing {rule} sample");
    }
}

#[test]
fn release_readiness_samples_are_real_blocking_findings() {
    let value: Value = serde_json::from_str(SAMPLE_ISSUES).unwrap();
    for issue in value["issues"].as_array().unwrap() {
        assert_eq!(issue["blocks"], true);
        assert!(issue["id"].as_str().unwrap().starts_with("issue:"));
        assert!(!issue["path"].as_str().unwrap().trim().is_empty());
        assert!(!issue["evidence"].as_array().unwrap().is_empty());
    }
}
