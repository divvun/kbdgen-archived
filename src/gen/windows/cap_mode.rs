use std::fmt::Display;

use super::layout::Row;

#[derive(Debug, Clone, PartialEq, Eq)]
pub(super) enum CapMode {
    SGCap,
    Column(u8),
}

impl CapMode {
    pub fn is_sgcap(&self) -> bool {
        match self {
            CapMode::SGCap => true,
            CapMode::Column(_) => false,
        }
    }
}

impl Display for CapMode {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            CapMode::SGCap => f.write_str("SGCap"),
            CapMode::Column(c) => f.write_fmt(format_args!("{}", c)),
        }
    }
}

pub(super) fn derive_cap_mode(row: &Row) -> CapMode {
    if !row.caps.is_none() && row.default != row.caps && row.shift != row.caps {
        return CapMode::SGCap;
    } else if row.caps.is_none() {
        let mut c = 0;
        if row.default != row.shift {
            c += 1;
        }
        if row.alt != row.alt_shift {
            c += 4;
        }
        CapMode::Column(c)
    } else {
        let mut c = 0;
        if row.caps == row.shift {
            c += 1;
        }
        if row.alt_caps == row.alt_shift {
            c += 4;
        }
        CapMode::Column(c)
    }
}
