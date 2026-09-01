use std::path::PathBuf;
use std::sync::Mutex;
#[cfg(test)]
use std::sync::{Arc, Barrier};

use chrono::Utc;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};

use crate::workspace::{
    AuthorityEventCommitRequest, AuthorityObjectCommitRequest, AuthorityWriter, CommitError,
    StoredObjectReference, Workspace, WorkspaceGeneration,
};

use super::lifecycle::{AdmittedEvent, Moment, Transition, View as AuthorityView};
use super::protocol::{
    parse_proposal, reject_duplicate_json_keys, require_canonical_json, schema_content_hashes,
    validate_current_capacity, validate_registered_structure, validate_structure, Capacity,
    Decision, Proposal, Relation, Revision, CAPACITY_SCHEMA, CHECK_SCHEMA, PROTOCOL_IDENTIFIER,
};

const VIEW_PROJECTION_KEY: &str = "authority_view";

/// One private verified authority state.
///
/// A verified state arises only from one successful complete audit or one
/// successful atomic commit performed from the currently verified head. It
/// records the durable generation that was audited, the revision that was
/// observed, and the replayed view. Stable `view` and `decide` reuse it while
/// the durable generation still agrees, and re-audit the moment it does not.
#[derive(Debug)]
struct VerifiedState {
    generation: WorkspaceGeneration,
    revision: Revision,
    view: AuthorityView,
}

enum AdmissionError {
    LedgerHeadMismatch,
    Failed(String),
}

impl From<String> for AdmissionError {
    fn from(message: String) -> Self {
        Self::Failed(message)
    }
}

impl From<CommitError> for AdmissionError {
    fn from(error: CommitError) -> Self {
        match error {
            CommitError::LedgerHeadMismatch { .. } => Self::LedgerHeadMismatch,
            CommitError::Failed(message) => Self::Failed(message),
        }
    }
}

#[derive(Debug)]
/// Owns one workspace's generic state and integrity boundary.
pub struct Authority {
    workspace: Workspace,
    verified: Mutex<Option<VerifiedState>>,
    #[cfg(test)]
    after_audit: Mutex<Option<(Arc<Barrier>, Arc<Barrier>)>>,
}

impl Authority {
    /// Opens an initialized workspace or creates one at a new path.
    pub fn open(workspace_path: PathBuf) -> Result<Self, String> {
        let workspace = if workspace_path.exists() {
            Workspace::open(workspace_path)?
        } else {
            Workspace::create(workspace_path)?
        };
        workspace.recover_pending_transaction()?;
        let authority = Self {
            workspace,
            verified: Mutex::new(None),
            #[cfg(test)]
            after_audit: Mutex::new(None),
        };
        authority.refresh_verified()?;
        Ok(authority)
    }

    /// Verifies stored objects, ledger continuity, and projection replay.
    pub fn check(&self) -> Result<Value, String> {
        let writer = match self.workspace.writer() {
            Ok(writer) => writer,
            Err(_) => {
                self.forget_verified();
                return Ok(check_result(
                    vec!["workspace_integrity_failed".to_string()],
                    0,
                ));
            }
        };
        let (verification, replay, stored) = match writer.audit_projection(VIEW_PROJECTION_KEY) {
            Ok(audit) => audit,
            Err(_) => {
                self.forget_verified();
                return Ok(check_result(
                    vec!["workspace_integrity_failed".to_string()],
                    0,
                ));
            }
        };
        let mut findings = verification.findings;
        let rebuilt = self.rebuild_view(&replay.payloads);
        // Serialization failure is an Interface error. Replay or projection
        // mismatch is an integrity finding. This distinction preserves the
        // public check contract while keeping verified state private.
        let projection_matches = match rebuilt.as_ref() {
            Ok(view_opt) => {
                let rebuilt_value = view_opt.as_ref().map(AuthorityView::to_value).transpose()?;
                replay.projection == stored && rebuilt_value == stored
            }
            Err(_) => false,
        };
        if !projection_matches {
            findings.push("projection_replay_mismatch".to_string());
        }
        if projection_matches && verification.valid {
            let revision = Revision::observed(replay.ledger_head);
            let view = rebuilt.ok().flatten().unwrap_or_else(AuthorityView::empty);
            match writer.observe_generation() {
                Ok(generation) => self.remember_verified(generation, revision, view),
                Err(_) => {
                    self.forget_verified();
                    findings.push("workspace_integrity_failed".to_string());
                }
            }
        } else {
            self.forget_verified();
        }
        findings.sort();
        findings.dedup();
        Ok(check_result(findings, replay.event_count))
    }

