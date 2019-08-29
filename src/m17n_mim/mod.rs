//! M17n
//!
//! The docs in this module quote the [m17n "Data format of the m17n database"
//! docs][1] a lot.
//!
//! [1]: https://www.nongnu.org/m17n/manual-en/m17nDBFormat.html

use shrinkwraprs::Shrinkwrap;
use snafu::ResultExt;
use std::{convert::TryFrom, fmt, str::FromStr};

mod ser;
pub use ser::ToMim;

/// M17n Input Method, i.e., the content of a `.mim` file
//
// INPUT-METHOD ::=
//     IM-DECLARATION ? IM-DESCRIPTION ? TITLE ?
//      VARIABLE-LIST ? COMMAND-LIST ?  MODULE-LIST ?
//      MACRO-LIST ? MAP-LIST ? STATE-LIST ?
//
//
// IM-DESCRIPTION ::= '(' 'description' DESCRIPTION ')'
// DESCRIPTION ::= MTEXT-OR-GETTEXT | 'nil'
// MTEXT-OR-GETTEXT ::=  [ MTEXT | '(' '_' MTEXT ')']
//
// TITLE ::= '(' 'title' TITLE-TEXT ')'
// TITLE-TEXT ::= MTEXT
pub struct Root {
    pub input_method: InputMethod,
    pub description: Option<Text>,
    pub title: Text,
    // variable_list: Vec<Variable>,
    // command_list: Vec<Command>,
    // module_list: Vec<Mgodule>,
    // macro_list: Vec<Macro>,
    pub maps: Vec<Map>,
    pub states: Vec<State>,
}

// IM-DECLARATION ::= '(' 'input-method' LANGUAGE NAME EXTRA-ID ? VERSION ? ')'
// LANGUAGE ::= SYMBOL
// NAME ::= SYMBOL
// EXTRA-ID ::= SYMBOL
// VERSION ::= '(' 'version' VERSION-NUMBER ')'
pub struct InputMethod {
    pub language: Symbol,
    pub name: Symbol,
    pub extra_id: Option<Symbol>,
    pub version: Option<String>,
}

// MAP-LIST ::= MAP-INCLUSION ? '(' 'map' MAP * ')'
// MAP ::= '(' MAP-NAME RULE * ')'
// MAP-NAME ::= SYMBOL
pub struct Map {
    pub name: Symbol,
    pub rules: Vec<Rule>,
}

// RULE ::= '(' KEYSEQ MAP-ACTION * ')'
pub struct Rule {
    /// Keys to press to produce mapping
    pub keyseq: KeySeq,
    /// The mapping describes what to do
    ///
    /// Right now we only support inserting characters.
    pub action: MapAction,
}

// KEYSEQ ::= MTEXT | '(' [ SYMBOL | INTEGER ] * ')'
pub enum KeySeq {
    /// > MTEXT in the definition of `KEYSEQ` consists of characters that can be
    /// > generated by a keyboard. Therefore MTEXT usually contains only ASCII
    /// > characters. However, if the input method is intended to be used, for
    /// > instance, with a West European keyboard, MTEXT may contain Latin-1
    /// > characters.
    Character(Text),
    /// > If the shift, control, meta, alt, super, and hyper modifiers are used,
    /// > they are represented by the `S-`, `C-`, `M-`, `A-`, `s-`, and `H-`
    /// > prefixes respectively in this order. Thus, "return with shift with
    /// > meta with hyper" is `(S-M-H-Return)`. Note that "a with shift" .. "z
    /// > with shift" are represented simply as `A .. Z`. Thus "a with shift
    /// > with meta with hyper" is `(M-H-A)`.
    KeyCombo(KeyCombo),
}

pub struct KeyCombo {
    /// Represents something like `C-S` for "Control + Shift"
    pub modifiers: Vec<Modifier>,
    // Can be TEXT or INTEGER but let's be conservative and expect a character
    // code.
    pub key: KeyDef,
}

