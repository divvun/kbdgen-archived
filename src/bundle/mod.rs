use derive_collect_docs::CollectDocs;
use serde::{Deserialize, Serialize};
use std::{collections::HashMap, path::PathBuf};

pub mod key_map;
pub mod models;
pub mod target;

mod loading;
mod modes;
mod saving;

pub use key_map::{DesktopKeyMap, Error as KeyMapError, MobileKeyMap};
pub use modes::{Desktop, Mobile};

pub use loading::{Error as LoadError, Load};
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
    pub android: Option<target::android::Target>,
    pub ios: Option<target::ios::Target>,
    pub macos: Option<target::macos::Target>,
    pub windows: Option<target::windows::Target>,
    pub chrome: Option<target::chrome::Target>,
    pub x11: Option<target::x11::Target>,
    pub mim: Option<target::mim::Target>,
}

/// A `.kbdgen` bundle is a directory with a specific structure.
///
/// Please note that the fields listed here are built from the contents of the
/// files in the bundle directory.
///
/// .Example of the structure of a `.kbdgen` bundle
/// ```console
/// smj.kbdgen
/// ├── layouts
/// │  ├── smj-NO.yaml
/// │  └── smj-SE.yaml
/// ├── project.yaml
/// ├── resources
/// │  └── mac
/// │     ├── background.png
/// │     ├── icon.smj-NO.png
/// │     └── icon.smj-SE.png
/// └── targets
///    ├── android.yaml
///    ├── ios.yaml
///    ├── mac.yaml
///    └── win.yaml
/// ```
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
