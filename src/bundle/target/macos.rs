use derive_collect_docs::CollectDocs;
use serde::{Deserialize, Serialize};

// TODO: Keyboards have a provisioningProfileId -- add this here?
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize, CollectDocs)]
pub struct Target {
    #[example(yaml, r#"version: 0.1.6"#)]
    pub version: String,

    #[example(yaml, r#"build: 12"#)]
    pub build: u32,

    #[example(yaml, r#"packageId: com.example.mypackageid"#)]
    #[serde(rename = "packageId")]
    pub package_id: String,

    #[example(yaml, r#"icon: icons/icon.png"#)]
    #[serde(skip_serializing_if = "Option::is_none")]
    pub icon: Option<String>,

    #[example(yaml, r#"bundleName: Fancy Example Keyboards"#)]
    #[serde(rename = "bundleName")]
    pub bundle_name: String,

    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "teamId")]
    pub team_id: Option<String>,

    #[example(
        yaml,
        r#"codeSignId: "iPhone Distribution: The University of Tromso (000ABC000)""#
    )]
    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "codeSignId")]
    pub code_sign_id: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize, CollectDocs)]
pub struct LayoutTarget {}