pub enum KeyDef {
    /// > INTEGER in the definition of `KEYSEQ` must be a valid character code.
    CharacterCode(Integer),
    /// > SYMBOL in the definition of `KEYSEQ` must be the return value of the
    /// > `minput_event_to_key()` function. Under the X window system, you can
    /// > quickly check the value using the `xev` command. For example, the
    /// > return key, the backspace key, and the 0 key on the keypad are
    /// > represented as `(Return)`, `(BackSpace)`, and `(KP_0)` respectively.
    Character(Symbol),
}

/// Modifier keys
///
/// > "S-" (Shift), "C-" (Control), "M-" (Meta), "A-" (Alt), "G-" (AltGr), "s-"
/// > (Super), and "H-" (Hyper)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[derive(strum_macros::EnumString, strum_macros::Display)]
#[strum(serialize_all = "snake_case")]
pub enum Modifier {
    Shift,
    #[strum(serialize = "ctrl", serialize = "control")]
    Control,
    /// Often one of the Alt keys in terminals
    Meta,
    Alt,
    AltGr,
    /// Super key is assumed to be Command key on macOS
    #[strum(serialize = "super", serialize = "cmd")]
    Super,
    /// Mo layers, mo fun
    Hyper,
}

impl Modifier {
    /// Parse kbdgen-typical key combo syntax
    ///
    /// ```rust
    /// use kbdgen::m17n_mim::Modifier;
    ///
    /// assert_eq!(
    ///     Modifier::parse_keycombo("ctrl").unwrap(),
    ///     vec![Modifier::Control],
    /// );
    /// assert_eq!(
    ///     Modifier::parse_keycombo("alt+shift").unwrap(),
    ///     vec![Modifier::Alt, Modifier::Shift],
    /// );
    /// assert_eq!(
    ///     Modifier::parse_keycombo("cmd+alt").unwrap(),
    ///     vec![Modifier::Super, Modifier::Alt],
    /// );
    /// ```
    pub fn parse_keycombo(input: &str) -> Result<Vec<Modifier>, MimConversion> {
        let mut res = vec![];
        for m in input.split('+') {
            if let Ok(m) = Modifier::from_str(m) {
                res.push(m);
            } else {
                InvalidKeyCombo {
                    input: format!("unknown modifier `{}`", m),
                }
                .fail()?;
            }
        }
        Ok(res)
    }
}

// Originally a quite complex type, defined as:
//
// ```bnf
// MAP-ACTION ::= ACTION
//
// ACTION ::= INSERT | DELETE | SELECT | MOVE | MARK
//            | SHOW | HIDE | PUSHBACK | POP | UNDO
// 	          | COMMIT | UNHANDLE | SHIFT | CALL
// 	          | SET | IF | COND | '(' MACRO-NAME ')'
//
// PREDEFINED-SYMBOL ::=
//     '@0' | '@1' | '@2' | '@3' | '@4'
//     | '@5' | '@6' | '@7' | '@8' | '@9'
//     | '@<' | '@=' | '@>' | '@-' | '@+' | '@[' | '@]'
//     | '@@'
//     | '@-0' | '@-N' | '@+N'
// ```
//
// but we've only implemented the trivial Insert variants at the moment.
pub enum MapAction {
    Insert(Insert),

