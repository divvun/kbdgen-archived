use crate::models::IsoKey;
use itertools::Itertools;
use serde::{
    de::{self, Deserializer},
    ser::{SerializeMap, Serializer},
    Deserialize, Serialize,
};
use snafu::Snafu;
use std::{collections::BTreeMap, fmt, str::FromStr};

/// Map of keys on a desktop keyboard
///
/// A full keymap has 48 items. It has two forms of representation, a
/// string-based one with 12 items per line; the other representation is a
/// regular YAML map. Some keys might be omitted, which is represented as
/// `\u{0}` (the unicode escape for a `NULL` byte) in the string representation
/// or `None` in the map.
///
/// We will try to serialize everything that is more than half of a full map as
/// string-based key map; other sizes will be regular maps in YAML.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DesktopKeyMap(BTreeMap<IsoKey, Option<String>>);

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
            Map(BTreeMap<IsoKey, Option<String>>),
        }

        match Wat::deserialize(deserializer)? {
            Wat::String(s) => Ok(s.parse().map_err(de::Error::custom)?),
            Wat::Map(m) => Ok(DesktopKeyMap(m)),
        }
    }
}

impl Serialize for DesktopKeyMap {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        const KEYMAP_FULL_SIZE: usize = 48;
        if self.0.len() < KEYMAP_FULL_SIZE / 2 {
            let mut map = serializer.serialize_map(Some(self.0.len()))?;
            for (k, v) in &self.0 {
                map.serialize_entry(k, v)?;
            }
            map.end()
        } else {
            serializer.serialize_str(&self.to_string())
        }
    }
}

impl FromStr for DesktopKeyMap {
    type Err = Error;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        use strum::IntoEnumIterator;

        Ok(DesktopKeyMap(
            s.lines()
                .flat_map(|l| l.split_whitespace().map(String::from))
                .map(keys::escape)
                .zip(IsoKey::iter())
                .map(|(val, key)| (key, val))
                .collect(),
        ))
    }
}

impl fmt::Display for DesktopKeyMap {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        for keys in &self.0.iter().chunks(12) {
            let line = keys.map(|(_key_id, value)| keys::decode(value)).join(" ");
            writeln!(f, "{}", line)?;
        }
        Ok(())
    }
}

// TODO: Implement proper escaping rules
//
// - [x] \u{0} <-> None
// - [ ] escpae unicode categories "C", "Z", "M"
// - [ ] proptests
mod keys {
    pub fn escape(input: String) -> Option<String> {
        if input == "\u{0}" {
            None
        } else {
            Some(input)
        }
    }

    pub fn decode(input: &Option<String>) -> String {
        if let Some(key) = input {
            key.clone()
        } else {
            String::from("\u{0}")
        }
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
