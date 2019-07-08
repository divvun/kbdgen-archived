use kbdgen::{cldr::Keyboard, Load, ProjectBundle};
use log::{debug, log_enabled};
use snafu::{ResultExt, Snafu};
use snafu_cli_debug::SnafuCliDebug;
use std::{fs::File, io::BufWriter, path::PathBuf};
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
struct Cli {
    #[structopt(parse(from_os_str))]
    input: PathBuf,

    #[structopt(parse(from_os_str))]
    output: PathBuf,

    #[structopt(flatten)]
    verbose: clap_verbosity_flag::Verbosity,
}

fn main() -> Result<(), Error> {
    let opts = Cli::from_args();
    let _ = opts.verbose.setup_env_logger("kbdgen-to-cldr");

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
        .map(|(name, layout)| (name, layout_to_cldr(&name, layout)))
        .try_for_each(|(name, keyboards)| {
            use kbdgen::cldr::ToXml;

            for (platform, keyboard) in keyboards? {
                let path = &opts.output.join(name).join(platform).with_extension("xml");
                std::fs::create_dir_all(path.parent().unwrap())
                    .context(CannotCreateFile { path })?;
                let file = File::create(path).context(CannotCreateFile { path })?;
                let mut writer = BufWriter::new(file);
                keyboard
                    .write_xml(&mut writer)
                    .context(CannotSerializeXml)?;
            }
            Ok(())
        })
        .context(CannotBeSaved)?;

    Ok(())
}

fn layout_to_cldr(
    name: &str,
    layout: &kbdgen::models::Layout,
) -> Result<Vec<(String, Keyboard)>, SavingError> {
    log::debug!("to cldr with you, {}!", name);

    use kbdgen::{
        cldr::*,
        models::{IsoKey, MobileModes},
    };
    use std::collections::BTreeMap;
    use strum::IntoEnumIterator;

    let mut res = vec![];

    fn mobile_mode_to_keyboard(
        name: &str,
        mobile: &MobileModes,
        long_presses: Option<&BTreeMap<String, String>>,
    ) -> Keyboard {
        let mut key_maps = vec![];

        for (modifiers, mapping) in mobile {
            let keys = IsoKey::iter()
                .zip(mapping.iter())
                .map(|(iso, value)| {
                    let long_press = long_presses.and_then(|l| l.get(value)).cloned();
                    Map {
                        iso: iso.to_string(),
                        to: value.to_string(),
                        transform: None,
                        long_press,
                    }
                })
                .collect();

            key_maps.push(KeyMap {
                keys,
                modifiers: Some(modifiers.to_string()),
            })
        }

        Keyboard {
            locale: name.to_string(),
            names: vec![Names {
                values: vec![Name {
                    value: name.to_string(),
                }],
            }],
            key_maps,
            ..Keyboard::default()
        }
    }

    if let Some(a) = layout.modes.android.as_ref() {
        log::debug!("android: check");
        res.push((
            String::from("android"),
            mobile_mode_to_keyboard(name, a, layout.longpress.as_ref()),
        ));
    }
    if let Some(a) = layout.modes.ios.as_ref() {
        log::debug!("ios: check");
        res.push((
            String::from("ios"),
            mobile_mode_to_keyboard(name, a, layout.longpress.as_ref()),
        ));
    }
    if let Some(a) = layout.modes.mobile.as_ref() {
        log::debug!("generic mobile: check");
        res.push((
            String::from("mobile"),
            mobile_mode_to_keyboard(name, a, layout.longpress.as_ref()),
        ));
    }

    Ok(res)
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
    #[snafu(display("Could transform to xml"))]
    CannotSerializeXml {
        source: std::io::Error,
        backtrace: snafu::Backtrace,
    },
}
