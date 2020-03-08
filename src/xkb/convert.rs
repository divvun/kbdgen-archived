use super::{Key, Symbols, XkbFile, XkbKeySym};
use crate::{
    models::{DesktopModes, Layout},
    utils::UnwrapOrUnknownExt,
};
use snafu::{OptionExt, Snafu};

impl XkbFile {
    pub fn from_layout(name: &str, layout: Layout) -> Result<Self, Error> {
        let mut modes = vec![
            layout.modes.x11.clone().map(|x| ("x11", x)),
            layout.modes.win.clone().map(|x| ("win", x)),
            layout.modes.mac.clone().map(|x| ("mac", x)),
            layout.modes.chrome.clone().map(|x| ("chrome", x)),
        ]
        .into_iter()
        .flatten();

        let default = modes
            .next()
            .map(|(target, mode)| {
                Ok(Symbols {
                    id: "basic".to_string(),
                    name: format!("{} ({})", layout.name().unwrap_or_unknown(), target),
                    leading_includes: vec!["latin".to_string()],
                    keys: collect_keys(&mode, None)?,
                    trailing_includes: vec!["level3(ralt_switch)".to_string()],
                })
            })
            .context(NoXkbCompatibleModes {
                available_modes: layout.modes.available_modes(),
            })??;

        let others = modes
            .map(|(target, mode)| {
                Ok(Symbols {
                    id: target.to_string(),
                    name: format!("{} ({})", layout.name().unwrap_or_unknown(), target),
                    leading_includes: vec!["latin".to_string(), format!("{}(basic)", name)],
                    keys: collect_keys(&mode, Some(&default))?,
                    trailing_includes: vec!["level3(ralt_switch)".to_string()],
                })
            })
            .collect::<Result<Vec<Symbols>, Error>>()?;

        Ok(XkbFile { default, others })
    }
}

fn collect_keys(key_map: &DesktopModes, default: Option<&Symbols>) -> Result<Vec<Key>, Error> {
    let default = key_map.get("default").cloned().context(NoDefaultKeyMap)?;
    let shift = key_map.get("shift").cloned().unwrap_or_default();
    let alt = key_map.get("alt").cloned().unwrap_or_default();
    let alt_shift = key_map.get("alt_shift").cloned().unwrap_or_default();

    let mut res = Vec::new();

    for (iso_code, default) in &*default {
        res.push(Key {
            iso_code: iso_code.to_string(),
            default: default.0.clone().map(|x| XkbKeySym(x)),
            shift: shift.get_string(&iso_code).map(|x| XkbKeySym(x)),
            alt: alt.get_string(&iso_code).map(|x| XkbKeySym(x)),
            alt_shift: alt_shift.get_string(&iso_code).map(|x| XkbKeySym(x)),
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
