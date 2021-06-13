use pathos::AppDirs;
use std::{
    path::{Path, PathBuf},
    process::Command,
};

fn kbdgen_dirs() -> pathos::user::AppDirs {
    pathos::user::AppDirs::new("kbdgen").unwrap()
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
            .map_err(|source| Error::RepoCloneFailed { source })?;
        command
            .wait()
            .map_err(|source| Error::RepoCloneFailed { source })?;
    } else {
        log::info!("Updating {} repo in `{}`…", name, dir.display());
        let mut command = Command::new("git")
            .current_dir(&dir)
            .args(&["pull"])
            .spawn()
            .map_err(|source| Error::RepoUpdateFailed { source })?;
        command
            .wait()
            .map_err(|source| Error::RepoUpdateFailed { source })?;
    }

    Ok(())
}

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("Failed to cloning CLDR repo")]
    RepoCloneFailed { source: std::io::Error },
    #[error("Failed to pull CLDR repo changes")]
    RepoUpdateFailed { source: std::io::Error },
}
