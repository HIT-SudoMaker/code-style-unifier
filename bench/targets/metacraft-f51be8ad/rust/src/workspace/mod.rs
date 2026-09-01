use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::SystemTime;

use fs2::FileExt;
use rusqlite::{params, Connection, OptionalExtension, Transaction, TransactionBehavior};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};

const WORKSPACE_MARKER: &[u8] = b"metacraft.workspace\n";
static TEMPORARY_FILE_SEQUENCE: AtomicU64 = AtomicU64::new(0);

// Test-only structural counters. Production callers never observe these; they
// exist so the private verified-state regression can prove that the stable
// common path performs no historical-row scan. They are thread-local so each
// test function observes only the audits and row reads its own thread caused,
// even while the harness runs tests in parallel.
#[cfg(test)]
mod test_counters {
    thread_local! {
        pub(crate) static AUDIT_COUNT: std::cell::Cell<u64> =
            const { std::cell::Cell::new(0) };
        pub(crate) static HISTORICAL_ROW_COUNT: std::cell::Cell<u64> =
            const { std::cell::Cell::new(0) };
    }
}

/// Cheap durable workspace identity observed without replaying history.
///
/// The authority records this generation at the moment it completes a full
/// audit. Stable `view` and `decide` compare it to detect whether durable
/// storage has changed under, around, or since that proof. Any difference
/// triggers one complete re-audit rather than suffix guessing.
///
/// The fields are intentionally cheap O(1) facts that change on any legitimate
/// write or external mutation of governed durable storage: another authority
/// committing advances the ledger head and event count and rewrites the
/// database file; direct tampering of a projection, event, object, head, or
/// marker rewrites the file or marker; replacing the whole database changes the
/// file signature. The full audit remains the integrity gate; the generation is
/// only a cache-validity signal.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct WorkspaceGeneration {
    marker_signature: String,
    database_size: u64,
    database_modified: SystemTime,
    ledger_head: Option<String>,
    event_count: u64,
}

#[derive(Debug, Clone)]
pub(crate) struct Workspace {
    root: PathBuf,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct StoredObjectReference {
    pub(crate) content_hash: String,
    pub(crate) media_type: String,
    pub(crate) size_bytes: u64,
    pub(crate) metadata_content_hash: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct WorkspaceVerification {
    pub(crate) valid: bool,
    pub(crate) object_count: u64,
    pub(crate) findings: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct AuthorityCommit {
    pub(crate) ledger_head: String,
    pub(crate) sequence: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) enum CommitError {
    LedgerHeadMismatch {
        expected: Option<String>,
        actual: Option<String>,
    },
    Failed(String),
}

impl From<String> for CommitError {
    fn from(message: String) -> Self {
        Self::Failed(message)
    }
}

pub(crate) struct AuthorityEventCommitRequest<'a> {
    pub(crate) expected_ledger_head: Option<&'a str>,
    pub(crate) canonical_command_content_hash: &'a str,
    pub(crate) event_kind: &'a str,
    pub(crate) required_references: &'a [StoredObjectReference],
    pub(crate) event_payload: &'a Value,
    pub(crate) projection_key: &'a str,
    pub(crate) projection_value: &'a Value,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct PreparedAuthorityObject {
    raw_bytes: Vec<u8>,
    metadata_bytes: Vec<u8>,
    pub(crate) object_reference: StoredObjectReference,
}

pub(crate) struct AuthorityObjectCommitRequest<'a> {
    pub(crate) event: AuthorityEventCommitRequest<'a>,
    pub(crate) prepared_objects: &'a [PreparedAuthorityObject],
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct ProjectionReplay {
    pub(crate) event_count: u64,
    pub(crate) ledger_head: Option<String>,
    pub(crate) payloads: Vec<Value>,
    pub(crate) projection: Option<Value>,
}

pub(crate) struct AuthorityWriter<'a> {
    workspace: &'a Workspace,
    _lock_file: fs::File,
}

impl AuthorityWriter<'_> {
    pub(crate) fn audit_projection(
        &self,
        projection_key: &str,
    ) -> Result<(WorkspaceVerification, ProjectionReplay, Option<Value>), String> {
        #[cfg(test)]
        test_counters::AUDIT_COUNT.with(|counter| counter.set(counter.get().saturating_add(1)));
        let verification = self.workspace.verify()?;
        let replay = self.workspace.replay_projection(projection_key)?;
        let stored = self.workspace.read_projection(projection_key)?;
        Ok((verification, replay, stored))
    }

