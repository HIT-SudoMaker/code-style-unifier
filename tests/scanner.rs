use std::fs;

use tempfile::tempdir;
use unifier::core::error::CoreError;
use unifier::core::issue::Language;
use unifier::core::scanner::scan_workspace;

#[test]
fn recursively_detects_supported_languages_and_skips_target() {
    let dir = tempdir().unwrap();
    fs::create_dir_all(dir.path().join("src")).unwrap();
    fs::create_dir_all(dir.path().join("target")).unwrap();
    fs::write(dir.path().join("src/lib.rs"), "pub fn run() {}\n").unwrap();
    fs::write(
        dir.path().join("src/module.py"),
        "def run():\n    return 1\n",
    )
    .unwrap();
    fs::write(
        dir.path().join("src/main.cpp"),
        "int main() { return 0; }\n",
    )
    .unwrap();
    fs::write(
        dir.path().join("target/generated.rs"),
        "pub fn generated() {}\n",
    )
    .unwrap();

    let state = scan_workspace(dir.path(), &["target"]).unwrap();

    assert_eq!(state.files.len(), 3);
    assert!(state
        .files
        .iter()
        .any(|file| file.language == Language::Rust));
    assert!(state
        .files
        .iter()
        .any(|file| file.language == Language::Python));
    assert!(state
        .files
        .iter()
        .any(|file| file.language == Language::Cpp));
}

#[test]
fn scans_single_file_target() {
    let dir = tempdir().unwrap();
    let file_path = dir.path().join("module.py");
    fs::write(&file_path, "def run():\n    return 1\n").unwrap();

    let state = scan_workspace(&file_path, &[]).unwrap();

    assert_eq!(state.files.len(), 1);
    assert_eq!(state.files[0].language, Language::Python);
    assert_eq!(state.files[0].relative_path, "module.py");
}

#[test]
fn detects_typescript_extensions_and_flags_declaration_files() {
    let dir = tempdir().unwrap();
    fs::write(dir.path().join("app.ts"), "export const a = 1;\n").unwrap();
    fs::write(dir.path().join("view.tsx"), "export const B = () => null;\n").unwrap();
    fs::write(dir.path().join("types.d.ts"), "export declare const c: number;\n").unwrap();

    let state = scan_workspace(dir.path(), &[]).unwrap();

    assert!(state
        .files
        .iter()
        .all(|file| file.language == Language::Typescript));
    assert_eq!(state.files.len(), 3);
    let declaration = state
        .files
        .iter()
        .find(|file| file.relative_path == "types.d.ts")
        .expect("declaration file");
    assert!(declaration.generated, ".d.ts must be flagged generated");
    assert!(state
        .files
        .iter()
        .find(|file| file.relative_path == "app.ts")
        .is_some_and(|file| !file.generated));
}

#[test]
fn filters_unsupported_files() {
    let dir = tempdir().unwrap();
    fs::write(dir.path().join("README.md"), "# ignored\n").unwrap();
    fs::write(dir.path().join("lib.rs"), "pub fn run() {}\n").unwrap();

    let state = scan_workspace(dir.path(), &[]).unwrap();

    assert_eq!(state.files.len(), 1);
    assert_eq!(state.files[0].relative_path, "lib.rs");
}

#[test]
fn produces_deterministic_order_and_fingerprint() {
    let dir = tempdir().unwrap();
    fs::write(dir.path().join("z.rs"), "pub fn zed() {}\n").unwrap();
    fs::write(dir.path().join("a.py"), "def alpha():\n    return 1\n").unwrap();

    let first = scan_workspace(dir.path(), &[]).unwrap();
    let second = scan_workspace(dir.path(), &[]).unwrap();

    let paths: Vec<_> = first
        .files
        .iter()
        .map(|file| file.relative_path.as_str())
        .collect();
    assert_eq!(paths, vec!["a.py", "z.rs"]);
    assert_eq!(first.fingerprint, second.fingerprint);
    assert_eq!(
        first
            .files
            .iter()
            .map(|file| file.fingerprint.as_str())
            .collect::<Vec<_>>(),
        second
            .files
            .iter()
            .map(|file| file.fingerprint.as_str())
            .collect::<Vec<_>>()
    );
}

#[test]
fn reports_missing_target() {
    let dir = tempdir().unwrap();
    let error = scan_workspace(&dir.path().join("missing"), &[]).unwrap_err();

    assert!(matches!(error, CoreError::MissingTarget(_)));
}

#[cfg(windows)]
#[test]
fn excludes_directories_case_insensitively_on_windows() {
    let dir = tempdir().unwrap();
    fs::create_dir_all(dir.path().join("src")).unwrap();
    fs::create_dir_all(dir.path().join("Target")).unwrap();
    fs::write(dir.path().join("src/lib.rs"), "pub fn run() {}\n").unwrap();
    fs::write(
        dir.path().join("Target/generated.rs"),
        "pub fn generated() {}\n",
    )
    .unwrap();

    let state = scan_workspace(dir.path(), &["target"]).unwrap();

    assert_eq!(state.files.len(), 1);
    assert_eq!(state.files[0].relative_path, "src/lib.rs");
}
