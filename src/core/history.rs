use std::fs;
use std::path::{Path, PathBuf};

use serde::Serialize;
use serde_json::json;
use time::format_description::well_known::Rfc3339;
use time::macros::format_description;
use time::{Date, Duration, Month, OffsetDateTime, PrimitiveDateTime, Time};

use crate::core::error::{CoreError, Result};
use crate::core::evidence::{EvidenceStore, HistoryHealthFact};
use crate::core::issue::{Issue, IssueKind};
use crate::core::scanner::WorkspaceState;

/// History 保留策略
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct HistoryRetention {
    /// 最多保留运行次数
    pub max_runs: usize,
    /// 最多保留天数
    pub max_days: i64,
    /// 最多占用字节数
    pub max_bytes: u64,
}

/// 写入一次扫描历史
pub fn write_history_run(
    history_root: &Path,
    state: &WorkspaceState,
    store: &EvidenceStore,
    issues: &[Issue],
    profile: &str,
    status: &str,
) -> Result<PathBuf> {
    let runs_dir = history_root.join("runs");
    fs::create_dir_all(&runs_dir).map_err(|source| CoreError::Io {
        path: runs_dir.display().to_string(),
        source,
    })?;

    let now = OffsetDateTime::now_utc();
    let timestamp = now
        .format(format_description!(
            "[year][month][day]T[hour][minute][second]Z"
        ))
        .map_err(serialization_error)?;
    let run_dir = unique_run_dir(&runs_dir, &timestamp)?;
    fs::create_dir_all(&run_dir).map_err(|source| CoreError::Io {
        path: run_dir.display().to_string(),
        source,
    })?;

    let run_name = run_dir
        .file_name()
        .map(|name| name.to_string_lossy().into_owned())
        .unwrap_or(timestamp);
    let started_at = now.format(&Rfc3339).map_err(serialization_error)?;
    let blocking_issue_count = issues.iter().filter(|issue| issue.blocks).count();

    let run_json = json!({
        "id": format!("run:{run_name}"),
        "target": state.target.display().to_string(),
        "started_at": started_at,
        "status": status,
        "profile": profile,
        "workspace_fingerprint": state.fingerprint,
        "file_count": state.files.len(),
        "issue_count": issues.len(),
        "blocking_issue_count": blocking_issue_count,
    });
    write_json_pretty(&run_dir.join("run.json"), &run_json)?;

    let summary_json = json!({
        "files": state.files.len(),
        "issues": issues.len(),
        "hard_violations": issues
            .iter()
            .filter(|issue| issue.kind == IssueKind::HardViolation)
            .count(),
        "soft_frictions": issues
            .iter()
            .filter(|issue| issue.kind == IssueKind::SoftFriction)
            .count(),
        "under_review": issues
            .iter()
            .filter(|issue| issue.kind == IssueKind::UnderReview)
            .count(),
    });
    write_json_pretty(&run_dir.join("summary.json"), &summary_json)?;
    write_issues_jsonl(&run_dir.join("issues.jsonl"), issues)?;
    write_evidence_index(&run_dir.join("evidence_index.jsonl"), store)?;

    Ok(run_dir)
}

/// 按保留策略清理扫描历史
pub fn prune_history(history_root: &Path, retention: HistoryRetention) -> Result<usize> {
    let mut runs = load_runs(history_root)?;
    if runs.is_empty() {
        return Ok(0);
    }

    let mut removed = 0;
    let cutoff = OffsetDateTime::now_utc() - Duration::days(retention.max_days);
    removed += remove_matching(&mut runs, |run| {
        run.started_at.is_some_and(|time| time < cutoff)
    })?;

    while runs.len() > retention.max_runs {
        removed += remove_oldest(&mut runs)?;
    }

    let mut total_bytes = runs.iter().map(|run| run.bytes).sum::<u64>();
    while total_bytes > retention.max_bytes {
        let removed_run = runs.first().map(|run| run.bytes).ok_or_else(|| {
            CoreError::Profile("history byte pruning has no run to remove".to_string())
        })?;
        removed += remove_oldest(&mut runs)?;
        total_bytes = total_bytes.saturating_sub(removed_run);
    }

    Ok(removed)
}

