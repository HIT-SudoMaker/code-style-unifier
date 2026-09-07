use std::fs;
use std::path::{Path, PathBuf};

fn rust_sources(root: &Path) -> Vec<PathBuf> {
    let mut sources = Vec::new();
    for entry in fs::read_dir(root).unwrap() {
        let path = entry.unwrap().path();
        if path.is_dir() {
            sources.extend(rust_sources(&path));
        } else if path.extension().is_some_and(|extension| extension == "rs") {
            sources.push(path);
        }
    }
    sources.sort();
    sources
}

fn contains_version_name(value: &str) -> bool {
    value
        .as_bytes()
        .windows(2)
        .any(|pair| pair[0].eq_ignore_ascii_case(&b'v') && pair[1].is_ascii_digit())
}

#[test]
fn rust_source_tree_stays_inside_the_authority_boundary() {
    let crate_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let source_root = crate_root.join("src");
    let sources = rust_sources(&source_root);
    let relative = sources
        .iter()
        .map(|path| {
            path.strip_prefix(&source_root)
                .unwrap()
                .to_string_lossy()
                .replace('\\', "/")
        })
        .collect::<Vec<_>>();
    assert!(relative.iter().all(|path| {
        path == "lib.rs"
            || path.starts_with("authority/")
            || path.starts_with("python_binding/")
            || path.starts_with("workspace/")
    }));
    assert!(
        relative.iter().all(|path| !contains_version_name(path)),
        "Rust contains a versioned source path"
    );

    let joined = sources
        .iter()
        .map(|path| fs::read_to_string(path).unwrap())
        .collect::<Vec<_>>()
        .join("\n")
        .to_ascii_lowercase();
    for forbidden in [
        "advice",
        "aperture",
        "brief",
        "campaign",
        "deepseek",
        "design",
        "fdtd",
        "geometry",
        "lumerical",
        "material",
        "metalens",
        "metric",
        "optimizer",
        "pancharatnam",
        "phase",
        "polarization",
        "route",
        "scientific",
        "simulation",
        "solver",
        "study",
        "sweep",
        "task",
        "workflow",
    ] {
        assert!(
            !joined.contains(forbidden),
            "Rust owns forbidden concern: {forbidden}"
        );
    }
    assert!(
        !contains_version_name(&joined),
        "Rust contains a versioned code name"
    );
}

#[test]
fn python_surface_is_one_authority_with_four_verbs() {
    let binding = fs::read_to_string(
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src/python_binding/mod.rs"),
    )
    .unwrap();
    assert_eq!(binding.matches("#[pyclass").count(), 1);
    assert!(!binding.contains("#[pyfunction"));
    let methods = binding
        .split("#[pymethods]")
        .nth(1)
        .unwrap()
        .split("#[pymodule]")
        .next()
        .unwrap()
        .lines()
        .filter_map(|line| {
            line.trim()
                .strip_prefix("fn ")
                .and_then(|declaration| declaration.split(['(', '<']).next())
        })
        .collect::<Vec<_>>();
    assert_eq!(methods, ["new", "check", "view", "fetch", "decide"]);
    for legacy in [
        "NativeWorkspace",
        "NativeAuthorityCore",
        "next_scientific",
        "_metacraft_core",
    ] {
        assert!(
            !binding.contains(legacy),
            "legacy surface escaped: {legacy}"
        );
    }
}

#[test]
fn dependency_set_contains_no_scientific_runtime() {
    let manifest =
        fs::read_to_string(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("Cargo.toml")).unwrap();
    for forbidden in ["rust_decimal", "serde_yaml", "numpy", "ndarray"] {
        assert!(
            !manifest.contains(forbidden),
            "forbidden dependency: {forbidden}"
        );
    }
}
