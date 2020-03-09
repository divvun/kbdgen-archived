use crate::{
    models::{Layout, Project},
    ProjectBundle, Targets,
};
use log::trace;
use serde::Serialize;
use std::{
    collections::HashMap,
    hash::BuildHasher,
    path::{Path, PathBuf},
};
use thiserror::Error;

pub trait Save: Sized {
    /// Write serialized data to target path
    fn save(&self, target_path: impl AsRef<Path>) -> Result<(), Error>;
}

impl Save for ProjectBundle {
    fn save(&self, target_path: impl AsRef<Path>) -> Result<(), Error> {
        let bundle_path: &Path = target_path.as_ref();
        trace!("Writing to {:?}", bundle_path);
        std::fs::create_dir_all(&bundle_path).map_err(|source| Error::CreateBundle {
            bundle_path: bundle_path.into(),
            source,
        })?;

        // destructure to get yelled at for missing a field
        let ProjectBundle {
            path: _path,
            project,
            layouts,
            targets,
        } = self;
        project.save(&bundle_path.join("project.yaml"))?;
        layouts.save(&bundle_path.join("layouts"))?;
        targets.save(&bundle_path.join("targets"))?;

        Ok(())
    }
}

impl Save for Project {
    fn save(&self, target_path: impl AsRef<Path>) -> Result<(), Error> {
        write_yaml(target_path, self)
    }
}

impl<S: BuildHasher> Save for HashMap<String, Layout, S> {
    fn save(&self, target_path: impl AsRef<Path>) -> Result<(), Error> {
        let path: &Path = target_path.as_ref();
        std::fs::create_dir_all(&path).map_err(|source| Error::WriteFile {
            path: path.into(),
            source,
        })?;

        for (name, data) in self {
            write_yaml(&path.join(&name).with_extension("yaml"), data)?;
        }

        Ok(())
    }
}

impl Save for Targets {
    fn save(&self, target_path: impl AsRef<Path>) -> Result<(), Error> {
        let path: &Path = target_path.as_ref();
        std::fs::create_dir_all(&path).map_err(|source| Error::WriteFile {
            path: path.into(),
            source,
        })?;

        // destructure to get yelled at for missing a field
        let Targets {
            android,
            i_os,
            mac_os,
            windows,
            chrome,
            x11,
            mim,
        } = self;

        write_yaml(&path.join("android.yaml"), android)?;
        write_yaml(&path.join("ios.yaml"), i_os)?;
        write_yaml(&path.join("macos.yaml"), mac_os)?;
        write_yaml(&path.join("windows.yaml"), windows)?;
        write_yaml(&path.join("chrome.yaml"), chrome)?;
        write_yaml(&path.join("x11.yaml"), x11)?;
        write_yaml(&path.join("mim.yaml"), mim)?;

        Ok(())
    }
}

fn write_yaml<T: Serialize>(path: impl AsRef<Path>, data: T) -> Result<(), Error> {
    use std::{fs::File, io::BufWriter};

    let path: &Path = path.as_ref();
    let file = File::create(&path).map_err(|source| Error::WriteFile {
        path: path.into(),
        source,
    })?;
    let writer = BufWriter::new(file);
    serde_yaml::to_writer(writer, &data).map_err(|source| Error::WriteData {
        path: path.into(),
        source,
    })?;
    Ok(())
}

#[derive(Debug, Error)]
pub enum Error {
    #[error("Could not create bundle in `{}`: {}", bundle_path.display(), source)]
    CreateBundle {
        bundle_path: PathBuf,
        source: std::io::Error,
    },
    #[error("Could not write to `{}`: {}", path.display(), source)]
    WriteFile {
        path: PathBuf,
        source: std::io::Error,
    },
    #[error("Could not serialize data to `{}`: {}", path.display(), source)]
    WriteData {
        path: PathBuf,
        source: serde_yaml::Error,
    },
}
