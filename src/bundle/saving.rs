use crate::{
    models::{Layout, Project},
    ProjectBundle, Targets,
};
use log::trace;
use serde::Serialize;
use snafu::{ResultExt, Snafu};
use std::{
    collections::HashMap,
    hash::BuildHasher,
    path::{Path, PathBuf},
};

pub trait Save: Sized {
    /// Write serialized data to target path
    fn save(&self, target_path: impl AsRef<Path>) -> Result<(), Error>;
}

impl Save for ProjectBundle {
    fn save(&self, target_path: impl AsRef<Path>) -> Result<(), Error> {
        let bundle_path: &Path = target_path.as_ref();
        trace!("Writing to {:?}", bundle_path);
        std::fs::create_dir_all(&bundle_path).context(CreateBundle { bundle_path })?;

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
        std::fs::create_dir_all(&path).context(WriteFile { path })?;

        for (name, data) in self {
            write_yaml(&path.join(&name).with_extension("yaml"), data)?;
        }

        Ok(())
    }
}

impl Save for Targets {
    fn save(&self, target_path: impl AsRef<Path>) -> Result<(), Error> {
        let path: &Path = target_path.as_ref();
        std::fs::create_dir_all(&path).context(WriteFile { path })?;

        // destructure to get yelled at for missing a field
        let Targets {
            android,
            i_os,
            mac_os,
            windows,
        } = self;

        write_yaml(&path.join("android.yaml"), android)?;
        write_yaml(&path.join("ios.yaml"), i_os)?;
        write_yaml(&path.join("macos.yaml"), mac_os)?;
        write_yaml(&path.join("windows.yaml"), windows)?;

        Ok(())
    }
}

fn write_yaml<T: Serialize>(path: impl AsRef<Path>, data: T) -> Result<(), Error> {
    use std::{fs::File, io::BufWriter};

    let path: &Path = path.as_ref();
    let file = File::create(&path).context(WriteFile { path })?;
    let writer = BufWriter::new(file);
    serde_yaml::to_writer(writer, &data).context(WriteData { path })?;
    Ok(())
}

#[derive(Debug, Snafu)]
pub enum Error {
    #[snafu(display("Could create bundle in `{}`: {}", bundle_path.display(), source))]
    CreateBundle {
        bundle_path: PathBuf,
        source: std::io::Error,
    },
    #[snafu(display("Could not write to `{}`: {}", path.display(), source))]
    WriteFile {
        path: PathBuf,
        source: std::io::Error,
    },
    #[snafu(display("Could not serialize data to `{}`: {}", path.display(), source))]
    WriteData {
        path: PathBuf,
        source: serde_yaml::Error,
    },
}
