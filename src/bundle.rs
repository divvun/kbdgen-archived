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

/// Mapping of target-specific properties, for example code signing
/// certificates, build and version numbers, and other resources to be included
/// at a project level.
///
/// See the documentation for each target for more information.
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

/// A `.kbdgen` bundle is a directory with a specific structure.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default, CollectDocs)]
pub struct ProjectBundle {
    /// The local file system path to the `.kbdgen` bundle.
    pub path: Option<PathBuf>,
    /// Data from `project.yaml` file
    pub project: models::Project,
    /// The layouts to be included in this project, read from the `layouts/`
    /// directory. The layout names are the names of the YAML files without the
    /// `.yaml` suffix.
    pub layouts: HashMap<String, models::Layout>,
    /// Target-specific project-level properties stored in `targets/` directory.
    pub targets: Targets,
}
