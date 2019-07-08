use snafu::{ResultExt, Snafu};
use std::{path::PathBuf, process::Command};

pub fn cldr_dir() -> PathBuf {
    directories::ProjectDirs::from("", "", "kbdgen")
        .expect("project dir")
        .cache_dir()
        .join("cldr")
}

pub fn update_cldr_repo() -> Result<(), Error> {
    let dir = cldr_dir();

    if !dir.exists() {
        log::info!("Downloading CLDR repo to `{}`…", dir.display());
        let mut command = Command::new("git")
            .args(&[
                "clone",
                "--depth",
                "1",
                "https://github.com/unicode-org/cldr",
            ])
            .arg(&dir)
            .spawn()
            .context(RepoCloneFailed)?;
        command.wait().context(RepoCloneFailed)?;
    } else {
        log::info!("Updating CLDR repo in `{}`…", dir.display());
        let mut command = Command::new("git")
            .current_dir(&dir)
            .args(&["pull"])
            .spawn()
            .context(RepoUpdateFailed)?;
        command.wait().context(RepoUpdateFailed)?;
    }

    Ok(())
}

#[derive(Debug, Snafu)]
pub enum Error {
    #[snafu(display("Failed to cloning CLDR repo"))]
    RepoCloneFailed {
        source: std::io::Error,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("Failed to pull CLDR repo changes"))]
    RepoUpdateFailed {
        source: std::io::Error,
        backtrace: snafu::Backtrace,
    },
}
