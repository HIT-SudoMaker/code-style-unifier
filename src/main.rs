use std::path::Path;
use std::process::ExitCode;

use clap::Parser;
use unifier::core::calibration::{
    read_calibration_cases_jsonl, read_issues_json, validate_cases_against_issues,
    CalibrationReport,
};
use unifier::core::cli::{CheckFormat, Cli, Command, HistoryCommand, RulesFormat};
use unifier::core::evaluators::evaluate_all;
use unifier::core::frontend::extract_text_evidence;
use unifier::core::history::{
    clear_history, list_runs, prune_history, read_history_health, write_history_run,
    HistoryRetention,
};
use unifier::core::issue::Issue;
use unifier::core::profile::Profile;
use unifier::core::rules::RuleCatalog;
use unifier::core::scanner::scan_workspace;

fn main() -> ExitCode {
    match run() {
        Ok(code) => code,
        Err(error) => {
            eprintln!("{error}");
            ExitCode::from(2)
        }
    }
}

fn run() -> anyhow::Result<ExitCode> {
    let cli = Cli::parse();
    match cli.command {
        Command::Check {
            path,
            profile,
            profile_path,
            format,
            output,
            history_dir,
            no_history,
        } => run_check(
            &path,
            &profile,
            profile_path.as_deref(),
            format,
            output.as_deref(),
            &history_dir,
            no_history,
        ),
        Command::Calibrate {
            issues,
            cases,
            output,
        } => run_calibrate(&issues, &cases, output.as_deref()),
        Command::Rules { format } => run_rules(format),
        Command::History {
            history_dir,
            command,
        } => run_history(&history_dir, command),
    }
}

fn run_check(
    path: &Path,
    profile_name: &str,
    profile_path: Option<&Path>,
    format: CheckFormat,
    output: Option<&Path>,
    history_root: &Path,
    no_history: bool,
) -> anyhow::Result<ExitCode> {
    let profile = load_profile(profile_name, profile_path)?;
    let exclude_dirs = profile
        .exclude_dirs
        .iter()
        .map(String::as_str)
        .collect::<Vec<_>>();
    let mut state = scan_workspace(path, &exclude_dirs)?;
    state.profile_id = profile.name.clone();
    let mut store = extract_text_evidence(&state)?;
    if !no_history {
        store.history_health = Some(read_history_health(history_root)?);
    }

    let issues: Vec<Issue> = evaluate_all(&store, &profile)
        .into_iter()
        .filter(|issue| profile.is_rule_enabled(&issue.rule))
        .collect();

    write_check_output(&issues, format, output)?;

    if !no_history {
        let status = if issues.iter().any(|issue| issue.blocks) {
            "failed"
        } else {
            "passed"
        };
        write_history_run(history_root, &state, &store, &issues, &profile.name, status)?;
        prune_history(
            history_root,
            HistoryRetention {
                max_runs: profile.thresholds.history_max_runs,
                max_days: profile.thresholds.history_max_days,
                max_bytes: profile.thresholds.history_max_bytes,
            },
        )?;
    }

    if issues.iter().any(|issue| issue.blocks) {
        Ok(ExitCode::from(1))
    } else {
        Ok(ExitCode::SUCCESS)
    }
}

fn run_calibrate(
    issues_path: &Path,
    cases_path: &Path,
    output: Option<&Path>,
) -> anyhow::Result<ExitCode> {
    let issues_input = std::fs::read_to_string(issues_path)?;
    let cases_input = std::fs::read_to_string(cases_path)?;
    let issues = read_issues_json(&issues_input).map_err(anyhow::Error::msg)?;
    let cases = read_calibration_cases_jsonl(&cases_input).map_err(anyhow::Error::msg)?;

    validate_cases_against_issues(&cases, &issues).map_err(anyhow::Error::msg)?;
    let report = CalibrationReport::from_cases(&cases).map_err(anyhow::Error::msg)?;
    let mut content = serde_json::to_string_pretty(&report)?;
    content.push('\n');

    if let Some(path) = output {
        if let Some(parent) = path
            .parent()
            .filter(|parent| !parent.as_os_str().is_empty())
        {
            std::fs::create_dir_all(parent)?;
        }
        std::fs::write(path, content)?;
    } else {
        print!("{content}");
    }

    Ok(ExitCode::SUCCESS)
}

fn run_rules(format: RulesFormat) -> anyhow::Result<ExitCode> {
    let catalog_toml = include_str!("../rules/catalog.toml");
    match format {
        RulesFormat::Json => {
            let catalog = RuleCatalog::from_toml_str(catalog_toml)?;
            println!("{}", serde_json::to_string_pretty(&catalog.to_view())?);
        }
        RulesFormat::Toml => print!("{catalog_toml}"),
    }
    Ok(ExitCode::SUCCESS)
}

fn run_history(root: &Path, command: HistoryCommand) -> anyhow::Result<ExitCode> {
    match command {
        HistoryCommand::List => {
            for run in list_runs(root)? {
                println!("{}", run.display());
            }
        }
        HistoryCommand::Prune => {
            let removed = prune_history(
                root,
                HistoryRetention {
                    max_runs: 30,
                    max_days: 14,
                    max_bytes: 536_870_912,
                },
            )?;
            println!(r#"{{"pruned":{removed}}}"#);
        }
        HistoryCommand::Clear => {
            let removed = clear_history(root)?;
            println!(r#"{{"cleared":{removed}}}"#);
        }
    }
    Ok(ExitCode::SUCCESS)
}

fn load_profile(profile_name: &str, profile_path: Option<&Path>) -> anyhow::Result<Profile> {
    if let Some(path) = profile_path {
        return Ok(Profile::from_toml_str(&std::fs::read_to_string(path)?)?);
    }

    if profile_name == "default" {
        return Ok(Profile::from_toml_str(include_str!(
            "../profiles/default.toml"
        ))?);
    }

    let path = Path::new("profiles").join(format!("{profile_name}.toml"));
    Ok(Profile::from_toml_str(&std::fs::read_to_string(path)?)?)
}

fn write_check_output(
    issues: &[Issue],
    format: CheckFormat,
    output: Option<&Path>,
) -> anyhow::Result<()> {
    let content = match format {
        CheckFormat::Json => {
            let mut content = serde_json::to_string(issues)?;
            content.push('\n');
            content
        }
        CheckFormat::Jsonl => {
            let mut content = String::new();
            for issue in issues {
                content.push_str(&serde_json::to_string(issue)?);
                content.push('\n');
            }
            content
        }
    };

    if let Some(path) = output {
        if let Some(parent) = path
            .parent()
            .filter(|parent| !parent.as_os_str().is_empty())
        {
            std::fs::create_dir_all(parent)?;
        }
        std::fs::write(path, content)?;
    } else {
        print!("{content}");
    }

    Ok(())
}
