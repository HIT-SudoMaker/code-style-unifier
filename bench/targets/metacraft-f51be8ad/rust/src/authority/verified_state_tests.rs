//! Private verified-state regression and focused scenarios.
//!
//! These tests drive the public `Authority` seam (open / check / view / fetch /
//! decide) and observe the test-only structural counters in `workspace` to
//! prove that the stable common path reuses one complete audit and re-audits
//! only when durable storage changes outside that proof. Production callers
//! receive no new diagnostic verb: the counters are visible only inside the
//! crate's test configuration.

use std::path::{Path, PathBuf};

use base64::Engine;
use serde_json::{json, Value};

use crate::workspace::{audit_count, historical_row_count, reset_audit_counters};
use crate::Authority;

fn fresh_dir(label: &str) -> PathBuf {
    static SEQUENCE: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let next = SEQUENCE.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
    std::env::temp_dir().join(format!(
        "metacraft-verified-{label}-{}-{next}",
        std::process::id()
    ))
}

fn record_proposal(body: &[u8]) -> String {
    serde_jcs::to_string(&json!({
        "body": {
            "bytes_base64": base64::engine::general_purpose::STANDARD.encode(body),
            "descriptive_metadata": {},
            "media_type": "application/json",
            "structure_reference": null,
        },
        "references": [],
        "relation": {"kind": "record"},
        "schema_identifier": "metacraft.authority.proposal",
    }))
    .unwrap()
}

fn sqlite(path: &Path) -> rusqlite::Connection {
    rusqlite::Connection::open(path.join("workspace.sqlite3")).unwrap()
}

fn decide_at(authority: &Authority, proposal: &str, at: &str) -> Value {
    authority.decide(proposal, at).unwrap()
}

fn revision_of(value: &Value) -> String {
    value["resulting_revision"].as_str().unwrap().to_string()
}