    /// Returns the replayed authority view at the observed revision.
    pub fn view(&self) -> Result<Value, String> {
        let (revision, mut view) = self.verified_view()?;
        view.revision = revision;
        view.to_value()
    }

    /// Resolves one canonical exact reference to immutable bytes.
    pub fn fetch(&self, reference_json: &str) -> Result<Vec<u8>, String> {
        super::protocol::reject_duplicate_json_keys(reference_json)?;
        let value: Value = serde_json::from_str(reference_json)
            .map_err(|error| format!("reference_invalid: {error}"))?;
        let canonical =
            serde_jcs::to_vec(&value).map_err(|error| format!("reference_invalid: {error}"))?;
        if canonical != reference_json.as_bytes() {
            return Err("reference_not_canonical".to_string());
        }
        let reference: StoredObjectReference =
            serde_json::from_value(value).map_err(|error| format!("reference_invalid: {error}"))?;
        self.workspace.resolve_reference(&reference)
    }

    /// Admits or rejects one canonical proposal at an exact revision.
    pub fn decide(&self, proposal_json: &str, at: &str) -> Result<Value, String> {
        let (proposal, proposal_bytes) = parse_proposal(proposal_json)?;
        let proposal_content_hash = content_hash(&proposal_bytes);
        let writer = self.workspace.writer()?;
        let (observed_revision, view) = self.verified_view_with(&writer)?;
        if at != observed_revision.as_str() {
            return Decision::rejected(
                observed_revision,
                Some(proposal_content_hash),
                "revision_mismatch",
            )
            .to_value();
        }
        match self.admit(proposal, proposal_bytes, &observed_revision, view, &writer) {
            Ok((decision, resulting_revision, resulting_view)) => {
                match writer.observe_generation() {
                    Ok(generation) => {
                        self.remember_verified(generation, resulting_revision, resulting_view)
                    }
                    Err(_) => self.forget_verified(),
                }
                Ok(decision)
            }
            Err(AdmissionError::LedgerHeadMismatch) => {
                let current_revision = self.revision()?;
                Decision::rejected(
                    current_revision,
                    Some(proposal_content_hash),
                    "revision_mismatch",
                )
                .to_value()
            }
            Err(AdmissionError::Failed(error)) if is_finding(&error) => Decision::rejected(
                observed_revision,
                Some(proposal_content_hash),
                stable_finding(&error),
            )
            .to_value(),
            Err(AdmissionError::Failed(error)) => Err(error),
        }
    }

