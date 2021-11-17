use std::fmt::{Display, LowerHex, Write};

use indexmap::IndexMap;

use crate::{models::Layout, KeyValue};

use super::{cap_mode::CapMode, ligature::Ligature};

#[derive(Debug, Clone, PartialEq, Eq)]
pub(super) enum Key {
    Ligature(Ligature),
    DeadKey(Char),
    Char(Char),
    None,
}

#[derive(Debug, Copy, Clone, PartialEq, Eq)]
pub(super) enum Char {
    Ascii(char),
    Unicode(char),
}

pub(super) fn derive_key(
    vk: &'static str,
    cap_mode: CapMode,
    layout: &Layout,
    mode: &str,
    input: &IndexMap<String, KeyValue>,
) -> Key {
    let input = match input.get(mode) {
        Some(KeyValue::Symbol(v)) => v.to_string(),
        Some(KeyValue::None) | None => return Key::None,
        Some(_) => {
            log::error!("Invalid key: {:?}", input);
            return Key::None;
        }
    };

    let u16s = input.encode_utf16().collect::<Vec<_>>();
    if u16s.len() == 0 || u16s[0] == 0 {
        return Key::None;
    }

    if u16s.len() == 1 {
        let ch = input.chars().next().unwrap();

        if is_dead_key_on_layer(layout, mode, &input) {
            Key::DeadKey(Char::new(ch))
        } else {
            Key::Char(Char::new(ch))
        }
    } else if u16s.len() <= 4 {
        Key::Ligature(Ligature {
            vk,
            cap_mode,
            bytes: u16s,
        })
    } else {
        log::error!("Invalid key: {:?}", input);
        Key::None
    }
}

fn is_dead_key_on_layer(layout: &Layout, mode: &str, input: &str) -> bool {
    let dead_keys = match layout.dead_keys.get("win") {
        Some(v) => v,
        None => return false,
    };
    let keys = match dead_keys.get(mode) {
        Some(v) => v,
        None => return false,
    };
    keys.contains(&input.to_string())
}

impl Key {
    pub fn is_none(&self) -> bool {
        match self {
            Key::None => true,
            _ => false,
        }
    }

    pub fn ligature(&self) -> Option<Ligature> {
        match self {
            Key::Ligature(v) => Some(v.clone()),
            _ => None,
        }
    }

    pub fn dead_key(&self) -> Option<Char> {
        match self {
            Key::DeadKey(v) => Some(v.clone()),
            _ => None,
        }
    }
}

impl Display for Key {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Key::Char(ch) => Display::fmt(ch, f),
            Key::Ligature(_) => f.write_str("%%"),
            Key::DeadKey(d) => f.write_fmt(format_args!("{}@", d)),
            Key::None => f.write_str("-1"),
        }
    }
}

impl Char {
    pub fn new(ch: char) -> Self {
        if ch.is_ascii_graphic() {
            Char::Ascii(ch)
        } else {
            Char::Unicode(ch)
        }
    }

    pub fn into_inner(&self) -> char {
        match self {
            Char::Ascii(x) => *x,
            Char::Unicode(x) => *x,
        }
    }
}

impl Display for Char {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Ascii(ascii) => f.write_char(*ascii),
            Self::Unicode(uni) => f.write_fmt(format_args!("{:04x}", *uni as u32)),
        }
    }
}

impl LowerHex for Char {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_fmt(format_args!(
            "{:04x}",
            *match self {
                Self::Ascii(x) => x,
                Self::Unicode(x) => x,
            } as u32
        ))
    }
}