/// 删除全部扫描历史
pub fn clear_history(history_root: &Path) -> Result<usize> {
    let runs = list_runs(history_root)?;
    let mut removed = 0;
    for path in runs {
        remove_dir(&path)?;
        removed += 1;
    }
    Ok(removed)
}

/// 列出扫描历史
pub fn list_runs(history_root: &Path) -> Result<Vec<PathBuf>> {
    Ok(load_runs(history_root)?
        .into_iter()
        .map(|run| run.path)
        .collect())
}

/// 读取扫描记录健康事实
pub fn read_history_health(history_root: &Path) -> Result<HistoryHealthFact> {
    let runs = load_runs(history_root)?;
    let now = OffsetDateTime::now_utc();
    let oldest_run_age_days = runs
        .iter()
        .filter_map(|run| run.started_at)
        .map(|started_at| (now - started_at).whole_days().max(0))
        .max()
        .unwrap_or(0);

    Ok(HistoryHealthFact {
        run_count: runs.len(),
        oldest_run_age_days,
        total_bytes: runs.iter().map(|run| run.bytes).sum(),
    })
}

#[derive(Debug)]
struct RunEntry {
    path: PathBuf,
    name: String,
    started_at: Option<OffsetDateTime>,
    bytes: u64,
}

fn load_runs(history_root: &Path) -> Result<Vec<RunEntry>> {
    let runs_dir = history_root.join("runs");
    if !path_exists(&runs_dir)? {
        return Ok(Vec::new());
    }

    let mut runs = Vec::new();
    for entry in fs::read_dir(&runs_dir).map_err(|source| CoreError::Io {
        path: runs_dir.display().to_string(),
        source,
    })? {
        let path = entry
            .map_err(|source| CoreError::Io {
                path: runs_dir.display().to_string(),
                source,
            })?
            .path();
        if !path.is_dir() {
            continue;
        }
        let name = path
            .file_name()
            .map(|name| name.to_string_lossy().into_owned())
            .unwrap_or_default();
        let started_at = parse_run_time(&name);
        let bytes = dir_size(&path)?;
        runs.push(RunEntry {
            path,
            name,
            started_at,
            bytes,
        });
    }
    sort_runs(&mut runs);
    Ok(runs)
}

fn sort_runs(runs: &mut [RunEntry]) {
    runs.sort_by(|left, right| match (left.started_at, right.started_at) {
        (Some(left_time), Some(right_time)) => left_time.cmp(&right_time),
        _ => left.name.cmp(&right.name),
    });
}

fn remove_matching(
    runs: &mut Vec<RunEntry>,
    should_remove: impl Fn(&RunEntry) -> bool,
) -> Result<usize> {
    let mut removed = 0;
    let mut kept = Vec::with_capacity(runs.len());
    for run in runs.drain(..) {
        if should_remove(&run) {
            remove_dir(&run.path)?;
            removed += 1;
        } else {
            kept.push(run);
        }
    }
    *runs = kept;
    Ok(removed)
}

fn remove_oldest(runs: &mut Vec<RunEntry>) -> Result<usize> {
    let run = runs.remove(0);
    remove_dir(&run.path)?;
    Ok(1)
}

fn dir_size(path: &Path) -> Result<u64> {
    let mut total = 0;
    for entry in fs::read_dir(path).map_err(|source| CoreError::Io {
        path: path.display().to_string(),
        source,
    })? {
        let path = entry
            .map_err(|source| CoreError::Io {
                path: path.display().to_string(),
                source,
            })?
            .path();
        let metadata = fs::metadata(&path).map_err(|source| CoreError::Io {
            path: path.display().to_string(),
            source,
        })?;
        if metadata.is_dir() {
            total += dir_size(&path)?;
        } else if metadata.is_file() {
            total += metadata.len();
        }
    }
    Ok(total)
}

fn remove_dir(path: &Path) -> Result<()> {
    fs::remove_dir_all(path).map_err(|source| CoreError::Io {
        path: path.display().to_string(),
        source,
    })
}

fn path_exists(path: &Path) -> Result<bool> {
    path.try_exists().map_err(|source| CoreError::Io {
        path: path.display().to_string(),
        source,
    })
}