    fn admit(
        &self,
        proposal: Proposal,
        proposal_bytes: Vec<u8>,
        observed_revision: &Revision,
        mut view: AuthorityView,
        writer: &AuthorityWriter<'_>,
    ) -> Result<(Value, Revision, AuthorityView), AdmissionError> {
        for reference in &proposal.references {
            self.workspace.resolve_reference(reference)?;
        }
        let body_bytes = proposal.body.bytes()?;
        let mut body_references = Vec::new();
        if let Some(structure_reference) = &proposal.body.structure_reference {
            let structure = self.workspace.resolve_reference(structure_reference)?;
            body_references.extend(validate_structure(
                &structure,
                &body_bytes,
                &proposal.references,
            )?);
        }
        if proposal.body.media_type == "application/json" {
            require_canonical_json(&body_bytes)?;
            body_references.extend(validate_registered_structure(&body_bytes)?);
        }
        let (capacity_limit, qualification_references) = self.capacity_limit(
            &proposal.relation,
            None,
            Some(&body_bytes),
            &proposal.references,
        )?;
        body_references.extend(qualification_references);
        require_exact_reference_closure(&proposal, &body_references)?;
        let body = Workspace::prepare_authority_object(
            &body_bytes,
            &proposal.body.media_type,
            &proposal.body.descriptive_metadata,
        )?;
        let proposal_object = Workspace::prepare_authority_object(
            &proposal_bytes,
            "application/vnd.metacraft.authority.proposal+json",
            &json!({"object_kind": "Proposal"}),
        )?;
        let body_reference = body.object_reference.clone();
        let proposal_reference = proposal_object.object_reference.clone();
        let mut required_references = proposal.references.clone();
        required_references.push(proposal_reference.clone());
        required_references.push(body_reference.clone());
        view.apply(
            Transition {
                relation: &proposal.relation,
                proposal_reference: &proposal_reference,
                body_reference: &body_reference,
                capacity_limit,
            },
            Moment::Admission(Utc::now()),
        )?;
        view.revision = Revision::committed();
        let projection = view.to_value()?;
        let event_payload = AdmittedEvent::new(
            proposal_object.object_reference.clone(),
            body.object_reference.clone(),
            proposal.references,
            proposal.relation,
        )
        .to_value()?;
        let prepared_objects = [proposal_object, body];
        let commit = writer.commit(AuthorityObjectCommitRequest {
            event: AuthorityEventCommitRequest {
                expected_ledger_head: observed_revision.head(),
                canonical_command_content_hash: &prepared_objects[0].object_reference.content_hash,
                event_kind: "DecisionAdmitted",
                required_references: &required_references,
                event_payload: &event_payload,
                projection_key: VIEW_PROJECTION_KEY,
                projection_value: &projection,
            },
            prepared_objects: &prepared_objects,
        })?;
        let resulting_revision = Revision::observed(Some(commit.ledger_head));
        let decision = Decision::admitted(
            observed_revision.clone(),
            resulting_revision.clone(),
            proposal_reference.content_hash.clone(),
            proposal_reference,
            body_reference,
        )
        .to_value()?;
        Ok((decision, resulting_revision, view))
    }

    fn revision(&self) -> Result<Revision, String> {
        Ok(Revision::observed(self.workspace.ledger_head()?))
    }

    /// Reuses the verified view when its durable generation still agrees, and
    /// performs one complete re-audit otherwise. This is the stable common
    /// path: it scans no historical rows while the durable workspace has not
    /// changed since the last complete audit.
    fn verified_view(&self) -> Result<(Revision, AuthorityView), String> {
        let generation = self
            .workspace
            .observe_generation()
            .inspect_err(|_| self.forget_verified())?;
        if let Some(verified) = self
            .verified
            .lock()
            .unwrap_or_else(|error| error.into_inner())
            .as_ref()
        {
            if verified.generation == generation {
                return Ok((verified.revision.clone(), verified.view.clone()));
            }
        }
        self.refresh_verified()
    }

    fn verified_view_with(
        &self,
        writer: &AuthorityWriter<'_>,
    ) -> Result<(Revision, AuthorityView), String> {
        let generation = writer
            .observe_generation()
            .inspect_err(|_| self.forget_verified())?;
        if let Some(verified) = self
            .verified
            .lock()
            .unwrap_or_else(|error| error.into_inner())
            .as_ref()
        {
            if verified.generation == generation {
                return Ok((verified.revision.clone(), verified.view.clone()));
            }
        }
        self.refresh_verified_with(writer)
    }

    /// Performs one complete audit and remembers its result. A failed refresh
    /// returns no stale view and leaves the handle unverified.
    fn refresh_verified(&self) -> Result<(Revision, AuthorityView), String> {
        let writer = self
            .workspace
            .writer()
            .inspect_err(|_| self.forget_verified())?;
        self.refresh_verified_with(&writer)
    }

    fn refresh_verified_with(
        &self,
        writer: &AuthorityWriter<'_>,
    ) -> Result<(Revision, AuthorityView), String> {
        let audited = writer.audit_projection(VIEW_PROJECTION_KEY).and_then(
            |(verification, replay, stored)| {
                let accepted = self.accept_audit(verification, replay, stored)?;
                self.pause_after_audit();
                let generation = writer.observe_generation()?;
                Ok((accepted, generation))
            },
        );
        match audited {
            Ok(((revision, view), generation)) => {
                self.remember_verified(generation, revision.clone(), view.clone());
                Ok((revision, view))
            }
            Err(error) => {
                self.forget_verified();
                Err(error)
            }
        }
    }

