//! Diagnostic scale exercise, kept out of the production Interface module.
//!
//! The authority performs one complete audit before it trusts a workspace and
//! then reuses that verified state on the stable common path. To exercise
//! REPLAY itself at scale, each admitted event is committed through the
//! workspace's atomic commit (O(1) per event) while the projection is evolved
//! with the same `View::apply` the authority uses on replay. The public
//! `Authority::check` then replays the whole ledger from disk and must
//! reproduce exactly that projection, and stable `Authority::view` must answer
//! without replaying a single historical row. Timings are diagnostic output
//! only; there is no pass/fail threshold.

use base64::Engine;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Instant;

use crate::authority::lifecycle::{AdmittedEvent, Moment, Transition, View as AuthorityView};
use crate::authority::protocol::{Relation, Revision, CAPACITY_SCHEMA, PROPOSAL_SCHEMA};
use crate::workspace::{
    audit_count, historical_row_count, reset_audit_counters, AuthorityEventCommitRequest,
    AuthorityObjectCommitRequest, CommitError, StoredObjectReference, Workspace,
};
use crate::Authority;
use serde_json::json;

static SCALE_DIR_SEQUENCE: AtomicU64 = AtomicU64::new(0);

const VIEW_PROJECTION_KEY: &str = "authority_view";
const PROPOSAL_MEDIA_TYPE: &str = "application/vnd.metacraft.authority.proposal+json";
const BODY_MEDIA_TYPE: &str = "application/json";

fn fresh_dir(label: &str) -> PathBuf {
    let sequence = SCALE_DIR_SEQUENCE.fetch_add(1, Ordering::Relaxed);
    std::env::temp_dir().join(format!(
        "metacraft-scale-{label}-{}-{sequence}",
        std::process::id()
    ))
}

fn seed_event(
    workspace: &Workspace,
    view: &mut AuthorityView,
    previous_head: Option<String>,
    relation: Relation,
    body_bytes: Vec<u8>,
    capacity_limit: Option<u64>,
) -> Result<(String, StoredObjectReference, StoredObjectReference), String> {
    let body_object =
        Workspace::prepare_authority_object(&body_bytes, BODY_MEDIA_TYPE, &json!({}))?;
    let references = serde_json::to_value(relation.references())
        .map_err(|error| format!("seed_failed:{error}"))?;
    let relation_value =
        serde_json::to_value(&relation).map_err(|error| format!("seed_failed:{error}"))?;
    let proposal_value = json!({
        "body": {
            "bytes_base64": base64::engine::general_purpose::STANDARD.encode(&body_bytes),
            "descriptive_metadata": {},
            "media_type": BODY_MEDIA_TYPE,
            "structure_reference": null,
        },
        "references": references,
        "relation": relation_value,
        "schema_identifier": PROPOSAL_SCHEMA,
    });
    let proposal_bytes =
        serde_jcs::to_vec(&proposal_value).map_err(|error| format!("seed_failed:{error}"))?;
    let proposal_object = Workspace::prepare_authority_object(
        &proposal_bytes,
        PROPOSAL_MEDIA_TYPE,
        &json!({"object_kind": "Proposal"}),
    )?;
    let body_reference = body_object.object_reference.clone();
    let proposal_reference = proposal_object.object_reference.clone();
    let mut required = relation.references();
    required.push(proposal_reference.clone());
    required.push(body_reference.clone());
    view.apply(
        Transition {
            relation: &relation,
            proposal_reference: &proposal_reference,
            body_reference: &body_reference,
            capacity_limit,
        },
        Moment::Replay,
    )?;
    view.revision = Revision::committed();
    let projection = view.to_value()?;
    let event = AdmittedEvent::new(
        proposal_reference.clone(),
        body_reference.clone(),
        relation.references(),
        relation,
    );
    let event_payload = event.to_value()?;
    let commit = workspace
        .commit_authority_objects_and_event(AuthorityObjectCommitRequest {
            event: AuthorityEventCommitRequest {
                expected_ledger_head: previous_head.as_deref(),
                canonical_command_content_hash: &proposal_reference.content_hash,
                event_kind: "DecisionAdmitted",
                required_references: &required,
                event_payload: &event_payload,
                projection_key: VIEW_PROJECTION_KEY,
                projection_value: &projection,
            },
            prepared_objects: &[proposal_object, body_object],
        })
        .map_err(|error: CommitError| format!("seed_commit_failed:{error:?}"))?;
    Ok((commit.ledger_head, proposal_reference, body_reference))
}

