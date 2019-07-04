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
        Ok(KeyValue(deserialize(x)))
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

pub fn deserialize(input: &str) -> Option<String> {
    if input == r"\u{0}" {
        None
    } else {
        Some(decode_unicode_escapes(input))
    }
}

pub fn serialize(input: &Option<String>) -> String {
    if let Some(input) = input {
        decode_unicode_escapes(input)
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
            .collect()
    } else {
        String::from(r"\u{0}")
    }
}

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

#[cfg(test)]
mod tests {
    use super::{decode_unicode_escapes, deserialize, serialize};
    use proptest::prelude::*;

    #[test]
    fn test_unicode_escapes() {
        assert_eq!("\u{35}", decode_unicode_escapes(r"\u{35}").unwrap());
        assert_eq!("5", decode_unicode_escapes(r"\u{35}").unwrap());

        assert_eq!("\u{5}", decode_unicode_escapes(r"\u{5}").unwrap());
        assert_eq!("\"", decode_unicode_escapes(r"\u{22}").unwrap());
    }

    #[test]
    fn roundtrips() {
        let x = r"0 1 2 3 4 5 6 7 8 9 0 \u{1F} = \
            \u{11} \u{17} \u{5} \u{12} \u{14} \u{19} \u{15} \u{9} \u{F} \u{10} \u{1B} \u{1D} \
            \u{1} \u{13} \u{4} \u{6} \u{7} \u{8} \u{A} \u{B} \u{C} ; ' \u{1C} \
            ` \u{1A} \u{18} \u{3} \u{16} \u{2} \u{E} \u{D} , . /";

        for s in x.split_whitespace() {
            assert_eq!(s.to_lowercase(), serialize(&deserialize(&s).unwrap()));
        }
    }

    proptest! {
        #[test]
        fn doesnt_crash(s in ".") {
            serialize(&deserialize(&s).unwrap())
        }

        #[test]
        fn escape_unicode_rountrip(c: char) {
            prop_assume!(c != '\u{0}');
            let esc = c.escape_unicode().to_string();
            assert_eq!(c.to_string(), deserialize(&esc).unwrap().unwrap());
        }

        #[test]
        fn unescape_unicode_rountrip(c: char) {
            prop_assume!(c != '\u{0}');
            assert_eq!(c.to_string(), deserialize(&serialize(&Some(c.to_string()))).unwrap().unwrap());
        }
    }
}
