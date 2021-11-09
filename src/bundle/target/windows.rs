use derive_collect_docs::CollectDocs;
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize, CollectDocs)]
#[serde(rename_all = "camelCase")]
pub struct Target {
    #[example(yaml, r#"version: 0.2.0"#)]
    pub version: String,

    // #[example(yaml, r#"appName: Fancy Example Keyboards"#)]
    pub app_name: String,

    #[example(yaml, r#"url: 'http://divvun.no'"#)]
    pub url: String,

    #[example(yaml, r#"uuid: 0D18406F-1209-43EF-B18F-58961BC8E2E3"#)]
    pub uuid: String,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub code_sign_pfx: Option<String>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub custom_locales: Option<String>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub license_path: Option<String>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub readme_path: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize, CollectDocs)]
#[serde(rename_all = "camelCase")]
pub struct LayoutTarget {
    /// The actual locale within Windows, as per their broken ISO 639-3 scheme
    /// or secret hardcoded lists.
    pub locale: String,

    /// The language name to be cached, in order to try to mask the ugly ISO
    /// code name that often shows.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub language_name: Option<String>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub id: Option<String>,
}
