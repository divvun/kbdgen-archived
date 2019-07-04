use crate::{Desktop, DesktopKeyMap, Mobile, MobileKeyMap};
use serde::{Deserialize, Serialize};
use serde_yaml as yaml;
use std::collections::BTreeMap;
use strum_macros::{Display, EnumIter, EnumString};

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ProjectDesc {
    pub name: String,
    pub description: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Project {
    pub locales: BTreeMap<String, ProjectDesc>,
    pub author: String,
    pub email: String,
    pub copyright: String,
    pub organisation: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct LayoutStrings {
    pub space: String,

    #[serde(rename = "return")]
    pub return_: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct DeriveOptions {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub transforms: Option<bool>,
}

#[derive(Debug, Clone, Copy, Hash, PartialEq, Eq, PartialOrd, Ord)]
#[derive(EnumString, Display, EnumIter)]
#[derive(Serialize, Deserialize)]
pub enum IsoKey {
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
    C06,
    C07,
    C08,
    C09,
    C10,
    C11,
    C12,
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

#[derive(Debug, Clone, PartialEq, Eq)]
#[derive(Serialize, Deserialize)]
pub struct Modes {
    #[serde(skip_serializing_if = "Option::is_none")]
    win: Option<DesktopModes>,
    #[serde(skip_serializing_if = "Option::is_none")]
    mac: Option<DesktopModes>,
    #[serde(skip_serializing_if = "Option::is_none")]
    ios: Option<MobileModes>,
    #[serde(skip_serializing_if = "Option::is_none")]
    android: Option<MobileModes>,
    #[serde(skip_serializing_if = "Option::is_none")]
    chrome: Option<DesktopModes>,
    #[serde(skip_serializing_if = "Option::is_none")]
    x11: Option<DesktopModes>,
    #[serde(skip_serializing_if = "Option::is_none")]
    desktop: Option<DesktopModes>,
    #[serde(skip_serializing_if = "Option::is_none")]
    mobile: Option<MobileModes>,
}

pub type MobileModes = Mobile<MobileKeyMap>;
pub type DesktopModes = Desktop<DesktopKeyMap>;

/// A layout is defined as a file by the name <locale>.yaml or <locale>.<target>.yaml, and lives in the
/// locales/ directory in the kbdgen project bundle.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Layout {
    /// The display names for the layout, keyed by locale.
    #[serde(rename = "displayNames")]
    pub display_names: BTreeMap<String, String>,

    /// The different modes.
    pub modes: Modes,

    /// The decimal key. Nominally a '.' or ','.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub decimal: Option<String>,

    /// An override for space keys on some OSes. Keyed by target.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub space: Option<Desktop<char>>,

    /// Dead keys present, keyed by layer code.
    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "deadKeys")]
    pub dead_keys: Option<Desktop<Vec<char>>>,

    /// The items to be shown when a key is long-pressed. Values are space separated in one string.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub longpress: Option<BTreeMap<String, String>>,

    /// The chain of inputs necessary to provide an output after a deadkey is pressed. Keyed by each individual input.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub transforms: Option<BTreeMap<String, BTreeMap<String, String>>>,

    /// Strings to be shown on some OSes
    #[serde(skip_serializing_if = "Option::is_none")]
    pub strings: Option<LayoutStrings>,

    /// Derives
    #[serde(skip_serializing_if = "Option::is_none")]
    pub derive: Option<DeriveOptions>,

    /// Targets...
    #[serde(skip_serializing_if = "Option::is_none")]
    pub targets: Option<LayoutTarget>,
}

#[derive(Debug, Clone, PartialEq)]
#[derive(Serialize, Deserialize)]
pub struct LayoutTarget {
    #[serde(skip_serializing_if = "Option::is_none")]
    win: Option<LayoutTargetWindows>,
    #[serde(skip_serializing_if = "Option::is_none")]
    mac: Option<yaml::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    ios: Option<LayoutTargetIOS>,
    #[serde(skip_serializing_if = "Option::is_none")]
    android: Option<LayoutTargetAndroid>,
    #[serde(skip_serializing_if = "Option::is_none")]
    chrome: Option<yaml::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    x11: Option<yaml::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    desktop: Option<yaml::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    mobile: Option<yaml::Value>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct LayoutTargetWindows {
    /// The actual locale within Windows, as per their broken ISO 639-3 scheme or secret hardcoded lists.
    pub locale: String,

    /// The language name to be cached, in order to try to mask the ugly ISO code name that often shows.
    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "languageName")]
    pub language_name: Option<String>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub id: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct LayoutTargetIOS {
    /// Minimum SDK can be specified for a specific layout
    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "legacyName")]
    pub legacy_name: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct LayoutTargetAndroid {
    /// Minimum SDK can be specified for a specific layout
    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "minimumSdk")]
    pub minimum_sdk: Option<u32>,

    /// Styles
    #[serde(skip_serializing_if = "Option::is_none")]
    pub style: Option<BTreeMap<String, yaml::Value>>,

    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "legacyName")]
    pub legacy_name: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct TargetAndroid {
    pub version: String,

    pub build: u32,

    #[serde(rename = "packageId")]
    pub package_id: String,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub icon: Option<String>,

    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "sentryDsn")]
    pub sentry_dsn: Option<String>,

    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "showNumberHints")]
    pub show_number_hints: Option<bool>,

    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "minimumSdk")]
    pub minimum_sdk: Option<u32>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub chfst: Option<bool>,

    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "keyStore")]
    pub key_store: Option<String>,

    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "keyAlias")]
    pub key_alias: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct TargetIOS {
    pub version: String,

    pub build: u32,

    #[serde(rename = "packageId")]
    pub package_id: String,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub icon: Option<String>,

    #[serde(rename = "bundleName")]
    pub bundle_name: String,

    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "teamId")]
    pub team_id: Option<String>,

    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "codeSignId")]
    pub code_sign_id: Option<String>,

    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "sentryDsn")]
    pub sentry_dsn: Option<String>,

    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "aboutDir")]
    pub about_dir: Option<String>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub chfst: Option<bool>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct TargetWindows {
    pub version: String,

    #[serde(rename = "appName")]
    pub app_name: String,

    pub url: String,

    pub uuid: String,

    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "codeSignPfx")]
    pub code_sign_pfx: Option<String>,

    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "customLocales")]
    pub custom_locales: Option<String>,

    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "licensePath")]
    pub license_path: Option<String>,

    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "readmePath")]
    pub readme_path: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct TargetMacOS {
    pub version: String,

    pub build: u32,

    #[serde(rename = "packageId")]
    pub package_id: String,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub icon: Option<String>,

    #[serde(rename = "bundleName")]
    pub bundle_name: String,

    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "teamId")]
    pub team_id: Option<String>,

    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "codeSignId")]
    pub code_sign_id: Option<String>,
}