    pub(crate) fn commit(
        &self,
        request: AuthorityObjectCommitRequest<'_>,
    ) -> Result<AuthorityCommit, CommitError> {
        self.workspace.commit_locked(request)
    }

    pub(crate) fn observe_generation(&self) -> Result<WorkspaceGeneration, String> {
        self.workspace.observe_generation()
    }
}

impl Workspace {
    pub(crate) fn create(root: PathBuf) -> Result<Self, String> {
        fs::create_dir(&root).map_err(|error| {
            format!(
                "workspace_create_failed: cannot create {}: {error}",
                root.display()
            )
        })?;
        atomic_publish(&root.join("workspace.marker"), WORKSPACE_MARKER)?;
        let workspace = Self { root };
        workspace.initialize_database()?;
        Ok(workspace)
    }

    pub(crate) fn open(root: PathBuf) -> Result<Self, String> {
        let marker = fs::read(root.join("workspace.marker"))
            .map_err(|error| format!("workspace_open_failed: {error}"))?;
        if marker != WORKSPACE_MARKER {
            return Err("workspace_open_failed: invalid workspace marker".to_string());
        }
        let workspace = Self { root };
        workspace.open_connection()?;
        Ok(workspace)
    }

    pub(crate) fn prepare_authority_object(
        raw_bytes: &[u8],
        media_type: &str,
        descriptive_metadata: &Value,
    ) -> Result<PreparedAuthorityObject, String> {
        if media_type.trim().is_empty() || !descriptive_metadata.is_object() {
            return Err("object_metadata_invalid".to_string());
        }
        reject_secret_metadata(descriptive_metadata)?;
        let raw_content_hash = content_hash(raw_bytes);
        let size_bytes = u64::try_from(raw_bytes.len())
            .map_err(|_| "object_too_large: size does not fit u64".to_string())?;
        let metadata = json!({
            "content_hash": raw_content_hash,
            "descriptive_metadata": descriptive_metadata,
            "media_type": media_type,
            "size_bytes": size_bytes,
        });
        let metadata_bytes = canonical_json_bytes(&metadata)?;
        let metadata_content_hash = content_hash(&metadata_bytes);
        Ok(PreparedAuthorityObject {
            raw_bytes: raw_bytes.to_vec(),
            metadata_bytes,
            object_reference: StoredObjectReference {
                content_hash: raw_content_hash,
                media_type: media_type.to_string(),
                size_bytes,
                metadata_content_hash,
            },
        })
    }

    pub(crate) fn resolve_reference(
        &self,
        object_reference: &StoredObjectReference,
    ) -> Result<Vec<u8>, String> {
        let connection = self.open_connection()?;
        verify_object_reference(&connection, object_reference)?;
        resolve_object(&connection, &object_reference.content_hash)
    }

    pub(crate) fn ledger_head(&self) -> Result<Option<String>, String> {
        ledger_head(&self.open_connection()?)
    }

    pub(crate) fn read_projection(&self, projection_key: &str) -> Result<Option<Value>, String> {
        read_projection(&self.open_connection()?, projection_key)
    }

    pub(crate) fn recover_pending_transaction(&self) -> Result<(), String> {
        let connection = self.open_connection()?;
        let integrity: String = connection
            .query_row("PRAGMA integrity_check", [], |row| row.get(0))
            .map_err(database_error)?;
        if integrity != "ok" {
            return Err(format!("transaction_recovery_failed:{integrity}"));
        }
        Ok(())
    }

    /// Observes the cheap durable identity of this workspace without replaying
    /// ledger history. Comparing two generations detects cooperative commits
    /// and ordinary observable changes to governed storage. Deliberate raw-byte
    /// tampering that preserves every observed file identity remains the work
    /// of an explicit complete audit rather than this common-path signal.
    pub(crate) fn observe_generation(&self) -> Result<WorkspaceGeneration, String> {
        let marker_bytes = fs::read(self.root.join("workspace.marker"))
            .map_err(|error| format!("workspace_generation_failed:{error}"))?;
        let database_metadata = fs::metadata(self.root.join("workspace.sqlite3"))
            .map_err(|error| format!("workspace_generation_failed:{error}"))?;
        let database_modified = database_metadata
            .modified()
            .map_err(|error| format!("workspace_generation_failed:{error}"))?;
        let connection = self.open_connection()?;
        let ledger_head = ledger_head(&connection)?;
        let event_count: u64 = connection
            .query_row("SELECT COALESCE(MAX(sequence), 0) FROM ledger", [], |row| {
                row.get(0)
            })
            .map_err(database_error)?;
        Ok(WorkspaceGeneration {
            marker_signature: content_hash(&marker_bytes),
            database_size: database_metadata.len(),
            database_modified,
            ledger_head,
            event_count,
        })
    }

