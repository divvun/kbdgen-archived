pub use crate::bundle::keys::{Error as KeyValueError, KeyValue};
use crate::{bundle::keys, models::IsoKey};
use serde::{
    de::{self, Deserializer},
    ser::{SerializeMap, Serializer},
    Deserialize, Serialize,
};
use snafu::{ResultExt, Snafu};
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
pub struct DesktopKeyMap(pub(crate) BTreeMap<IsoKey, keys::KeyValue>);

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
            Map(BTreeMap<IsoKey, keys::KeyValue>),
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

        let map: Result<_, Error> = s
            .lines()
            .flat_map(|l| l.split_whitespace())
            .zip(IsoKey::iter())
            .map(|(val, key)| Ok((key, keys::KeyValue(keys::deserialize(val)))))
            .collect();

        Ok(DesktopKeyMap(map?))
    }
}

impl fmt::Display for DesktopKeyMap {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let keys: Vec<String> = self.0.values().map(|v| keys::serialize(&v.0)).collect();
        let width = keys
            .iter()
            .map(|x| unic_segment::Graphemes::new(x).count())
            .max()
            .unwrap_or(1);
        let lines: Vec<&[String]> = [
            &keys.get(0..13),
            &keys.get(13..25),
            &keys.get(25..37),
            &keys.get(37..48),
            &keys.get(48..),
        ]
        .iter()
        .filter_map(|x| x.filter(|x| !x.is_empty()))
        .collect();

        for (idx, line) in lines.into_iter().enumerate() {
            use std::fmt::Write;
            let mut l = String::new();

            if idx == 1 || idx == 2 {
                write!(&mut l, "{key:width$} ", key = " ", width = width)?;
            }
            for key in line {
                write!(&mut l, "{key:width$} ", key = key, width = width)?;
            }

            writeln!(f, "{}", l.trim_end())?;
        }

        Ok(())
    }
}

#[derive(Debug, Snafu)]
pub enum Error {
    #[snafu(display("{}", description))]
    ParseError {
        description: String,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("failed process key `{}`: {}", input, source))]
    KeyError {
        input: String,
        source: KeyValueError,
        backtrace: snafu::Backtrace,
    },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MobileKeyMap(pub(crate) Vec<Vec<String>>);

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

impl Serialize for MobileKeyMap {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        let lines: Vec<String> = self.0.iter().map(|line| line.join(" ")).collect();
        let max_len = lines.iter().map(|x| x.trim().len()).max().unwrap_or(0);

        let mut res = String::new();
        for line in &lines {
            res.push_str(&format!("{line:^width$}", line = line, width = max_len));
            res.push_str("\n");
        }

        serializer.serialize_str(&res)
    }
}