fn reference_json(reference: &StoredObjectReference) -> String {
    serde_jcs::to_string(reference).expect("canonical reference")
}

fn exercise_stable_view(scale: u64) {
    let path = fresh_dir(&format!("seed-{scale}"));
    let workspace = Workspace::create(path.clone()).unwrap();
    let mut view = AuthorityView::empty();
    let mut head: Option<String> = None;

    let capacity_body = serde_jcs::to_vec(&json!({
        "limit": 1000_u64,
        "qualification_references": [],
        "schema_identifier": CAPACITY_SCHEMA,
        "scope": "work",
    }))
    .unwrap();
    let (next, _proposal, capacity_reference) = seed_event(
        &workspace,
        &mut view,
        head.take(),
        Relation::Current {
            key: "capacity:work".to_string(),
            supersedes: None,
        },
        capacity_body,
        Some(1000),
    )
    .unwrap();
    head = Some(next);

    let (next, _proposal, anchor_reference) = seed_event(
        &workspace,
        &mut view,
        head.take(),
        Relation::Current {
            key: "anchor".to_string(),
            supersedes: None,
        },
        br#"{"anchor":"root"}"#.to_vec(),
        None,
    )
    .unwrap();
    head = Some(next);

    let (next, permit_reference, _permit_body) = seed_event(
        &workspace,
        &mut view,
        head.take(),
        Relation::Permit {
            capacity_reference: capacity_reference.clone(),
            expires_at: "2099-01-01T00:00:00Z".to_string(),
            scope: "work".to_string(),
        },
        br#"{"work":"sample"}"#.to_vec(),
        Some(1000),
    )
    .unwrap();
    head = Some(next);

    let (next, _proposal, receipt_reference) = seed_event(
        &workspace,
        &mut view,
        head.take(),
        Relation::Receipt {
            permit_reference: permit_reference.clone(),
        },
        br#"{"observation":"complete"}"#.to_vec(),
        None,
    )
    .unwrap();
    head = Some(next);

    let seed_start = Instant::now();
    let mut last_record_reference: Option<StoredObjectReference> = None;
    for index in 0..scale {
        let body = format!(r#"{{"record":"event-{index}"}}"#).into_bytes();
        let (next, _proposal, record_reference) = seed_event(
            &workspace,
            &mut view,
            head.take(),
            Relation::Record,
            body,
            None,
        )
        .unwrap();
        head = Some(next);
        last_record_reference = Some(record_reference);
    }
    let seed_elapsed = seed_start.elapsed();

    // Reopen through the public seam: open performs one complete audit and
    // remembers the verified state.
    drop(workspace);
    reset_audit_counters();
    let open_start = Instant::now();
    let authority = Authority::open(path.clone()).unwrap();
    let open_elapsed = open_start.elapsed();
    let expected_events = scale + 4;
    let audits_after_open = audit_count();
    let rows_after_open = historical_row_count();
    assert_eq!(audits_after_open, 1, "scale {scale}: open audits once");

    // Explicit check always performs another complete audit.
    let check_start = Instant::now();
    let check = authority.check().unwrap();
    let check_elapsed = check_start.elapsed();
    assert_eq!(
        audit_count(),
        audits_after_open + 1,
        "scale {scale}: check audits once"
    );
    assert_eq!(
        check["workspace_valid"], true,
        "scale {scale}: workspace not valid after replay"
    );
    assert_eq!(check["ledger_event_count"], expected_events);

    // Stable view reuses the verified state: no historical rows, no audit.
    let rows_before_stable_view = historical_row_count();
    let audits_before_stable_view = audit_count();
    let view_start = Instant::now();
    let view_value = authority.view().unwrap();
    let view_elapsed = view_start.elapsed();
    assert_eq!(
        audit_count(),
        audits_before_stable_view,
        "scale {scale}: stable view performs no audit"
    );
    assert_eq!(
        historical_row_count(),
        rows_before_stable_view,
        "scale {scale}: stable view scans no historical row"
    );
    assert_eq!(
        view_value["revision"].as_str(),
        head.as_deref(),
        "scale {scale}: revision not preserved"
    );
    assert_eq!(
        view_value["decisions"].as_array().unwrap().len() as u64,
        expected_events
    );

    // Repeated stable view stays cheap and scans no history.
    let repeat_start = Instant::now();
    for _ in 0..16 {
        let _ = authority.view().unwrap();
    }
    let repeat_elapsed = repeat_start.elapsed();
    assert_eq!(
        audit_count(),
        audits_before_stable_view,
        "scale {scale}: repeated stable view performs no audit"
    );
    assert_eq!(
        historical_row_count(),
        rows_before_stable_view,
        "scale {scale}: repeated stable view scans no historical row"
    );

    let currents = view_value["current"].as_array().unwrap();
    assert_eq!(currents.len(), 2, "scale {scale}: current count");
    let capacity_current = currents
        .iter()
        .find(|entry| entry["key"] == "capacity:work")
        .expect("capacity current preserved");
    assert_eq!(
        capacity_current["body_reference"]["content_hash"],
        capacity_reference.content_hash
    );
    let anchor_current = currents
        .iter()
        .find(|entry| entry["key"] == "anchor")
        .expect("anchor current preserved");
    assert_eq!(
        anchor_current["body_reference"]["content_hash"],
        anchor_reference.content_hash
    );

    let permits = view_value["permits"].as_array().unwrap();
    assert_eq!(permits.len(), 1, "scale {scale}: permit count");
    assert_eq!(permits[0]["state"], "closed");
    assert_eq!(permits[0]["close_reason"], "consumed");
    assert_eq!(
        permits[0]["capacity_reference"]["content_hash"],
        capacity_reference.content_hash
    );

    // Object integrity: every admitted body stays fetchable at its exact
    // reference. `fetch` remains exact content-hash verification and never
    // substitutes the verified state.
    let fetched_record = authority
        .fetch(&reference_json(&last_record_reference.unwrap()))
        .unwrap();
    assert_eq!(
        fetched_record,
        format!(r#"{{"record":"event-{0}"}}"#, scale - 1).into_bytes()
    );
    let fetched_receipt = authority
        .fetch(&reference_json(&receipt_reference))
        .unwrap();
    assert_eq!(fetched_receipt, br#"{"observation":"complete"}"#);

    println!(
        "authority replay events={expected_events}: \
             seed {seed_elapsed:?}, open(audit) {open_elapsed:?}, \
             check(audit) {check_elapsed:?}, stable view {view_elapsed:?}, \
             16x stable view {repeat_elapsed:?}, \
             historical rows through open+check {rows_after_open}"
    );

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
#[ignore = "release diagnostic for 304 authority events"]
fn stable_view_reuses_one_complete_audit_at_304_events() {
    exercise_stable_view(300);
}

#[test]
#[ignore = "release diagnostic for 1,504 authority events"]
fn stable_view_reuses_one_complete_audit_at_1504_events() {
    exercise_stable_view(1_500);
}

#[test]
#[ignore = "release diagnostic for 3,004 authority events"]
fn stable_view_reuses_one_complete_audit_at_3004_events() {
    exercise_stable_view(3_000);
}