    #[cfg(test)]
    pub(crate) fn commit_authority_objects_and_event(
        &self,
        request: AuthorityObjectCommitRequest<'_>,
    ) -> Result<AuthorityCommit, CommitError> {
        self.writer().map_err(CommitError::from)?.commit(request)
    }

    pub(crate) fn verify(&self) -> Result<WorkspaceVerification, String> {
        let marker = fs::read(self.root.join("workspace.marker"))
            .map_err(|error| format!("workspace_verify_failed:{error}"))?;
        let connection = self.open_connection()?;
        let mut findings = Vec::new();
        if marker != WORKSPACE_MARKER {
            findings.push("workspace_marker_invalid".to_string());
        }
        let integrity: String = connection
            .query_row("PRAGMA integrity_check", [], |row| row.get(0))
            .map_err(database_error)?;
        if integrity != "ok" {
            findings.push(format!("sqlite_integrity_failed:{integrity}"));
        }
        let object_count = verify_objects(&connection, &mut findings)?;
        verify_ledger(&connection, &mut findings)?;
        verify_projections(&connection, &mut findings)?;
        findings.sort();
        findings.dedup();
        Ok(WorkspaceVerification {
            valid: findings.is_empty(),
            object_count,
            findings,
        })
    }

    pub(crate) fn replay_projection(
        &self,
        projection_key: &str,
    ) -> Result<ProjectionReplay, String> {
        replay_projection(&self.open_connection()?, projection_key)
    }

    pub(crate) fn writer(&self) -> Result<AuthorityWriter<'_>, String> {
        Ok(AuthorityWriter {
            workspace: self,
            _lock_file: self.lock_writer()?,
        })
    }

    fn lock_writer(&self) -> Result<fs::File, String> {
        let lock_file = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(false)
            .open(self.root.join("workspace.writer.lock"))
            .map_err(|error| format!("workspace_writer_conflict:{error}"))?;
        lock_file
            .lock_exclusive()
            .map_err(|error| format!("workspace_writer_conflict:{error}"))?;
        Ok(lock_file)
    }

    fn commit_locked(
        &self,
        request: AuthorityObjectCommitRequest<'_>,
    ) -> Result<AuthorityCommit, CommitError> {
        validate_commit_request(&request)?;
        let mut connection = self.open_connection()?;
        let transaction = connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(database_error)?;
        let current_head = ledger_head(&transaction)?;
        if current_head.as_deref() != request.event.expected_ledger_head {
            return Err(CommitError::LedgerHeadMismatch {
                expected: request.event.expected_ledger_head.map(str::to_owned),
                actual: current_head,
            });
        }
        for prepared in request.prepared_objects {
            publish_object(
                &transaction,
                &prepared.object_reference.content_hash,
                &prepared.raw_bytes,
            )?;
            publish_object(
                &transaction,
                &prepared.object_reference.metadata_content_hash,
                &prepared.metadata_bytes,
            )?;
        }
        for reference in request.event.required_references {
            verify_object_reference(&transaction, reference)?;
        }
        let previous_sequence: Option<u64> = transaction
            .query_row("SELECT MAX(sequence) FROM ledger", [], |row| row.get(0))
            .map_err(database_error)?;
        let sequence = previous_sequence
            .unwrap_or(0)
            .checked_add(1)
            .ok_or_else(|| "ledger_sequence_overflow".to_string())?;
        let mut references = request.event.required_references.to_vec();
        sort_references(&mut references);
        references.dedup();
        let projection_json = canonical_json_string(request.event.projection_value)?;
        let event = json!({
            "actor_kind": "authority_core",
            "canonical_command_content_hash": request.event.canonical_command_content_hash,
            "event_kind": request.event.event_kind,
            "payload": request.event.event_payload,
            "payload_content_hash": content_hash(
                &canonical_json_bytes(request.event.event_payload)?,
            ),
            "previous_event_hash": current_head,
            "referenced_object_closure": references,
            "resulting_projection_content_hash": content_hash(projection_json.as_bytes()),
            "sequence": sequence,
        });
        let event_json = canonical_json_string(&event)?;
        let event_hash = content_hash(event_json.as_bytes());
        let references_json = canonical_json_string(&event["referenced_object_closure"])?;
        transaction
            .execute(
                "INSERT INTO ledger (
                    sequence,
                    event_hash,
                    previous_event_hash,
                    event_json,
                    references_json,
                    projection_key,
                    projection_json
                 ) VALUES (?1,?2,?3,?4,?5,?6,?7)",
                params![
                    sequence,
                    event_hash,
                    current_head,
                    event_json,
                    references_json,
                    request.event.projection_key,
                    projection_json,
                ],
            )
            .map_err(database_error)?;
        transaction
            .execute(
                "INSERT INTO projections (projection_key,projection_json)
                 VALUES (?1,?2)
                 ON CONFLICT(projection_key)
                 DO UPDATE SET projection_json=excluded.projection_json",
                params![request.event.projection_key, projection_json],
            )
            .map_err(database_error)?;
        transaction
            .execute(
                "INSERT INTO metadata (key,value)
                 VALUES ('ledger_head',?1)
                 ON CONFLICT(key)
                 DO UPDATE SET value=excluded.value",
                params![event_hash],
            )
            .map_err(database_error)?;
        transaction.commit().map_err(database_error)?;
        Ok(AuthorityCommit {
            ledger_head: event_hash,
            sequence,
        })
    }

    fn initialize_database(&self) -> Result<(), String> {
        let connection =
            Connection::open(self.root.join("workspace.sqlite3")).map_err(database_error)?;
        connection
            .execute_batch(
                "PRAGMA foreign_keys=ON;
                 PRAGMA journal_mode=DELETE;
                 CREATE TABLE metadata (key TEXT PRIMARY KEY,value TEXT NOT NULL);
                 CREATE TABLE objects (content_hash TEXT PRIMARY KEY,raw_bytes BLOB NOT NULL);
                 CREATE TABLE ledger (
                    sequence INTEGER PRIMARY KEY,
                    event_hash TEXT NOT NULL UNIQUE,
                    previous_event_hash TEXT,
                    event_json TEXT NOT NULL,
                    references_json TEXT NOT NULL,
                    projection_key TEXT NOT NULL,
                    projection_json TEXT NOT NULL
                 );
                 CREATE TABLE projections (
                    projection_key TEXT PRIMARY KEY,
                    projection_json TEXT NOT NULL
                 );",
            )
            .map_err(database_error)?;
        atomic_publish(&self.root.join("workspace.writer.lock"), b"")
    }

    fn open_connection(&self) -> Result<Connection, String> {
        let connection =
            Connection::open(self.root.join("workspace.sqlite3")).map_err(database_error)?;
        connection
            .execute_batch("PRAGMA foreign_keys=ON; PRAGMA journal_mode=DELETE;")
            .map_err(database_error)?;
        Ok(connection)
    }
}

