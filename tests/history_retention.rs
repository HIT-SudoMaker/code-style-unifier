use std::fs;

use tempfile::tempdir;
use unifier::core::history::{clear_history, list_runs, prune_history, HistoryRetention};

#[test]
fn prunes_oldest_runs_when_count_exceeds_limit() {
    let dir = tempdir().unwrap();
    let runs = dir.path().join("runs");
    fs::create_dir_all(&runs).unwrap();
    for name in ["20990101T120000Z", "20990101T120100Z", "20990101T120200Z"] {
        fs::create_dir_all(runs.join(name)).unwrap();
    }

    let removed = prune_history(
        dir.path(),
        HistoryRetention {
            max_runs: 2,
            max_days: 14,
            max_bytes: 536_870_912,
        },
    )
    .unwrap();

    assert_eq!(removed, 1);
    assert!(!runs.join("20990101T120000Z").exists());
    assert_eq!(fs::read_dir(runs).unwrap().count(), 2);
}

#[test]
fn prunes_runs_older_than_day_limit_by_run_directory_name() {
    let dir = tempdir().unwrap();
    let runs = dir.path().join("runs");
    fs::create_dir_all(&runs).unwrap();
    fs::create_dir_all(runs.join("20000101T000000Z")).unwrap();
    fs::create_dir_all(runs.join("20990101T000000Z")).unwrap();

    let removed = prune_history(
        dir.path(),
        HistoryRetention {
            max_runs: 30,
            max_days: 14,
            max_bytes: 536_870_912,
        },
    )
    .unwrap();

    assert_eq!(removed, 1);
    assert!(!runs.join("20000101T000000Z").exists());
    assert!(runs.join("20990101T000000Z").exists());
}

#[test]
fn prunes_oldest_runs_until_total_bytes_fit_limit() {
    let dir = tempdir().unwrap();
    let runs = dir.path().join("runs");
    fs::create_dir_all(&runs).unwrap();
    for name in ["20990101T120000Z", "20990101T120100Z", "20990101T120200Z"] {
        let run = runs.join(name);
        fs::create_dir_all(&run).unwrap();
        fs::write(run.join("summary.json"), [0_u8; 4]).unwrap();
    }

    let removed = prune_history(
        dir.path(),
        HistoryRetention {
            max_runs: 30,
            max_days: 14,
            max_bytes: 8,
        },
    )
    .unwrap();

    assert_eq!(removed, 1);
    assert!(!runs.join("20990101T120000Z").exists());
    assert_eq!(fs::read_dir(runs).unwrap().count(), 2);
}

#[test]
fn lists_runs_in_oldest_first_order_and_clears_all_runs() {
    let dir = tempdir().unwrap();
    let runs = dir.path().join("runs");
    fs::create_dir_all(&runs).unwrap();
    fs::create_dir_all(runs.join("20990101T120200Z")).unwrap();
    fs::create_dir_all(runs.join("20990101T120000Z")).unwrap();

    let listed = list_runs(dir.path()).unwrap();
    let names: Vec<_> = listed
        .iter()
        .map(|path| path.file_name().unwrap().to_string_lossy().into_owned())
        .collect();
    assert_eq!(names, vec!["20990101T120000Z", "20990101T120200Z"]);

    assert_eq!(clear_history(dir.path()).unwrap(), 2);
    assert_eq!(
        list_runs(dir.path()).unwrap(),
        Vec::<std::path::PathBuf>::new()
    );
}
