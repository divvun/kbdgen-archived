/// Render some nice human-readable asciidoc files
// TODO: unescape quotes in docs
// TODO: Render types nicely
use crate::collect_docs::{Field, Struct, Type};
use std::io::{Result, Write};

pub trait ToAdoc {
    fn write_adoc(&self, w: impl Write) -> Result<()>;
}

impl ToAdoc for Struct {
    fn write_adoc(&self, mut w: impl Write) -> Result<()> {
        writeln!(w, "= {}", self.name)?;
        writeln!(w)?;
        writeln!(w, "{}", self.docs)?;
        writeln!(w)?;
        writeln!(w, ".Fields")?;
        writeln!(w)?;

        for field in &self.fields {
            field.write_adoc(&mut w)?;
        }

        Ok(())
    }
}

impl ToAdoc for Field {
    fn write_adoc(&self, mut w: impl Write) -> Result<()> {
        write!(w, "* `{}`, ", self.name)?;
        if !self.required {
            write!(w, "optional ")?;
        }
        self.r#type.write_adoc(&mut w)?;
        writeln!(w)?;

        let docs = self.docs.replace("\n\n", "\n+\n");
        if !docs.is_empty() {
            writeln!(w, "+")?;
            writeln!(w, "{}", docs)?;
        }

        Ok(())
    }
}

impl ToAdoc for Type {
    fn write_adoc(&self, mut w: impl Write) -> Result<()> {
        match self {
            Type::Primitive(name) => write!(w, "`{}`", name),
            Type::Link(name) => write!(w, "<<{}>>", name),
        }
    }
}
