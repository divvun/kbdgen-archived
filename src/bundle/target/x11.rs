use derive_collect_docs::CollectDocs;
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize, CollectDocs)]
pub struct LayoutTarget {}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize, CollectDocs)]
pub struct Target {
    pub version: String,
    pub build: u32,
}
