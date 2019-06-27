use log::trace;
use serde::de::DeserializeOwned;
use snafu::{ResultExt, Snafu};
use std::{
    ffi::OsStr,
    fs::{canonicalize, read_dir},
    path::Path,
};

use super::*;
use crate::models;

pub trait Load: Sized {
    /// Read data from given path into a structure of this type
    fn load(path: impl AsRef<Path>) -> Result<Self, Error>;
}

impl Load for ProjectBundle {
    fn load(bundle_path: impl AsRef<Path>) -> Result<Self, Error> {
        let bundle_path: &Path = bundle_path.as_ref();
        trace!("Loading {:?}", bundle_path);

        Ok(ProjectBundle {
            path: canonicalize(bundle_path.to_path_buf())
                .context(ReadFile { path: bundle_path })?,
            project: Load::load(&bundle_path.join("project.yaml"))?,
            layouts: Load::load(&bundle_path.join("layouts"))?,
            targets: Load::load(&bundle_path.join("targets"))?,
        })
    }
}

impl Load for models::Project {
    fn load(path: impl AsRef<Path>) -> Result<Self, Error> {
        let path: &Path = path.as_ref();
        Ok(read_yml(path)?)
    }
}

impl Load for Vec<models::Layout> {
    fn load(path: impl AsRef<Path>) -> Result<Self, Error> {
        let path: &Path = path.as_ref();
        let yml_files = read_dir(path)
            .context(ReadFile { path })?
            .filter_map(Result::ok)
            .map(|f| f.path())
            .filter(|p| p.is_file())
            .filter(|p| p.extension() == Some(OsStr::new("yaml")));

        yml_files.map(|p| read_yml(&p)).collect()
    }
}

impl Load for Targets {
    fn load(path: impl AsRef<Path>) -> Result<Self, Error> {
        let path: &Path = path.as_ref();
        Ok(Targets {
            android: read_yml_if_exists(&path.join("android.yaml"))?,
            i_os: read_yml_if_exists(&path.join("ios.yaml"))?,
            mac_os: read_yml_if_exists(&path.join("macos.yaml"))?,
            windows: read_yml_if_exists(&path.join("windows.yaml"))?,
        })
    }
}

fn read_yml<'a, T: DeserializeOwned>(path: &'a Path) -> Result<T, Error> {
    use std::{fs::File, io::BufReader};

    let file = File::open(path).context(ReadFile { path })?;
    let reader = BufReader::new(file);
    let parsed = serde_yaml::from_reader(reader).context(ParseFile { path })?;
    Ok(parsed)
}

fn read_yml_if_exists<'a, T: DeserializeOwned>(path: &'a Path) -> Result<Option<T>, Error> {
    let path: &Path = path.as_ref();
    if !path.is_file() {
        return Ok(None);
    }
    read_yml(path)
}

#[derive(Debug, Snafu)]
pub enum Error {
    #[snafu(display("Could not read {}: {}", path.display(), source))]
    ReadFile {
        path: PathBuf,
        source: std::io::Error,
    },
    #[snafu(display("Could not parse {}: {}", path.display(), source))]
    ParseFile {
        path: PathBuf,
        source: serde_yaml::Error,
    },
}
