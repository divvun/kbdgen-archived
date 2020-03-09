use crate::{
    models::{Layout, Project},
    ProjectBundle, Targets,
};
use log::trace;
use serde::de::DeserializeOwned;
use std::{
    collections::HashMap,
    default::Default,
    ffi::OsStr,
    fs::{canonicalize, read_dir},
    hash::BuildHasher,
    path::{Path, PathBuf},
};
use thiserror::Error;

pub trait Load: Sized {
    /// Read data from given path into a structure of this type
    fn load(path: impl AsRef<Path>) -> Result<Self, Error>;
}

impl Load for ProjectBundle {
    fn load(bundle_path: impl AsRef<Path>) -> Result<Self, Error> {
        let bundle_path: &Path = bundle_path.as_ref();
        trace!("Loading {:?}", bundle_path);

        Ok(ProjectBundle {
            path: Some(
                canonicalize(&bundle_path).map_err(|source| Error::ReadFile {
                    path: bundle_path.into(),
                    source,
                })?,
            ),
            project: Load::load(&bundle_path.join("project.yaml"))?,
            layouts: Load::load(&bundle_path.join("layouts"))?,
            targets: Load::load(&bundle_path.join("targets"))?,
        })
    }
}

impl Load for Project {
    fn load(path: impl AsRef<Path>) -> Result<Self, Error> {
        let path: &Path = path.as_ref();
        Ok(read_yml(path)?)
    }
}

impl<S: BuildHasher + Default> Load for HashMap<String, Layout, S> {
    fn load(path: impl AsRef<Path>) -> Result<Self, Error> {
        let path: &Path = path.as_ref();
        let yml_files = read_dir(path)
            .map_err(|source| Error::ReadFile {
                path: path.into(),
                source,
            })?
            .filter_map(Result::ok)
            .map(|f| f.path())
            .filter(|p| p.is_file())
            .filter(|p| p.extension() == Some(OsStr::new("yaml")));

        yml_files
            .map(|path| {
                let name = path
                    .file_stem()
                    .ok_or_else(|| Error::MalformedFilename { path: path.clone() })?
                    .to_string_lossy()
                    .to_string();
                let data = read_yml(&path)?;
                Ok((name, data))
            })
            .collect()
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
            chrome: read_yml_if_exists(&path.join("chrome.yaml"))?,
            x11: read_yml_if_exists(&path.join("x11.yaml"))?,
            mim: read_yml_if_exists(&path.join("mim.yaml"))?,
        })
    }
}

fn read_yml<T: DeserializeOwned>(path: &Path) -> Result<T, Error> {
    use std::{fs::File, io::BufReader};

    let file = File::open(path).map_err(|source| Error::ReadFile {
        path: path.into(),
        source,
    })?;
    let reader = BufReader::new(file);
    let parsed = serde_yaml::from_reader(reader).map_err(|source| Error::ParseFile {
        path: path.into(),
        source,
    })?;
    Ok(parsed)
}

fn read_yml_if_exists<T: DeserializeOwned>(path: impl AsRef<Path>) -> Result<Option<T>, Error> {
    let path: &Path = path.as_ref();
    if !path.is_file() {
        return Ok(None);
    }
    read_yml(path)
}

#[derive(Debug, Error)]
pub enum Error {
    #[error("Could not read `{}`: {}", path.display(), source)]
    ReadFile {
        path: PathBuf,
        source: std::io::Error,
    },
    #[error("Could not parse file with malfolmed name:: `{}`", path.display())]
    MalformedFilename { path: PathBuf },
    #[error("Could not parse `{}`: {}", path.display(), source)]
    ParseFile {
        path: PathBuf,
        source: serde_yaml::Error,
    },
}
