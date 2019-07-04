use kbdgen::{Load, ProjectBundle, Save};
use snafu::{ResultExt, Snafu};
use std::{fmt, path::PathBuf};
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
struct Cli {
    #[structopt(parse(from_os_str))]
    input: PathBuf,

    #[structopt(parse(from_os_str))]
    output: Option<PathBuf>,
}

fn main() -> Result<(), Error> {
    pretty_env_logger::init();
    let opts = Cli::from_args();

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

#[derive(Snafu)]
pub enum Error {
    #[snafu(display("Could load kbdgen bundle: {}", source))]
    CannotLoad {
        source: kbdgen::LoadError,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("Could write kbdgen bundle: {}", source))]
    CannotSave {
        source: kbdgen::SaveError,
        backtrace: snafu::Backtrace,
    },
}

impl fmt::Debug for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        writeln!(f, "{}", self)?;
        if let Some(backtrace) = snafu::ErrorCompat::backtrace(&self) {
            writeln!(f, "{}", backtrace)?;
        }
        Ok(())
    }
}