fn parse_run_time(name: &str) -> Option<OffsetDateTime> {
    let stamp = name.get(0.."YYYYMMDDTHHMMSSZ".len())?;
    if stamp.as_bytes().get(8) != Some(&b'T') || stamp.as_bytes().get(15) != Some(&b'Z') {
        return None;
    }

    let year = stamp.get(0..4)?.parse::<i32>().ok()?;
    let month = stamp.get(4..6)?.parse::<u8>().ok()?;
    let day = stamp.get(6..8)?.parse::<u8>().ok()?;
    let hour = stamp.get(9..11)?.parse::<u8>().ok()?;
    let minute = stamp.get(11..13)?.parse::<u8>().ok()?;
    let second = stamp.get(13..15)?.parse::<u8>().ok()?;
    let date = Date::from_calendar_date(year, Month::try_from(month).ok()?, day).ok()?;
    let time = Time::from_hms(hour, minute, second).ok()?;
    Some(PrimitiveDateTime::new(date, time).assume_utc())
}

fn unique_run_dir(runs_dir: &Path, timestamp: &str) -> Result<PathBuf> {
    let first = runs_dir.join(timestamp);
    if !path_exists(&first)? {
        return Ok(first);
    }

    for index in 1..1000 {
        let candidate = runs_dir.join(format!("{timestamp}-{index:03}"));
        if !path_exists(&candidate)? {
            return Ok(candidate);
        }
    }

    Err(CoreError::Profile(
        "history run directory collision limit reached".to_string(),
    ))
}

fn write_json_pretty(path: &Path, value: &impl Serialize) -> Result<()> {
    let bytes = serde_json::to_vec_pretty(value).map_err(serialization_error)?;
    fs::write(path, bytes).map_err(|source| CoreError::Io {
        path: path.display().to_string(),
        source,
    })
}

fn write_issues_jsonl(path: &Path, issues: &[Issue]) -> Result<()> {
    let mut output = String::new();
    for issue in issues {
        push_json_line(&mut output, issue)?;
    }
    fs::write(path, output).map_err(|source| CoreError::Io {
        path: path.display().to_string(),
        source,
    })
}

