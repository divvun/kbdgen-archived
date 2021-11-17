use std::fmt::Display;

use super::cap_mode::CapMode;

#[derive(Debug, Clone, PartialEq, Eq)]
pub(super) struct Ligature {
    pub vk: &'static str,
    pub cap_mode: CapMode,
    pub bytes: Vec<u16>,
}

pub(super) struct LigatureSection {
    pub ligatures: Vec<Ligature>,
}

impl Display for LigatureSection {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        if self.ligatures.is_empty() {
            return Ok(());
        }

        f.write_str("LIGATURE\n\n")?;
        for l in &self.ligatures {
            f.write_fmt(format_args!("{}\t{}", l.vk, l.cap_mode))?;
            for b in &l.bytes {
                f.write_fmt(format_args!("\t{:04x}", b))?;
            }
            f.write_str("\n")?;
        }
        Ok(())
    }
}
