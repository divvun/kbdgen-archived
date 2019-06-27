use log::trace;
use serde::de::DeserializeOwned;
use std::{error::Error, ffi::OsStr, fs::read_dir, path::Path};

use super::*;
use crate::models;

pub trait Load: Sized {
    fn load(path: impl AsRef<Path>) -> Result<Self, Box<dyn Error>>;
}

impl Load for ProjectBundle {
    fn load(bundle_path: impl AsRef<Path>) -> Result<Self, Box<dyn Error>> {
        let bundle_path: &Path = bundle_path.as_ref();
        trace!("Loading {:?}", bundle_path);

        Ok(ProjectBundle {
            path: std::fs::canonicalize(bundle_path.to_path_buf())?,
            project: Load::load(&bundle_path.join("project.yaml"))?,
            layouts: Load::load(&bundle_path.join("layouts"))?,
            targets: Load::load(&bundle_path.join("targets"))?,
        })
    }
}

impl Load for models::Project {
    fn load(path: impl AsRef<Path>) -> Result<Self, Box<dyn Error>> {
        Ok(read_yml(path.as_ref())?)
    }
}

impl Load for Vec<models::Layout> {
    fn load(path: impl AsRef<Path>) -> Result<Self, Box<dyn Error>> {
        let yml_files = read_dir(path.as_ref())?
            .filter_map(Result::ok)
            .map(|f| f.path())
            .filter(|p| p.is_file())
            .filter(|p| p.extension() == Some(OsStr::new("yaml")));

        yml_files.map(|p| read_yml(&p)).collect()
    }
}

impl Load for Targets {
    fn load(path: impl AsRef<Path>) -> Result<Self, Box<dyn Error>> {
        let path: &Path = path.as_ref();
        Ok(Targets {
            android: read_yml_if_exists(&path.join("android.yaml"))?,
            i_os: read_yml_if_exists(&path.join("ios.yaml"))?,
            mac_os: read_yml_if_exists(&path.join("macos.yaml"))?,
            windows: read_yml_if_exists(&path.join("windows.yaml"))?,
        })
    }
}

fn read_yml<'a, T: DeserializeOwned>(path: &'a Path) -> Result<T, Box<dyn Error>> {
    use std::{fs::File, io::BufReader};
    let file = File::open(path)?;
    let reader = BufReader::new(file);
    let parsed = serde_yaml::from_reader(reader)?;
    Ok(parsed)
}

fn read_yml_if_exists<'a, T: DeserializeOwned>(
    path: &'a Path,
) -> Result<Option<T>, Box<dyn Error>> {
    let path: &Path = path.as_ref();
    if !path.is_file() {
        return Ok(None);
    }
    read_yml(path)
}
