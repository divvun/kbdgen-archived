use std::path::PathBuf;

use serde::{Deserialize, Serialize};
use strum_macros::{Display, EnumIter, EnumString};

use crate::models;

mod loading;
pub use loading::Load;

#[derive(
    Debug,
    Clone,
    Copy,
    Hash,
    PartialEq,
    Eq,
    PartialOrd,
    Ord,
    EnumString,
    Display,
    EnumIter,
    Serialize,
    Deserialize,
)]
enum IsoKeys {
    E00,
    E01,
    E02,
    E03,
    E04,
    E05,
    E06,
    E07,
    E08,
    E09,
    E10,
    E11,
    E12,
    D01,
    D02,
    D03,
    D04,
    D05,
    D06,
    D07,
    D08,
    D09,
    D10,
    D11,
    D12,
    C01,
    C02,
    C03,
    C04,
    C05,
    // TODO: fix the D13 special case.
    C06,
    C07,
    C08,
    C09,
    C10,
    C11,
    // C12 -> D13
    D13,
    B00,
    B01,
    B02,
    B03,
    B04,
    B05,
    B06,
    B07,
    B08,
    B09,
    B10,
}

#[derive(
    Debug,
    Clone,
    Copy,
    Hash,
    PartialEq,
    Eq,
    PartialOrd,
    Ord,
    EnumString,
    Display,
    EnumIter,
    Serialize,
    Deserialize,
)]
#[strum(serialize_all = "snake_case")]
enum MobileModes {
    Default,
    Shift,
}

#[derive(
    Debug,
    Clone,
    Copy,
    Hash,
    PartialEq,
    Eq,
    PartialOrd,
    Ord,
    EnumString,
    Display,
    EnumIter,
    Serialize,
    Deserialize,
)]
enum DesktopModes {
    #[strum(serialize = "default")]
    Default,
    #[strum(serialize = "shift")]
    Shift,
    #[strum(serialize = "caps")]
    Caps,
    #[strum(serialize = "caps+shift")]
    CapsShift,
    #[strum(serialize = "alt")]
    Alt,
    #[strum(serialize = "alt+shift")]
    AltShift,
    #[strum(serialize = "caps+alt")]
    CapsAlt,
    #[strum(serialize = "ctrl")]
    Ctrl,
}

#[derive(
    Debug,
    Clone,
    Copy,
    Hash,
    PartialEq,
    Eq,
    PartialOrd,
    Ord,
    EnumString,
    Display,
    EnumIter,
    Serialize,
    Deserialize,
)]
enum MacModes {
    #[strum(serialize = "cmd")]
    Cmd,
    #[strum(serialize = "cmd+shift")]
    CmdShift,
    #[strum(serialize = "cmd+alt")]
    CmdAlt,
    #[strum(serialize = "cmd+alt+shift")]
    CmdAltShift,
}

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
