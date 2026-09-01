use std::path::PathBuf;

use _authority::Authority;
use base64::Engine;
use chrono::{Duration, SecondsFormat, Utc};

fn fresh_workspace(label: &str) -> PathBuf {
    std::env::temp_dir().join(format!(
        "metacraft-authority-{label}-{}",
        uuid::Uuid::new_v4()
    ))
}

fn proposal(
    body: &[u8],
    references: Vec<serde_json::Value>,
    relation: serde_json::Value,
) -> String {
    serde_jcs::to_string(&serde_json::json!({
        "body": {
            "bytes_base64": base64::engine::general_purpose::STANDARD.encode(body),
            "descriptive_metadata": {},
            "media_type": "application/json",
            "structure_reference": null,
        },
        "references": references,
        "relation": relation,
        "schema_identifier": "metacraft.authority.proposal",
    }))
    .unwrap()
}

fn structured_proposal(body: &[u8], structure_reference: serde_json::Value) -> String {
    serde_jcs::to_string(&serde_json::json!({
        "body": {
            "bytes_base64": base64::engine::general_purpose::STANDARD.encode(body),
            "descriptive_metadata": {},
            "media_type": "application/json",
            "structure_reference": structure_reference,
        },
        "references": [structure_reference],
        "relation": {"kind": "record"},
        "schema_identifier": "metacraft.authority.proposal",
    }))
    .unwrap()
}

fn canonical_body(value: serde_json::Value) -> Vec<u8> {
    serde_jcs::to_vec(&value).unwrap()
}

fn capacity_body(limit: u64) -> Vec<u8> {
    canonical_body(serde_json::json!({
        "limit": limit,
        "qualification_references": [],
        "schema_identifier": "metacraft.authority.capacity",
        "scope": "solver",
    }))
}

#[test]
fn canonical_json_orders_raw_property_names_by_utf16() {
    assert_eq!(
        canonical_body(serde_json::json!({
            "silicon": 1,
            "silicon dioxide": 2,
        })),
        br#"{"silicon":1,"silicon dioxide":2}"#,
    );
    assert_eq!(
        canonical_body(serde_json::json!({
            "\u{e000}": 1,
            "\u{10000}": 2,
        })),
        "{\"\u{10000}\":2,\"\u{e000}\":1}".as_bytes(),
    );
}

