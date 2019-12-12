use crate::repos::{update_repo, xkb_dir};
use kbdgen::{
    bundle::{
        models::{IsoKey, TargetX11},
        KeyValue,
    },
    Load, ProjectBundle, Save,
};
use snafu::{OptionExt, ResultExt, Snafu};
use snafu_cli_debug::SnafuCliDebug;
use std::{
    collections::BTreeMap,
    convert::TryFrom,
    error::Error as StdError,
    path::{Path, PathBuf},
};
use structopt::StructOpt;
use strum::IntoEnumIterator;
use xkb_parser::{ast, parse, Xkb};

const REPO_URL: &str = "https://gitlab.freedesktop.org/xkeyboard-config/xkeyboard-config.git";

#[derive(Debug, StructOpt)]
pub struct Cli {
    /// Target directory for `.kbdgen` bundle
    #[structopt(parse(from_os_str))]
    output: PathBuf,

    /// Update bundle if it already exists
    #[structopt(short = "u", long = "update")]
    update_bundle: bool,

    #[structopt(flatten)]
    verbose: clap_verbosity_flag::Verbosity,
}

pub fn xkb_to_kbdgen(opts: &Cli) -> Result<(), Error> {
    // let _ = opts.verbose.setup_env_logger("kbdgen-cli");

    let mut bundle = if opts.update_bundle {
        let b = ProjectBundle::load(&opts.output).context(CannotLoadBundle)?;
        log::info!(
            "Bundle `{}` loaded, will try to update it",
            opts.output.display()
        );
        b
    } else {
        log::info!("Will create new bundle in `{}`", opts.output.display());
        ProjectBundle::default()
    };

    update_repo("xkb", &xkb_dir(), REPO_URL).context(FailedRepoUpdate)?;

    let (locale, file_path) = select_base_locale()?;
    log::debug!("opening `{}`", file_path.display());
    let file = std::fs::read_to_string(&file_path).context(CannotOpenFile { path: &file_path })?;
    let section = select_sub_locale(&file).context(CannotReadXkb { path: &file_path })?;
    log::info!(
        "selected locale `{}` with style `{}`",
        locale,
        section.name.as_ref()
    );
    let include_dir = xkb_dir().join("symbols");
    let (keys, dead_keys) = resolve_keys(&section, &include_dir)?;

    // Set X11 target metadata to some values that not completely random
    bundle.targets.x11 = Some(TargetX11 {
        version: chrono::Utc::now().format("%Y-%m-%d").to_string(),
        build: 1,
    });

    // Update X11 layout entry
    let mut layout = bundle.layouts.entry(locale.to_string()).or_default();
    layout.modes.x11 = Some(keys.into_iter().map(|(k, v)| (k, v.into())).collect());

    // Do a neat switcheroo with possibly-None dead keys map
    let mut dead = layout.dead_keys.take().unwrap_or_default();
    dead.insert("x11".to_string(), dead_keys);
    layout.dead_keys = Some(dead);

    bundle.save(&opts.output).context(CannotBeSaved)?;
    log::info!("New bundle written to `{}`.", opts.output.display());
    log::info!(
        "It now contains a X11 target with version `{}`.",
        bundle.targets.x11.unwrap().version
    );

    Ok(())
}

