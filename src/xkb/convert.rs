use super::{Group, Key, Symbols, XkbKeySym};
use crate::{models::{DesktopModes, Layout}, utils::UnwrapOrUnknownExt};
use snafu::{OptionExt, Snafu};
use std::convert::TryFrom;

impl TryFrom<Layout> for Symbols {
    type Error = Error;

    fn try_from(layout: Layout) -> Result<Self, Self::Error> {
        Ok(Symbols {
            name: layout.name().unwrap_or_else(|| "<unknown>".into()),
            groups: collect_groups(&layout)?,
        })
    }
}

fn collect_groups(layout: &Layout) -> Result<Vec<Group>, Error> {
    let key_def = layout
        .modes
        .x11
        .as_ref()
        .or(layout.modes.win.as_ref())
        .context(NoXkbCompatibleModes {
            available_modes: layout.modes.available_modes(),
        })?;

    Ok(vec![Group {
        name: layout.name().unwrap_or_unknown(),
        leading_includes: vec![],
        keys: collect_keys(&key_def)?,
        trailing_includes: vec![],
    }])
}

fn collect_keys(key_map: &DesktopModes) -> Result<Vec<Key>, Error> {
    let default = key_map.get("default").cloned().context(NoDefaultKeyMap)?;
    let shift = key_map.get("shift").cloned().unwrap_or_default();
    let alt = key_map.get("alt").cloned().unwrap_or_default();
    let alt_shift = key_map.get("alt_shift").cloned().unwrap_or_default();

    let mut res = Vec::new();

    for (iso_code, default) in &*default {
        res.push(Key {
            iso_code: iso_code.to_string(),
            default: default.0.clone(),
            shift: shift.get_string(&iso_code),
            alt: alt.get_string(&iso_code),
            alt_shift: alt_shift.get_string(&iso_code),
        });
    }

    Ok(res)
}

#[derive(Snafu, Debug)]
pub enum Error {
    #[snafu(display("No `default` keymap"))]
    NoDefaultKeyMap { backtrace: snafu::Backtrace },
    #[snafu(display("No XKB compatible modes, found: {}", available_modes.join(", ")))]
    NoXkbCompatibleModes {
        available_modes: Vec<String>,
        backtrace: snafu::Backtrace,
    },
}