#[test]
fn new_authority_reports_one_stable_protocol_and_empty_view() {
    let path = fresh_workspace("empty-view");
    let authority = Authority::open(path.clone()).unwrap();

    let check = authority.check().unwrap();
    assert_eq!(check["schema_identifier"], "metacraft.authority.check");
    assert_eq!(check["protocol_identifier"], "metacraft.authority");
    assert_eq!(check["workspace_valid"], true);

    let view = authority.view().unwrap();
    assert_eq!(view["schema_identifier"], "metacraft.authority.view");
    assert_eq!(view["revision"], "root");
    assert_eq!(view["decisions"], serde_json::json!([]));
    assert_eq!(view["permits"], serde_json::json!([]));
    assert_eq!(view["current"], serde_json::json!([]));

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn decide_records_and_fetches_one_opaque_body_at_an_exact_revision() {
    let path = fresh_workspace("record");
    let authority = Authority::open(path.clone()).unwrap();
    let proposal = proposal(
        br#"{"kind":"fixture"}"#,
        vec![],
        serde_json::json!({"kind": "record"}),
    );

    let decision = authority.decide(&proposal, "root").unwrap();
    assert_eq!(decision["outcome"], "admitted");
    assert_eq!(decision["observed_revision"], "root");
    assert_ne!(decision["resulting_revision"], "root");
    assert_eq!(
        decision["body_reference"]["content_hash"],
        "sha256:0ece1d6200d82a40c6f4c4a8736cd4dccdf3f854684e416200bf47daa0d8e948"
    );

    let reference_json = serde_jcs::to_string(&decision["body_reference"]).unwrap();
    assert_eq!(
        authority.fetch(&reference_json).unwrap(),
        br#"{"kind":"fixture"}"#
    );
    let noncanonical_reference = serde_json::to_string_pretty(&decision["body_reference"]).unwrap();
    assert_eq!(
        authority.fetch(&noncanonical_reference).unwrap_err(),
        "reference_not_canonical"
    );

    let stale = authority.decide(&proposal, "root").unwrap();
    assert_eq!(stale["outcome"], "rejected");
    assert_eq!(stale["findings"], serde_json::json!(["revision_mismatch"]));
    assert_eq!(stale["resulting_revision"], decision["resulting_revision"]);

    let view = authority.view().unwrap();
    assert_eq!(view["revision"], decision["resulting_revision"]);
    assert_eq!(view["decisions"].as_array().unwrap().len(), 1);

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn current_relation_supersedes_only_the_exact_current_body() {
    let path = fresh_workspace("current");
    let authority = Authority::open(path.clone()).unwrap();
    let first = proposal(
        br#"{"name":"alpha"}"#,
        vec![],
        serde_json::json!({"key": "study", "kind": "current", "supersedes": null}),
    );
    let first_decision = authority.decide(&first, "root").unwrap();
    let first_body = first_decision["body_reference"].clone();

    let second = proposal(
        br#"{"name":"beta"}"#,
        vec![first_body.clone()],
        serde_json::json!({
            "key": "study",
            "kind": "current",
            "supersedes": first_body,
        }),
    );
    let revision = first_decision["resulting_revision"].as_str().unwrap();
    let second_decision = authority.decide(&second, revision).unwrap();
    assert_eq!(second_decision["outcome"], "admitted");

    let view = authority.view().unwrap();
    assert_eq!(view["current"].as_array().unwrap().len(), 1);
    assert_eq!(view["current"][0]["key"], "study");
    assert_eq!(
        view["current"][0]["body_reference"]["content_hash"],
        "sha256:a3beb590eed7b4f00e9c227f147843c5d64f41116a7f86d30ca90519c9a2f5a6"
    );
    assert_eq!(
        view["current"][0]["superseded"],
        serde_json::json!([first_body])
    );

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn permits_reserve_capacity_and_one_receipt_consumes_one_open_permit() {
    let path = fresh_workspace("permits");
    let authority = Authority::open(path.clone()).unwrap();
    let capacity = proposal(
        &capacity_body(2),
        vec![],
        serde_json::json!({
            "key": "capacity:solver",
            "kind": "current",
            "supersedes": null,
        }),
    );
    let capacity_decision = authority.decide(&capacity, "root").unwrap();
    let capacity_reference = capacity_decision["body_reference"].clone();
    let mut revision = capacity_decision["resulting_revision"]
        .as_str()
        .unwrap()
        .to_string();

    let permit = |label: &str| {
        proposal(
            format!(r#"{{"work":"{label}"}}"#).as_bytes(),
            vec![capacity_reference.clone()],
            serde_json::json!({
                "capacity_reference": capacity_reference,
                "expires_at": "2099-01-01T00:00:00Z",
                "kind": "permit",
                "scope": "solver",
            }),
        )
    };
    let first = authority.decide(&permit("first"), &revision).unwrap();
    revision = first["resulting_revision"].as_str().unwrap().to_string();
    let second = authority.decide(&permit("second"), &revision).unwrap();
    revision = second["resulting_revision"].as_str().unwrap().to_string();

    let excess = authority.decide(&permit("third"), &revision).unwrap();
    assert_eq!(excess["outcome"], "rejected");
    assert_eq!(
        excess["findings"],
        serde_json::json!(["permit_capacity_exceeded"])
    );
    assert_eq!(authority.view().unwrap()["revision"], revision);

    let first_permit = first["proposal_reference"].clone();
    let receipt = proposal(
        br#"{"observation":"complete"}"#,
        vec![first_permit.clone()],
        serde_json::json!({
            "kind": "receipt",
            "permit_reference": first_permit,
        }),
    );
    let receipt_decision = authority.decide(&receipt, &revision).unwrap();
    revision = receipt_decision["resulting_revision"]
        .as_str()
        .unwrap()
        .to_string();
    let duplicate = authority.decide(&receipt, &revision).unwrap();
    assert_eq!(duplicate["outcome"], "rejected");
    assert_eq!(
        duplicate["findings"],
        serde_json::json!(["permit_already_closed"])
    );
    assert_eq!(authority.view().unwrap()["revision"], revision);
    let third = authority.decide(&permit("third"), &revision).unwrap();
    assert_eq!(third["outcome"], "admitted");

    let permits = authority.view().unwrap()["permits"]
        .as_array()
        .unwrap()
        .clone();
    assert_eq!(permits.len(), 3);
    assert_eq!(
        permits
            .iter()
            .filter(|permit| permit["state"] == "open")
            .count(),
        2
    );
    assert_eq!(
        permits
            .iter()
            .filter(|permit| permit["close_reason"] == "consumed")
            .count(),
        1
    );

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn an_open_permit_proposal_is_rejected_when_proposed_again() {
    let path = fresh_workspace("duplicate-permit");
    let authority = Authority::open(path.clone()).unwrap();
    let capacity = proposal(
        &capacity_body(2),
        vec![],
        serde_json::json!({
            "key": "capacity:solver",
            "kind": "current",
            "supersedes": null,
        }),
    );
    let capacity_decision = authority.decide(&capacity, "root").unwrap();
    let capacity_reference = capacity_decision["body_reference"].clone();
    let permit = proposal(
        br#"{"work":"same"}"#,
        vec![capacity_reference.clone()],
        serde_json::json!({
            "capacity_reference": capacity_reference,
            "expires_at": "2099-01-01T00:00:00Z",
            "kind": "permit",
            "scope": "solver",
        }),
    );
    let first = authority
        .decide(
            &permit,
            capacity_decision["resulting_revision"].as_str().unwrap(),
        )
        .unwrap();
    let revision = first["resulting_revision"].as_str().unwrap();

    let repeated = authority.decide(&permit, revision).unwrap();

    assert_eq!(repeated["outcome"], "rejected");
    assert_eq!(
        repeated["findings"],
        serde_json::json!(["permit_already_open"])
    );
    assert_eq!(repeated["observed_revision"], revision);
    assert_eq!(repeated["resulting_revision"], revision);
    assert_eq!(authority.view().unwrap()["revision"], revision);

    let permit_reference = first["proposal_reference"].clone();
    let receipt = proposal(
        br#"{"observation":"complete"}"#,
        vec![permit_reference.clone()],
        serde_json::json!({
            "kind": "receipt",
            "permit_reference": permit_reference,
        }),
    );
    let receipt_decision = authority.decide(&receipt, revision).unwrap();
    let closed_revision = receipt_decision["resulting_revision"].as_str().unwrap();

    let repeated_after_close = authority.decide(&permit, closed_revision).unwrap();

    assert_eq!(repeated_after_close["outcome"], "rejected");
    assert_eq!(
        repeated_after_close["findings"],
        serde_json::json!(["permit_already_closed"])
    );
    assert_eq!(repeated_after_close["observed_revision"], closed_revision);
    assert_eq!(repeated_after_close["resulting_revision"], closed_revision);
    assert_eq!(authority.view().unwrap()["revision"], closed_revision);

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn registered_structure_is_generic_and_rejects_a_mismatched_body_without_mutation() {
    let path = fresh_workspace("structure");
    let authority = Authority::open(path.clone()).unwrap();
    let structure = proposal(
        &canonical_body(serde_json::json!({
            "schema_identifier": "metacraft.authority.structure",
            "shape": {
                "fields": {
                    "enabled": {"kind": "boolean"},
                    "name": {"kind": "string"},
                },
                "kind": "object",
                "required": ["name", "enabled"],
            },
        })),
        vec![],
        serde_json::json!({"kind": "record"}),
    );
    let structure_decision = authority.decide(&structure, "root").unwrap();
    let structure_reference = structure_decision["body_reference"].clone();
    let revision = structure_decision["resulting_revision"].as_str().unwrap();

    let invalid = structured_proposal(
        br#"{"enabled":"yes","name":"sample"}"#,
        structure_reference.clone(),
    );
    let rejected = authority.decide(&invalid, revision).unwrap();
    assert_eq!(rejected["outcome"], "rejected");
    assert_eq!(
        rejected["findings"],
        serde_json::json!(["structure_mismatch:$.enabled"])
    );
    assert_eq!(rejected["observed_revision"], revision);
    assert_eq!(rejected["resulting_revision"], revision);
    assert_eq!(authority.view().unwrap()["revision"], revision);

    let valid = structured_proposal(br#"{"enabled":true,"name":"sample"}"#, structure_reference);
    assert_eq!(
        authority.decide(&valid, revision).unwrap()["outcome"],
        "admitted"
    );

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn registered_structure_rejects_duplicate_required_fields_without_mutation() {
    let path = fresh_workspace("structure-duplicate-required");
    let authority = Authority::open(path.clone()).unwrap();
    let structure = proposal(
        &canonical_body(serde_json::json!({
            "schema_identifier": "metacraft.authority.structure",
            "shape": {
                "fields": {"name": {"kind": "string"}},
                "kind": "object",
                "required": ["name", "name"],
            },
        })),
        vec![],
        serde_json::json!({"kind": "record"}),
    );

    let rejected = authority.decide(&structure, "root").unwrap();

    assert_eq!(rejected["outcome"], "rejected");
    assert_eq!(
        rejected["findings"],
        serde_json::json!(["structure_invalid"])
    );
    assert_eq!(rejected["observed_revision"], "root");
    assert_eq!(rejected["resulting_revision"], "root");
    assert_eq!(authority.view().unwrap()["revision"], "root");

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn proposal_reference_closure_is_exact_and_duplicate_free() {
    let path = fresh_workspace("reference-closure");
    let authority = Authority::open(path.clone()).unwrap();
    let recorded = authority
        .decide(
            &proposal(
                br#"{"name":"source"}"#,
                vec![],
                serde_json::json!({"kind": "record"}),
            ),
            "root",
        )
        .unwrap();
    let reference = recorded["body_reference"].clone();
    let revision = recorded["resulting_revision"].as_str().unwrap();
    let duplicate = proposal(
        br#"{"name":"dependent"}"#,
        vec![reference.clone(), reference],
        serde_json::json!({"kind": "record"}),
    );

    let rejected = authority.decide(&duplicate, revision).unwrap();
    assert_eq!(rejected["outcome"], "rejected");
    assert_eq!(
        rejected["findings"],
        serde_json::json!(["reference_closure_duplicate"])
    );
    assert_eq!(rejected["resulting_revision"], revision);

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn malformed_and_dangling_proposals_fail_closed() {
    let path = fresh_workspace("fail-closed");
    let authority = Authority::open(path.clone()).unwrap();
    let duplicate_key = concat!(
        r#"{"body":{"bytes_base64":"e30=","descriptive_metadata":{},"#,
        r#""media_type":"application/json","structure_reference":null},"#,
        r#""references":[],"relation":{"kind":"record"},"#,
        r#""schema_identifier":"metacraft.authority.proposal","#,
        r#""schema_identifier":"metacraft.authority.proposal"}"#,
    );
    assert!(authority
        .decide(duplicate_key, "stale")
        .unwrap_err()
        .starts_with("json_invalid:"));

    let dangling = serde_json::json!({
        "content_hash": format!("sha256:{}", "a".repeat(64)),
        "media_type": "application/json",
        "metadata_content_hash": format!("sha256:{}", "b".repeat(64)),
        "size_bytes": 2,
    });
    let rejected = authority
        .decide(
            &proposal(
                br#"{}"#,
                vec![dangling],
                serde_json::json!({"kind": "record"}),
            ),
            "root",
        )
        .unwrap();
    assert_eq!(rejected["outcome"], "rejected");
    assert_eq!(
        rejected["findings"],
        serde_json::json!(["reference_unresolvable"])
    );
    assert_eq!(rejected["resulting_revision"], "root");
    assert_eq!(authority.view().unwrap()["revision"], "root");

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn expired_permit_rejects_receipt_and_closes_only_as_expired() {
    let path = fresh_workspace("expired");
    let authority = Authority::open(path.clone()).unwrap();
    let capacity = proposal(
        &capacity_body(1),
        vec![],
        serde_json::json!({"key": "capacity:solver", "kind": "current", "supersedes": null}),
    );
    let capacity_decision = authority.decide(&capacity, "root").unwrap();
    let capacity_reference = capacity_decision["body_reference"].clone();
    let expiry =
        (Utc::now() + Duration::milliseconds(250)).to_rfc3339_opts(SecondsFormat::Millis, true);
    let permit = proposal(
        br#"{"work":"brief"}"#,
        vec![capacity_reference.clone()],
        serde_json::json!({
            "capacity_reference": capacity_reference,
            "expires_at": expiry,
            "kind": "permit",
            "scope": "solver",
        }),
    );
    let permit_decision = authority
        .decide(
            &permit,
            capacity_decision["resulting_revision"].as_str().unwrap(),
        )
        .unwrap();
    let permit_reference = permit_decision["proposal_reference"].clone();
    let mut revision = permit_decision["resulting_revision"]
        .as_str()
        .unwrap()
        .to_string();
    std::thread::sleep(std::time::Duration::from_millis(400));

    let receipt = proposal(
        br#"{"observation":"late"}"#,
        vec![permit_reference.clone()],
        serde_json::json!({"kind": "receipt", "permit_reference": permit_reference}),
    );
    let rejected = authority.decide(&receipt, &revision).unwrap();
    assert_eq!(rejected["findings"], serde_json::json!(["permit_expired"]));
    assert_eq!(rejected["resulting_revision"], revision);
    assert_eq!(authority.check().unwrap()["workspace_valid"], true);

    let close = proposal(
        br#"{"reason":"time"}"#,
        vec![permit_reference.clone()],
        serde_json::json!({
            "kind": "close",
            "permit_reference": permit_reference,
            "reason": "expired",
        }),
    );
    let closed = authority.decide(&close, &revision).unwrap();
    revision = closed["resulting_revision"].as_str().unwrap().to_string();
    assert_eq!(closed["outcome"], "admitted");
    assert_eq!(authority.view().unwrap()["revision"], revision);
    assert_eq!(
        authority.view().unwrap()["permits"][0]["close_reason"],
        "expired"
    );

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn current_capacity_never_drops_below_open_permits() {
    let path = fresh_workspace("capacity-floor");
    let authority = Authority::open(path.clone()).unwrap();
    let capacity = proposal(
        &capacity_body(2),
        vec![],
        serde_json::json!({"key": "capacity:solver", "kind": "current", "supersedes": null}),
    );
    let capacity_decision = authority.decide(&capacity, "root").unwrap();
    let capacity_reference = capacity_decision["body_reference"].clone();
    let mut revision = capacity_decision["resulting_revision"]
        .as_str()
        .unwrap()
        .to_string();
    for label in ["alpha", "beta"] {
        let permit = proposal(
            format!(r#"{{"work":"{label}"}}"#).as_bytes(),
            vec![capacity_reference.clone()],
            serde_json::json!({
                "capacity_reference": capacity_reference,
                "expires_at": "2099-01-01T00:00:00Z",
                "kind": "permit",
                "scope": "solver",
            }),
        );
        let decision = authority.decide(&permit, &revision).unwrap();
        revision = decision["resulting_revision"].as_str().unwrap().to_string();
    }
    let smaller = proposal(
        &capacity_body(1),
        vec![capacity_reference.clone()],
        serde_json::json!({
            "key": "capacity:solver",
            "kind": "current",
            "supersedes": capacity_reference,
        }),
    );
    let rejected = authority.decide(&smaller, &revision).unwrap();
    assert_eq!(rejected["outcome"], "rejected");
    assert_eq!(
        rejected["findings"],
        serde_json::json!(["capacity_below_open_permits"])
    );
    assert_eq!(rejected["resulting_revision"], revision);

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn resolvable_but_unused_reference_is_rejected_as_surplus() {
    let path = fresh_workspace("surplus");
    let authority = Authority::open(path.clone()).unwrap();
    let source = authority
        .decide(
            &proposal(br#"{}"#, vec![], serde_json::json!({"kind": "record"})),
            "root",
        )
        .unwrap();
    let reference = source["body_reference"].clone();
    let revision = source["resulting_revision"].as_str().unwrap();
    let surplus = proposal(
        br#"{"independent":true}"#,
        vec![reference],
        serde_json::json!({"kind": "record"}),
    );
    let rejected = authority.decide(&surplus, revision).unwrap();
    assert_eq!(
        rejected["findings"],
        serde_json::json!(["reference_closure_surplus"])
    );
    assert_eq!(rejected["resulting_revision"], revision);

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn tampered_projection_cannot_feed_view_or_decide() {
    let path = fresh_workspace("tampered-projection");
    let authority = Authority::open(path.clone()).unwrap();
    let recorded = authority
        .decide(
            &proposal(br#"{}"#, vec![], serde_json::json!({"kind": "record"})),
            "root",
        )
        .unwrap();
    rusqlite::Connection::open(path.join("workspace.sqlite3"))
        .unwrap()
        .execute(
            "UPDATE projections SET projection_json='{}' WHERE projection_key='authority_view'",
            [],
        )
        .unwrap();

    let check = authority.check().unwrap();
    assert_eq!(check["workspace_valid"], false);
    assert!(check["findings"]
        .as_array()
        .unwrap()
        .iter()
        .any(|finding| finding
            .as_str()
            .unwrap()
            .contains("projection_replay_mismatch")));
    assert!(authority
        .view()
        .unwrap_err()
        .starts_with("workspace_integrity_failed:"));
    assert!(authority
        .decide(
            &proposal(br#"{}"#, vec![], serde_json::json!({"kind": "record"})),
            recorded["resulting_revision"].as_str().unwrap(),
        )
        .unwrap_err()
        .starts_with("workspace_integrity_failed:"));
    assert!(Authority::open(path.clone())
        .unwrap_err()
        .starts_with("workspace_integrity_failed:"));

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn root_protocol_outputs_are_canonical_and_stable() {
    let path = fresh_workspace("golden");
    let authority = Authority::open(path.clone()).unwrap();
    assert_eq!(
        serde_jcs::to_string(&authority.view().unwrap()).unwrap(),
        concat!(
            r#"{"current":[],"decisions":[],"permits":[],"revision":"root","#,
            r#""schema_identifier":"metacraft.authority.view"}"#,
        )
    );
    let proposal = proposal(
        br#"{"kind":"fixture"}"#,
        vec![],
        serde_json::json!({"kind": "record"}),
    );
    let rejected = authority
        .decide(&proposal, &format!("sha256:{}", "f".repeat(64)))
        .unwrap();
    assert_eq!(
        serde_jcs::to_string(&rejected).unwrap(),
        concat!(
            r#"{"body_reference":null,"findings":["revision_mismatch"],"#,
            r#""observed_revision":"root","outcome":"rejected","#,
            r#""proposal_content_hash":"sha256:"#,
            r#"94e1c90797bfde8f22c36bd1e228759dbd442b154c64d44f55beb9a6ce31525c","#,
            r#""proposal_reference":null,"resulting_revision":"root","#,
            r#""schema_identifier":"metacraft.authority.decision"}"#,
        )
    );
    let check = authority.check().unwrap();
    assert_eq!(check["ledger_event_count"], 0);
    assert_eq!(
        check["schema_content_hashes"],
        serde_json::json!({
            "capacity": "sha256:b3f8f4089f897c9cb9b9bfe4db2f2cc1e043841834109f3ebeb4f28ab8e919e7",
            "decision": "sha256:2d6a0e816fa1c9cf973f68fe90e3b119f960690afb198a959bc4376128e199a7",
            "proposal": "sha256:3ac33ccc4183fcbd63534824a3d8ae24bdf4094fe4ac4b5865efa114ca6fda5a",
            "reference": "sha256:bab101133f0f759d8201581c5e68c47391f8c84fe079f3b73a1e276f297330ea",
            "structure": "sha256:69517363134539f624477f451f9973b4ba872a2dcdaa171d0eea52dbc421f56e",
            "view": "sha256:ffef8a6d313c417cd89384bdda1b7c99aaef4d11d8181a4245e53d8894bc0ba3",
        })
    );

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn permit_and_receipt_canonical_fixtures_are_frozen_end_to_end() {
    let fixtures: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/authority_protocol.json")).unwrap();
    let canonical = |name: &str| serde_jcs::to_string(&fixtures[name]).unwrap();
    let path = fresh_workspace("canonical-fixtures");
    let authority = Authority::open(path.clone()).unwrap();

    let capacity_proposal = canonical("capacity_proposal");
    let capacity_decision = authority.decide(&capacity_proposal, "root").unwrap();
    assert_eq!(
        serde_jcs::to_string(&capacity_decision).unwrap(),
        canonical("capacity_decision")
    );

    let permit_proposal = canonical("permit_proposal");
    let permit_decision = authority
        .decide(
            &permit_proposal,
            capacity_decision["resulting_revision"].as_str().unwrap(),
        )
        .unwrap();
    assert_eq!(
        serde_jcs::to_string(&permit_decision).unwrap(),
        canonical("permit_decision")
    );

    let receipt_proposal = canonical("receipt_proposal");
    let receipt_decision = authority
        .decide(
            &receipt_proposal,
            permit_decision["resulting_revision"].as_str().unwrap(),
        )
        .unwrap();
    assert_eq!(
        serde_jcs::to_string(&receipt_decision).unwrap(),
        canonical("receipt_decision")
    );
    assert_eq!(
        serde_jcs::to_string(&authority.view().unwrap()).unwrap(),
        canonical("view")
    );

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn concurrent_decisions_serialize_at_one_exact_revision() {
    let path = fresh_workspace("concurrent");
    let authority = Authority::open(path.clone()).unwrap();
    let capacity = proposal(
        &capacity_body(2),
        vec![],
        serde_json::json!({"key": "capacity:solver", "kind": "current", "supersedes": null}),
    );
    let capacity_decision = authority.decide(&capacity, "root").unwrap();
    let capacity_reference = capacity_decision["body_reference"].clone();
    let revision = capacity_decision["resulting_revision"]
        .as_str()
        .unwrap()
        .to_string();
    drop(authority);

    let barrier = std::sync::Arc::new(std::sync::Barrier::new(2));
    let mut workers = Vec::new();
    for label in ["alpha", "beta"] {
        let path = path.clone();
        let barrier = barrier.clone();
        let revision = revision.clone();
        let capacity_reference = capacity_reference.clone();
        workers.push(std::thread::spawn(move || {
            let authority = Authority::open(path).unwrap();
            let permit = proposal(
                format!(r#"{{"work":"{label}"}}"#).as_bytes(),
                vec![capacity_reference.clone()],
                serde_json::json!({
                    "capacity_reference": capacity_reference,
                    "expires_at": "2099-01-01T00:00:00Z",
                    "kind": "permit",
                    "scope": "solver",
                }),
            );
            barrier.wait();
            authority.decide(&permit, &revision).unwrap()
        }));
    }
    let decisions = workers
        .into_iter()
        .map(|worker| worker.join().unwrap())
        .collect::<Vec<_>>();
    assert_eq!(
        decisions
            .iter()
            .filter(|decision| decision["outcome"] == "admitted")
            .count(),
        1
    );
    assert_eq!(
        decisions
            .iter()
            .filter(|decision| decision["findings"] == serde_json::json!(["revision_mismatch"]))
            .count(),
        1
    );
    assert_eq!(
        Authority::open(path.clone()).unwrap().view().unwrap()["permits"]
            .as_array()
            .unwrap()
            .len(),
        1
    );

    std::fs::remove_dir_all(path).unwrap();
}

#[test]
fn close_revokes_one_open_permit_without_a_receipt() {
    let path = fresh_workspace("revoke");
    let authority = Authority::open(path.clone()).unwrap();
    let capacity = proposal(
        &capacity_body(1),
        vec![],
        serde_json::json!({
            "key": "capacity:solver",
            "kind": "current",
            "supersedes": null,
        }),
    );
    let capacity_decision = authority.decide(&capacity, "root").unwrap();
    let capacity_reference = capacity_decision["body_reference"].clone();
    let permit = proposal(
        br#"{"work":"revocable"}"#,
        vec![capacity_reference.clone()],
        serde_json::json!({
            "capacity_reference": capacity_reference,
            "expires_at": "2099-01-01T00:00:00Z",
            "kind": "permit",
            "scope": "solver",
        }),
    );
    let permit_decision = authority
        .decide(
            &permit,
            capacity_decision["resulting_revision"].as_str().unwrap(),
        )
        .unwrap();
    let permit_reference = permit_decision["proposal_reference"].clone();
    let close = proposal(
        br#"{"reason":"operator_request"}"#,
        vec![permit_reference.clone()],
        serde_json::json!({
            "kind": "close",
            "permit_reference": permit_reference,
            "reason": "revoked",
        }),
    );
    authority
        .decide(
            &close,
            permit_decision["resulting_revision"].as_str().unwrap(),
        )
        .unwrap();

    let permit = authority.view().unwrap()["permits"][0].clone();
    assert_eq!(permit["state"], "closed");
    assert_eq!(permit["close_reason"], "revoked");
    assert_eq!(permit["receipt_reference"], serde_json::Value::Null);

    std::fs::remove_dir_all(path).unwrap();
}
