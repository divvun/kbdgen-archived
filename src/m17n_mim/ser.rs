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
            writeln!(w, "(map ")?;

            let mut inner = PadAdapter::wrap(&mut w);
            for map in &self.maps {
                map.write_mim(&mut inner)?;
            }

            writeln!(w, ")")?;
        }

        if !self.states.is_empty() {
            writeln!(w, "(state ")?;

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
        writeln!(w, "(input-method")?;
        writeln!(w, " {}", self.language)?;
        writeln!(w, " {}", self.name)?;
        if let Some(extra_id) = self.extra_id.as_ref() {
            writeln!(w, " {}", extra_id)?;
        }
        if let Some(version) = self.version.as_ref() {
            writeln!(w, " {}", version)?;
        }
        writeln!(w, ")")?;
        Ok(())
    }
}

impl ToMim for Map {
    fn write_mim(&self, mut w: impl Write) -> Result<()> {
        writeln!(w, r"({}", self.name)?;

        let mut inner = PadAdapter::wrap(&mut w);
        for state in &self.rules {
            state.write_mim(&mut inner)?;
        }

        writeln!(w, ")")?;

        Ok(())
    }
}

impl ToMim for Rule {
    fn write_mim(&self, mut w: impl Write) -> Result<()> {
        writeln!(w, "(")?;
        self.keyseq.write_mim(&mut w)?;
        writeln!(w, " ")?;
        self.action.write_mim(&mut w)?;
        writeln!(w, ")")?;

        Ok(())
    }
}

impl ToMim for KeySeq {
    fn write_mim(&self, mut w: impl Write) -> Result<()> {
        match self {
            KeySeq::Character(c) => writeln!(w, r#""{}""#, c.as_ref()),
            KeySeq::CharacterCode(num) => writeln!(w, r#"{}"#, num.as_ref()),
            KeySeq::KeyCombo(s) => {
                writeln!(w, "(")?;
                s.write_mim(&mut w)?;
                writeln!(w, ")")?;
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
            Insert::Character(c) => writeln!(w, r#""{}""#, c.as_ref()),
            Insert::CharacterCode(num) => writeln!(w, r#"{}"#, num.as_ref()),
        }
    }
}

impl ToMim for State {
    fn write_mim(&self, mut w: impl Write) -> Result<()> {
        writeln!(w, "({}", self.name)?;
        if let Some(title) = self.title.as_ref() {
            writeln!(w, " {}", title.as_ref())?;
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
        writeln!(w, "{}", self.map_name)
    }
}

impl ToMim for KeyCombo {
    fn write_mim(&self, mut w: impl Write) -> Result<()> {
        for modifier in &self.modifiers {
            modifier.write_mim(&mut w)?;
            writeln!(w, "-")?;
        }
        writeln!(w, "{}", self.key.as_ref())?;
        Ok(())
    }
}

impl ToMim for Modifier {
    fn write_mim(&self, mut w: impl Write) -> Result<()> {
        match self {
            Modifier::Shift => writeln!(w, "S"),
            Modifier::Control => writeln!(w, "C"),
            Modifier::Meta => writeln!(w, "M"),
            Modifier::Alt => writeln!(w, "A"),
            Modifier::AltGr => writeln!(w, "G"),
            Modifier::Super => writeln!(w, "s"),
            Modifier::Hyper => writeln!(w, "H"),
        }
    }
}
