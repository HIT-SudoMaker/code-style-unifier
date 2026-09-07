use std::collections::{BTreeMap, BTreeSet};
use std::fmt;

use base64::Engine;
use serde::de::{self, DeserializeSeed, MapAccess, SeqAccess, Visitor};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};

use crate::workspace::StoredObjectReference;

pub(super) const PROTOCOL_IDENTIFIER: &str = "metacraft.authority";
pub(super) const CAPACITY_SCHEMA: &str = "metacraft.authority.capacity";
pub(super) const CHECK_SCHEMA: &str = "metacraft.authority.check";
pub(super) const DECISION_SCHEMA: &str = "metacraft.authority.decision";
pub(super) const EVENT_SCHEMA: &str = "metacraft.authority.event";
pub(super) const PROPOSAL_SCHEMA: &str = "metacraft.authority.proposal";
pub(super) const STRUCTURE_SCHEMA: &str = "metacraft.authority.structure";
pub(super) const VIEW_SCHEMA: &str = "metacraft.authority.view";

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(transparent)]
pub(super) struct Revision(String);

impl Revision {
    pub(super) fn root() -> Self {
        Self("root".to_string())
    }

    pub(super) fn committed() -> Self {
        Self("committed".to_string())
    }

    pub(super) fn observed(head: Option<String>) -> Self {
        head.map(Self).unwrap_or_else(Self::root)
    }

    pub(super) fn as_str(&self) -> &str {
        &self.0
    }

    pub(super) fn head(&self) -> Option<&str> {
        (self.0 != "root").then_some(self.0.as_str())
    }
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub(super) struct Decision {
    body_reference: Option<StoredObjectReference>,
    findings: Vec<String>,
    observed_revision: Revision,
    outcome: DecisionOutcome,
    proposal_content_hash: Option<String>,
    proposal_reference: Option<StoredObjectReference>,
    resulting_revision: Revision,
    schema_identifier: String,
}

impl Decision {
    pub(super) fn admitted(
        observed_revision: Revision,
        resulting_revision: Revision,
        proposal_content_hash: String,
        proposal_reference: StoredObjectReference,
        body_reference: StoredObjectReference,
    ) -> Self {
        Self {
            body_reference: Some(body_reference),
            findings: Vec::new(),
            observed_revision,
            outcome: DecisionOutcome::Admitted,
            proposal_content_hash: Some(proposal_content_hash),
            proposal_reference: Some(proposal_reference),
            resulting_revision,
            schema_identifier: DECISION_SCHEMA.to_string(),
        }
    }

    pub(super) fn rejected(
        revision: Revision,
        proposal_content_hash: Option<String>,
        finding: &str,
    ) -> Self {
        Self {
            body_reference: None,
            findings: vec![finding.to_string()],
            observed_revision: revision.clone(),
            outcome: DecisionOutcome::Rejected,
            proposal_content_hash,
            proposal_reference: None,
            resulting_revision: revision,
            schema_identifier: DECISION_SCHEMA.to_string(),
        }
    }

