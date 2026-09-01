use clap::Parser;
use clap::Subcommand;
use clap::ValueEnum;
use csu::AuthorityInput;
use csu::Disposition;
use csu::ReviewInput;
use csu::ReviewTerminal;
use csu::WorkspaceReviewer;
use csu::project_human;
use csu::project_javascript_object_notation;
use std::io;
use std::io::Write;
use std::path::PathBuf;
use std::process::ExitCode;
#[derive(Debug, Parser)]
#[command(name = "csu", version, about = "Stateless source review")]
struct CommandLine {
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    Review {
        #[arg(long)]
        authority: PathBuf,
        #[arg(long)]
        workspace: PathBuf,
        #[arg(long, value_enum, default_value_t = OutputFormat::Human)]
        format: OutputFormat,
    },
}

#[derive(Clone, Copy, Debug, ValueEnum)]
enum OutputFormat {
    Human,
    #[value(name = "json")]
    JavascriptObjectNotation,
}

/// 执行 `main` 内部逻辑
fn main() -> ExitCode {
    let CommandLine { command } = CommandLine::parse();
    match command {
        Command::Review {
            authority,
            workspace,
            format,
        } => execute_review(authority, workspace, format),
    }
}

/// 执行 `execute_review` 内部逻辑
fn execute_review(
    authority: PathBuf,
    workspace: PathBuf,
    format: OutputFormat,
) -> ExitCode {
    let terminal = match WorkspaceReviewer::compile(AuthorityInput::Directory(
        &authority,
    )) {
        Ok(reviewer) => reviewer.review(ReviewInput::Workspace(&workspace)),
        Err(rejection) => ReviewTerminal::Rejected(rejection),
    };
    let disposition = terminal.disposition();
    let bytes = match format {
        OutputFormat::Human => project_human(&terminal).into_bytes(),
        OutputFormat::JavascriptObjectNotation => {
            match project_javascript_object_notation(&terminal) {
                Ok(bytes) => bytes,
                Err(error) => {
                    let _ =
                        writeln!(io::stderr(), "projection failed: {error}");
                    return ExitCode::from(2);
                }
            }
        }
    };
    let mut standard_output = io::stdout().lock();
    if standard_output.write_all(&bytes).is_err()
        || standard_output.write_all(b"\n").is_err()
    {
        return ExitCode::from(2);
    }
    match disposition {
        Disposition::Clean => ExitCode::SUCCESS,
        Disposition::Findings => ExitCode::from(1),
        Disposition::Incomplete
        | Disposition::Rejected
        | Disposition::Failed => ExitCode::from(2),
    }
}
