use super::{Group, Key, Symbols};
use crate::pad::PadAdapter;
use std::io::{Result, Write};

pub trait ToXkb {
    fn write_xkb(&self, w: impl Write) -> Result<()>;
}

impl ToXkb for Symbols {
    fn write_xkb(&self, mut w: impl Write) -> Result<()> {
        writeln!(w, r#"default partial alphanumeric_keys"#)?;
        writeln!(w, r#"xkb_symbols "basic" {{"#)?;

        let mut inner = PadAdapter::wrap(&mut w);
        writeln!(&mut inner, r#"include "latin""#)?;
        writeln!(&mut inner)?;

        for group in &self.groups {
            group.write_xkb(&mut inner)?;
        }

        writeln!(w, r#"}}"#)?;
        writeln!(w)?;

        Ok(())
    }
}

impl ToXkb for Group {
    fn write_xkb(&self, mut w: impl Write) -> Result<()> {
        writeln!(w, r#"name[Group1] = "{}";"#, self.name)?;
        writeln!(w)?;

        let mut inner = PadAdapter::wrap(&mut w);
        for include in &self.leading_includes {
            writeln!(&mut inner, r#"include "{}""#, include)?;
        }
        if !self.leading_includes.is_empty() {
            writeln!(w)?;
        }

        let mut inner = PadAdapter::wrap(&mut w);
        for key in &self.keys {
            key.write_xkb(&mut inner)?;
        }

        let mut inner = PadAdapter::wrap(&mut w);
        for include in &self.trailing_includes {
            writeln!(&mut inner, r#"include "{}""#, include)?;
        }

        Ok(())
    }
}

impl ToXkb for Key {
    fn write_xkb(&self, mut w: impl Write) -> Result<()> {
        write!(w, "key <{}> {{[ ", self.iso_code)?;

        /// Since modifiers are ordered, we need to make sure we don't continue
        /// emitting them when the previous one was empty.
        fn collect_keys(key: &Key, mut w: impl Write) -> Result<()> {
            if let Some(k) = &key.default {
                write!(w, "{}, ", k)?;
            } else {
                return Ok(());
            }
            if let Some(k) = &key.shift {
                write!(w, "{}, ", k)?;
            } else {
                return Ok(());
            }
            if let Some(k) = &key.alt {
                write!(w, "{}, ", k)?;
            } else {
                return Ok(());
            }
            if let Some(k) = &key.alt_shift {
                write!(w, "{}", k)?;
            } else {
                return Ok(());
            }
            Ok(())
        }

        collect_keys(self, &mut w)?;

        write!(w, " ]}};")?;
        writeln!(w)?;

        Ok(())
    }
}
