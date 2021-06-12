use std::convert::TryFrom;

use bigdecimal::BigDecimal;
use derive_collect_docs::CollectDocs;
use lazy_static::lazy_static;
use regex::Regex;
use serde::{de::Deserializer, ser::Serializer, Deserialize, Serialize};
use thiserror::Error;

#[derive(Clone, Debug, PartialEq, PartialOrd, Eq, Ord)]
#[derive(CollectDocs)]
pub enum KeyValue {
    Symbol(String),
    Special { id: String, width: BigDecimal },
    None,
}

impl From<Option<String>> for KeyValue {
    fn from(x: Option<String>) -> Self {
        x.map(KeyValue::Symbol).unwrap_or(KeyValue::None)
    }
}

impl From<String> for KeyValue {
    fn from(x: String) -> Self {
        KeyValue::Symbol(x)
    }
}

impl ToString for KeyValue {
    fn to_string(&self) -> String {
        serialize(self)
    }
}

impl<'de> Deserialize<'de> for KeyValue {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        let x: &str = Deserialize::deserialize(deserializer)?;
        Ok(deserialize(x))
    }
}

impl Serialize for KeyValue {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        serializer.serialize_str(&serialize(self))
    }
}

pub fn deserialize_special(input: &str) -> Option<KeyValue> {
    lazy_static! {
        static ref RE: Regex =
            Regex::new(r"^\\s\{([^}:]+)(?::(\d+(?:\.\d+)?))?\}$").expect("valid regex");
    }

    // Symbol syntax \s{id:width}, or with optional width defaulting to 1.0, \s{id}
    RE.captures(input).map(|cap| KeyValue::Special {
        id: match cap.get(1).unwrap().as_str() {
            id if id.starts_with('"') && id.ends_with('"') => id.to_owned(),
            id => format!("_{}", id),
        },
        width: cap
            .get(2)
            .and_then(|v| v.as_str().parse::<BigDecimal>().ok())
            .unwrap_or_else(|| BigDecimal::try_from(1.0).unwrap()),
    })
}

pub fn deserialize(input: &str) -> KeyValue {
    if let Some(special) = deserialize_special(input) {
        special
    } else if input == r"\u{0}" {
        KeyValue::None
    } else {
        KeyValue::Symbol(decode_unicode_escapes(input))
    }
}

pub fn serialize_special(id: &str, width: &BigDecimal) -> String {
    let id = if id.starts_with('"') && id.ends_with('"') {
        id
    } else {
        &id[1..]
    };

    if width == &BigDecimal::try_from(1.0).unwrap() {
        format!("\\s{{{}}}", id)
    } else {
        format!("\\s{{{}:{:.2}}}", id, width)
    }
}

pub fn serialize(input: &KeyValue) -> String {
    match input {
        KeyValue::Special { id, width } => serialize_special(id, width),
        KeyValue::Symbol(input) => decode_unicode_escapes(input)
            .chars()
            .map(|c| {
                let char_category = unic_ucd_category::GeneralCategory::of(c);

                if char_category.is_other()
                    || char_category.is_separator()
                    || char_category.is_mark()
                {
                    c.escape_unicode().to_string()
                } else {
                    c.to_string()
                }
            })
            .collect(),
        _ => String::from(r"\u{0}"),
    }
}

/// Decode unicode escapes like `\u{30A}`
fn decode_unicode_escapes(input: &str) -> String {
    lazy_static! {
        static ref RE: Regex = Regex::new(r"\\u\{([0-9A-Fa-f]{1,6})\}").expect("valid regex");
    }

    let new = RE.replace_all(input, |hex: &regex::Captures| {
        let number = u32::from_str_radix(hex.get(1).unwrap().as_str(), 16).unwrap_or(0xfeff);
        std::char::from_u32(number).unwrap().to_string()
    });

    new.to_string()
}

#[derive(Debug, Error)]
pub enum Error {
    #[error("std failed to parse `{input}` as char: {source}")]
    CharParseError {
        input: String,
        source: std::char::ParseCharError,
    },
    #[error("Error parsing `{input}` as char: {description}")]
    CharFromStrError { input: String, description: String },
}

#[cfg(test)]
#[allow(clippy::unnecessary_operation)]
mod tests {
    use super::{decode_unicode_escapes, deserialize, deserialize_special, serialize, KeyValue};
    use proptest::prelude::*;

    #[test]
    fn test_unicode_escapes() {
        assert_eq!("\u{35}", decode_unicode_escapes(r"\u{35}"));
        assert_eq!("5", decode_unicode_escapes(r"\u{35}"));

        assert_eq!("\u{5}", decode_unicode_escapes(r"\u{5}"));
        assert_eq!("\"", decode_unicode_escapes(r"\u{22}"));
    }

    #[test]
    fn roundtrips() {
        let x = r"0 1 2 3 4 5 6 7 8 9 0 \u{1F} = \
            \u{11} \u{17} \u{5} \u{12} \u{14} \u{19} \u{15} \u{9} \u{F} \u{10} \u{1B} \u{1D} \
            \u{1} \u{13} \u{4} \u{6} \u{7} \u{8} \u{A} \u{B} \u{C} ; ' \u{1C} \
            ` \u{1A} \u{18} \u{3} \u{16} \u{2} \u{E} \u{D} , . /";

        for s in x.split_whitespace() {
            assert_eq!(s.to_lowercase(), serialize(&deserialize(&s)));
        }
    }

    #[test]
    fn roundtrips_special_chars() {
        let x = r"0 1 2 3 4 5 6 7 8 9 0 \u{1F} = \
            \u{11} \u{17} \u{5} \u{12} \u{14} \u{19} \u{15} \u{9} \s{sdsda:1.50} \u{10} \u{1B} \u{1D} \
            \u{1} \u{13} \u{4} \s{hello:1.05} \u{7} \u{8} \u{A} \u{B} \u{C} ; ' \u{1C} \
            ` \s{casdc:1.20} \u{18} \u{3} \u{16} \u{2} \u{E} \s{helvfvflo} , . /";

        for s in x.split_whitespace() {
            assert_eq!(s.to_lowercase(), serialize(&deserialize(&s)));
        }
    }

    #[test]
    fn special_chars() {
        assert_eq!(
            deserialize_special(r"\s{hello:1.00}"),
            Some(KeyValue::Special {
                id: "_hello".to_owned(),
                width: 1.0.into()
            })
        )
    }

    proptest! {
        #[test]
        fn doesnt_crash(s in ".") {
            serialize(&deserialize(&s))
        }

        #[test]
        fn escape_unicode_rountrip(c: char) {
            prop_assume!(c != '\u{0}');
            let esc = c.escape_unicode().to_string();
            assert_eq!(KeyValue::Symbol(c.to_string()), deserialize(&esc));
        }

        #[test]
        fn unescape_unicode_rountrip(c: char) {
            prop_assume!(c != '\u{0}');
            assert_eq!(KeyValue::Symbol(c.to_string()), deserialize(&serialize(&KeyValue::Symbol(c.to_string()))));
        }
    }
}
