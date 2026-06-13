use std::fs;

use tempfile::tempdir;
use unifier::core::evidence::EvidenceStore;
use unifier::core::frontend::extract_text_evidence;
use unifier::core::profile::Profile;
use unifier::core::scanner::scan_workspace;

/// 读取默认 profile
pub fn profile() -> Profile {
    Profile::from_toml_str(include_str!("../../profiles/default.toml")).unwrap()
}

/// 从临时源码提取事实
pub fn store_from_source(path: &str, source: &str) -> EvidenceStore {
    let dir = tempdir().unwrap();
    fs::write(dir.path().join(path), source).unwrap();
    let state = scan_workspace(dir.path(), &[]).unwrap();
    extract_text_evidence(&state).unwrap()
}
