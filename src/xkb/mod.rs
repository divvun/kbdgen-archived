mod ser;
pub use ser::ToXkb;

#[derive(Debug, PartialEq, Eq, PartialOrd, Ord, Clone)]
pub struct Symbols {
    pub name: String,
    pub groups: Vec<Group>,
}

#[derive(Debug, PartialEq, Eq, PartialOrd, Ord, Clone)]
pub struct Group {
    pub name: String,
    pub leading_includes: Vec<String>,
    pub keys: Vec<Key>,
    pub trailing_includes: Vec<String>,
}

#[derive(Debug, PartialEq, Eq, PartialOrd, Ord, Clone)]
pub struct Key {
    pub iso_code: String,
    pub default: Option<String>,
    pub shift: Option<String>,
    pub alt: Option<String>,
    pub alt_shift: Option<String>,
}