    fn remember_verified(
        &self,
        generation: WorkspaceGeneration,
        revision: Revision,
        view: AuthorityView,
    ) {
        *self
            .verified
            .lock()
            .unwrap_or_else(|error| error.into_inner()) = Some(VerifiedState {
            generation,
            revision,
            view,
        });
    }

    fn forget_verified(&self) {
        *self
            .verified
            .lock()
            .unwrap_or_else(|error| error.into_inner()) = None;
    }

    #[cfg(test)]
    pub(super) fn pause_after_next_audit(&self, reached: Arc<Barrier>, release: Arc<Barrier>) {
        *self
            .after_audit
            .lock()
            .unwrap_or_else(|error| error.into_inner()) = Some((reached, release));
    }

    #[cfg(test)]
    fn pause_after_audit(&self) {
        let pause = self
            .after_audit
            .lock()
            .unwrap_or_else(|error| error.into_inner())
            .take();
        if let Some((reached, release)) = pause {
            reached.wait();
            release.wait();
        }
    }

    #[cfg(not(test))]
    fn pause_after_audit(&self) {}

    fn accept_audit(
        &self,
        verification: crate::workspace::WorkspaceVerification,
        replay: crate::workspace::ProjectionReplay,
        stored: Option<Value>,
    ) -> Result<(Revision, AuthorityView), String> {
        if !verification.valid {
            return Err(format!(
                "workspace_integrity_failed:{}",
                verification.findings.join(",")
            ));
        }
        let rebuilt = self.rebuild_view(&replay.payloads)?;
        let rebuilt_value = rebuilt.as_ref().map(AuthorityView::to_value).transpose()?;
        if replay.projection != stored || rebuilt_value != stored {
            return Err("workspace_integrity_failed:projection_replay_mismatch".to_string());
        }
        let revision = Revision::observed(replay.ledger_head);
        Ok((revision, rebuilt.unwrap_or_else(AuthorityView::empty)))
    }

    fn rebuild_view(&self, payloads: &[Value]) -> Result<Option<AuthorityView>, String> {
        if payloads.is_empty() {
            return Ok(None);
        }
        let mut view = AuthorityView::empty();
        for payload in payloads {
            let event = AdmittedEvent::from_value(payload.clone())?;
            let (capacity_limit, _) = self.capacity_limit(
                &event.relation,
                Some(&event.body_reference),
                None,
                &event.references,
            )?;
            view.apply(
                Transition {
                    relation: &event.relation,
                    proposal_reference: &event.proposal_reference,
                    body_reference: &event.body_reference,
                    capacity_limit,
                },
                Moment::Replay,
            )
            .map_err(|error| format!("ledger_replay_failed:{error}"))?;
        }
        view.revision = Revision::committed();
        Ok(Some(view))
    }

    fn permit_capacity_limit(
        &self,
        capacity_reference: &StoredObjectReference,
        scope: &str,
    ) -> Result<u64, String> {
        if scope.trim().is_empty() {
            return Err("permit_capacity_reference_missing".to_string());
        }
        let capacity_bytes = self.workspace.resolve_reference(capacity_reference)?;
        let capacity_raw =
            std::str::from_utf8(&capacity_bytes).map_err(|_| "capacity_invalid".to_string())?;
        reject_duplicate_json_keys(capacity_raw)?;
        let capacity: Capacity =
            serde_json::from_slice(&capacity_bytes).map_err(|_| "capacity_invalid".to_string())?;
        if capacity.schema_identifier != CAPACITY_SCHEMA
            || capacity.scope != scope
            || capacity.limit == 0
        {
            return Err("capacity_invalid".to_string());
        }
        for qualification in &capacity.qualification_references {
            self.workspace.resolve_reference(qualification)?;
        }
        Ok(capacity.limit)
    }