    #[cfg(sorry_not_yet_implemented)]
    Delete(Delete),
    #[cfg(sorry_not_yet_implemented)]
    Select(Select),
    #[cfg(sorry_not_yet_implemented)]
    Move(Move),
    #[cfg(sorry_not_yet_implemented)]
    Mark(Mark),
    #[cfg(sorry_not_yet_implemented)]
    Show(Show),
    #[cfg(sorry_not_yet_implemented)]
    Hide(Hide),
    #[cfg(sorry_not_yet_implemented)]
    Pushback(Pushback),
    #[cfg(sorry_not_yet_implemented)]
    Pop(Pop),
    #[cfg(sorry_not_yet_implemented)]
    Undo(Undo),
    #[cfg(sorry_not_yet_implemented)]
    Commit(Commit),
    #[cfg(sorry_not_yet_implemented)]
    Unhandle(Unhandle),
    #[cfg(sorry_not_yet_implemented)]
    Shift(Shift),
    #[cfg(sorry_not_yet_implemented)]
    Call(Call),
    #[cfg(sorry_not_yet_implemented)]
    Set(Set),
    #[cfg(sorry_not_yet_implemented)]
    If(If),
    #[cfg(sorry_not_yet_implemented)]
    Cond(Cond),
    #[cfg(sorry_not_yet_implemented)]
    Macro(Symbol),
}

/// Insert action: insert something before the current position
//
// Originally defined as:
//
// ```bnf
// INSERT ::= '(' 'insert' MTEXT ')'
//             | MTEXT
//             | INTEGER
//             | SYMBOL
//             | '(' 'insert' SYMBOL ')'
//             | '(' 'insert' '(' CANDIDATES * ')' ')'
//             | '(' CANDIDATES * ')'
//
// CANDIDATES ::= MTEXT | '(' MTEXT * ')'
// ```
//
// but we'll only use the simple forms for now
pub enum Insert {
    /// > insert TEXT before the current position
    Character(Text),
    /// > inserts the character INTEGER before the current position
    CharacterCode(Integer),

    #[cfg(sorry_not_yet_implemented)]
    /// > treats SYMBOL as a variable, and inserts its value (if it is a valid
    /// > character code) before the current position
    KeyCombo(Symbol),

    #[cfg(sorry_not_yet_implemented)]
    /// > each CANDIDATES represents a candidate group, and each element of
    /// >CANDIDATES represents a candidate, i.e. if CANDIDATES is an M-text, the
    /// >candidates are the characters in the M-text; if CANDIDATES is a list of
    /// >M-texts, the candidates are the M-texts in the list.
    /// >
    /// >These forms insert the first candidate before the current position. The
    /// >inserted string is associated with the list of candidates and the
    /// >information indicating the currently selected candidate.
    Candidates(Vec<Text>),
}

// STATE-LIST ::= STATE-INCUSION ? '(' 'state' STATE * ')'  STATE-INCUSION ?
// STATE ::= '(' STATE-NAME [ STATE-TITLE-TEXT ] BRANCH * ')'
// STATE-NAME ::= SYMBOL
// STATE-TITLE-TEXT ::= MTEXT
// STATE-INCLUSION ::= '(' 'include' TAGS 'state' STATE-NAME ? ')'
pub struct State {
    name: Symbol,
    title: Option<Text>,
    branches: Vec<Branch>,
}

// BRANCH ::= '(' MAP-NAME BRANCH-ACTION * ')'
// 	   | '(' 'nil' BRANCH-ACTION * ')'
// 	   | '(' 't' BRANCH-ACTION * ')'
pub struct Branch {
    map_name: Symbol,

    #[cfg(sorry_not_yet_implemented)]
    actions: Vec<Action>,
}

/// The "MSymbol" type
///
/// [Defined](https://www.nongnu.org/m17n/manual-en/m17nDBFormat.html) as:
///
/// > An element that matches the regular expression `[^-0-9(]([^\()]|\.)+`
/// > represents a property whose key is `Msymbol`. In the element, `\t`, `\n`,
/// > `\r`, and `\e` are replaced with tab (code 9), newline (code 10), carriage
/// > return (code 13), and escape (code 27) respectively. Other characters
/// > following a backslash is interpreted as it is. The value of the property
/// > is the symbol having the resulting string as its name.
/// >
/// > For instance, the element `abc\ def` represents a property whose value is
/// > the symbol having the name "abc def".
#[derive(Clone)]
pub struct Symbol(String);