fn write_evidence_index(path: &Path, store: &EvidenceStore) -> Result<()> {
    let mut output = String::new();
    push_json_line(
        &mut output,
        &json!({
            "id": store.workspace.id,
            "type": "workspace",
            "root": store.workspace.root,
            "target": store.workspace.target,
            "profile_id": store.workspace.profile_id,
            "fingerprint": store.workspace.fingerprint,
        }),
    )?;

    if let Some(history) = store.history_health {
        push_json_line(
            &mut output,
            &json!({
                "id": "history:health",
                "type": "history_health",
                "run_count": history.run_count,
                "oldest_run_age_days": history.oldest_run_age_days,
                "total_bytes": history.total_bytes,
            }),
        )?;
    }

    for file in &store.file_units {
        push_json_line(
            &mut output,
            &json!({
                "id": file.id,
                "type": "file_unit",
                "path": file.path,
                "language": file.language,
                "generated": file.generated,
                "excluded": file.excluded,
                "fingerprint": file.fingerprint,
            }),
        )?;
    }

    for module in &store.module_units {
        push_json_line(
            &mut output,
            &json!({
                "id": module.id,
                "type": "module_unit",
                "file_id": module.file_id,
                "language": module.language,
                "path": module.path,
                "range": module.range,
                "has_module_doc_region": module.has_module_doc_region,
                "is_header": module.is_header,
                "include_guard": module.include_guard,
                "pragma_once": module.pragma_once,
            }),
        )?;
    }

    for edge in &store.dependency_edges {
        push_json_line(
            &mut output,
            &json!({
                "id": edge.id,
                "type": "dependency_edge",
                "file_id": edge.file_id,
                "module_id": edge.module_id,
                "group": edge.group,
                "range": edge.range,
                "source_hash": hash_index_text(&edge.source),
                "imported_hash": hash_index_text(&edge.imported),
                "alias_hash": edge.alias.as_ref().map(|alias| hash_index_text(alias)),
                "is_glob": edge.is_glob,
                "is_public": edge.is_public,
                "is_relative": edge.is_relative,
            }),
        )?;
    }

    for doc in &store.doc_regions {
        push_json_line(
            &mut output,
            &json!({
                "id": doc.id,
                "type": "doc_region",
                "file_id": doc.file_id,
                "symbol_name_hash": hash_index_text(&doc.symbol_name),
                "range": doc.range,
                "summary_text_id": doc.summary_text_id,
                "full_text_id": doc.full_text_id,
            }),
        )?;
    }

    for comment in &store.comment_regions {
        push_json_line(
            &mut output,
            &json!({
                "id": comment.id,
                "type": "comment_region",
                "file_id": comment.file_id,
                "range": comment.range,
                "kind": comment.kind,
                "text_id": comment.text_id,
            }),
        )?;
    }

    for text in &store.text_spans {
        let terminal_punctuation = text
            .terminal_punctuation
            .map(|character| character.to_string());

        push_json_line(
            &mut output,
            &json!({
                "id": text.id,
                "type": "text_span",
                "file_id": text.file_id,
                "range": text.range,
                "role": text.role,
                "text_hash": text.text_hash,
                "terminal_punctuation": terminal_punctuation,
            }),
        )?;
    }

    for line in &store.line_spans {
        push_json_line(
            &mut output,
            &json!({
                "id": line.id,
                "type": "line_span",
                "file_id": line.file_id,
                "line": line.line,
                "visual_width": line.visual_width,
                "line_hash": line.line_hash,
            }),
        )?;
    }

    for public_surface in &store.public_surfaces {
        push_json_line(
            &mut output,
            &json!({
                "id": public_surface.id,
                "type": "public_surface",
                "symbol_name_hash": hash_index_text(&public_surface.symbol_name),
                "visibility": public_surface.visibility,
                "has_doc_region": public_surface.has_doc_region,
                "file_id": public_surface.file_id,
                "range": public_surface.range,
            }),
        )?;
    }

    for symbol in &store.symbols {
        let return_annotation_hash = symbol
            .return_annotation
            .as_ref()
            .map(|value| hash_index_text(value));

        push_json_line(
            &mut output,
            &json!({
                "id": symbol.id,
                "type": "symbol",
                "file_id": symbol.file_id,
                "module_id": symbol.module_id,
                "name_hash": hash_index_text(&symbol.name),
                "qualified_name_hash": hash_index_text(&symbol.qualified_name),
                "kind": symbol.kind,
                "visibility": symbol.visibility,
                "language": symbol.language,
                "range": symbol.range,
                "doc_region_id": symbol.doc_region_id,
                "return_annotation_hash": return_annotation_hash,
                "missing_parameter_count": symbol.missing_parameter_annotations.len(),
                "type_text_hash": symbol.type_text.as_ref().map(|value| hash_index_text(value)),
                "is_async": symbol.is_async,
                "is_unsafe": symbol.is_unsafe,
                "attribute_count": symbol.attributes.len(),
            }),
        )?;
    }

    for block in &store.block_regions {
        push_json_line(
            &mut output,
            &json!({
                "id": block.id,
                "type": "block_region",
                "file_id": block.file_id,
                "range": block.range,
                "kind": block.kind,
                "intent_comment_id": block.intent_comment_id,
            }),
        )?;
    }

    for expression in &store.expressions {
        let expression_hash = format!(
            "blake3:{}",
            blake3::hash(expression.text.as_bytes()).to_hex()
        );
        push_json_line(
            &mut output,
            &json!({
                "id": expression.id,
                "type": "expression",
                "file_id": expression.file_id,
                "module_id": expression.module_id,
                "symbol_id": expression.symbol_id,
                "kind": expression.kind,
                "range": expression.range,
                "text_hash": expression_hash,
                "callee_hash": expression.callee.as_ref().map(|callee| hash_index_text(callee)),
            }),
        )?;
    }

    fs::write(path, output).map_err(|source| CoreError::Io {
        path: path.display().to_string(),
        source,
    })
}

fn push_json_line(output: &mut String, value: &impl Serialize) -> Result<()> {
    output.push_str(&serde_json::to_string(value).map_err(serialization_error)?);
    output.push('\n');
    Ok(())
}

fn hash_index_text(text: &str) -> String {
    format!("blake3:{}", blake3::hash(text.as_bytes()).to_hex())
}

fn serialization_error(error: impl std::fmt::Display) -> CoreError {
    CoreError::Serialization(error.to_string())
}