fn validate_commit_request(request: &AuthorityObjectCommitRequest<'_>) -> Result<(), String> {
    if !is_exact_sha256(request.event.canonical_command_content_hash)
        || request.event.event_kind.trim().is_empty()
        || request.event.projection_key.trim().is_empty()
    {
        return Err("authority_event_invalid".to_string());
    }
    for prepared in request.prepared_objects {
        if content_hash(&prepared.raw_bytes) != prepared.object_reference.content_hash
            || content_hash(&prepared.metadata_bytes)
                != prepared.object_reference.metadata_content_hash
            || u64::try_from(prepared.raw_bytes.len()).ok()
                != Some(prepared.object_reference.size_bytes)
            || !request
                .event
                .required_references
                .contains(&prepared.object_reference)
        {
            return Err("authority_object_invalid".to_string());
        }
    }
    canonical_json_bytes(request.event.event_payload)?;
    canonical_json_bytes(request.event.projection_value)?;
    Ok(())
}

fn publish_object(
    transaction: &Transaction<'_>,
    expected_hash: &str,
    bytes: &[u8],
) -> Result<(), String> {
    if content_hash(bytes) != expected_hash {
        return Err("object_hash_mismatch".to_string());
    }
    transaction
        .execute(
            "INSERT OR IGNORE INTO objects (content_hash,raw_bytes) VALUES (?1,?2)",
            params![expected_hash, bytes],
        )
        .map_err(database_error)?;
    let stored = resolve_object(transaction, expected_hash)?;
    if stored != bytes {
        return Err("object_collision".to_string());
    }
    Ok(())
}

fn resolve_object(connection: &Connection, expected_hash: &str) -> Result<Vec<u8>, String> {
    if !is_exact_sha256(expected_hash) {
        return Err("reference_unresolvable: content hash".to_string());
    }
    let bytes = connection
        .query_row(
            "SELECT raw_bytes FROM objects WHERE content_hash=?1",
            params![expected_hash],
            |row| row.get::<_, Vec<u8>>(0),
        )
        .optional()
        .map_err(database_error)?
        .ok_or_else(|| "reference_unresolvable: object missing".to_string())?;
    if content_hash(bytes.as_slice()) != expected_hash {
        return Err("reference_unresolvable: object hash".to_string());
    }
    Ok(bytes)
}

