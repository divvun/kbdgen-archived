use kbdgen::{bundle::Save, cldr::Keyboard};
use kbdgen_cli::{update_repo, xkb_dir};
use snafu::{OptionExt, ResultExt, Snafu};
use snafu_cli_debug::SnafuCliDebug;
use std::{collections::BTreeMap, error::Error as StdError, path::PathBuf};
use structopt::StructOpt;
use xkb_parser::{ast, parse, Xkb};

const REPO_URL: &str = "https://gitlab.freedesktop.org/xkeyboard-config/xkeyboard-config.git";

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
    let _ = opts.verbose.setup_env_logger("xkb-to-kbdgen");

    update_repo("xkb", &xkb_dir(), REPO_URL).context(FailedRepoUpdate)?;

    let file_path = select_base_locale()?;
    let file = std::fs::read_to_string(&file_path).context(CannotOpenFile { path: &file_path })?;
    let section = select_sub_locale(&file).context(CannotReadXkb { path: &file_path })?;
    let include_dir = xkb_dir().join("symbols");

    Ok(())
}

fn select_base_locale() -> Result<PathBuf, Error> {
    let kbd_path = xkb_dir().join("symbols");
    let files: BTreeMap<String, PathBuf> = globwalk::GlobWalkerBuilder::new(kbd_path, "*")
        .build()
        .unwrap()
        .filter_map(Result::ok)
        .filter(|entry| "Makefile.am" != entry.path().file_stem().unwrap())
        .map(|entry| {
            (
                entry.path().file_stem().unwrap().to_string_lossy().into(),
                entry.path().into(),
            )
        })
        .collect();

    let file_path = {
        let options = skim::SkimOptionsBuilder::default()
            .prompt(Some("Which keyboard base to load? "))
            .exact(true)
            .ansi(true)
            .build()
            .unwrap();

        let text = files
            .iter()
            .fold(String::new(), |mut text, (file_name, _path)| {
                text.push_str(&file_name);
                text.push_str("\n");
                text
            })
            .into_bytes();
        let cur = std::io::Cursor::new(text);

        let result =
            skim::Skim::run_with(&options, Some(Box::new(cur))).context(NoLocaleSelected)?;
        let result = result
            .selected_items
            .first()
            .context(NoLocaleSelected)?
            .get_text();

        &files[result]
    };

    Ok(file_path.clone())
}

fn select_sub_locale(file: &str) -> Result<ast::XkbSymbols, Box<dyn StdError>> {
    let sections = fetch_symbols(&file)?;

    if sections.len() == 1 {
        return Ok(sections[0].clone());
    }

    let options = skim::SkimOptionsBuilder::default()
        .prompt(Some("Which section to load? "))
        .exact(true)
        .ansi(true)
        .build()
        .unwrap();

    let text = sections
        .iter()
        .fold(String::new(), |mut text, section| {
            text.push_str(&String::from(&section.name));
            text.push_str("\n");
            text
        })
        .into_bytes();
    let cur = std::io::Cursor::new(text);

    let result = skim::Skim::run_with(&options, Some(Box::new(cur))).context(NoLocaleSelected)?;
    let result = result
        .selected_items
        .first()
        .context(NoLocaleSelected)?
        .get_text();

    Ok(sections
        .into_iter()
        .find(|ast::XkbSymbols { name, .. }| name.content == result)
        .context(NoLocaleSelected)?)
}

fn fetch_symbols(source: &str) -> Result<Vec<ast::XkbSymbols>, Box<dyn StdError>> {
    let x: Xkb = parse(&source)?;

    let symbols = x
        .definitions
        .iter()
        .filter_map(|x| {
            if let ast::Directive::XkbSymbols(x) = &x.directive {
                Some(x.clone())
            } else {
                None
            }
        })
        .collect();

    Ok(symbols)
}

#[derive(Snafu, SnafuCliDebug)]
pub enum Error {
    #[snafu(display("Updating XKB repo failed"))]
    FailedRepoUpdate {
        source: kbdgen_cli::Error,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("No locale selected"))]
    NoLocaleSelected { backtrace: snafu::Backtrace },
    #[snafu(display("Could load XKB file"))]
    CannotOpenFile {
        path: PathBuf,
        source: std::io::Error,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("Could load XKB file"))]
    CannotReadXkb {
        path: PathBuf,
        source: Box<dyn StdError>,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("Could write kbdgen bundle"))]
    CannotSave {
        source: kbdgen::SaveError,
        backtrace: snafu::Backtrace,
    },
}