    pub(super) fn to_value(&self) -> Result<Value, String> {
        serde_json::to_value(self).map_err(|error| format!("decision_invalid:{error}"))
    }
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub(super) enum DecisionOutcome {
    Admitted,
    Rejected,
}

pub(super) fn schema_content_hashes() -> Value {
    Value::Object(
        schema_contracts()
            .into_iter()
            .map(|(name, contract)| {
                let bytes =
                    serde_jcs::to_vec(&contract).expect("static protocol contract must serialize");
                (
                    name.to_string(),
                    Value::String(format!("sha256:{:x}", Sha256::digest(&bytes))),
                )
            })
            .collect(),
    )
}

fn schema_contracts() -> [(&'static str, Value); 6] {
    [
        (
            "capacity",
            json!({
                "limit": "positive_integer",
                "qualification_references": "exact_references",
                "schema_identifier": CAPACITY_SCHEMA,
                "scope": "nonempty_string",
            }),
        ),
        (
            "decision",
            json!({
                "body_reference": "reference|null",
                "findings": "ordered_strings",
                "observed_revision": "revision",
                "outcome": "admitted|rejected",
                "proposal_content_hash": "sha256|null",
                "proposal_reference": "reference|null",
                "resulting_revision": "revision",
                "schema_identifier": DECISION_SCHEMA,
            }),
        ),
        (
            "proposal",
            json!({
                "body": {
                    "bytes_base64": "canonical_base64",
                    "descriptive_metadata": "object_without_secrets",
                    "media_type": "nonempty_string",
                    "structure_reference": "reference|null",
                },
                "references": "exact_duplicate_free_reference_closure",
                "relation": {
                    "close": {"permit_reference": "reference", "reason": "revoked|expired"},
                    "current": {"key": "nonempty_string", "supersedes": "reference|null"},
                    "permit": {
                        "capacity_reference": "reference",
                        "expires_at": "future_rfc3339",
                        "scope": "nonempty_string",
                    },
                    "receipt": {"permit_reference": "reference"},
                    "record": {},
                },
                "schema_identifier": PROPOSAL_SCHEMA,
            }),
        ),
        (
            "reference",
            json!({
                "content_hash": "sha256",
                "media_type": "nonempty_string",
                "metadata_content_hash": "sha256",
                "size_bytes": "unsigned_integer",
            }),
        ),
        (
            "structure",
            json!({
                "schema_identifier": STRUCTURE_SCHEMA,
                "shape": {
                    "array": {"items": "shape"},
                    "boolean": {},
                    "enum": {"values": "json_values"},
                    "integer": {},
                    "null": {},
                    "object": {"fields": "shape_map", "required": "unique_field_names"},
                    "reference": {"exact": "reference"},
                    "string": {},
                },
            }),
        ),
        (
            "view",
            json!({
                "current": "ordered_current_entries",
                "decisions": "ordered_admitted_decisions",
                "permits": "ordered_permit_entries",
                "revision": "revision",
                "schema_identifier": VIEW_SCHEMA,
            }),
        ),
    ]
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Proposal {
    pub(super) schema_identifier: String,
    pub(super) body: ProposedBody,
    pub(super) references: Vec<StoredObjectReference>,
    pub(super) relation: Relation,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct ProposedBody {
    pub(super) bytes_base64: String,
    pub(super) descriptive_metadata: Value,
    pub(super) media_type: String,
    pub(super) structure_reference: Option<StoredObjectReference>,
}

impl ProposedBody {
    pub(super) fn bytes(&self) -> Result<Vec<u8>, String> {
        base64::engine::general_purpose::STANDARD
            .decode(&self.bytes_base64)
            .map_err(|_| "proposal_body_invalid: bytes_base64".to_string())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub(super) enum Relation {
    Record,
    Current {
        key: String,
        supersedes: Option<StoredObjectReference>,
    },
    Permit {
        capacity_reference: StoredObjectReference,
        expires_at: String,
        scope: String,
    },
    Receipt {
        permit_reference: StoredObjectReference,
    },
    Close {
        permit_reference: StoredObjectReference,
        reason: CloseReason,
    },
}

impl Relation {
    pub(super) fn references(&self) -> Vec<StoredObjectReference> {
        match self {
            Self::Record => Vec::new(),
            Self::Current { supersedes, .. } => supersedes.iter().cloned().collect(),
            Self::Permit {
                capacity_reference, ..
            } => vec![capacity_reference.clone()],
            Self::Receipt { permit_reference }
            | Self::Close {
                permit_reference, ..
            } => {
                vec![permit_reference.clone()]
            }
        }
    }
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub(super) enum CloseReason {
    Revoked,
    Expired,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Capacity {
    pub(super) schema_identifier: String,
    pub(super) scope: String,
    pub(super) limit: u64,
    pub(super) qualification_references: Vec<StoredObjectReference>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Structure {
    schema_identifier: String,
    shape: Shape,
}

#[derive(Debug, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
enum Shape {
    Object {
        fields: BTreeMap<String, Shape>,
        required: Vec<String>,
    },
    Array {
        items: Box<Shape>,
    },
    String,
    Integer,
    Boolean,
    Null,
    Enum {
        values: Vec<Value>,
    },
    Reference {
        exact: StoredObjectReference,
    },
}

pub(super) fn parse_proposal(raw: &str) -> Result<(Proposal, Vec<u8>), String> {
    reject_duplicate_json_keys(raw)?;
    let value: Value =
        serde_json::from_str(raw).map_err(|error| format!("proposal_invalid: {error}"))?;
    let canonical =
        serde_jcs::to_vec(&value).map_err(|error| format!("proposal_invalid: {error}"))?;
    if canonical != raw.as_bytes() {
        return Err("proposal_not_canonical".to_string());
    }
    let proposal: Proposal =
        serde_json::from_value(value).map_err(|error| format!("proposal_invalid: {error}"))?;
    if proposal.schema_identifier != PROPOSAL_SCHEMA {
        return Err("proposal_schema_mismatch".to_string());
    }
    Ok((proposal, canonical))
}

pub(super) fn require_canonical_json(bytes: &[u8]) -> Result<(), String> {
    let raw =
        std::str::from_utf8(bytes).map_err(|_| "proposal_body_invalid: json_utf8".to_string())?;
    reject_duplicate_json_keys(raw)?;
    let value: Value =
        serde_json::from_str(raw).map_err(|error| format!("proposal_body_invalid: {error}"))?;
    let canonical =
        serde_jcs::to_vec(&value).map_err(|error| format!("proposal_body_invalid: {error}"))?;
    if canonical != bytes {
        return Err("proposal_body_not_canonical".to_string());
    }
    Ok(())
}

pub(super) fn validate_structure(
    structure_bytes: &[u8],
    body_bytes: &[u8],
    references: &[StoredObjectReference],
) -> Result<Vec<StoredObjectReference>, String> {
    let structure = parse_structure(structure_bytes)?;
    validate_shape_definition(&structure.shape, &mut Vec::new())?;
    let body: Value = serde_json::from_slice(body_bytes)
        .map_err(|error| format!("proposal_body_invalid: {error}"))?;
    let mut used_references = Vec::new();
    validate_shape(
        &structure.shape,
        &body,
        references,
        &mut used_references,
        "$",
    )?;
    Ok(used_references)
}

pub(super) fn validate_registered_structure(
    body_bytes: &[u8],
) -> Result<Vec<StoredObjectReference>, String> {
    let value: Value = serde_json::from_slice(body_bytes)
        .map_err(|error| format!("proposal_body_invalid: {error}"))?;
    if value.get("schema_identifier").and_then(Value::as_str) != Some(STRUCTURE_SCHEMA) {
        return Ok(Vec::new());
    }
    let structure = parse_structure(body_bytes)?;
    let mut references = Vec::new();
    validate_shape_definition(&structure.shape, &mut references)?;
    Ok(references)
}

fn parse_structure(bytes: &[u8]) -> Result<Structure, String> {
    require_canonical_json(bytes).map_err(|error| format!("structure_invalid:{error}"))?;
    let structure: Structure =
        serde_json::from_slice(bytes).map_err(|error| format!("structure_invalid:{error}"))?;
    if structure.schema_identifier != STRUCTURE_SCHEMA {
        return Err("structure_schema_mismatch".to_string());
    }
    Ok(structure)
}

fn validate_shape_definition(
    shape: &Shape,
    references: &mut Vec<StoredObjectReference>,
) -> Result<(), String> {
    match shape {
        Shape::Object { fields, required } => {
            let unique_required = required.iter().collect::<BTreeSet<_>>();
            if unique_required.len() != required.len() {
                return Err("structure_invalid:duplicate required field".to_string());
            }
            if required.iter().any(|key| !fields.contains_key(key)) {
                return Err("structure_invalid:required field is undefined".to_string());
            }
            for child in fields.values() {
                validate_shape_definition(child, references)?;
            }
        }
        Shape::Array { items } => validate_shape_definition(items, references)?,
        Shape::Reference { exact } => references.push(exact.clone()),
        Shape::String | Shape::Integer | Shape::Boolean | Shape::Null | Shape::Enum { .. } => {}
    }
    Ok(())
}

pub(super) fn validate_current_capacity(
    body_bytes: &[u8],
    references: &[StoredObjectReference],
    key: &str,
) -> Result<(u64, Vec<StoredObjectReference>), String> {
    let raw = std::str::from_utf8(body_bytes).map_err(|_| "capacity_invalid".to_string())?;
    reject_duplicate_json_keys(raw).map_err(|_| "capacity_invalid".to_string())?;
    let capacity: Capacity =
        serde_json::from_slice(body_bytes).map_err(|_| "capacity_invalid".to_string())?;
    if capacity.schema_identifier != CAPACITY_SCHEMA
        || capacity.limit == 0
        || capacity.scope.trim().is_empty()
        || key != format!("capacity:{}", capacity.scope)
    {
        return Err("capacity_invalid".to_string());
    }
    let mut identities = BTreeSet::new();
    for reference in &capacity.qualification_references {
        let identity =
            serde_jcs::to_string(reference).map_err(|_| "capacity_invalid".to_string())?;
        if !identities.insert(identity) {
            return Err("capacity_invalid".to_string());
        }
        if !references.contains(reference) {
            return Err("reference_closure_incomplete".to_string());
        }
    }
    Ok((capacity.limit, capacity.qualification_references))
}

fn validate_shape(
    shape: &Shape,
    value: &Value,
    references: &[StoredObjectReference],
    used_references: &mut Vec<StoredObjectReference>,
    path: &str,
) -> Result<(), String> {
    let mismatch = || format!("structure_mismatch:{path}");
    match shape {
        Shape::Object { fields, required } => {
            let object = value.as_object().ok_or_else(mismatch)?;
            let unique_required = required.iter().collect::<BTreeSet<_>>();
            if unique_required.len() != required.len() {
                return Err("structure_invalid:duplicate required field".to_string());
            }
            if required.iter().any(|key| !fields.contains_key(key))
                || object.keys().any(|key| !fields.contains_key(key))
                || required.iter().any(|key| !object.contains_key(key))
            {
                return Err(mismatch());
            }
            for (key, child) in object {
                validate_shape(
                    &fields[key],
                    child,
                    references,
                    used_references,
                    &format!("{path}.{key}"),
                )?;
            }
            Ok(())
        }
        Shape::Array { items } => {
            let values = value.as_array().ok_or_else(mismatch)?;
            for (index, child) in values.iter().enumerate() {
                validate_shape(
                    items,
                    child,
                    references,
                    used_references,
                    &format!("{path}[{index}]"),
                )?;
            }
            Ok(())
        }
        Shape::String if value.is_string() => Ok(()),
        Shape::Integer if value.as_i64().is_some() || value.as_u64().is_some() => Ok(()),
        Shape::Boolean if value.is_boolean() => Ok(()),
        Shape::Null if value.is_null() => Ok(()),
        Shape::Enum { values } if values.contains(value) => Ok(()),
        Shape::Reference { exact } => {
            let observed: StoredObjectReference =
                serde_json::from_value(value.clone()).map_err(|_| mismatch())?;
            if observed != *exact {
                return Err(mismatch());
            }
            if !references.contains(exact) {
                return Err("reference_closure_incomplete".to_string());
            }
            used_references.push(exact.clone());
            Ok(())
        }
        _ => Err(mismatch()),
    }
}

pub(super) fn reject_duplicate_json_keys(raw: &str) -> Result<(), String> {
    let mut deserializer = serde_json::Deserializer::from_str(raw);
    DuplicateKeySeed
        .deserialize(&mut deserializer)
        .map_err(|error| format!("json_invalid: {error}"))?;
    deserializer
        .end()
        .map_err(|error| format!("json_invalid: {error}"))
}

#[derive(Clone, Copy)]
struct DuplicateKeySeed;

impl<'de> DeserializeSeed<'de> for DuplicateKeySeed {
    type Value = ();

    fn deserialize<D>(self, deserializer: D) -> Result<Self::Value, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        deserializer.deserialize_any(DuplicateKeyVisitor)
    }
}

struct DuplicateKeyVisitor;

impl<'de> Visitor<'de> for DuplicateKeyVisitor {
    type Value = ();

    fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("valid JSON without duplicate object keys")
    }

    fn visit_bool<E>(self, _value: bool) -> Result<Self::Value, E> {
        Ok(())
    }
    fn visit_i64<E>(self, _value: i64) -> Result<Self::Value, E> {
        Ok(())
    }
    fn visit_u64<E>(self, _value: u64) -> Result<Self::Value, E> {
        Ok(())
    }
    fn visit_f64<E>(self, _value: f64) -> Result<Self::Value, E> {
        Ok(())
    }
    fn visit_str<E>(self, _value: &str) -> Result<Self::Value, E> {
        Ok(())
    }
    fn visit_string<E>(self, _value: String) -> Result<Self::Value, E> {
        Ok(())
    }
    fn visit_none<E>(self) -> Result<Self::Value, E> {
        Ok(())
    }
    fn visit_unit<E>(self) -> Result<Self::Value, E> {
        Ok(())
    }

    fn visit_some<D>(self, deserializer: D) -> Result<Self::Value, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        DuplicateKeySeed.deserialize(deserializer)
    }

    fn visit_seq<A>(self, mut sequence: A) -> Result<Self::Value, A::Error>
    where
        A: SeqAccess<'de>,
    {
        while sequence.next_element_seed(DuplicateKeySeed)?.is_some() {}
        Ok(())
    }

    fn visit_map<A>(self, mut object: A) -> Result<Self::Value, A::Error>
    where
        A: MapAccess<'de>,
    {
        let mut keys = BTreeSet::new();
        while let Some(key) = object.next_key::<String>()? {
            if !keys.insert(key.clone()) {
                return Err(de::Error::custom(format!("duplicate field: {key}")));
            }
            object.next_value_seed(DuplicateKeySeed)?;
        }
        Ok(())
    }
}
