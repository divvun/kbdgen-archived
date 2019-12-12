use kbdgen::{Load, ProjectBundle, Save};
use snafu::{ResultExt, Snafu};
use snafu_cli_debug::SnafuCliDebug;
use std::path::PathBuf;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
struct Cli {
    #[structopt(parse(from_os_str))]
    input: PathBuf,

    #[structopt(parse(from_os_str))]
    output: Option<PathBuf>,

    #[structopt(flatten)]
    verbose: clap_verbosity_flag::Verbosity,
}

fn main() -> Result<(), Error> {
    let opts = Cli::from_args();
    // let _ = opts.verbose.setup_env_logger("cldr");

    let bundle = ProjectBundle::load(&opts.input).context(CannotLoad)?;
    log::info!("Bundle `{}` loaded, looking great!", opts.input.display());
    if let Some(output) = opts.output {
        bundle.save(&output).context(CannotSave)?;
        log::info!("New bundle written to `{}`.", output.display());
    } else {
        log::info!("No output path specified, skipping");
    }

    Ok(())
}

#[derive(Snafu, SnafuCliDebug)]
pub enum Error {
    #[snafu(display("Could not load kbdgen bundle: {}", source))]
    CannotLoad {
        source: kbdgen::LoadError,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("Could not write kbdgen bundle: {}", source))]
    CannotSave {
        source: kbdgen::SaveError,
        backtrace: snafu::Backtrace,
    },
}
