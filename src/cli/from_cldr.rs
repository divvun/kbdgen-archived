use crate::{
    bundle::Save,
    cldr::Keyboard,
    cli::repos::{cldr_dir, update_repo},
};
use std::{collections::BTreeMap, path::Path};

const REPO_URL: &str = "https://github.com/unicode-org/cldr";

pub fn cldr_to_kbdgen(output: &Path, bundle_name: &str) -> Result<(), Error> {
    update_repo("cldr", &cldr_dir(), REPO_URL)
        .map_err(|source| Error::CldrRepoUpdate { source })?;
    let locale = select_base_locale().ok_or(Error::NoLocaleSelected)?;

    log::debug!("Selected locale: '{}'", &locale.0);
    log::debug!("Files: {:#?}", &locale.1);

    let mut modes = crate::models::Modes::default();

    let xml_map: Vec<Keyboard> = locale
        .1
        .into_iter()
        .map(|(key, mut v)| {
            v.sort();
            let last = v.last().unwrap();
            parse_path(&key, last)
        })
        .collect::<Result<_, _>>()?;

    for keyboard in xml_map {
        match keyboard.mode_name() {
            "mobile" => modes.mobile = Some(keyboard.to_mobile_modes()),
            "mac" => modes.mac = Some(keyboard.to_desktop_modes()),
            "win" => modes.win = Some(keyboard.to_desktop_modes()),
            "chrome" => modes.chrome = Some(keyboard.to_desktop_modes()),
            _ => {}
        }
    }

    let mut layout = crate::models::Layout::default();
    layout.modes = modes;

    let mut bundle = crate::bundle::ProjectBundle::default();
    bundle.layouts.insert(locale.0, layout);

    let bundle_name = if !bundle_name.ends_with(".kbdgen") {
        format!("{}.kbdgen", bundle_name)
    } else {
        bundle_name.into()
    };

    bundle
        .save(output.join(bundle_name))
        .map_err(|source| Error::CannotSave { source })?;
    log::info!("New bundle written to `{}`.", output.display());

    Ok(())
}

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("Updating CLDR repo failed")]
    CldrRepoUpdate { source: crate::cli::repos::Error },
    #[error("No locale selected")]
    NoLocaleSelected,
    #[error("Could not load CLDR file")]
    CannotOpenFile { source: std::io::Error },
    #[error("Could not load CLDR file")]
    CannotReadXml { source: serde_xml_rs::Error },
    #[error("Could not write kbdgen bundle")]
    CannotSave { source: crate::SaveError },
}

#[cfg(windows)]
pub fn select_base_locale() -> Option<(String, BTreeMap<String, Vec<String>>)> {
    use std::io::Write;

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

    std::io::stdout()
        .write_all(&text)
        .expect("could not write list of locales to stdout");
    println!(); // Make a new line and flush!

    let result = dialoguer::Input::<String>::new()
        .with_prompt("Which locale to use as base? ")
        .interact()
        .expect("no valid locale selected");

    if locale_map.get(&result).is_none() {
        return None;
    }

    Some((result.to_string(), locale_map.remove(&result).unwrap()))
}

#[cfg(unix)]
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

    let f = std::fs::File::open(fn_).map_err(|source| Error::CannotOpenFile { source })?;
    let kbd: Keyboard =
        serde_xml_rs::from_reader(f).map_err(|source| Error::CannotReadXml { source })?;
    Ok(kbd)
}
