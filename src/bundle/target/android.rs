use derive_collect_docs::CollectDocs;
use indexmap::IndexMap;
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize, CollectDocs)]
pub struct Target {
    pub version: String,

    pub build: u32,

    /// The reverse-domain notation ID for the package
    #[example(yaml, "packageId: com.example.mypackageid")]
    #[serde(rename = "packageId")]
    pub package_id: String,

    /// Path to the icon file to be converted into the various sizes required by
    /// Android, relative to project root.
    #[example(yaml, "icon: icons/icon.png")]
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

    /// Path to the Android keystore (see <<Generating keystores>> section for
    /// more information)
    #[example(yaml, "keyStore: my.keystore")]
    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "keyStore")]
    pub key_store: Option<String>,

    /// The key to use within the provided keystore
    #[example(yaml, "keyAlias: myprojectkey")]
    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "keyAlias")]
    pub key_alias: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize, CollectDocs)]
pub struct LayoutTarget {
    /// The API level that is the minimum supported for a keyboard. Useful for
    /// limiting access to a keyboard where it is known several glyphs are
    /// missing on older devices.
    ///
    /// https://source.android.com/source/build-numbers.html[See the Android documentation for API versions compared to OS version].
    ///
    /// NOTE: The lowest API supported by this keyboard is API 16, but it may
    /// work on older variants.
    #[example(yaml, "minimumSdk: 16")]
    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "minimumSdk")]
    pub minimum_sdk: Option<u32>,

    /// Styles
    #[serde(skip_serializing_if = "Option::is_none")]
    pub style: Option<IndexMap<String, serde_yaml::Value>>,

    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "legacyName")]
    pub legacy_name: Option<String>,
}
