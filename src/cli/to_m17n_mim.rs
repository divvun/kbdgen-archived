use crate::{bundle::keys::KeyValue, m17n_mim::*, models::DesktopModes, Load, ProjectBundle};
use indexmap::IndexMap;
use log::{debug, log_enabled};
use std::{
    convert::TryFrom,
    fs::File,
    io::BufWriter,
    path::{Path, PathBuf},
};

pub fn kbdgen_to_mim(input: &Path, output: &Path) -> Result<(), Error> {
    // let _ = opts.verbose.setup_env_logger("kbdgen-cli");

    let bundle = ProjectBundle::load(input).map_err(|source| Error::CannotLoad { source })?;
    if log_enabled!(log::Level::Debug) {
        debug!("Bundle `{}` loaded", input.display());
        let locales = bundle
            .project
            .locales
            .values()
            .map(|l| l.name.as_str())
            .collect::<Vec<_>>();
        debug!("Bundle contains these locales: {:?}", locales);
    }

    bundle
        .layouts
        .iter()
        .map(|(name, layout)| (name, layout_to_mim(&name, layout, &bundle)))
        .try_for_each(|(name, keyboards)| {
            for (platform, keyboard) in keyboards? {
                let path = output.join(name).join(platform).with_extension("mim");
                std::fs::create_dir_all(path.parent().unwrap()).map_err(|source| {
                    SavingError::CannotCreateFile {
                        path: path.clone(),
                        source,
                    }
                })?;
                let file = File::create(&path).map_err(|source| SavingError::CannotCreateFile {
                    path: path.clone(),
                    source,
                })?;
                debug!("Created file `{}`", path.display());
                let mut writer = BufWriter::new(file);
                keyboard
                    .write_mim(&mut writer)
                    .map_err(|source| SavingError::CannotSerializeMim { source })?;
                log::info!("Wrote to file `{}`", path.display());
            }
            Ok(())
        })
        .map_err(|source| Error::CannotBeSaved { source })?;

    Ok(())
}

fn layout_to_mim(
    name: &str,
    layout: &crate::models::Layout,
    project: &crate::ProjectBundle,
) -> Result<Vec<(String, Root)>, SavingError> {
    log::debug!("to mim with you, {}!", name);
    let mut res = vec![];

    macro_rules! mode {
        (desktop: $platform:ident) => {
            mode!(desktop_mode_to_keyboard -> $platform)
        };
        ($fn:ident -> $platform:ident) => {
            if let Some(a) = layout.modes.$platform.as_ref() {
                log::debug!("{}: check", stringify!($platform));
                let dead_key_rules = dead_key_transforms(&layout, stringify!($platform))
                    .map_err(|source| SavingError::CannotCreateTransformMap {source})?;

                res.push((
                    String::from(stringify!($platform)),
                    $fn(name, stringify!($platform), a, dead_key_rules, project)?,
                ));
            }
        };
    }

    mode!(desktop: win);
    mode!(desktop: mac);
    mode!(desktop: chrome);
    mode!(desktop: x11);
    mode!(desktop: desktop);

    Ok(res)
}

