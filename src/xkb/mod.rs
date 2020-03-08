use std::fmt;

mod convert;
mod ser;
pub use convert::Error as ConversionError;
pub use ser::ToXkb;

#[derive(Debug, PartialEq, Eq, PartialOrd, Ord, Clone)]
pub struct XkbFile {
    pub default: Symbols,
    pub others: Vec<Symbols>,
}

#[derive(Debug, PartialEq, Eq, PartialOrd, Ord, Clone)]
pub struct Symbols {
    pub id: String,
    pub name: String,
    pub leading_includes: Vec<String>,
    pub keys: Vec<Key>,
    pub trailing_includes: Vec<String>,
}

#[derive(Debug, PartialEq, Eq, PartialOrd, Ord, Clone)]
pub struct Key {
    pub iso_code: String,
    pub default: Option<XkbKeySym>,
    pub shift: Option<XkbKeySym>,
    pub alt: Option<XkbKeySym>,
    pub alt_shift: Option<XkbKeySym>,
}

#[derive(Debug, PartialEq, Eq, PartialOrd, Ord, Clone)]
pub struct XkbKeySym(pub String);

impl fmt::Display for XkbKeySym {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        let c = self.0.chars().next().expect("keysym can't be empty");
        if let Some(sym) = x11_keysymdef::lookup_by_codepoint(c).and_then(|r| r.names.get(0)) {
            write!(f, "{}", sym)
        } else {
            write!(f, "U{}", c as u32)
        }
    }
}
