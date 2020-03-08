use derive_collect_docs::CollectDocs;
use serde::{Deserialize, Serialize};
use std::{collections::HashMap, path::PathBuf};

pub mod models;

pub mod key_map;
pub use key_map::{DesktopKeyMap, Error as KeyMapError, MobileKeyMap};
mod modes;
pub use modes::{Desktop, Mobile};

mod loading;
pub use loading::{Error as LoadError, Load};
mod saving;
pub use saving::{Error as SaveError, Save};

pub(crate) mod keys;
pub use keys::KeyValue;

/// Map of all targets
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default, CollectDocs)]
pub struct Targets {
    /// Android keyboard settings
    pub android: Option<models::TargetAndroid>,
    pub i_os: Option<models::TargetIOS>,
    pub mac_os: Option<models::TargetMacOS>,
    pub windows: Option<models::TargetWindows>,
    pub chrome: Option<models::TargetChrome>,
    pub x11: Option<models::TargetX11>,
    pub mim: Option<models::TargetMim>,
}

/// A project bundle consists of a `project.yaml` file, a `targets/` directory
/// and a `layouts/` directory.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default, CollectDocs)]
pub struct ProjectBundle {
    pub path: Option<PathBuf>,
    pub project: models::Project,
    pub layouts: HashMap<String, models::Layout>,
    pub targets: Targets,
}
