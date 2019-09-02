use kbdgen::{m17n_mim::*, models::DesktopModes, Load, ProjectBundle};
use log::{debug, log_enabled};
use snafu::{ResultExt, Snafu};
use snafu_cli_debug::SnafuCliDebug;
use std::{collections::BTreeMap, convert::TryFrom, fs::File, io::BufWriter, path::PathBuf};
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
pub struct Cli {
    #[structopt(parse(from_os_str))]
    input: PathBuf,

    #[structopt(parse(from_os_str))]
    output: PathBuf,

    #[structopt(flatten)]
    verbose: clap_verbosity_flag::Verbosity,
}

pub fn kbdgen_to_mim(opts: &Cli) -> Result<(), Error> {
    let _ = opts.verbose.setup_env_logger("kbdgen-cli");

    let bundle = ProjectBundle::load(&opts.input).context(CannotLoad)?;
    if log_enabled!(log::Level::Debug) {
        debug!("Bundle `{}` loaded", opts.input.display());
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
                let path = &opts.output.join(name).join(platform).with_extension("mim");
                std::fs::create_dir_all(path.parent().unwrap())
                    .context(CannotCreateFile { path })?;
                let file = File::create(path).context(CannotCreateFile { path })?;
                debug!("Created file `{}`", path.display());
                let mut writer = BufWriter::new(file);
                keyboard
                    .write_mim(&mut writer)
                    .context(CannotSerializeMim)?;
                log::info!("Wrote to file `{}`", path.display());
            }
            Ok(())
        })
        .context(CannotBeSaved)?;

    Ok(())
}

fn layout_to_mim(
    name: &str,
    layout: &kbdgen::models::Layout,
    _project: &kbdgen::ProjectBundle,
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
                    .context(CannotCreateTransformMap)?;

                res.push((
                    String::from(stringify!($platform)),
                    $fn(name, stringify!($platform), a, dead_key_rules)?,
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
) -> Result<Root, SavingError> {
    let mut rules = vec![];

    for (key_combo, mapping) in desktop {
        let key_combo = if key_combo == "default" {
            vec![]
        } else {
            Modifier::parse_keycombo(key_combo).context(CannotSerializeKeyCombo)?
        };

        for (iso_key, key_val) in mapping.iter() {
            let key_code = KeyDef::CharacterCode(
                Integer::try_from(format!("{:#x}", iso_key.to_character_code()))
                    .context(InvalidCharacterCodeIndex)?,
            );

            let keyseq = KeySeq::KeyCombo(KeyCombo {
                modifiers: key_combo.clone(),
                key: key_code,
            });

            if let Some(key) = key_val.0.as_ref() {
                rules.push(Rule {
                    keyseq,
                    action: MapAction::Insert(Insert::Character(
                        Text::try_from(key.to_string()).context(CannotSerializeSymbol)?,
                    )),
                });
            }
        }
    }

    // TODO: Add map for space transforms
    rules.extend(dead_key_transforms);

    Ok(Root {
        input_method: InputMethod {
            language: Symbol::try_from(name.to_string()).context(CannotSerializeSymbol)?,
            name: Symbol::try_from(name.to_string()).context(CannotSerializeSymbol)?,
            extra_id: None,
            version: None,
        },
        title: Text::try_from(name.to_string()).context(CannotSerializeSymbol)?,
        description: Some(
            Text::try_from(format!("{} ({})", name, target)).context(CannotSerializeSymbol)?,
        ),
        maps: vec![Map {
            name: Symbol::try_from(String::from("mapping")).context(CannotSerializeSymbol)?,
            rules,
        }],
        // (state (init (mapping)))
        states: vec![State {
            name: Symbol::try_from("init".to_string()).context(CannotSerializeSymbol)?,
            title: None,
            branches: vec![Branch {
                map_name: Symbol::try_from("mapping".to_string()).context(CannotSerializeSymbol)?,
            }],
        }],
    })
}

/// Combine dead keys with transforms
///
/// Generates MIM rules in the style of `(("´" "a") "á")`.
fn dead_key_transforms(
    layout: &kbdgen::models::Layout,
    platform: &str,
) -> Result<Vec<Rule>, MimConversion> {
    let mut rules = vec![];

    let empty_dead_keys = BTreeMap::new();
    let empty_transforms = BTreeMap::new();

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

#[derive(Snafu, SnafuCliDebug)]
pub enum Error {
    #[snafu(display("Could not load kbdgen bundle"))]
    CannotLoad {
        source: kbdgen::LoadError,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("Could not write CLDR file"))]
    CannotBeSaved {
        source: SavingError,
        backtrace: snafu::Backtrace,
    },
}

#[derive(Snafu, Debug)]
pub enum SavingError {
    #[snafu(display("Could not create file `{}`", path.display()))]
    CannotCreateFile {
        path: PathBuf,
        source: std::io::Error,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("Could transform to MIM"))]
    CannotSerializeMim {
        source: std::io::Error,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("Could serialize MIM symbol"))]
    CannotSerializeSymbol {
        source: MimConversion,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("Could serialize key combo"))]
    CannotSerializeKeyCombo {
        source: MimConversion,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("Invalid character code index"))]
    InvalidCharacterCodeIndex {
        source: MimConversion,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("Cannot create transform map"))]
    CannotCreateTransformMap {
        source: MimConversion,
        backtrace: snafu::Backtrace,
    },
}
