use kbdgen::{Load, ProjectBundle, Save};
use snafu::{ResultExt, Snafu};
use std::{fmt, path::PathBuf};
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
struct Cli {
    #[structopt(parse(from_os_str))]
    input: PathBuf,

    #[structopt(parse(from_os_str))]
    output: PathBuf,
}

fn main() -> Result<(), Error> {
    pretty_env_logger::init();
    let opts = Cli::from_args();

    let bundle = ProjectBundle::load(&opts.input).context(CannotLoad)?;
    log::info!(
        "Bundle `{}` loaded, looking great to far!",
        opts.input.display()
    );
    bundle.save(&opts.output).context(CannotSave)?;
    log::info!("New bundle written to `{}`.", opts.output.display());

    Ok(())
}

#[derive(Snafu)]
pub enum Error {
    #[snafu(display("Could not read stdin: {}", source))]
    CannotLoad { source: kbdgen::LoadError },
    #[snafu(display("Could not enhance input: {}", source))]
    CannotSave { source: kbdgen::SaveError },
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