fn select_base_locale() -> Result<(String, PathBuf), Error> {
    let kbd_path = xkb_dir().join("symbols");
    let files: BTreeMap<String, PathBuf> = globwalk::GlobWalkerBuilder::new(&kbd_path, "**")
        .max_depth(8)
        .build()
        .unwrap()
        .filter_map(Result::ok)
        .filter(|entry| !entry.path().ends_with("Makefile.am"))
        .map(|entry| {
            (
                entry
                    .path()
                    .strip_prefix(&kbd_path)
                    .unwrap()
                    .to_string_lossy()
                    .into(),
                entry.path().into(),
            )
        })
        .collect();

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

    let result = skim::Skim::run_with(&options, Some(Box::new(cur))).context(NoLocaleSelected)?;
    let result = result
        .selected_items
        .first()
        .context(NoLocaleSelected)?
        .get_text();

    Ok((result.into(), files[result].clone()))
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

type LayeredKeyMap = BTreeMap<String, BTreeMap<IsoKey, KeyValue>>;
type DeadKeyMap = BTreeMap<String, Vec<String>>;

/// Build a partial layout from an xkb symbols definition
///
/// It will return two maps:
///
/// 1. A map (`Layer -> IsoKey -> KeyValue`) that will eventually become
///    `layout.modes.x11`
/// 2. A map of dead keys (`Layer -> Vec<KeyValue`) that will become
///    `layout.dead_keys["x11"]`
fn resolve_keys(
    symbols: &ast::XkbSymbols,
    include_dir: &Path,
) -> Result<(LayeredKeyMap, DeadKeyMap), Error> {
    // TODO: figure out the actual names for the layers
    let layers = &["default", "shift", "alt", "shift+alt"];

    // Collect keys into modes while iterating
    let mut map: BTreeMap<String, BTreeMap<IsoKey, KeyValue>> = BTreeMap::new();

    // Collect dead keys while iterating.
    let mut dead_keys: BTreeMap<String, Vec<String>> = BTreeMap::new();

    let keys = extract_keys(symbols, include_dir)?;
    log::debug!("found {} keys in {}", keys.len(), symbols.name.content);

    for key in &keys {
        for (codepoint, mode) in key.values.iter().zip(layers) {
            map.entry(mode.to_string())
                .or_default()
                .insert(key.iso_key, KeyValue::from(codepoint.as_ref().to_string()));

            if let Codepoint::Deadkey(c) = codepoint {
                dead_keys
                    .entry(mode.to_string())
                    .or_default()
                    .push(c.clone());
            }
        }
    }

    // Fill in all the ISO keys that were not defined
    for mode in map.values_mut() {
        for key in IsoKey::iter() {
            mode.entry(key).or_insert_with(|| None.into());
        }
    }

    Ok((map, dead_keys))
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

fn extract_keys(symbols: &ast::XkbSymbols, include_dir: &Path) -> Result<Vec<Key>, Error> {
    symbols.value.iter().try_fold(Vec::new(), |mut res, item| {
        match item {
            ast::XkbSymbolsItem::Include(ast::Include { name }) => {
                res.extend(read_include(name, include_dir)?)
            }
            ast::XkbSymbolsItem::Key(k) => match Key::try_from(k) {
                Ok(k) => res.push(k),
                Err(e) => log::warn!("Skipping `{:?}`: {}", k, e),
            },
            _ => {}
        }

        Ok(res)
    })
}

fn parse_include_name(include: &str) -> Result<(&str, Option<&str>), Error> {
    fn parse(input: &str) -> nom::IResult<&str, (&str, Option<&str>)> {
        use nom::{
            bytes::complete::{is_not, take_until},
            character::complete::char,
            combinator::{complete, opt},
            sequence::{delimited, tuple},
        };

        complete(tuple((
            take_until("("),
            opt(delimited(char('('), is_not(")"), char(')'))),
        )))(input)
    }

    if include.contains('(') {
        let (_, (name, section)) = parse(include).map_err(|_| Error::FailedToParseInclude {
            include: include.to_string(),
        })?;
        Ok((name, section))
    } else {
        Ok((include, None))
    }
}

fn read_include(name: &str, include_dir: &Path) -> Result<Vec<Key>, Error> {
    let (name, section_name) = parse_include_name(name)?;
    let file_path = include_dir.join(name);
    log::debug!("opening `{}` to fetch includes", file_path.display());
    let file = std::fs::read_to_string(&file_path).context(CannotOpenFile { path: &file_path })?;
    let sections = fetch_symbols(&file).context(CannotReadXkb { path: &file_path })?;
    let symbols = if let Some(section_name) = section_name {
        sections
            .iter()
            .find(|ast::XkbSymbols { name, .. }| name.content == section_name)
            .context(SymbolSectionNotFound {
                path: &file_path,
                section_name,
            })?
    } else {
        sections.get(0).context(SymbolSectionNotFound {
            path: &file_path,
            section_name: "first section (no section name specified)",
        })?
    };

    Ok(extract_keys(&symbols, include_dir)?)
}

#[derive(Debug, Clone)]
struct Key {
    iso_key: IsoKey,
    values: Vec<Codepoint>,
}

impl<'a, 'src> TryFrom<&'a ast::Key<'src>> for Key {
    type Error = Error;

    fn try_from(key: &ast::Key) -> Result<Key, Error> {
        let iso_key = iso_key_from_xkb_symbol(&key.id.as_ref()).context(UnknownIsoKey {
            value: key.id.content,
        })?;
        let values = key.values.iter().try_fold(Vec::new(), |mut res, v| {
            if let ast::KeyValue::KeyNames(ast::KeyNames { values }) = v {
                res.extend(
                    values
                        .iter()
                        .map(|x| Codepoint::from_keysym(x.as_ref()))
                        .collect::<Result<Vec<_>, Error>>()?,
                )
            };
            Ok(res)
        })?;
        Ok(Key { iso_key, values })
    }
}

fn iso_key_from_xkb_symbol(s: &str) -> Option<IsoKey> {
    if !s.starts_with('A') {
        return None;
    }
    let s = &s[1..];
    s.parse().ok()
}

#[derive(Debug, Clone)]
enum Codepoint {
    Regular(String),
    Deadkey(String),
}

impl Codepoint {
    fn from_keysym(keysym: &str) -> Result<Codepoint, Error> {
        fn parse_unicode_def(input: &str) -> nom::IResult<&str, &str> {
            use nom::{
                bytes::complete::{tag, take_while1},
                combinator::complete,
            };

            fn is_hex_digit(c: char) -> bool {
                c.is_digit(16)
            }

            let (input, _) = tag("U")(input)?;
            complete(take_while1(is_hex_digit))(input)
        }

        if let Ok((_, c)) = parse_unicode_def(keysym) {
            let c: u32 = u32::from_str_radix(c, 16).unwrap_or_else(|_| {
                panic!(
                    "found unicode-like codepoint but couldn't parse hex `{}`",
                    c
                )
            });
            return Ok(Codepoint::Regular(
                std::char::from_u32(c).unwrap().to_string(),
            ));
        }

        if let Some(k) = x11_keysymdef::lookup_by_name(&keysym) {
            if keysym.starts_with("dead_") {
                return Ok(Codepoint::Deadkey(k.unicode.to_string()));
            } else {
                return Ok(Codepoint::Regular(k.unicode.to_string()));
            }
        }

        Err(Error::UnknownCodepointMapping {
            keysym: keysym.to_string(),
        })
    }
}

impl AsRef<str> for Codepoint {
    fn as_ref(&self) -> &str {
        match self {
            Codepoint::Regular(x) => &x,
            Codepoint::Deadkey(x) => &x,
        }
    }
}

#[derive(Snafu, SnafuCliDebug)]
pub enum Error {
    #[snafu(display("Updating XKB repo failed"))]
    FailedRepoUpdate {
        source: crate::repos::Error,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("No locale selected"))]
    NoLocaleSelected { backtrace: snafu::Backtrace },
    #[snafu(display("Could load XKB file `{}`", path.display()))]
    CannotOpenFile {
        path: PathBuf,
        source: std::io::Error,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("Could read XKB file `{}`", path.display()))]
    CannotReadXkb {
        path: PathBuf,
        source: Box<dyn StdError>,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("Could not translate key id `{}` to iso key", value))]
    UnknownIsoKey {
        value: String,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("Could not translate keysym `{}` to codepoint", keysym))]
    UnknownCodepointMapping { keysym: String },
    #[snafu(display("Failed to parse include `{}`", include))]
    FailedToParseInclude { include: String },
    #[snafu(display("Failed to find/read section `{}` in `{}`", section_name, path.display()))]
    SymbolSectionNotFound {
        path: PathBuf,
        section_name: String,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("Could not load kbdgen bundle"))]
    CannotLoadBundle {
        source: kbdgen::LoadError,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("Could write kbdgen bundle"))]
    CannotBeSaved {
        source: kbdgen::SaveError,
        backtrace: snafu::Backtrace,
    },
}
