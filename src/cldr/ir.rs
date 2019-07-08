use super::{models::RawIsoKey, KeyMap};
use std::collections::BTreeMap;

#[derive(Debug, Clone)]
pub enum Layer {
    Desktop(DesktopLayer),
    Mobile(MobileLayer),
}

pub(crate) fn parse_modifiers(mods: Option<&String>) -> String {
    let mess = match mods {
        Some(v) => {
            if v == "shift caps" || v == "caps shift" {
                return "shift".into();
            }

            v
        }
        None => return "default".into(),
    };

    mess.split(' ')
        .map(|chunk| {
            chunk
                .split('+')
                .filter(|x| !x.ends_with('?'))
                .map(|v| match v {
                    "shift" | "shiftR" | "shiftL" => "shift".into(),
                    "ctrl" | "ctrlR" | "ctrlL" => "ctrl".into(),
                    "opt" | "optR" | "optL" => "alt".into(),
                    x if x.ends_with('R') || x.ends_with('L') => x[..x.len() - 1].into(),
                    _ => v.into(),
                })
                .collect::<Vec<String>>()
        })
        .min()
        .unwrap()
        .join("+")
}

#[derive(Debug, Clone)]
pub struct DesktopLayer {
    pub mode: String,
    pub keys: BTreeMap<RawIsoKey, String>,
}

#[derive(Debug, Clone)]
pub struct MobileLayer {
    pub mode: String,
    pub keys: Vec<Vec<String>>,
}

impl DesktopLayer {
    pub(crate) fn new(mode: String, keys: BTreeMap<RawIsoKey, String>) -> DesktopLayer {
        DesktopLayer { mode, keys }
    }

    pub fn iter(&self) -> DesktopLayerIterator {
        DesktopLayerIterator::new(self)
    }
}

impl MobileLayer {
    pub(crate) fn new(mode: String, keys: Vec<Vec<String>>) -> MobileLayer {
        MobileLayer { mode, keys }
    }
}

pub struct DesktopLayerIterator<'a> {
    layer: &'a DesktopLayer,
    letter: &'static str,
    n: u8,
    d13_workaround: Option<&'a str>,
}

impl<'a> DesktopLayerIterator<'a> {
    fn new(layer: &'a DesktopLayer) -> DesktopLayerIterator<'a> {
        DesktopLayerIterator {
            layer,
            letter: "E",
            n: 0,
            d13_workaround: None,
        }
    }
}

const MAX_E: u8 = 12;
const MIN_D: u8 = 1;
const MAX_D: u8 = 13;
const MIN_C: u8 = 1;
const MAX_C: u8 = 12;
const MIN_B: u8 = 0;
const MAX_B: u8 = 10;

impl<'a> Iterator for DesktopLayerIterator<'a> {
    type Item = (&'a str, u8, Option<&'a str>);

    fn next(&mut self) -> Option<Self::Item> {
        use std::str::FromStr;

        if self.letter == "A" {
            return None;
        }

        let iso_k = format!("{}{:02}", self.letter, self.n);
        let key = match RawIsoKey::from_str(&iso_k) {
            Ok(v) => v,
            Err(_) => return None,
        };

        let mut result = match self.layer.keys.get(&key) {
            Some(input) => (self.letter, self.n, Some(&**input)),
            None => (self.letter, self.n, None),
        };

        // Handle ANSI vs ISO nonsense
        if self.letter == "D" && self.n == 13 {
            self.d13_workaround = result.2;
            self.letter = "C";
            self.n = MIN_C;
            return self.next();
        }

        if self.letter == "C" && self.n == 12 && result.2.is_none() {
            if let Some(v) = self.d13_workaround.take() {
                result = (self.letter, self.n, Some(v));
            }
        }

        let max = match self.letter {
            "E" => MAX_E,
            "D" => MAX_D,
            "C" => MAX_C,
            "B" => MAX_B,
            _ => unreachable!(),
        };

        if self.n + 1 > max {
            let (min, letter) = match self.letter {
                "E" => (MIN_D, "D"),
                "D" => (MIN_C, "C"),
                "C" => (MIN_B, "B"),
                "B" => (0, "A"),
                _ => unreachable!(),
            };

            self.n = min;
            self.letter = letter;
        } else {
            self.n += 1;
        }

        Some(result)
    }
}

impl From<&KeyMap> for DesktopLayer {
    fn from(key_map: &KeyMap) -> DesktopLayer {
        use std::str::FromStr;

        let mut keys = BTreeMap::new();

        for map in key_map.keys.iter() {
            if let Ok(key) = RawIsoKey::from_str(&map.iso) {
                keys.insert(key, map.to.clone());
            }
        }

        DesktopLayer::new(parse_modifiers(key_map.modifiers.as_ref()), keys)
    }
}

impl From<&KeyMap> for MobileLayer {
    fn from(key_map: &KeyMap) -> MobileLayer {
        let mut keys = vec![];
        let mut next = vec![];

        let mut letter = "D";
        for map in key_map.keys.iter() {
            if !map.iso.starts_with(letter) {
                keys.push(next);
                next = vec![];
                letter = &map.iso[..1];
            }

            next.push(map.to.clone());
        }
        keys.push(next);

        MobileLayer::new(parse_modifiers(key_map.modifiers.as_ref()), keys)
    }
}

impl From<&MobileLayer> for String {
    fn from(layer: &MobileLayer) -> String {
        layer
            .keys
            .iter()
            .map(|row| row.join(" "))
            .collect::<Vec<_>>()
            .join("\n")
    }
}

impl From<&Layer> for String {
    fn from(layer: &Layer) -> String {
        match layer {
            Layer::Desktop(layer) => String::from(layer),
            Layer::Mobile(layer) => String::from(layer),
        }
    }
}

impl From<&DesktopLayer> for String {
    fn from(layer: &DesktopLayer) -> String {
        let mut cur = "Z";
        let mut out = String::new();

        for (letter, _n, value) in layer.iter() {
            let v = match value {
                Some(v) => v,
                None => "\\u{0}",
            };

            if cur != letter {
                if cur != "Z" {
                    out.push('\n');
                }
                cur = letter;
            } else {
                out.push(' ');
            }

            out.push_str(v);
        }

        out
    }
}

impl From<&DesktopLayer> for serde_yaml::Value {
    fn from(layer: &DesktopLayer) -> serde_yaml::Value {
        serde_yaml::Value::String(String::from(layer))
    }
}
