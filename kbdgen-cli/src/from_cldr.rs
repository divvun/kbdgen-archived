use crate::repos::{cldr_dir, update_repo};
use kbdgen::{bundle::Save, cldr::Keyboard};
use snafu::{OptionExt, ResultExt, Snafu};
use snafu_cli_debug::SnafuCliDebug;
use std::{collections::BTreeMap, path::PathBuf};
use structopt::StructOpt;

const REPO_URL: &str = "https://github.com/unicode-org/cldr";

#[derive(Debug, StructOpt)]
pub struct Cli {
    #[structopt(parse(from_os_str))]
    output: PathBuf,

    #[structopt(flatten)]
    verbose: clap_verbosity_flag::Verbosity,
}

pub fn cldr_to_kbdgen(opts: &Cli) -> Result<(), Error> {
    // let _ = opts.verbose.setup_env_logger("kbdgen-cli");

    update_repo("cldr", &cldr_dir(), REPO_URL).context(CldrRepoUpdate)?;
    let locale = select_base_locale().context(NoLocaleSelected)?;

    log::debug!("Selected locale: '{}'", &locale.0);
    log::debug!("Files: {:#?}", &locale.1);

    let mut modes = kbdgen::models::Modes::default();

    let xml_map: Vec<Keyboard> = locale
        .1
        .into_iter()
        .map(|(key, mut v)| {
            v.sort();
            let last = v.last().unwrap();
            parse_path(&key, last)
        })
        .collect::<Result<_, _>>()?;

    for keyboard in dbg!(xml_map) {
        match keyboard.mode_name() {
            "mobile" => modes.mobile = Some(keyboard.to_mobile_modes()),
            "mac" => modes.mac = Some(keyboard.to_desktop_modes()),
            "win" => modes.win = Some(keyboard.to_desktop_modes()),
            "chrome" => modes.chrome = Some(keyboard.to_desktop_modes()),
            _ => {}
        }
    }

    let mut layout = kbdgen::models::Layout::default();
    layout.modes = modes;

    let mut bundle = kbdgen::bundle::ProjectBundle::default();
    bundle.layouts.insert(locale.0, layout);

    bundle.save(&opts.output).context(CannotSave)?;
    log::info!("New bundle written to `{}`.", opts.output.display());

    Ok(())
}

#[derive(Snafu, SnafuCliDebug)]
pub enum Error {
    #[snafu(display("Updating CLDR repo failed"))]
    CldrRepoUpdate {
        source: crate::repos::Error,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("No locale selected"))]
    NoLocaleSelected { backtrace: snafu::Backtrace },
    #[snafu(display("Could load CLDR file"))]
    CannotOpenFile {
        source: std::io::Error,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("Could load CLDR file"))]
    CannotReadXml {
        source: serde_xml_rs::Error,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("Could write kbdgen bundle"))]
    CannotSave {
        source: kbdgen::SaveError,
        backtrace: snafu::Backtrace,
    },
}

pub fn select_base_locale() -> Option<(String, BTreeMap<String, Vec<String>>)> {
    let kbd_path = cldr_dir().join("keyboards");
    let set: BTreeMap<String, BTreeMap<String, Vec<String>>> = BTreeMap::new();
    let mut locale_map = globwalk::GlobWalkerBuilder::new(kbd_path, "*.xml")
        .build()
        .unwrap()
        .filter_map(Result::ok)
        .filter(|entry| {
            !entry
                .path()
                .file_stem()
                .unwrap()
                .to_string_lossy()
                .starts_with('_')
        })
        .fold(set, |mut acc, cur| {
            let tag = (&*cur.path().file_stem().unwrap().to_string_lossy())
                .split("-t")
                .next()
                .unwrap()
                .to_string();
            let kbd_os = (&*cur
                .path()
                .parent()
                .unwrap()
                .file_name()
                .unwrap()
                .to_string_lossy())
                .to_string();
            let entry = acc
                .entry(tag)
                .or_insert_with(BTreeMap::new)
                .entry(kbd_os)
                .or_insert_with(Vec::new);
            (*entry).push(
                cur.path()
                    .file_name()
                    .unwrap()
                    .to_string_lossy()
                    .to_string(),
            );
            acc
        });
    let mut locales = locale_map.iter().collect::<Vec<_>>();
    locales.sort();

    let options = skim::SkimOptionsBuilder::default()
        .prompt(Some("Which locale to use as base? "))
        .exact(true)
        .ansi(true)
        .build()
        .unwrap();

    let cyan = console::Style::new().cyan().dim();
    let text = locales
        .iter()
        .map(|(locale, items)| {
            let x = items.keys().map(|x| &**x).collect::<Vec<_>>();
            format!("{}   {}", locale, cyan.apply_to(x.join(", ")))
        })
        .collect::<Vec<_>>()
        .join("\n")
        .as_bytes()
        .to_owned();
    let cur = std::io::Cursor::new(text);

    let result = skim::Skim::run_with(&options, Some(Box::new(cur)))?;
    let result = result
        .selected_items
        .first()?
        .get_text()
        .split("   ")
        .next()
        .unwrap();

    Some((result.to_string(), locale_map.remove(result).unwrap()))
}

pub fn parse_path(os: &str, file: &str) -> Result<Keyboard, Error> {
    let fn_ = cldr_dir().join("keyboards").join(os).join(file);

    let f = std::fs::File::open(fn_).context(CannotOpenFile)?;
    let kbd: Keyboard = serde_xml_rs::from_reader(f).context(CannotReadXml)?;
    Ok(kbd)
}