fn verify_object_reference(
    connection: &Connection,
    reference: &StoredObjectReference,
) -> Result<(), String> {
    if reference.media_type.trim().is_empty() || !is_exact_sha256(&reference.metadata_content_hash)
    {
        return Err("reference_unresolvable: reference shape".to_string());
    }
    let raw = resolve_object(connection, &reference.content_hash)?;
    if u64::try_from(raw.len()).ok() != Some(reference.size_bytes) {
        return Err("reference_unresolvable: object size".to_string());
    }
    let metadata = resolve_object(connection, &reference.metadata_content_hash)?;
    let metadata: Value = serde_json::from_slice(&metadata)
        .map_err(|_| "reference_unresolvable: metadata".to_string())?;
    if metadata["content_hash"] != reference.content_hash
        || metadata["media_type"] != reference.media_type
        || metadata["size_bytes"] != reference.size_bytes
    {
        return Err("reference_unresolvable: metadata mismatch".to_string());
    }
    Ok(())
}

fn ledger_head(connection: &Connection) -> Result<Option<String>, String> {
    connection
        .query_row(
            "SELECT value FROM metadata WHERE key='ledger_head'",
            [],
            |row| row.get(0),
        )
        .optional()
        .map_err(database_error)
}

fn read_projection(connection: &Connection, key: &str) -> Result<Option<Value>, String> {
    connection
        .query_row(
            "SELECT projection_json FROM projections WHERE projection_key=?1",
            params![key],
            |row| row.get::<_, String>(0),
        )
        .optional()
        .map_err(database_error)?
        .map(|raw| {
            serde_json::from_str(&raw).map_err(|error| format!("projection_corrupt:{error}"))
        })
        .transpose()
}

fn replay_projection(connection: &Connection, key: &str) -> Result<ProjectionReplay, String> {
    let mut statement = connection
        .prepare(
            "SELECT
                sequence,
                event_hash,
                previous_event_hash,
                event_json,
                references_json,
                projection_key,
                projection_json
             FROM ledger
             ORDER BY sequence",
        )
        .map_err(database_error)?;
    let rows = statement
        .query_map([], |row| {
            Ok((
                row.get::<_, u64>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, Option<String>>(2)?,
                row.get::<_, String>(3)?,
                row.get::<_, String>(4)?,
                row.get::<_, String>(5)?,
                row.get::<_, String>(6)?,
            ))
        })
        .map_err(database_error)?
        .collect::<Result<Vec<_>, _>>()
        .map_err(database_error)?;
    drop(statement);
    let mut previous = None;
    let mut payloads = Vec::new();
    let mut projection = None;
    for (
        index,
        (
            sequence,
            event_hash,
            recorded_previous,
            event_json,
            references_json,
            projection_key,
            projection_json,
        ),
    ) in rows.iter().enumerate()
    {
        let expected_sequence =
            u64::try_from(index + 1).map_err(|_| "ledger_sequence_overflow".to_string())?;
        if *sequence != expected_sequence
            || recorded_previous.as_deref() != previous.as_deref()
            || content_hash(event_json.as_bytes()) != *event_hash
        {
            return Err("ledger_integrity_failed:event chain".to_string());
        }
        let event: Value = serde_json::from_str(event_json)
            .map_err(|_| "ledger_integrity_failed:event json".to_string())?;
        let event_projection: Value = serde_json::from_str(projection_json)
            .map_err(|_| "ledger_integrity_failed:projection json".to_string())?;
        let references: Vec<StoredObjectReference> = serde_json::from_str(references_json)
            .map_err(|_| "ledger_integrity_failed:references".to_string())?;
        let mut canonical_references = references.clone();
        sort_references(&mut canonical_references);
        canonical_references.dedup();
        if canonical_references != references {
            return Err("ledger_integrity_failed:reference order".to_string());
        }
        if !event["canonical_command_content_hash"]
            .as_str()
            .is_some_and(is_exact_sha256)
            || canonical_json_string(&event)? != *event_json
            || canonical_json_string(&event_projection)? != *projection_json
            || canonical_json_string(
                &serde_json::to_value(&references)
                    .map_err(|_| "ledger_integrity_failed:references".to_string())?,
            )? != *references_json
            || event["payload_content_hash"]
                != content_hash(&canonical_json_bytes(&event["payload"])?)
            || event["resulting_projection_content_hash"]
                != content_hash(&canonical_json_bytes(&event_projection)?)
            || event["referenced_object_closure"]
                != serde_json::to_value(&references)
                    .map_err(|_| "ledger_integrity_failed:references".to_string())?
        {
            return Err("ledger_integrity_failed:event binding".to_string());
        }
        for reference in &references {
            verify_object_reference(connection, reference)?;
        }
        if projection_key == key {
            payloads.push(event["payload"].clone());
            projection = Some(event_projection);
        }
        previous = Some(event_hash.clone());
    }
    if ledger_head(connection)? != previous {
        return Err("ledger_integrity_failed:head".to_string());
    }
    #[cfg(test)]
    test_counters::HISTORICAL_ROW_COUNT.with(|counter| {
        counter.set(
            counter
                .get()
                .saturating_add(u64::try_from(rows.len()).unwrap_or(u64::MAX)),
        )
    });
    Ok(ProjectionReplay {
        event_count: u64::try_from(rows.len())
            .map_err(|_| "ledger_sequence_overflow".to_string())?,
        ledger_head: previous,
        payloads,
        projection,
    })
}