impl TryFrom<String> for Symbol {
    type Error = MimConversion;

    fn try_from(x: String) -> Result<Self, Self::Error> {
        // FIXME: Escaping and stuff
        Ok(Symbol(x))
    }
}

impl fmt::Display for Symbol {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        let t = self
            .0
            .replace(r"(", r"\(")
            .replace(r")", r"\)")
            .replace(r"]", r"\]")
            .replace(r"[", r"\[")
            .replace(r";", r"\;")
            .replace(r"'", r"\'")
            .replace(r#"""#, r#"\""#)
            .replace(r"\", r"\\");

        writeln!(f, "{}", t)?;

        Ok(())
    }
}

/// The "MText" type
///
/// [Defined](https://www.nongnu.org/m17n/manual-en/m17nDBFormat.html) as:
///
/// > An element that matches the regular expression `([^"]|\")*` represents a
/// > property whose key is `Mtext`. The backslash escape explained above also
/// > applies here. Moreover, each part in the element matching the regular
/// > expression `\[xX][0-9A-Fa-f][0-9A-Fa-f]` is replaced with its hexadecimal
/// > interpretation.
///
/// > After having resolved the backslash escapes, the byte sequence between the
/// > double quotes is interpreted as a UTF-8 sequence and decoded into an
/// > M-text. This M-text is the value of the property.
#[derive(Shrinkwrap)]
pub struct Text(String);

impl TryFrom<String> for Text {
    type Error = MimConversion;

    fn try_from(x: String) -> Result<Self, Self::Error> {
        // FIXME: Escaping and stuff
        Ok(Text(x))
    }
}

#[derive(snafu::Snafu, Debug)]
pub enum MimConversion {
    #[snafu(display("Could serialize MIM symbol"))]
    InvalidSymbol { backtrace: snafu::Backtrace },
    #[snafu(display("Could serialize MIM text"))]
    InvalidText { backtrace: snafu::Backtrace },
    #[snafu(display("Could serialize MIM key combo: {}", input))]
    InvalidKeyCombo {
        input: String,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("Could not map index `{}` to a character code", index))]
    InvalidCharactorCodeIndex {
        index: usize,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display(
        "Assumed hexadecimal MIM integer but there was no `0x` prefix in `{}`",
        input
    ))]
    InvalidIntegerHexPrefix {
        input: String,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display(
        "Assumed hexadecimal MIM integer but `{}` is not a valid hex value",
        input
    ))]
    InvalidIntegerHexValue {
        input: String,
        source: std::num::ParseIntError,
        backtrace: snafu::Backtrace,
    },
}

/// The "Minteger" type
///
/// [Defined](https://www.nongnu.org/m17n/manual-en/m17nDBFormat.html) as:
///
/// > An element that matches the regular expression `-?[0-9]+ or
/// > 0[xX][0-9A-Fa-f]+` represents a property whose key is `Minteger`. An
/// > element matching the former expression is interpreted as an integer in
/// > decimal notation, and one matching the latter is interpreted as an integer
/// > in hexadecimal notation. The value of the property is the result of
/// > interpretation.
/// >
/// > For instance, the element `0xA0` represents a property whose value is 160
/// > in decimal.
#[derive(Shrinkwrap)]
pub struct Integer(String);

impl TryFrom<String> for Integer {
    type Error = MimConversion;

    fn try_from(input: String) -> Result<Self, Self::Error> {
        // decimal
        if let Ok(_) = u32::from_str_radix(&input, 10) {
            return Ok(Integer(input));
        }

        // hex
        if !(input.starts_with("0x") || input.starts_with("0X")) {
            return InvalidIntegerHexPrefix { input }.fail();
        }
        let _parsed =
            u64::from_str_radix(&input[2..], 16).with_context(|| InvalidIntegerHexValue { input: &input })?;
        Ok(Integer(input))
    }
}
