use unifier::core::profile::Profile;

#[test]
fn default_profile_parses_thresholds_and_terms() {
    let profile = Profile::from_toml_str(include_str!("../profiles/default.toml")).unwrap();

    assert_eq!(profile.name, "default");
    assert_eq!(profile.thresholds.line_length_limit, 100);
    assert_eq!(profile.thresholds.doc_summary_max_chars, 80);
    assert_eq!(profile.thresholds.history_max_runs, 30);
    assert_eq!(profile.thresholds.history_max_days, 14);
    assert_eq!(profile.thresholds.history_max_bytes, 536_870_912);
    assert!(profile
        .term_policy
        .allowed_abbreviation_tokens
        .contains(&"ssim".to_string()));
    assert_eq!(
        profile.term_policy.banned_abbreviation_tokens["ctx"],
        "context"
    );
}

#[test]
fn term_policy_separates_deterministic_tokens_from_natural_language() {
    let profile = Profile::from_toml_str(include_str!("../profiles/default.toml")).unwrap();

    assert!(profile.term_policy.is_allowed_abbreviation("SSIM"));
    assert!(profile.term_policy.is_banned_abbreviation("ctx"));
    assert!(!profile
        .term_policy
        .is_banned_abbreviation("This is English text"));
}

#[test]
fn term_policy_normalizes_abbreviation_tokens_from_profile() {
    let profile = Profile::from_toml_str(
        r#"
name = "mixed-case"
enabled_rules = []
exclude_dirs = []
exclude_file_patterns = []

[thresholds]
line_length_limit = 100
doc_summary_max_chars = 80
history_max_runs = 30
history_max_days = 14
history_max_bytes = 536870912

[term_policy]
allowed_abbreviation_tokens = ["SSIM"]
allowed_abbreviation_names = []
allowed_technical_fragments = ["SSIM"]

[term_policy.banned_abbreviation_tokens]
Ctx = "context"
"#,
    )
    .unwrap();

    assert!(profile.term_policy.is_allowed_abbreviation("ssim"));
    assert!(profile.term_policy.is_allowed_abbreviation("SSIM"));
    assert!(profile.term_policy.is_banned_abbreviation("ctx"));
    assert!(profile.term_policy.is_banned_abbreviation("CTX"));
}
