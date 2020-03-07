use serde::{Deserialize, Serialize};
use derive_collect_docs::CollectDocs;

#[derive(Debug, Clone, PartialEq, Eq)]
#[derive(Serialize, Deserialize, CollectDocs)]
pub struct Mobile<T> {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub default: Option<T>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub shift: Option<T>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
#[derive(Serialize, Deserialize, CollectDocs)]
pub struct Desktop<T> {
    #[serde(rename = "default", skip_serializing_if = "Option::is_none")]
    pub default: Option<T>,
    #[serde(rename = "shift", skip_serializing_if = "Option::is_none")]
    pub shift: Option<T>,
    #[serde(rename = "caps", skip_serializing_if = "Option::is_none")]
    pub caps: Option<T>,
    #[serde(rename = "caps+shift", skip_serializing_if = "Option::is_none")]
    pub caps_shift: Option<T>,
    #[serde(rename = "alt", skip_serializing_if = "Option::is_none")]
    pub alt: Option<T>,
    #[serde(rename = "alt+shift", skip_serializing_if = "Option::is_none")]
    pub alt_shift: Option<T>,
    #[serde(rename = "caps+alt", skip_serializing_if = "Option::is_none")]
    pub caps_alt: Option<T>,
    #[serde(rename = "ctrl", skip_serializing_if = "Option::is_none")]
    pub ctrl: Option<T>,
    #[serde(rename = "cmd", skip_serializing_if = "Option::is_none")]
    pub cmd: Option<T>,
    #[serde(rename = "cmd+shift", skip_serializing_if = "Option::is_none")]
    pub cmd_shift: Option<T>,
    #[serde(rename = "cmd+alt", skip_serializing_if = "Option::is_none")]
    pub cmd_alt: Option<T>,
    #[serde(rename = "cmd+alt+shift", skip_serializing_if = "Option::is_none")]
    pub cmd_alt_shift: Option<T>,
}