fn verify_objects(connection: &Connection, findings: &mut Vec<String>) -> Result<u64, String> {
    let mut statement = connection
        .prepare("SELECT content_hash,raw_bytes FROM objects ORDER BY content_hash")
        .map_err(database_error)?;
    let rows = statement
        .query_map([], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, Vec<u8>>(1)?))
        })
        .map_err(database_error)?;
    let mut count = 0_u64;
    for row in rows {
        let (stored_hash, bytes) = row.map_err(database_error)?;
        count = count
            .checked_add(1)
            .ok_or_else(|| "object_count_overflow".to_string())?;
        if content_hash(&bytes) != stored_hash {
            findings.push(format!("object_hash_mismatch:{stored_hash}"));
        }
    }
    Ok(count)
}

fn verify_ledger(connection: &Connection, findings: &mut Vec<String>) -> Result<(), String> {
    match replay_projection(connection, "authority_view") {
        Ok(_) => Ok(()),
        Err(error) => {
            findings.push(error);
            Ok(())
        }
    }
}

fn verify_projections(connection: &Connection, findings: &mut Vec<String>) -> Result<(), String> {
    let mut statement = connection
        .prepare("SELECT projection_key,projection_json FROM projections ORDER BY projection_key")
        .map_err(database_error)?;
    let rows = statement
        .query_map([], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
        })
        .map_err(database_error)?
        .collect::<Result<Vec<_>, _>>()
        .map_err(database_error)?;
    drop(statement);
    for (key, raw) in rows {
        let stored: Value = match serde_json::from_str(&raw) {
            Ok(value) => value,
            Err(_) => {
                findings.push(format!("projection_corrupt:{key}"));
                continue;
            }
        };
        match replay_projection(connection, &key) {
            Ok(replay) if replay.projection == Some(stored) => {}
            _ => findings.push(format!("projection_replay_mismatch:{key}")),
        }
    }
    Ok(())
}

fn sort_references(references: &mut [StoredObjectReference]) {
    references.sort_by(|left, right| {
        (
            &left.content_hash,
            &left.metadata_content_hash,
            &left.media_type,
            left.size_bytes,
        )
            .cmp(&(
                &right.content_hash,
                &right.metadata_content_hash,
                &right.media_type,
                right.size_bytes,
            ))
    });
}

fn canonical_json_bytes(value: &Value) -> Result<Vec<u8>, String> {
    serde_jcs::to_vec(value).map_err(|error| format!("canonical_json_failed:{error}"))
}

fn canonical_json_string(value: &Value) -> Result<String, String> {
    String::from_utf8(canonical_json_bytes(value)?)
        .map_err(|error| format!("canonical_json_failed:{error}"))
}

fn content_hash(bytes: &[u8]) -> String {
    format!("sha256:{:x}", Sha256::digest(bytes))
}

fn is_exact_sha256(value: &str) -> bool {
    value.len() == 71
        && value.starts_with("sha256:")
        && value[7..]
            .bytes()
            .all(|character| character.is_ascii_digit() || (b'a'..=b'f').contains(&character))
}

fn database_error(error: rusqlite::Error) -> String {
    format!("workspace_database_failed:{error}")
}

