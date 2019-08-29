use super::*;
use crate::pad::PadAdapter;
use std::io::{Result, Write};

pub trait ToMim {
    fn write_mim(&self, w: impl Write) -> Result<()>;
}

impl ToMim for Root {
    fn write_mim(&self, mut w: impl Write) -> Result<()> {
        self.input_method.write_mim(&mut w)?;

        if let Some(description) = self.description.as_ref() {
            writeln!(w, r#"(description "{}")"#, description.as_ref())?;
        }

        writeln!(w, r#"(title "{}")"#, *self.title)?;

        if !self.maps.is_empty() {
            writeln!(w, "(map")?;

            let mut inner = PadAdapter::wrap(&mut w);
            for map in &self.maps {
                map.write_mim(&mut inner)?;
            }

            writeln!(w, ")")?;
        }

        if !self.states.is_empty() {
            write!(w, "(state")?;

            let mut inner = PadAdapter::wrap(&mut w);
            for state in &self.states {
                state.write_mim(&mut inner)?;
            }

            writeln!(w, ")")?;
        }

        Ok(())
    }
}

impl ToMim for InputMethod {
    fn write_mim(&self, mut w: impl Write) -> Result<()> {
        write!(w, "(input-method")?;
        write!(w, " {}", self.language)?;
        write!(w, " {}", self.name)?;
        if let Some(extra_id) = self.extra_id.as_ref() {
            write!(w, " {}", extra_id)?;
        }
        if let Some(version) = self.version.as_ref() {
            write!(w, " {}", version)?;
        }
        writeln!(w, ")")?;
        Ok(())
    }
}

impl ToMim for Map {
    fn write_mim(&self, mut w: impl Write) -> Result<()> {
        write!(w, r"({}", self.name)?;

        let mut inner = PadAdapter::wrap(&mut w);
        for state in &self.rules {
            state.write_mim(&mut inner)?;
            writeln!(&mut inner)?;
        }

        writeln!(w, ")")?;

        Ok(())
    }
}

impl ToMim for Rule {
    fn write_mim(&self, mut w: impl Write) -> Result<()> {
        write!(w, "(")?;
        self.keyseq.write_mim(&mut w)?;
        write!(w, " ")?;
        self.action.write_mim(&mut w)?;
        write!(w, ")")?;

        Ok(())
    }
}

impl ToMim for KeySeq {
    fn write_mim(&self, mut w: impl Write) -> Result<()> {
        match self {
            KeySeq::Character(c) => write!(w, r#""{}""#, c.as_ref()),
            KeySeq::KeyCombo(s) => {
                write!(w, "(")?;
                s.write_mim(&mut w)?;
                write!(w, ")")?;
                Ok(())
            },
        }
    }
}

impl ToMim for MapAction {
    fn write_mim(&self, mut w: impl Write) -> Result<()> {
        match self {
            MapAction::Insert(i) => i.write_mim(&mut w),
        }
    }
}

impl ToMim for Insert {
    fn write_mim(&self, mut w: impl Write) -> Result<()> {
        match self {
            Insert::Character(c) => write!(w, r#""{}""#, c.as_ref()),
            Insert::CharacterCode(num) => write!(w, r#"{}"#, num.as_ref()),
        }
    }
}

impl ToMim for State {
    fn write_mim(&self, mut w: impl Write) -> Result<()> {
        write!(w, "({}", self.name)?;
        if let Some(title) = self.title.as_ref() {
            write!(w, " {}", title.as_ref())?;
        }

        let mut inner = PadAdapter::wrap(&mut w);
        for branch in &self.branches {
            branch.write_mim(&mut inner)?;
        }

        writeln!(w, ")")?;

        Ok(())
    }
}

impl ToMim for Branch {
    fn write_mim(&self, mut w: impl Write) -> Result<()> {
        write!(w, "{}", self.map_name)
    }
}

impl ToMim for KeyCombo {
    fn write_mim(&self, mut w: impl Write) -> Result<()> {
        for modifier in &self.modifiers {
            modifier.write_mim(&mut w)?;
            write!(w, "-")?;
        }
        self.key.write_mim(&mut w)?;
        Ok(())
    }
}

impl ToMim for KeyDef {
    fn write_mim(&self, mut w: impl Write) -> Result<()> {
        match self {
            KeyDef::CharacterCode(int) => write!(w, "{}", int.as_ref()),
            KeyDef::Character(sym) => write!(w, "{}", sym),
        }
    }
}

impl ToMim for Modifier {
    fn write_mim(&self, mut w: impl Write) -> Result<()> {
        match self {
            Modifier::Shift => write!(w, "S"),
            Modifier::Control => write!(w, "C"),
            Modifier::Meta => write!(w, "M"),
            Modifier::Alt => write!(w, "A"),
            Modifier::AltGr => write!(w, "G"),
            Modifier::Super => write!(w, "s"),
            Modifier::Hyper => write!(w, "H"),
        }
    }
}
