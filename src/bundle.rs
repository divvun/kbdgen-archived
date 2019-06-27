use std::path::PathBuf;

use serde::{Deserialize, Serialize};

pub mod models;

mod key_map;
pub use key_map::*;
mod modes;
pub use modes::*;

mod loading;
pub use loading::Load;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Targets {
    android: Option<models::TargetAndroid>,
    i_os: Option<models::TargetIOS>,
    mac_os: Option<models::TargetMacOS>,
    windows: Option<models::TargetWindows>,
}

/// A project bundle consists of a project.yaml file, a targets/ directory and a layouts/ directory.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProjectBundle {
    pub path: PathBuf,
    pub project: models::Project,
    pub layouts: Vec<models::Layout>,
    pub targets: Targets,
}
