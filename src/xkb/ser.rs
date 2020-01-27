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
        writeln!(
            w,
            r#"key <{iso_code}> {{[ {default} {shift} {alt} {alt_shift} ]}};"#,
            iso_code = self.iso_code,
            default = self.default.clone().unwrap_or_default(),
            shift = self.shift.clone().unwrap_or_default(),
            alt = self.alt.clone().unwrap_or_default(),
            alt_shift = self.alt_shift.clone().unwrap_or_default(),
        )?;

        Ok(())
    }
}
