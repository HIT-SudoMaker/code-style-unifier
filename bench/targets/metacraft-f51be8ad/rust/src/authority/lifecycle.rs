use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::workspace::StoredObjectReference;

use super::protocol::{
    CloseReason, DecisionOutcome, Relation, Revision, EVENT_SCHEMA, VIEW_SCHEMA,
};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub(super) struct View {
    pub(super) current: Vec<Current>,
    pub(super) decisions: Vec<AdmittedDecision>,
    pub(super) permits: Vec<Permit>,
    pub(super) revision: Revision,
    schema_identifier: String,
}

impl View {
    pub(super) fn empty() -> Self {
        Self {
            current: Vec::new(),
            decisions: Vec::new(),
            permits: Vec::new(),
            revision: Revision::root(),
            schema_identifier: VIEW_SCHEMA.to_string(),
        }
    }

    pub(super) fn to_value(&self) -> Result<Value, String> {
        serde_json::to_value(self).map_err(|error| format!("authority_view_corrupt:{error}"))
    }

    pub(super) fn apply(
        &mut self,
        transition: Transition<'_>,
        moment: Moment,
    ) -> Result<(), String> {
        match transition.relation {
            Relation::Record => {}
            Relation::Current { key, supersedes } => {
                self.guard_current(key, supersedes.as_ref())?;
                if let Some(limit) = transition.capacity_limit {
                    self.guard_capacity_change(key, limit)?;
                }
                if let Some(current) = self.current.iter_mut().find(|current| current.key == *key) {
                    current.superseded.push(current.body_reference.clone());
                    current.body_reference = transition.body_reference.clone();
                } else {
                    self.current.push(Current {
                        body_reference: transition.body_reference.clone(),
                        key: key.clone(),
                        superseded: Vec::new(),
                    });
                    self.current.sort_by(|left, right| left.key.cmp(&right.key));
                }
            }
            Relation::Permit {
                capacity_reference,
                expires_at,
                scope,
            } => {
                self.guard_permit(&transition, moment)?;
                let expiry = parse_expiry(expires_at, "permit_expiry_invalid")?;
                self.permits.push(Permit {
                    body_reference: transition.body_reference.clone(),
                    capacity_reference: capacity_reference.clone(),
                    close_reason: None,
                    expires_at: expiry.to_rfc3339(),
                    permit_reference: transition.proposal_reference.clone(),
                    receipt_body_reference: None,
                    receipt_reference: None,
                    scope: scope.clone(),
                    state: PermitState::Open,
                });
                self.permits.sort_by(|left, right| {
                    left.permit_reference
                        .content_hash
                        .cmp(&right.permit_reference.content_hash)
                });
            }
            Relation::Receipt { permit_reference } => {
                self.guard_receipt(permit_reference, moment)?;
                let permit = self
                    .permit_mut(permit_reference)
                    .ok_or_else(|| "receipt_permit_missing".to_string())?;
                permit.state = PermitState::Closed;
                permit.close_reason = Some(PermitCloseReason::Consumed);
                permit.receipt_reference = Some(transition.proposal_reference.clone());
                permit.receipt_body_reference = Some(transition.body_reference.clone());
            }
            Relation::Close {
                permit_reference,
                reason,
            } => {
                self.guard_close(permit_reference, *reason, moment)?;
                let permit = self
                    .permit_mut(permit_reference)
                    .ok_or_else(|| "close_permit_missing".to_string())?;
                permit.state = PermitState::Closed;
                permit.close_reason = Some((*reason).into());
            }
        }
        self.decisions.push(AdmittedDecision {
            body_reference: transition.body_reference.clone(),
            outcome: DecisionOutcome::Admitted,
            proposal_reference: transition.proposal_reference.clone(),
            relation: RelationName::from(transition.relation),
        });
        Ok(())
    }

