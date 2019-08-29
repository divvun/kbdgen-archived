use kbdgen::{
    m17n_mim::*,
    models::{DesktopModes, MobileModes},
    Load, ProjectBundle,
};
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
    log::debug!("to cldr with you, {}!", name);

    let mut res = vec![];

    macro_rules! mode {
        (desktop: $name:ident) => {
            mode!(desktop_mode_to_keyboard -> $name)
        };
        ($fn:ident -> $name:ident) => {
            if let Some(a) = layout.modes.$name.as_ref() {
                log::debug!("{}: check", stringify!($name));
                res.push((
                    String::from(stringify!($name)),
                    $fn(name, stringify!($name), a, layout)?,
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
    layout: &kbdgen::models::Layout,
) -> Result<Root, SavingError> {
    let mut maps = vec![];

    for (key_combo, mapping) in desktop {
        let mut rules = vec![];
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

        maps.push(Map {
            name: Symbol::try_from(String::from("mapping")).context(CannotSerializeSymbol)?,
            rules,
        });
    }

    // TODO: Add more maps for transforms based on dead keys
    // TODO: Add map for space transforms

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
        maps,
        states: vec![],
    })
}

fn pick_name_from_display_names(names: &BTreeMap<String, String>) -> String {
    names
        .get("en")
        .or_else(|| names.values().next())
        .cloned()
        .unwrap_or_default()
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
}
