const SKILL: &str = include_str!("../agent-skills/csu/SKILL.md");
const OUTPUT_TEMPLATE: &str = concat!(
    "classification: CodeCleanup | NarrowRuleContract | ",
    "BroadenRuleContract | AddProfilePolicy | KeepUnderReview\n",
    "rationale: <one sentence grounded in evidence, rule, kind, range, or profile>\n",
    "next_action: <specific file, profile, or calibration fixture>"
);

fn skill_text() -> String {
    SKILL.replace("\r\n", "\n")
}

#[test]
fn agent_skill_covers_required_commands() {
    assert!(SKILL.contains("csu check <path> --format json --output <file> --no-history"));
    assert!(SKILL.contains(
        "csu calibrate --issues <issues.json> --cases <cases.jsonl> --output <report.json>"
    ));
    assert!(SKILL.contains("csu rules --format json"));
}

#[test]
fn agent_skill_forbids_count_driven_decisions() {
    assert!(SKILL.contains("Do not optimize for findings count"));
    assert!(SKILL.contains("evidence"));
    assert!(SKILL.contains("rule boundary"));
    assert!(SKILL.contains("profile"));
}

#[test]
fn agent_skill_keeps_profile_boundaries_explicit() {
    assert!(SKILL.contains("Framework overrides and ABI names are profile policy"));
    assert!(SKILL.contains("NarrowRuleContract"));
    assert!(SKILL.contains("BroadenRuleContract"));
}

#[test]
fn agent_skill_stays_concise() {
    assert!(!SKILL.contains("### Core011"));
    assert!(!SKILL.contains("### Core018"));
    assert!(SKILL.lines().count() <= 40);
}

#[test]
fn agent_skill_output_format_is_exact_and_unique() {
    let skill = skill_text();
    assert!(skill.contains(OUTPUT_TEMPLATE));
    assert_eq!(skill.matches("classification:").count(), 1);
    assert_eq!(skill.matches("rationale:").count(), 1);
    assert_eq!(skill.matches("next_action:").count(), 1);
}