    fn guard_current(
        &self,
        key: &str,
        supersedes: Option<&StoredObjectReference>,
    ) -> Result<(), String> {
        if key.trim().is_empty() {
            return Err("current_key_invalid".to_string());
        }
        match self.current.iter().find(|current| current.key == key) {
            Some(current) if supersedes == Some(&current.body_reference) => Ok(()),
            Some(_) => Err("current_reference_mismatch".to_string()),
            None if supersedes.is_some() => Err("current_reference_missing".to_string()),
            None => Ok(()),
        }
    }

    fn guard_capacity_change(&self, key: &str, limit: u64) -> Result<(), String> {
        let scope = key
            .strip_prefix("capacity:")
            .ok_or_else(|| "capacity_invalid".to_string())?;
        let open_count = self
            .permits
            .iter()
            .filter(|permit| permit.scope == *scope && permit.state == PermitState::Open)
            .count();
        if u64::try_from(open_count).map_err(|_| "capacity_invalid".to_string())? > limit {
            return Err("capacity_below_open_permits".to_string());
        }
        Ok(())
    }

    fn guard_permit(&self, transition: &Transition<'_>, moment: Moment) -> Result<(), String> {
        let Relation::Permit {
            capacity_reference,
            expires_at,
            scope,
        } = transition.relation
        else {
            return Err("lifecycle_invalid:permit relation".to_string());
        };
        if scope.trim().is_empty() {
            return Err("permit_capacity_reference_missing".to_string());
        }
        let capacity_key = format!("capacity:{scope}");
        let current = self
            .current
            .iter()
            .find(|current| current.key == capacity_key)
            .ok_or_else(|| "permit_capacity_not_current".to_string())?;
        if current.body_reference != *capacity_reference {
            return Err("permit_capacity_not_current".to_string());
        }
        if let Some(existing) = self
            .permits
            .iter()
            .find(|permit| permit.permit_reference == *transition.proposal_reference)
        {
            return Err(if existing.state == PermitState::Open {
                "permit_already_open".to_string()
            } else {
                "permit_already_closed".to_string()
            });
        }
        let expiry = parse_expiry(expires_at, "permit_expiry_invalid")?;
        if let Moment::Admission(now) = moment {
            if expiry <= now {
                return Err("permit_expired".to_string());
            }
        }
        let limit = transition
            .capacity_limit
            .ok_or_else(|| "capacity_invalid".to_string())?;
        let open_count = self
            .permits
            .iter()
            .filter(|permit| permit.scope == *scope && permit.state == PermitState::Open)
            .count();
        if u64::try_from(open_count).map_err(|_| "capacity_invalid".to_string())? >= limit {
            return Err("permit_capacity_exceeded".to_string());
        }
        Ok(())
    }

    fn guard_receipt(
        &self,
        permit_reference: &StoredObjectReference,
        moment: Moment,
    ) -> Result<(), String> {
        let permit = self
            .permit(permit_reference)
            .ok_or_else(|| "receipt_permit_missing".to_string())?;
        if permit.state != PermitState::Open {
            return Err("permit_already_closed".to_string());
        }
        if let Moment::Admission(now) = moment {
            let expiry = parse_expiry(&permit.expires_at, "permit_expiry_invalid")?;
            if now >= expiry {
                return Err("permit_expired".to_string());
            }
        }
        Ok(())
    }

    fn guard_close(
        &self,
        permit_reference: &StoredObjectReference,
        reason: CloseReason,
        moment: Moment,
    ) -> Result<(), String> {
        let permit = self
            .permit(permit_reference)
            .ok_or_else(|| "close_permit_missing".to_string())?;
        if permit.state != PermitState::Open {
            return Err("permit_already_closed".to_string());
        }
        if reason == CloseReason::Expired {
            if let Moment::Admission(now) = moment {
                let expiry = parse_expiry(&permit.expires_at, "permit_expiry_invalid")?;
                if now < expiry {
                    return Err("permit_not_expired".to_string());
                }
            }
        }
        Ok(())
    }

