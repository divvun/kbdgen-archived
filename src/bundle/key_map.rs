use crate::models::IsoKey;
use serde::{
    de::{self, Deserializer},
    Deserialize, Serialize,
};
use snafu::Snafu;
use std::{collections::BTreeMap, str::FromStr};

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(transparent)]
pub struct DesktopKeyMap(BTreeMap<IsoKey, String>);

impl<'de> Deserialize<'de> for DesktopKeyMap {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        #[derive(Debug, Clone, PartialEq, Eq)]
        #[derive(Serialize, Deserialize)]
        #[serde(untagged)]
        enum Wat {
            String(String),
            Map(BTreeMap<IsoKey, String>),
        }

        match Wat::deserialize(deserializer)? {
            Wat::String(s) => Ok(s.parse().map_err(de::Error::custom)?),
            Wat::Map(m) => Ok(DesktopKeyMap(m)),
        }
    }
}

impl FromStr for DesktopKeyMap {
    type Err = Error;

    // TODO: Implement this, actually
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        Ok(DesktopKeyMap(BTreeMap::new()))
    }
}

#[derive(Debug, Snafu)]
pub enum Error {
    #[snafu(display("{}", description))]
    ParseError { description: String },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(transparent)]
pub struct MobileKeyMap(Vec<Vec<String>>);

impl<'de> Deserialize<'de> for MobileKeyMap {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        let s = String::deserialize(deserializer)?;
        Ok(MobileKeyMap(
            s.lines()
                .map(|l| l.split_whitespace().map(String::from).collect())
                .collect(),
        ))
    }
}
