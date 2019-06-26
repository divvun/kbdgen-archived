use serde_yaml as yaml;
use serde::{Deserialize, Serialize};
use std::collections;

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Bundle {
  // TODO
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ProjectDesc {
  pub name: String,

  pub description: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Project {
  pub locales: collections::HashMap<String, ProjectDesc>,

  pub author: String,

  pub email: String,

  pub copyright: String,

  pub organisation: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct LayoutStrings {
  pub space: String,

  #[serde(rename = "return")]
  pub _return: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct DeriveOptions {
  #[serde(skip_serializing_if="Option::is_none")]
  pub transforms: Option<bool>,
}

/// A layout is defined as a file by the name <locale>.yaml or <locale>.<target>.yaml, and lives in the
/// locales/ directory in the kbdgen project bundle.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Layout {
  /// The display names for the layout, keyed by locale.
  #[serde(rename = "displayNames")]
  pub display_names: collections::HashMap<String, String>,

  /// The different modes.
  pub modes: collections::HashMap<String, yaml::Value>,

  /// The decimal key. Nominally a '.' or ','.
  #[serde(skip_serializing_if="Option::is_none")]
  pub decimal: Option<String>,

  /// An override for space keys on some OSes. Keyed by target.
  #[serde(skip_serializing_if="Option::is_none")]
  pub space: Option<collections::HashMap<String, yaml::Value>>,

  /// Dead keys present, keyed by layer code.
  #[serde(skip_serializing_if="Option::is_none")]
  #[serde(rename = "deadKeys")]
  pub dead_keys: Option<collections::HashMap<String, yaml::Value>>,

  /// The items to be shown when a key is long-pressed. Values are space separated in one string.
  #[serde(skip_serializing_if="Option::is_none")]
  pub longpress: Option<collections::HashMap<String, String>>,

  /// The chain of inputs necessary to provide an output after a deadkey is pressed. Keyed by each individual input.
  #[serde(skip_serializing_if="Option::is_none")]
  pub transforms: Option<collections::HashMap<String, yaml::Value>>,

  /// Strings to be shown on some OSes
  #[serde(skip_serializing_if="Option::is_none")]
  pub strings: Option<LayoutStrings>,

  /// Derives
  #[serde(skip_serializing_if="Option::is_none")]
  pub derive: Option<DeriveOptions>,

  /// Targets...
  #[serde(skip_serializing_if="Option::is_none")]
  pub targets: Option<collections::HashMap<String, yaml::Value>>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct LayoutTargetWindows {
  /// The actual locale within Windows, as per their broken ISO 639-3 scheme or secret hardcoded lists.
  pub locale: String,

  /// The language name to be cached, in order to try to mask the ugly ISO code name that often shows.
  #[serde(rename = "languageName")]
  pub language_name: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct LayoutTargetAndroid {
  /// Minimum SDK can be specified for a specific layout
  #[serde(skip_serializing_if="Option::is_none")]
  #[serde(rename = "minimumSdk")]
  pub minimum_sdk: Option<u32>,

  /// Styles
  #[serde(skip_serializing_if="Option::is_none")]
  pub style: Option<collections::HashMap<String, yaml::Value>>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct TargetAndroid {
  pub version: String,

  pub build: u32,

  #[serde(rename = "packageId")]
  pub package_id: String,

  #[serde(skip_serializing_if="Option::is_none")]
  pub icon: Option<String>,

  #[serde(skip_serializing_if="Option::is_none")]
  #[serde(rename = "sentryDsn")]
  pub sentry_dsn: Option<String>,

  #[serde(skip_serializing_if="Option::is_none")]
  #[serde(rename = "showNumberHints")]
  pub show_number_hints: Option<bool>,

  #[serde(skip_serializing_if="Option::is_none")]
  #[serde(rename = "minimumSdk")]
  pub minimum_sdk: Option<u32>,

  #[serde(skip_serializing_if="Option::is_none")]
  pub chfst: Option<bool>,

  #[serde(skip_serializing_if="Option::is_none")]
  #[serde(rename = "keyStore")]
  pub key_store: Option<String>,

  #[serde(skip_serializing_if="Option::is_none")]
  #[serde(rename = "keyAlias")]
  pub key_alias: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct TargetIOS {
  pub version: String,

  pub build: u32,

  #[serde(rename = "packageId")]
  pub package_id: String,

  #[serde(skip_serializing_if="Option::is_none")]
  pub icon: Option<String>,

  #[serde(rename = "bundleName")]
  pub bundle_name: String,

  #[serde(skip_serializing_if="Option::is_none")]
  #[serde(rename = "teamId")]
  pub team_id: Option<String>,

  #[serde(skip_serializing_if="Option::is_none")]
  #[serde(rename = "codeSignId")]
  pub code_sign_id: Option<String>,

  #[serde(skip_serializing_if="Option::is_none")]
  #[serde(rename = "sentryDsn")]
  pub sentry_dsn: Option<String>,

  #[serde(skip_serializing_if="Option::is_none")]
  #[serde(rename = "aboutDir")]
  pub about_dir: Option<String>,

  #[serde(skip_serializing_if="Option::is_none")]
  pub chfst: Option<bool>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct TargetWindows {
  pub version: String,

  #[serde(rename = "appName")]
  pub app_name: String,

  pub url: String,

  pub uuid: String,

  #[serde(skip_serializing_if="Option::is_none")]
  #[serde(rename = "codeSignPfx")]
  pub code_sign_pfx: Option<String>,

  #[serde(skip_serializing_if="Option::is_none")]
  #[serde(rename = "customLocales")]
  pub custom_locales: Option<String>,

  #[serde(skip_serializing_if="Option::is_none")]
  #[serde(rename = "licensePath")]
  pub license_path: Option<String>,

  #[serde(skip_serializing_if="Option::is_none")]
  #[serde(rename = "readmePath")]
  pub readme_path: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct TargetMacOS {
  pub version: String,

  pub build: u32,

  #[serde(rename = "packageId")]
  pub package_id: String,

  #[serde(skip_serializing_if="Option::is_none")]
  pub icon: Option<String>,

  #[serde(rename = "bundleName")]
  pub bundle_name: String,

  #[serde(skip_serializing_if="Option::is_none")]
  #[serde(rename = "teamId")]
  pub team_id: Option<String>,

  #[serde(skip_serializing_if="Option::is_none")]
  #[serde(rename = "codeSignId")]
  pub code_sign_id: Option<String>,
}