    fn permit(&self, reference: &StoredObjectReference) -> Option<&Permit> {
        self.permits
            .iter()
            .find(|permit| permit.permit_reference == *reference)
    }

    fn permit_mut(&mut self, reference: &StoredObjectReference) -> Option<&mut Permit> {
        self.permits
            .iter_mut()
            .find(|permit| permit.permit_reference == *reference)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub(super) struct Current {
    body_reference: StoredObjectReference,
    key: String,
    superseded: Vec<StoredObjectReference>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub(super) struct AdmittedDecision {
    body_reference: StoredObjectReference,
    outcome: DecisionOutcome,
    proposal_reference: StoredObjectReference,
    relation: RelationName,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
enum RelationName {
    Record,
    Current,
    Permit,
    Receipt,
    Close,
}

impl From<&Relation> for RelationName {
    fn from(relation: &Relation) -> Self {
        match relation {
            Relation::Record => Self::Record,
            Relation::Current { .. } => Self::Current,
            Relation::Permit { .. } => Self::Permit,
            Relation::Receipt { .. } => Self::Receipt,
            Relation::Close { .. } => Self::Close,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub(super) struct Permit {
    body_reference: StoredObjectReference,
    capacity_reference: StoredObjectReference,
    close_reason: Option<PermitCloseReason>,
    expires_at: String,
    permit_reference: StoredObjectReference,
    #[serde(skip_serializing_if = "Option::is_none")]
    receipt_body_reference: Option<StoredObjectReference>,
    receipt_reference: Option<StoredObjectReference>,
    scope: String,
    state: PermitState,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
enum PermitState {
    Open,
    Closed,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
enum PermitCloseReason {
    Consumed,
    Revoked,
    Expired,
}

impl From<CloseReason> for PermitCloseReason {
    fn from(reason: CloseReason) -> Self {
        match reason {
            CloseReason::Revoked => Self::Revoked,
            CloseReason::Expired => Self::Expired,
        }
    }
}

#[derive(Debug, Clone, Copy)]
pub(super) enum Moment {
    Admission(DateTime<Utc>),
    Replay,
}

pub(super) struct Transition<'a> {
    pub(super) relation: &'a Relation,
    pub(super) proposal_reference: &'a StoredObjectReference,
    pub(super) body_reference: &'a StoredObjectReference,
    pub(super) capacity_limit: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub(super) struct AdmittedEvent {
    pub(super) body_reference: StoredObjectReference,
    outcome: DecisionOutcome,
    pub(super) proposal_reference: StoredObjectReference,
    pub(super) references: Vec<StoredObjectReference>,
    pub(super) relation: Relation,
    schema_identifier: String,
}

impl AdmittedEvent {
    pub(super) fn new(
        proposal_reference: StoredObjectReference,
        body_reference: StoredObjectReference,
        references: Vec<StoredObjectReference>,
        relation: Relation,
    ) -> Self {
        Self {
            body_reference,
            outcome: DecisionOutcome::Admitted,
            proposal_reference,
            references,
            relation,
            schema_identifier: EVENT_SCHEMA.to_string(),
        }
    }

    pub(super) fn from_value(value: Value) -> Result<Self, String> {
        let event: Self = serde_json::from_value(value)
            .map_err(|error| format!("ledger_replay_failed:event payload: {error}"))?;
        if event.schema_identifier != EVENT_SCHEMA {
            return Err("ledger_replay_failed:event schema".to_string());
        }
        if event.outcome != DecisionOutcome::Admitted {
            return Err("ledger_replay_failed:event outcome".to_string());
        }
        Ok(event)
    }

    pub(super) fn to_value(&self) -> Result<Value, String> {
        serde_json::to_value(self).map_err(|error| format!("authority_event_invalid:{error}"))
    }
}

fn parse_expiry(value: &str, finding: &str) -> Result<DateTime<Utc>, String> {
    DateTime::parse_from_rfc3339(value)
        .map(|expiry| expiry.with_timezone(&Utc))
        .map_err(|_| finding.to_string())
}