fn reject_secret_metadata(value: &Value) -> Result<(), String> {
    match value {
        Value::Object(fields) => {
            for (key, child) in fields {
                let normalized: String = key
                    .chars()
                    .filter(|character| character.is_ascii_alphanumeric())
                    .flat_map(char::to_lowercase)
                    .collect();
                if matches!(
                    normalized.as_str(),
                    "authorization" | "apikey" | "password" | "secret" | "accesstoken"
                ) {
                    return Err("secret_persistence_forbidden".to_string());
                }
                reject_secret_metadata(child)?;
            }
        }
        Value::Array(items) => {
            for item in items {
                reject_secret_metadata(item)?;
            }
        }
        Value::String(text) => {
            let lowercase = text.to_ascii_lowercase();
            if lowercase.contains("authorization: bearer ") || lowercase.starts_with("bearer ") {
                return Err("secret_persistence_forbidden".to_string());
            }
        }
        _ => {}
    }
    Ok(())
}

fn atomic_publish(target: &Path, bytes: &[u8]) -> Result<(), String> {
    if target.exists() {
        return (fs::read(target).map_err(|error| format!("object_publish_failed:{error}"))?
            == bytes)
            .then_some(())
            .ok_or_else(|| "object_collision".to_string());
    }
    let parent = target
        .parent()
        .ok_or_else(|| "object_publish_failed".to_string())?;
    let sequence = TEMPORARY_FILE_SEQUENCE.fetch_add(1, Ordering::Relaxed);
    let temporary = parent.join(format!(".{}.{}.tmp", std::process::id(), sequence));
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&temporary)
        .map_err(|error| format!("object_publish_failed:{error}"))?;
    file.write_all(bytes)
        .and_then(|_| file.sync_all())
        .map_err(|error| format!("object_publish_failed:{error}"))?;
    drop(file);
    fs::rename(&temporary, target).map_err(|error| format!("object_publish_failed:{error}"))
}

#[cfg(test)]
pub(crate) fn reset_audit_counters() {
    test_counters::AUDIT_COUNT.with(|counter| counter.set(0));
    test_counters::HISTORICAL_ROW_COUNT.with(|counter| counter.set(0));
}

#[cfg(test)]
pub(crate) fn audit_count() -> u64 {
    test_counters::AUDIT_COUNT.with(|counter| counter.get())
}

#[cfg(test)]
pub(crate) fn historical_row_count() -> u64 {
    test_counters::HISTORICAL_ROW_COUNT.with(|counter| counter.get())
}

#[cfg(test)]
mod tests {
    fn path(label: &str) -> std::path::PathBuf {
        let sequence =
            super::TEMPORARY_FILE_SEQUENCE.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        std::env::temp_dir().join(format!(
            "metacraft-{label}-{}-{sequence}",
            std::process::id()
        ))
    }