fn desktop_mode_to_keyboard(
    name: &str,
    target: &str,
    desktop: &DesktopModes,
    dead_key_transforms: Vec<Rule>,
    project: &crate::ProjectBundle,
) -> Result<Root, SavingError> {
    let mut rules = vec![];
    let mim_config = project.targets.mim.as_ref();

    for (key_combo, mapping) in &desktop.0 {
        let key_combo = if key_combo == "default" {
            vec![]
        } else {
            Modifier::parse_keycombo(&key_combo)
                .map_err(|source| SavingError::CannotSerializeKeyCombo { source })?
        };

        for (iso_key, key_val) in mapping.iter() {
            // At least on Ubuntu 19.04, using the symbol name for key combos
            // with no modifier didn't trigger. Thus, we'll have to use the
            // keycode here.
            let key_code = if key_combo.is_empty() {
                KeyDef::CharacterCode(
                    Integer::try_from(format!("{:#x}", iso_key.to_character_code()))
                        .map_err(|source| SavingError::CannotSerializeInteger { source })?,
                )
            } else {
                KeyDef::Character(
                    Symbol::try_from(format!("{}", iso_key.to_character()))
                        .map_err(|source| SavingError::CannotSerializeSymbol { source })?,
                )
            };

            let keyseq = KeySeq::KeyCombo(KeyCombo {
                modifiers: key_combo.clone(),
                key: key_code,
            });

            if let KeyValue::Symbol(key) = key_val {
                if key.is_empty() {
                    continue;
                }
                if key == " " {
                    continue;
                }

                rules.push(Rule {
                    keyseq,
                    action: MapAction::Insert(Insert::Character(
                        Text::try_from(key.to_string())
                            .map_err(|source| SavingError::CannotSerializeSymbol { source })?,
                    )),
                });
            }
        }
    }

    // TODO: Add map for space transforms
    rules.extend(dead_key_transforms);

    Ok(Root {
        input_method: InputMethod {
            // TODO: Convert language code automatically
            // cf. https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
            language: Symbol::try_from(
                mim_config
                    .map(|x| x.language_code.clone())
                    .unwrap_or_else(|| name.to_string()),
            )
            .map_err(|source| SavingError::CannotSerializeSymbol { source })?,
            name: Symbol::try_from(format!("{}-kbdgen", target))
                .map_err(|source| SavingError::CannotSerializeSymbol { source })?,
            extra_id: None,
            version: None,
        },
        title: Text::try_from(name.to_string())
            .map_err(|source| SavingError::CannotSerializeSymbol { source })?,
        description: if let Some(d) = mim_config.and_then(|x| x.description.as_ref()) {
            Some(
                Text::try_from(format!("{} ({} {})", d, name, target))
                    .map_err(|source| SavingError::CannotSerializeSymbol { source })?,
            )
        } else {
            None
        },
        maps: vec![Map {
            name: Symbol::try_from(String::from("mapping"))
                .map_err(|source| SavingError::CannotSerializeSymbol { source })?,
            rules,
        }],
        // (state (init (mapping)))
        states: vec![State {
            name: Symbol::try_from("init".to_string())
                .map_err(|source| SavingError::CannotSerializeSymbol { source })?,
            title: None,
            branches: vec![Branch {
                map_name: Symbol::try_from("mapping".to_string())
                    .map_err(|source| SavingError::CannotSerializeSymbol { source })?,
            }],
        }],
    })
}

/// Combine dead keys with transforms
///
/// Generates MIM rules in the style of `(("´" "a") "á")`.
fn dead_key_transforms(
    layout: &crate::models::Layout,
    platform: &str,
) -> Result<Vec<Rule>, MimConversion> {
    let mut rules = vec![];

    let empty_dead_keys = IndexMap::new();
    let empty_transforms = IndexMap::new();

    let dead_key_map = layout
        .dead_keys
        .as_ref()
        .and_then(|dead_keys| dead_keys.get(platform))
        .unwrap_or_else(|| &empty_dead_keys);
    let transforms = layout
        .transforms
        .as_ref()
        .unwrap_or_else(|| &empty_transforms);

    let dead_keys = dead_key_map.iter().flat_map(|(_modifier, keys)| keys);

    for first_key in dead_keys {
        let mapping = match transforms.get(first_key) {
            Some(map) => map,
            None => {
                log::warn!(
                    "dead key map for `{}` contains `{}` but no transforms found",
                    platform,
                    first_key
                );
                continue;
            }
        };

        for (second_key, transformed_char) in mapping {
            rules.push(Rule {
                keyseq: KeySeq::Character(Text::try_from(format!("{}{}", first_key, second_key))?),
                action: MapAction::Insert(Insert::Character(Text::try_from(
                    transformed_char.to_string(),
                )?)),
            });
        }
    }

    Ok(rules)
}

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("Could not load kbdgen bundle")]
    CannotLoad { source: crate::LoadError },
    #[error("Could not write CLDR file")]
    CannotBeSaved { source: SavingError },
}

#[derive(Debug, thiserror::Error)]
pub enum SavingError {
    #[error("Could not create file `{}`", path.display())]
    CannotCreateFile {
        path: PathBuf,
        source: std::io::Error,
    },
    #[error("Could not transform to MIM")]
    CannotSerializeMim { source: std::io::Error },
    #[error("Could not serialize MIM symbol")]
    CannotSerializeSymbol { source: MimConversion },
    #[error("Could not serialize MIM integer")]
    CannotSerializeInteger { source: MimConversion },
    #[error("Could not serialize key combo")]
    CannotSerializeKeyCombo { source: MimConversion },
    #[error("Invalid character code index")]
    InvalidCharacterCodeIndex { source: MimConversion },
    #[error("Cannot create transform map")]
    CannotCreateTransformMap { source: MimConversion },
}
