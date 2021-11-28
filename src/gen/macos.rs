use std::{convert::TryInto, fmt::Display, ops::Deref, path::PathBuf, rc::Rc};

use indexmap::IndexMap;
use nova::newtype;
use xmlem::QName;

use crate::ProjectBundle;

pub fn generate(bundle: ProjectBundle, project_path: PathBuf) {}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
enum Str<'a> {
    Borrowed(&'a str),
    Owned(Rc<str>),
}

impl<'a> Deref for Str<'a> {
    type Target = str;

    fn deref(&self) -> &Self::Target {
        match self {
            Self::Borrowed(x) => *x,
            Self::Owned(x) => &*x,
        }
    }
}

impl<'a> From<&'a str> for Str<'a> {
    fn from(x: &'a str) -> Self {
        Self::Borrowed(x)
    }
}

impl From<String> for Str<'_> {
    fn from(x: String) -> Self {
        Self::Owned(x.into_boxed_str().into())
    }
}

#[newtype(borrow = "str")]
type ModifiersId<'a> = Str<'a>;

#[newtype(new, borrow = "str")]
type KeyMapId = Rc<String>;

#[newtype(new, borrow = "str")]
type ActionId<'a> = Str<'a>;

#[newtype(borrow = "str")]
type StateId<'a> = Str<'a>;

const STATE_NONE: StateId = StateId(Str::Borrowed("none"));

// <keyboard group="126" id="-2844" name="enusaltsv">

struct Layout<'a> {
    first: u8,
    last: u8,
    map_set: String,
    modifiers: ModifiersId<'a>,
    key_map_sets: IndexMap<KeyMapId, Vec<Vec<Key<'a>>>>,
    actions: IndexMap<ActionId<'a>, IndexMap<StateId<'a>, String>>,
    teminators: IndexMap<StateId<'a>, String>,
}

struct Keyboard<'a> {
    name: String,
    id: i16,
    group: u8,
    layouts: Vec<Layout<'a>>,
}

impl Display for Keyboard<'_> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(r#"<?xml version="1.1" encoding="UTF-8"?>"#)?;
        f.write_str(r#"<!DOCTYPE keyboard PUBLIC "" "file://localhost/System/Library/DTDs/KeyboardLayout.dtd">"#)?;

        let root = xmlem::Root::new("keyboard");
        {
            let el = root.borrow();
            el.add_attr(QName::new(&root, "group"), &self.group.to_string());
            el.add_attr(QName::new(&root, "id"), &self.id.to_string());
            el.add_attr(QName::new(&root, "name"), &self.name);

            let mut layouts = root.element("layouts");
            {
                let layouts = layouts.borrow();
                let layout = root.element("layout");

                {
                    let layout = layout.borrow();

                    layout.add_attr(QName::new(&root, "first"), "0");
                }

                layouts.add_child(layout);
            }

            el.add_child(layouts);
        }

        f.write_str(&root.to_string())
    }
}

struct ModifierMap<'a> {
    id: ModifiersId<'a>,
    default_index: u8,
    key_map_select: Vec<String>,
}

enum Key<'a> {
    Action { code: Str<'a>, id: ActionId<'a> },
    Output { code: Str<'a>, output: String },
}

#[test]
fn lalala() {}