#[test]
fn stable_view_reuses_verified_state_without_any_historical_scan() {
    let path = fresh_dir("stable-view");
    let authority = Authority::open(path.clone()).unwrap();
    let admit = decide_at(&authority, &record_proposal(br#"{"k":1}"#), "root");
    let revision = revision_of(&admit);

    reset_audit_counters();
    let rows_before = historical_row_count();
    let audits_before = audit_count();
    for _ in 0..4 {
        let view = authority.view().unwrap();
        assert_eq!(view["revision"].as_str(), Some(revision.as_str()));
        assert_eq!(view["decisions"].as_array().unwrap().len(), 1);
    }
    assert_eq!(audit_count(), audits_before, "stable view must not audit");
    assert_eq!(
        historical_row_count(),
        rows_before,
        "stable view must scan no historical rows"
    );

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn open_performs_one_complete_audit_and_check_performs_one_more() {
    let path = fresh_dir("open-audit");
    let authority = Authority::open(path.clone()).unwrap();
    let _ = decide_at(&authority, &record_proposal(br#"{"k":1}"#), "root");
    drop(authority);

    reset_audit_counters();
    let authority = Authority::open(path.clone()).unwrap();
    assert_eq!(
        audit_count(),
        1,
        "open must perform exactly one complete audit"
    );
    let rows_after_open = historical_row_count();
    assert!(rows_after_open > 0, "open must replay historical rows");

    reset_audit_counters();
    let check = authority.check().unwrap();
    assert_eq!(check["workspace_valid"], true);
    assert_eq!(
        audit_count(),
        1,
        "check must perform exactly one complete audit"
    );

    reset_audit_counters();
    let _ = authority.view().unwrap();
    assert_eq!(audit_count(), 0, "stable view after check reuses the proof");

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn local_commit_advances_verified_revision_and_view_without_replay() {
    let path = fresh_dir("commit-advance");
    let authority = Authority::open(path.clone()).unwrap();

    reset_audit_counters();
    let first = decide_at(&authority, &record_proposal(br#"{"k":1}"#), "root");
    let first_revision = revision_of(&first);
    assert_eq!(
        audit_count(),
        0,
        "decide at the verified head performs no audit"
    );
    let second = decide_at(&authority, &record_proposal(br#"{"k":2}"#), &first_revision);
    let second_revision = revision_of(&second);
    assert_ne!(second_revision, first_revision);
    assert_eq!(
        audit_count(),
        0,
        "successive commits reuse the verified proof"
    );

    reset_audit_counters();
    let view = authority.view().unwrap();
    assert_eq!(view["revision"].as_str(), Some(second_revision.as_str()));
    assert_eq!(view["decisions"].as_array().unwrap().len(), 2);
    assert_eq!(audit_count(), 0);

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn rejection_and_stale_revision_do_not_advance_verified_state() {
    let path = fresh_dir("no-advance");
    let authority = Authority::open(path.clone()).unwrap();
    let admit = decide_at(&authority, &record_proposal(br#"{"k":1}"#), "root");
    let revision = revision_of(&admit);

    reset_audit_counters();
    let stale = decide_at(&authority, &record_proposal(br#"{"k":2}"#), "root");
    assert_eq!(stale["outcome"], "rejected");
    assert_eq!(stale["findings"], json!(["revision_mismatch"]));
    assert_eq!(stale["resulting_revision"], revision);
    assert_eq!(
        audit_count(),
        0,
        "rejection at the verified head performs no audit"
    );

    let surplus = serde_jcs::to_string(&json!({
        "body": {
            "bytes_base64": base64::engine::general_purpose::STANDARD.encode(br#"{"k":3}"#),
            "descriptive_metadata": {},
            "media_type": "application/json",
            "structure_reference": null,
        },
        "references": [{
            "content_hash": format!("sha256:{}", "a".repeat(64)),
            "media_type": "application/json",
            "metadata_content_hash": format!("sha256:{}", "b".repeat(64)),
            "size_bytes": 1,
        }],
        "relation": {"kind": "record"},
        "schema_identifier": "metacraft.authority.proposal",
    }))
    .unwrap();
    let rejected = decide_at(&authority, &surplus, &revision);
    assert_eq!(rejected["outcome"], "rejected");
    assert_eq!(rejected["resulting_revision"], revision);

    reset_audit_counters();
    let view = authority.view().unwrap();
    assert_eq!(view["revision"].as_str(), Some(revision.as_str()));
    assert_eq!(view["decisions"].as_array().unwrap().len(), 1);
    assert_eq!(audit_count(), 0);

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn another_authority_commit_invalidates_and_triggers_exactly_one_refresh() {
    let path = fresh_dir("external-commit");
    let alpha = Authority::open(path.clone()).unwrap();
    let first = decide_at(&alpha, &record_proposal(br#"{"k":1}"#), "root");
    let first_revision = revision_of(&first);

    let beta = Authority::open(path.clone()).unwrap();
    let second = decide_at(&beta, &record_proposal(br#"{"k":2}"#), &first_revision);
    let second_revision = revision_of(&second);
    assert_eq!(
        second_revision,
        *beta.view().unwrap()["revision"].as_str().unwrap(),
    );

    reset_audit_counters();
    let view = alpha.view().unwrap();
    assert_eq!(
        view["revision"].as_str(),
        Some(second_revision.as_str()),
        "alpha must observe beta's commit after one refresh"
    );
    assert_eq!(
        audit_count(),
        1,
        "external change triggers exactly one re-audit"
    );
    assert!(historical_row_count() > 0);

    reset_audit_counters();
    let _ = alpha.view().unwrap();
    assert_eq!(
        audit_count(),
        0,
        "the refreshed proof is reused on the next call"
    );

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn audit_and_generation_capture_exclude_an_interleaving_writer() {
    let path = fresh_dir("audit-generation");
    let alpha = std::sync::Arc::new(Authority::open(path.clone()).unwrap());
    let beta = std::sync::Arc::new(Authority::open(path.clone()).unwrap());
    let first = decide_at(&beta, &record_proposal(br#"{"k":1}"#), "root");
    let first_revision = revision_of(&first);

    let audit_reached = std::sync::Arc::new(std::sync::Barrier::new(2));
    let audit_release = std::sync::Arc::new(std::sync::Barrier::new(2));
    alpha.pause_after_next_audit(audit_reached.clone(), audit_release.clone());

    let viewing = {
        let alpha = alpha.clone();
        std::thread::spawn(move || alpha.view().unwrap())
    };
    audit_reached.wait();

    let (committed_tx, committed_rx) = std::sync::mpsc::channel();
    let deciding = {
        let beta = beta.clone();
        std::thread::spawn(move || {
            let decision = decide_at(&beta, &record_proposal(br#"{"k":2}"#), &first_revision);
            committed_tx.send(decision.clone()).unwrap();
            decision
        })
    };
    assert!(
        committed_rx
            .recv_timeout(std::time::Duration::from_millis(250))
            .is_err(),
        "another writer must wait until audit and generation are bound"
    );

    audit_release.wait();
    let audited_view = viewing.join().unwrap();
    assert_eq!(
        audited_view["revision"], first["resulting_revision"],
        "the refreshed view belongs to the generation held during its audit"
    );

    let second = committed_rx
        .recv_timeout(std::time::Duration::from_secs(5))
        .unwrap();
    assert_eq!(deciding.join().unwrap(), second);
    let refreshed = alpha.view().unwrap();
    assert_eq!(refreshed["revision"], second["resulting_revision"]);
    assert_eq!(refreshed["decisions"].as_array().unwrap().len(), 2);

    drop(alpha);
    drop(beta);
    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn restart_reconstructs_truth_from_durable_history() {
    let path = fresh_dir("restart");
    let authority = Authority::open(path.clone()).unwrap();
    let admit = decide_at(&authority, &record_proposal(br#"{"k":1}"#), "root");
    let revision = revision_of(&admit);
    drop(authority);

    reset_audit_counters();
    let reopened = Authority::open(path.clone()).unwrap();
    assert_eq!(audit_count(), 1, "restart performs one complete audit");
    let view = reopened.view().unwrap();
    assert_eq!(view["revision"].as_str(), Some(revision.as_str()));
    assert_eq!(view["decisions"].as_array().unwrap().len(), 1);

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn tampered_projection_leaves_handle_unverified_and_fails_closed() {
    let path = fresh_dir("tamper-projection");
    let authority = Authority::open(path.clone()).unwrap();
    let _ = decide_at(&authority, &record_proposal(br#"{"k":1}"#), "root");
    sqlite(&path)
        .execute(
            "UPDATE projections SET projection_json='{}' WHERE projection_key='authority_view'",
            [],
        )
        .unwrap();

    let first = authority.view();
    assert!(
        first
            .unwrap_err()
            .starts_with("workspace_integrity_failed:"),
        "tampered projection must fail closed"
    );
    let second = authority.view();
    assert!(
        second
            .unwrap_err()
            .starts_with("workspace_integrity_failed:"),
        "failed refresh leaves the handle unverified (no stale view)"
    );
    let rejected = authority.decide(&record_proposal(br#"{"k":2}"#), "root");
    assert!(
        rejected
            .unwrap_err()
            .starts_with("workspace_integrity_failed:"),
        "decide through an unverified handle fails closed"
    );

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn generation_observation_failure_forgets_the_verified_state() {
    let path = fresh_dir("generation-failure");
    let authority = Authority::open(path.clone()).unwrap();
    let admit = decide_at(&authority, &record_proposal(br#"{"k":1}"#), "root");
    let revision = revision_of(&admit);
    let database = path.join("workspace.sqlite3");
    let displaced = path.join("workspace.displaced.sqlite3");

    std::fs::rename(&database, &displaced).unwrap();
    std::fs::create_dir(&database).unwrap();
    let failed = authority.view().unwrap_err();
    assert!(
        failed.starts_with("workspace_database_failed:")
            || failed.starts_with("database_open_failed:")
            || failed.starts_with("workspace_generation_failed:"),
        "generation observation must fail exactly, got {failed}"
    );
    std::fs::remove_dir(&database).unwrap();
    std::fs::rename(&displaced, &database).unwrap();

    reset_audit_counters();
    let restored = authority.view().unwrap();
    assert_eq!(restored["revision"].as_str(), Some(revision.as_str()));
    assert_eq!(
        audit_count(),
        1,
        "a recovered handle must re-audit after observation failure"
    );

    std::fs::remove_dir_all(path).unwrap();
}

fn run_fail_closed_case(label: &str, tamper: impl Fn(&Path)) {
    let path = fresh_dir(&format!("tamper-{label}"));
    let authority = Authority::open(path.clone()).unwrap();
    let _ = decide_at(&authority, &record_proposal(br#"{"k":1}"#), "root");
    tamper(&path);

    reset_audit_counters();
    let attempted = authority.view();
    assert!(
        attempted.is_err(),
        "tampered {label} must fail closed (got {attempted:?})"
    );
    assert!(
        audit_count() <= 1,
        "tampered {label} refresh attempts at most one complete audit"
    );

    let again = authority.view();
    assert!(again.is_err(), "tampered {label} must stay unverified");

    std::fs::remove_dir_all(&path).unwrap();
}

#[test]
fn each_governed_durable_identity_failure_triggers_one_fail_closed_refresh() {
    run_fail_closed_case("projection", |path| {
        sqlite(path)
            .execute(
                "UPDATE projections SET projection_json='{}' \
                 WHERE projection_key='authority_view'",
                [],
            )
            .unwrap();
    });
    run_fail_closed_case("head", |path| {
        sqlite(path)
            .execute(
                "UPDATE metadata SET value='sha256:deadbeef' WHERE key='ledger_head'",
                [],
            )
            .unwrap();
    });
    run_fail_closed_case("object", |path| {
        sqlite(path)
            .execute(
                "UPDATE objects SET raw_bytes = X'00' \
                 WHERE content_hash = (SELECT content_hash FROM objects LIMIT 1)",
                [],
            )
            .unwrap();
    });
    run_fail_closed_case("event", |path| {
        sqlite(path)
            .execute("UPDATE ledger SET event_json='{}' WHERE sequence=1", [])
            .unwrap();
    });
    run_fail_closed_case("marker", |path| {
        std::fs::write(path.join("workspace.marker"), b"not a workspace\n").unwrap();
    });
    run_fail_closed_case("database", |path| {
        std::fs::write(path.join("workspace.sqlite3"), b"not a sqlite database").unwrap();
    });
}

#[test]
fn race_two_authority_handles_admits_at_most_one_winner() {
    let path = fresh_dir("race");
    let setup = Authority::open(path.clone()).unwrap();
    let admit = decide_at(&setup, &record_proposal(br#"{"seed":true}"#), "root");
    let revision = revision_of(&admit);
    drop(setup);

    let barrier = std::sync::Arc::new(std::sync::Barrier::new(2));
    let mut workers = Vec::new();
    for label in ["alpha", "beta"] {
        let path = path.clone();
        let barrier = barrier.clone();
        let revision = revision.clone();
        workers.push(std::thread::spawn(move || {
            let authority = Authority::open(path).unwrap();
            barrier.wait();
            decide_at(
                &authority,
                &record_proposal(format!(r#"{{"work":"{label}"}}"#).as_bytes()),
                &revision,
            )
        }));
    }
    let decisions: Vec<Value> = workers.into_iter().map(|w| w.join().unwrap()).collect();
    let admitted = decisions
        .iter()
        .filter(|decision| decision["outcome"] == "admitted")
        .count();
    let rejected = decisions
        .iter()
        .filter(|decision| decision["findings"] == json!(["revision_mismatch"]))
        .count();
    assert_eq!(admitted, 1, "exactly one race winner is admitted");
    assert_eq!(
        rejected, 1,
        "exactly one race loser is rejected for stale revision"
    );

    let final_view = Authority::open(path.clone()).unwrap().view().unwrap();
    assert_eq!(final_view["decisions"].as_array().unwrap().len(), 2);

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn fetch_verifies_content_hash_before_and_after_a_verified_refresh() {
    let path = fresh_dir("fetch-exact");
    let authority = Authority::open(path.clone()).unwrap();
    let admit = decide_at(&authority, &record_proposal(br#"{"k":1}"#), "root");
    let body_reference = admit["body_reference"].clone();
    let reference_json = serde_jcs::to_string(&body_reference).unwrap();
    let first_revision = revision_of(&admit);

    reset_audit_counters();
    let valid_bytes = authority.fetch(&reference_json).unwrap();
    assert_eq!(valid_bytes, br#"{"k":1}"#);
    assert_eq!(audit_count(), 0, "fetch never performs an audit");

    sqlite(&path)
        .execute(
            "UPDATE objects SET raw_bytes = X'deadbeef' WHERE content_hash = ?1",
            rusqlite::params![body_reference["content_hash"].as_str().unwrap()],
        )
        .unwrap();
    let corrupt = authority.fetch(&reference_json).unwrap_err();
    assert!(
        corrupt.starts_with("reference_unresolvable:"),
        "fetch must reject a corrupt object exactly, got {corrupt}"
    );

    sqlite(&path)
        .execute(
            "UPDATE objects SET raw_bytes = ?1 WHERE content_hash = ?2",
            rusqlite::params![
                valid_bytes.as_slice(),
                body_reference["content_hash"].as_str().unwrap()
            ],
        )
        .unwrap();

    let beta = Authority::open(path.clone()).unwrap();
    let second = decide_at(&beta, &record_proposal(br#"{"k":2}"#), &first_revision);
    let second_body_reference = second["body_reference"].clone();
    let second_reference_json = serde_jcs::to_string(&second_body_reference).unwrap();

    reset_audit_counters();
    let refreshed = authority.view().unwrap();
    assert_eq!(
        refreshed["revision"].as_str(),
        Some(second["resulting_revision"].as_str().unwrap()),
        "alpha refreshes to beta's commit"
    );
    assert_eq!(audit_count(), 1);

    assert_eq!(authority.fetch(&reference_json).unwrap(), br#"{"k":1}"#);
    assert_eq!(
        authority.fetch(&second_reference_json).unwrap(),
        br#"{"k":2}"#
    );

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn failed_commit_does_not_advance_verified_state() {
    let path = fresh_dir("failed-commit");
    let authority = Authority::open(path.clone()).unwrap();
    let admit = decide_at(&authority, &record_proposal(br#"{"k":1}"#), "root");
    let revision = revision_of(&admit);

    let beta = Authority::open(path.clone()).unwrap();
    let interfering = decide_at(&beta, &record_proposal(br#"{"k":2}"#), &revision);
    let interfering_revision = revision_of(&interfering);
    assert_ne!(interfering_revision, revision);

    reset_audit_counters();
    let stale = decide_at(&authority, &record_proposal(br#"{"k":3}"#), &revision);
    assert_eq!(stale["outcome"], "rejected");
    assert_eq!(stale["findings"], json!(["revision_mismatch"]));
    let view = authority.view().unwrap();
    assert_eq!(
        view["revision"].as_str(),
        Some(interfering_revision.as_str()),
        "alpha catches up to durable truth, not to its stale offer"
    );

    std::fs::remove_dir_all(path).unwrap();
}
