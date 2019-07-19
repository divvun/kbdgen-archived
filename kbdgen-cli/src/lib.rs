use snafu::{ResultExt, Snafu};
use std::{
    path::{Path, PathBuf},
    process::Command,
};

fn kbdgen_dirs() -> directories::ProjectDirs {
    directories::ProjectDirs::from("", "", "kbdgen").expect("project dir")
}

pub fn cldr_dir() -> PathBuf {
    kbdgen_dirs().cache_dir().join("cldr")
}

pub fn xkb_dir() -> PathBuf {
    kbdgen_dirs().cache_dir().join("xkb")
}

pub fn update_repo(name: &str, dir: &Path, repo: &str) -> Result<(), Error> {
    if !dir.exists() {
        log::info!("Downloading {} repo to `{}`…", name, dir.display());
        let mut command = Command::new("git")
            .args(&["clone", "--depth", "1", repo])
            .arg(&dir)
            .spawn()
            .context(RepoCloneFailed)?;
        command.wait().context(RepoCloneFailed)?;
    } else {
        log::info!("Updating {} repo in `{}`…", name, dir.display());
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
