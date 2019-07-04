use lazy_static::lazy_static;
use regex::Regex;
use serde::{
    de::{self, Deserializer},
    ser::Serializer,
    Deserialize, Serialize,
};
use snafu::Snafu;

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub struct KeyValue(pub(crate) Option<String>);

impl<'de> Deserialize<'de> for KeyValue {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        let x: &str = Deserialize::deserialize(deserializer)?;
        Ok(KeyValue(deserialize(x).map_err(de::Error::custom)?))
    }
}

impl Serialize for KeyValue {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        let KeyValue(v) = self;
        serializer.serialize_str(&serialize(v))
    }
}

pub fn deserialize(input: &str) -> Result<Option<String>, Error> {
    if input == r"\u{0}" {
        Ok(None)
    } else {
        Ok(Some(decode_unicode_escapes(input)?))
    }
}

pub fn serialize(input: &Option<String>) -> String {
    if let Some(input) = input {
        input
            .chars()
            .map(|c| {
                let char_category = unic_ucd_category::GeneralCategory::of(c);

                if char_category.is_other()
                    || char_category.is_separator()
                    || char_category.is_mark()
                {
                    input.escape_unicode().to_string()
                } else {
                    input.to_string()
                }
            })
            .collect()
    } else {
        String::from(r"\u{0}")
    }
}

fn decode_unicode_escapes(input: &str) -> Result<String, Error> {
    lazy_static! {
        static ref RE: Regex = Regex::new(r"\\u\{([0-9A-Fa-f]{2,6})\}").expect("valid regex");
    }

    let new = RE.replace_all(input, |hex: &regex::Captures| {
        let number = u32::from_str_radix(hex.get(1).unwrap().as_str(), 16).unwrap();
        std::char::from_u32(number).unwrap().to_string()
    });

    Ok(new.to_string())
}

#[derive(Debug, Snafu)]
pub enum Error {
    #[snafu(display("std failed to parse `{}` as char: {}", input, source))]
    CharParseError {
        input: String,
        source: std::char::ParseCharError,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("Error parsing `{}` as char: {}", input, description))]
    CharFromStrError { input: String, description: String },
}