    fn capacity_limit(
        &self,
        relation: &Relation,
        body_reference: Option<&StoredObjectReference>,
        body_bytes: Option<&[u8]>,
        references: &[StoredObjectReference],
    ) -> Result<(Option<u64>, Vec<StoredObjectReference>), String> {
        match relation {
            Relation::Current { key, .. } if key.starts_with("capacity:") => {
                let owned_body;
                let body = if let Some(bytes) = body_bytes {
                    bytes
                } else {
                    owned_body = self.workspace.resolve_reference(
                        body_reference.ok_or_else(|| "capacity_invalid".to_string())?,
                    )?;
                    &owned_body
                };
                let (limit, qualifications) = validate_current_capacity(body, references, key)?;
                Ok((Some(limit), qualifications))
            }
            Relation::Permit {
                capacity_reference,
                scope,
                ..
            } => Ok((
                Some(self.permit_capacity_limit(capacity_reference, scope)?),
                Vec::new(),
            )),
            _ => Ok((None, Vec::new())),
        }
    }
}

fn require_exact_reference_closure(
    proposal: &Proposal,
    body_references: &[StoredObjectReference],
) -> Result<(), String> {
    let mut identities = std::collections::BTreeSet::new();
    for reference in &proposal.references {
        let identity = serde_jcs::to_string(reference)
            .map_err(|error| format!("proposal_invalid: {error}"))?;
        if !identities.insert(identity) {
            return Err("reference_closure_duplicate".to_string());
        }
    }
    let mut required: Vec<StoredObjectReference> = body_references.to_vec();
    if let Some(reference) = &proposal.body.structure_reference {
        required.push(reference.clone());
    }
    required.extend(proposal.relation.references());
    let mut required = required
        .iter()
        .map(serde_jcs::to_string)
        .collect::<Result<Vec<_>, _>>()
        .map_err(|error| format!("proposal_invalid: {error}"))?;
    required.sort();
    required.dedup();
    let supplied = identities.into_iter().collect::<Vec<_>>();
    if required
        .iter()
        .any(|reference| !supplied.contains(reference))
    {
        return Err("reference_closure_incomplete".to_string());
    }
    if supplied
        .iter()
        .any(|reference| !required.contains(reference))
    {
        return Err("reference_closure_surplus".to_string());
    }
    Ok(())
}

fn check_result(findings: Vec<String>, event_count: u64) -> Value {
    let workspace_valid = findings.is_empty();
    json!({
        "findings": findings,
        "ledger_event_count": event_count,
        "protocol_identifier": PROTOCOL_IDENTIFIER,
        "schema_identifier": CHECK_SCHEMA,
        "schema_content_hashes": schema_content_hashes(),
        "workspace_valid": workspace_valid,
    })
}

fn finding_code(error: &str) -> &str {
    error.split(':').next().unwrap_or(error)
}

fn stable_finding(error: &str) -> &str {
    if error.starts_with("structure_mismatch:") {
        error
    } else {
        finding_code(error)
    }
}

fn is_finding(error: &str) -> bool {
    const FINDINGS: &[&str] = &[
        "capacity_below_open_permits",
        "capacity_invalid",
        "close_permit_missing",
        "close_permit_reference_missing",
        "current_key_invalid",
        "current_reference_mismatch",
        "current_reference_missing",
        "json_invalid",
        "permit_already_closed",
        "permit_already_open",
        "permit_capacity_exceeded",
        "permit_capacity_not_current",
        "permit_capacity_reference_missing",
        "permit_expired",
        "permit_expiry_invalid",
        "permit_not_expired",
        "proposal_body_invalid",
        "proposal_body_not_canonical",
        "receipt_permit_missing",
        "receipt_permit_reference_missing",
        "reference_closure_duplicate",
        "reference_closure_incomplete",
        "reference_closure_surplus",
        "reference_unresolvable",
        "structure_invalid",
        "structure_mismatch",
        "structure_schema_mismatch",
    ];
    FINDINGS.contains(&finding_code(error))
}

fn content_hash(bytes: &[u8]) -> String {
    format!("sha256:{:x}", Sha256::digest(bytes))
}