    #[test]
    fn sqlite_transaction_publishes_objects_event_and_projection_together() {
        let root = path("atomic");
        let workspace = super::Workspace::create(root.clone()).unwrap();
        let prepared = super::Workspace::prepare_authority_object(
            br#"{"kind":"fixture"}"#,
            "application/json",
            &serde_json::json!({}),
        )
        .unwrap();
        let reference = prepared.object_reference.clone();
        let projection = serde_json::json!({"current": reference});
        let commit = workspace
            .commit_authority_objects_and_event(super::AuthorityObjectCommitRequest {
                event: super::AuthorityEventCommitRequest {
                    expected_ledger_head: None,
                    canonical_command_content_hash: &format!("sha256:{}", "a".repeat(64)),
                    event_kind: "fixture_recorded",
                    required_references: std::slice::from_ref(&reference),
                    event_payload: &serde_json::json!({"body_reference": reference}),
                    projection_key: "authority_view",
                    projection_value: &projection,
                },
                prepared_objects: &[prepared],
            })
            .unwrap();
        assert_eq!(commit.sequence, 1);
        assert_eq!(
            workspace.resolve_reference(&reference).unwrap(),
            br#"{"kind":"fixture"}"#
        );
        assert_eq!(
            workspace.read_projection("authority_view").unwrap(),
            Some(projection)
        );
        assert!(workspace.verify().unwrap().valid);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn stale_revision_rolls_back_every_prepared_object() {
        let root = path("rollback");
        let workspace = super::Workspace::create(root.clone()).unwrap();
        let seed_projection = serde_json::json!({"seed": true});
        let seed = workspace
            .commit_authority_objects_and_event(super::AuthorityObjectCommitRequest {
                event: super::AuthorityEventCommitRequest {
                    expected_ledger_head: None,
                    canonical_command_content_hash: &format!("sha256:{}", "a".repeat(64)),
                    event_kind: "fixture_recorded",
                    required_references: &[],
                    event_payload: &serde_json::json!({"kind": "seed"}),
                    projection_key: "authority_view",
                    projection_value: &seed_projection,
                },
                prepared_objects: &[],
            })
            .unwrap();
        let prepared = super::Workspace::prepare_authority_object(
            b"new",
            "text/plain",
            &serde_json::json!({}),
        )
        .unwrap();
        let reference = prepared.object_reference.clone();
        let error = workspace
            .commit_authority_objects_and_event(super::AuthorityObjectCommitRequest {
                event: super::AuthorityEventCommitRequest {
                    expected_ledger_head: None,
                    canonical_command_content_hash: &format!("sha256:{}", "b".repeat(64)),
                    event_kind: "fixture_recorded",
                    required_references: std::slice::from_ref(&reference),
                    event_payload: &serde_json::json!({"kind": "stale"}),
                    projection_key: "authority_view",
                    projection_value: &serde_json::json!({"stale": true}),
                },
                prepared_objects: &[prepared],
            })
            .unwrap_err();
        assert_eq!(
            error,
            super::CommitError::LedgerHeadMismatch {
                expected: None,
                actual: Some(seed.ledger_head.clone()),
            }
        );
        assert!(workspace.resolve_reference(&reference).is_err());
        assert_eq!(workspace.ledger_head().unwrap(), Some(seed.ledger_head));
        assert_eq!(
            workspace.read_projection("authority_view").unwrap(),
            Some(seed_projection)
        );
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn sqlite_recovers_an_uncommitted_transaction() {
        let root = path("recovery");
        let workspace = super::Workspace::create(root.clone()).unwrap();
        {
            let mut connection = workspace.open_connection().unwrap();
            let transaction = connection.transaction().unwrap();
            transaction
                .execute(
                    "INSERT INTO objects (content_hash,raw_bytes) VALUES (?1,?2)",
                    rusqlite::params![super::content_hash(b"orphan"), b"orphan"],
                )
                .unwrap();
        }
        workspace.recover_pending_transaction().unwrap();
        assert_eq!(workspace.verify().unwrap().object_count, 0);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn projection_tampering_is_detected() {
        let root = path("tamper");
        let workspace = super::Workspace::create(root.clone()).unwrap();
        workspace
            .commit_authority_objects_and_event(super::AuthorityObjectCommitRequest {
                event: super::AuthorityEventCommitRequest {
                    expected_ledger_head: None,
                    canonical_command_content_hash: &format!("sha256:{}", "a".repeat(64)),
                    event_kind: "fixture_recorded",
                    required_references: &[],
                    event_payload: &serde_json::json!({"kind": "fixture"}),
                    projection_key: "authority_view",
                    projection_value: &serde_json::json!({"valid": true}),
                },
                prepared_objects: &[],
            })
            .unwrap();
        workspace
            .open_connection()
            .unwrap()
            .execute(
                "UPDATE projections SET projection_json='{}' WHERE projection_key='authority_view'",
                [],
            )
            .unwrap();
        let verification = workspace.verify().unwrap();
        assert!(!verification.valid);
        assert!(verification
            .findings
            .contains(&"projection_replay_mismatch:authority_view".to_string()));
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn missing_committed_object_breaks_ledger_integrity() {
        let root = path("missing-object");
        let workspace = super::Workspace::create(root.clone()).unwrap();
        let prepared = super::Workspace::prepare_authority_object(
            br#"{"kind":"fixture"}"#,
            "application/json",
            &serde_json::json!({}),
        )
        .unwrap();
        let reference = prepared.object_reference.clone();
        workspace
            .commit_authority_objects_and_event(super::AuthorityObjectCommitRequest {
                event: super::AuthorityEventCommitRequest {
                    expected_ledger_head: None,
                    canonical_command_content_hash: &format!("sha256:{}", "a".repeat(64)),
                    event_kind: "fixture_recorded",
                    required_references: std::slice::from_ref(&reference),
                    event_payload: &serde_json::json!({"body_reference": reference}),
                    projection_key: "authority_view",
                    projection_value: &serde_json::json!({"recorded": true}),
                },
                prepared_objects: &[prepared],
            })
            .unwrap();
        workspace
            .open_connection()
            .unwrap()
            .execute(
                "DELETE FROM objects WHERE content_hash=?1",
                rusqlite::params![reference.content_hash],
            )
            .unwrap();
        let verification = workspace.verify().unwrap();
        assert!(!verification.valid);
        assert!(verification
            .findings
            .iter()
            .any(|finding| finding.starts_with("reference_unresolvable:")));
        std::fs::remove_dir_all(root).unwrap();
    }
}
