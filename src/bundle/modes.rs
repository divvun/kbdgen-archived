use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq)]
#[derive(Serialize, Deserialize)]
pub struct Mobile<T> {
    pub default: Option<T>,
    pub shift: Option<T>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
#[derive(Serialize, Deserialize)]
pub struct Desktop<T> {
    #[serde(rename = "default")]
    pub default: Option<T>,
    #[serde(rename = "shift")]
    pub shift: Option<T>,
    #[serde(rename = "caps")]
    pub caps: Option<T>,
    #[serde(rename = "caps+shift")]
    pub caps_shift: Option<T>,
    #[serde(rename = "alt")]
    pub alt: Option<T>,
    #[serde(rename = "alt+shift")]
    pub alt_shift: Option<T>,
    #[serde(rename = "caps+alt")]
    pub caps_alt: Option<T>,
    #[serde(rename = "ctrl")]
    pub ctrl: Option<T>,
    #[serde(rename = "cmd")]
    pub cmd: Option<T>,
    #[serde(rename = "cmd+shift")]
    pub cmd_shift: Option<T>,
    #[serde(rename = "cmd+alt")]
    pub cmd_alt: Option<T>,
    #[serde(rename = "cmd+alt+shift")]
    pub cmd_alt_shift: Option<T>,
}
