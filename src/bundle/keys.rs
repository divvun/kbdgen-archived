use serde::{
    de::{self, Deserializer},
    ser::Serializer,
    Deserialize, Serialize,
};
use snafu::{ResultExt, Snafu};
use std::str::FromStr;

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub struct KeyValue(pub(crate) Option<char>);

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

pub fn deserialize(input: &str) -> Result<Option<char>, Error> {
    let input_char = char_from_str(&input)?;
    if input_char == '\u{0}' {
        Ok(None)
    } else {
        Ok(Some(input_char))
    }
}

pub fn serialize(input: &Option<char>) -> String {
    if let Some(input) = input {
        let char_category = unic_ucd_category::GeneralCategory::of(*input);

        if char_category.is_other() || char_category.is_separator() || char_category.is_mark() {
            input.escape_unicode().to_string()
        } else {
            input.to_string()
        }
    } else {
        String::from("\u{0}")
    }
}

fn char_from_str(input: &str) -> Result<char, Error> {
    let first_try = char::from_str(&input).context(CharParseError { input });
    if let Ok(c) = first_try {
        return Ok(c);
    }

    match dbg!((input.find("\\u{"), input.rfind("}"))) {
        (Some(0), Some(end)) => {
            let inner = &input[3..end];
            let number =
                dbg!(u32::from_str_radix(inner, 16)).map_err(|e| Error::CharFromStrError {
                    input: input.to_string(),
                    description: e.to_string(),
                })?;
            Ok(
                dbg!(std::char::from_u32(number)).ok_or_else(|| Error::CharFromStrError {
                    input: input.to_string(),
                    description: String::from("not enough char"),
                })?,
            )
        }
        _ => Ok(first_try?),
    }
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
