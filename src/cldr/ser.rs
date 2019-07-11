use super::*;
use pad::PadAdapter;
use std::io::{Result, Write};
use xml::escape::escape_str_attribute as escape;

pub trait ToXml {
    fn write_xml(&self, w: impl Write) -> Result<()>;
}

impl ToXml for Keyboard {
    fn write_xml(&self, mut w: impl Write) -> Result<()> {
        writeln!(w, r#"<?xml version="1.0" encoding="UTF-8" ?>"#)?;
        writeln!(w, r#"<!DOCTYPE keyboard SYSTEM "../dtd/ldmlKeyboard.dtd">"#)?;
        writeln!(w, r#"<keyboard locale="{}">"#, escape(&self.locale))?;

        let mut inner = PadAdapter::wrap(&mut w);
        self.version.write_xml(&mut inner)?;
        for names in &self.names {
            names.write_xml(&mut inner)?;
        }
        for keymap in &self.key_maps {
            keymap.write_xml(&mut inner)?;
        }

        writeln!(w, "</keyboard>")?;
        Ok(())
    }
}

impl ToXml for Version {
    fn write_xml(&self, mut w: impl Write) -> Result<()> {
        writeln!(
            w,
            r#"<version platform="{}" number="{}"/>"#,
            escape(&self.platform),
            escape(&self.number)
        )
    }
}

impl ToXml for Names {
    fn write_xml(&self, mut w: impl Write) -> Result<()> {
        writeln!(w, "<names>")?;

        let mut inner = PadAdapter::wrap(&mut w);
        for name in &self.values {
            name.write_xml(&mut inner)?;
        }

        writeln!(w, "</names>")?;
        Ok(())
    }
}

impl ToXml for Name {
    fn write_xml(&self, mut w: impl Write) -> Result<()> {
        writeln!(w, r#"<name value="{}"/>"#, self.value)
    }
}

impl ToXml for KeyMap {
    fn write_xml(&self, mut w: impl Write) -> Result<()> {
        write!(w, "<keyMap")?;
        if let Some(modifiers) = self.modifiers.as_ref() {
            write!(w, r#" modifiers="{}""#, escape(&modifiers))?;
        }
        writeln!(w, ">")?;

        let mut inner = PadAdapter::wrap(&mut w);
        for key in &self.keys {
            key.write_xml(&mut inner)?;
        }

        writeln!(w, "</keyMap>")?;
        Ok(())
    }
}

impl ToXml for Map {
    fn write_xml(&self, mut w: impl Write) -> Result<()> {
        write!(w, r#"<map"#)?;
        write!(w, r#" iso="{}""#, escape(&self.iso))?;
        write!(w, r#" to="{}""#, escape(&self.to))?;
        if let Some(transform) = self.transform.as_ref() {
            write!(w, r#" transform="{}""#, escape(&transform))?;
        }
        if let Some(long_press) = self.long_press.as_ref() {
            write!(w, r#" longPress="{}""#, escape(&long_press))?;
        }
        writeln!(w, r#"/>"#)?;

        Ok(())
    }
}

// adopted from libcore's `fmt/builders.rs`
pub(crate) mod pad {
    use std::io::{Result, Write};

    /// Indents all lines written to this by four spaces
    pub(crate) struct PadAdapter<'a> {
        buf: &'a mut (dyn Write + 'a),
        on_newline: bool,
    }

    impl<'a> PadAdapter<'a> {
        pub(crate) fn wrap<'fmt: 'a>(buf: &'fmt mut (dyn Write + 'a)) -> Self {
            PadAdapter {
                buf,
                on_newline: true,
            }
        }
    }

    impl Write for PadAdapter<'_> {
        fn write(&mut self, mut s: &[u8]) -> Result<usize> {
            let len = s.len();
            while !s.is_empty() {
                if self.on_newline {
                    self.buf.write_all(b"    ")?;
                }

                let split = match s.iter().enumerate().find(|(_, byte)| **byte == b'\n') {
                    Some((pos, _)) => {
                        self.on_newline = true;
                        pos + 1
                    }
                    None => {
                        self.on_newline = false;
                        s.len()
                    }
                };
                self.buf.write_all(&s[..split])?;
                s = &s[split..];
            }

            Ok(len)
        }

        fn flush(&mut self) -> Result<()> {
            Ok(())
        }
    }
}
