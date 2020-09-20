use super::{Key, Symbols, XkbFile, XkbKeySym};
use crate::{
    bundle::keys::KeyValue,
    models::{DesktopModes, Layout},
    utils::UnwrapOrUnknownExt,
};
use std::collections::BTreeMap;

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
            .ok_or_else(|| Error::NoXkbCompatibleModes {
                available_modes: layout.modes.available_modes(),
            })??;

        let mut others = modes
            .map(|(target, mode)| {
                Ok(Symbols {
                    id: target.to_string(),
                    name: format!("{} ({})", layout.name().unwrap_or_unknown(), target),
                    leading_includes: vec![format!("{}(basic)", name)],
                    keys: collect_keys(&mode, Some(&default))?,
                    trailing_includes: vec!["level3(ralt_switch)".to_string()],
                })
            })
            .collect::<Result<Vec<Symbols>, Error>>()?;

        if let Some(dead_keys) = layout.dead_keys.as_ref() {
            for (target, mode_keys) in dead_keys {
                let parent =
                    match target.as_str() {
                        "x11" => layout.modes.x11.as_ref().ok_or(
                            Error::DeadKeysForUnconfiguredTarget {
                                target: target.clone(),
                            },
                        )?,
                        "win" => layout.modes.win.as_ref().ok_or(
                            Error::DeadKeysForUnconfiguredTarget {
                                target: target.clone(),
                            },
                        )?,
                        "mac" => layout.modes.mac.as_ref().ok_or(
                            Error::DeadKeysForUnconfiguredTarget {
                                target: target.clone(),
                            },
                        )?,
                        "chrome" => layout.modes.chrome.as_ref().ok_or(
                            Error::DeadKeysForUnconfiguredTarget {
                                target: target.clone(),
                            },
                        )?,
                        _ => continue,
                    };

                others.push(Symbols {
                    id: format!("{}_deadkeys", target.to_string()),
                    name: format!(
                        "{} ({}) (dead keys)",
                        layout.name().unwrap_or_unknown(),
                        target
                    ),
                    leading_includes: vec![format!("{}({})", name, target)],
                    keys: collect_dead_keys(&mode_keys, parent)?,
                    trailing_includes: vec![],
                });
            }
        }

        Ok(XkbFile { default, others })
    }
}

fn collect_keys(key_map: &DesktopModes, _default: Option<&Symbols>) -> Result<Vec<Key>, Error> {
    let default = key_map
        .get("default")
        .cloned()
        .ok_or(Error::NoDefaultKeyMap)?;
    let shift = key_map.get("shift").cloned().unwrap_or_default();
    let alt = key_map.get("alt").cloned().unwrap_or_default();
    let alt_shift = key_map.get("alt+shift").cloned().unwrap_or_default();

    let mut res = Vec::new();

    for (iso_code, default) in &*default {
        res.push(Key {
            iso_code: iso_code.to_string(),
            default: if let KeyValue::Symbol(s) = default {
                Some(XkbKeySym(s.to_owned()))
            } else {
                None
            },
            shift: shift.get_string(*iso_code).map(XkbKeySym),
            alt: alt.get_string(*iso_code).map(XkbKeySym),
            alt_shift: alt_shift.get_string(*iso_code).map(XkbKeySym),
        });
    }

    Ok(res)
}

fn collect_dead_keys(
    key_map: &BTreeMap<String, Vec<String>>,
    parent: &DesktopModes,
) -> Result<Vec<Key>, Error> {
    fn char_to_dead(c: &str) -> Option<char> {
        let c = c.chars().next().expect("keysym can't be empty");
        let original = x11_keysymdef::lookup_by_codepoint(c)?;
        let name = original.names.get(0)?;
        let dead = format!("dead_{}", name);
        if let Some(record) = x11_keysymdef::lookup_by_name(&dead) {
            Some(record.unicode)
        } else {
            None
        }
    }

    let default = parent
        .get("default")
        .cloned()
        .ok_or(Error::NoDefaultKeyMap)?;
    let shift = parent.get("shift").cloned().unwrap_or_default();
    let alt = parent.get("alt").cloned().unwrap_or_default();
    let alt_shift = parent.get("alt_shift").cloned().unwrap_or_default();

    let mut overwritten_keys = BTreeMap::new();

    for (mode, map) in key_map {
        let parent_key = parent
            .get(mode)
            .expect("dead keys only defined for know modes");
        for key in map {
            let (iso_code, value) = parent_key
                .iter()
                .find(|(_iso, value)| match value {
                    KeyValue::Symbol(value) => key == value,
                    _ => false,
                })
                .expect("dead key not in parent mode");
            let value = value.to_string();

            let mut key = overwritten_keys.entry(iso_code).or_insert_with(|| Key {
                iso_code: iso_code.to_string(),
                default: default.get_string(*iso_code).map(XkbKeySym),
                shift: shift.get_string(*iso_code).map(XkbKeySym),
                alt: alt.get_string(*iso_code).map(XkbKeySym),
                alt_shift: alt_shift.get_string(*iso_code).map(XkbKeySym),
            });
            let dead = char_to_dead(&value).map(|x| XkbKeySym(x.to_string()));
            let dead = if let Some(x) = dead {
                x
            } else {
                log::warn!(
                    "while generating XKB dead key block: `{}` cannot be turned into a dead key",
                    value
                );
                continue;
            };

            match mode.as_str() {
                "default" => key.default = Some(dead),
                "shift" => key.shift = Some(dead),
                "alt" => key.alt = Some(dead),
                "alt+shift" => key.alt_shift = Some(dead),
                _ => {}
            }
        }
    }

    Ok(overwritten_keys
        .into_iter()
        .map(|(_iso, val)| val)
        .collect())
}

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("No `default` keymap")]
    NoDefaultKeyMap,
    #[error("No XKB compatible modes, found: {}", available_modes.join(", "))]
    NoXkbCompatibleModes { available_modes: Vec<String> },
    #[error("Cannot set dead keys for unconfigured target `{}`", target)]
    DeadKeysForUnconfiguredTarget { target: String },
}
