use std::collections::HashMap;

fn parse_modifiers(mods: Option<&String>) -> String {
    // TODO
    match mods {
        Some(v) => v.to_string(),
        None => "default".into()
    }
}

#[derive(Debug, Clone)]
pub struct Layer {
    pub mode: String,
    pub keys: HashMap<String, String>
}

impl Layer {
    fn new(mode: String, keys: HashMap<String, String>) -> Layer {
        Layer { mode, keys }
    }

    pub fn iter<'a>(&'a self) -> LayerIterator<'a> {
        LayerIterator { layer: self, letter: "E", n: 0, d13_workaround: None }
    }
}

pub struct LayerIterator<'a> {
    layer: &'a Layer,
    letter: &'static str,
    n: u8,
    d13_workaround: Option<&'a str>
}

static MAX_E: u8 = 12;
static MIN_D: u8 = 1;
static MAX_D: u8 = 13;
static MIN_C: u8 = 1;
static MAX_C: u8 = 12;
static MIN_B: u8 = 0;
static MAX_B: u8 = 10;

impl<'a> Iterator for LayerIterator<'a> {
    type Item = (&'a str, u8, Option<&'a str>);

    fn next(&mut self) -> Option<Self::Item> {
        if self.letter == "A" {
            return None;
        }

        let iso_k = format!("{}{:02}", self.letter, self.n);

        let mut result = match self.layer.keys.get(&iso_k) {
            Some(input) => (self.letter, self.n, Some(&**input)),
            None => (self.letter, self.n, None)
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
            _ => unreachable!()
        };

        if self.n + 1 > max {
            let (min, letter) = match self.letter {
                "E" => (MIN_D, "D"),
                "D" => (MIN_C, "C"),
                "C" => (MIN_B, "B"),
                "B" => (0, "A"),
                _ => unreachable!()
            };

            self.n = min;
            self.letter = letter;
        } else {
            self.n += 1;
        }

        Some(result)
    }
}

// impl From<&crate::KeyMap> for Layer {
//     fn from(key_map: &crate::KeyMap) -> Layer {
//         let mut keys = HashMap::new();

//         for map in key_map.maps.iter() {
//         keys.insert(map.iso.clone(), map.to.clone());
//         }
        
//         Layer::new(parse_modifiers(key_map.modifiers.as_ref()), keys)
//     }
// }

impl From<&Layer> for String {
    fn from(layer: &Layer) -> String {
        let mut cur = "Z";
        let mut out = String::new();

        for (letter, n, value) in layer.iter() {
            let v = match value {
                Some(v) => v,
                None => "\\u{0}"
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

impl From<&Layer> for serde_yaml::Value {
    fn from(layer: &Layer) -> serde_yaml::Value {
        serde_yaml::Value::String(String::from(layer))
    }
}

use std::convert::TryFrom;
use std::error::Error;

impl TryFrom<&serde_yaml::Value> for Layer {
  type Error = Box<dyn Error>;

  fn try_from(value: &serde_yaml::Value) -> Result<Layer, Self::Error> {
    
    unimplemented!()
  }
}
