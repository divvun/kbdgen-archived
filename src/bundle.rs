use serde::{Deserialize, Serialize};
use std::{collections::HashMap, path::PathBuf};

pub mod models;

mod key_map;
pub use key_map::{DesktopKeyMap, Error as KeyMapError, MobileKeyMap};
mod modes;
pub use modes::{Desktop, Mobile};

mod loading;
pub use loading::{Error as LoadError, Load};
mod saving;
pub use saving::{Error as SaveError, Save};

// TODO: Implement proper escaping rules
//
// - [x] \u{0} <-> None
// - [ ] escpae unicode categories "C", "Z", "M"
// - [ ] proptests
pub(crate) mod keys;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Targets {
    android: Option<models::TargetAndroid>,
    i_os: Option<models::TargetIOS>,
    mac_os: Option<models::TargetMacOS>,
    windows: Option<models::TargetWindows>,
    chrome: Option<models::TargetChrome>,
}

/// A project bundle consists of a `project.yaml` file, a `targets/` directory
/// and a `layouts/` directory.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProjectBundle {
    pub path: Option<PathBuf>,
    pub project: models::Project,
    pub layouts: HashMap<String, models::Layout>,
    pub targets: Targets,
}
