// use strum::IntoEnumIterator;
// use crate::{
//     cldr::{Keyboard, *},
//     models::{DesktopModes, IsoKey, MobileModes},
//     Load, ProjectBundle,
// };
// use log::{debug, log_enabled};
// use snafu::{ResultExt, Snafu};
// use snafu_cli_debug::SnafuCliDebug;
// use std::{collections::IndexMap, fs::File, io::BufWriter, path::PathBuf};
// use structopt::StructOpt;

// pub fn kbdgen_to_cldr() -> Result<(), Error> {
//     // let _ = opts.verbose.setup_env_logger("kbdgen-cli");

//     let bundle = ProjectBundle::load(&opts.input).context(CannotLoad)?;
//     if log_enabled!(log::Level::Debug) {
//         debug!("Bundle `{}` loaded", opts.input.display());
//         let locales = bundle
//             .project
//             .locales
//             .values()
//             .map(|l| l.name.as_str())
//             .collect::<Vec<_>>();
//         debug!("Bundle contains these locales: {:?}", locales);
//     }

//     bundle
//         .layouts
//         .iter()
//         .map(|(name, layout)| (name, layout_to_cldr(&name, layout, &bundle)))
//         .try_for_each(|(name, keyboards)| {
//             for (platform, keyboard) in keyboards? {
//                 let path = &opts.output.join(name).join(platform).with_extension("xml");
//                 std::fs::create_dir_all(path.parent().unwrap())
//                     .context(CannotCreateFile { path })?;
//                 let file = File::create(path).context(CannotCreateFile { path })?;
//                 let mut writer = BufWriter::new(file);
//                 keyboard
//                     .write_xml(&mut writer)
//                     .context(CannotSerializeXml)?;
//             }
//             Ok(())
//         })
//         .context(CannotBeSaved)?;

//     Ok(())
// }

// fn layout_to_cldr(
//     name: &str,
//     layout: &crate::models::Layout,
//     _project: &crate::ProjectBundle,
// ) -> Result<Vec<(String, Keyboard)>, SavingError> {
//     log::debug!("to cldr with you, {}!", name);

//     let mut res = vec![];

//     macro_rules! mode {
//         (mobile: $name:ident) => {
//             mode!(mobile_mode_to_keyboard -> $name)
//         };
//         (desktop: $name:ident) => {
//             mode!(desktop_mode_to_keyboard -> $name)
//         };
//         ($fn:ident -> $name:ident) => {
//             if let Some(a) = layout.modes.$name.as_ref() {
//                 log::debug!("{}: check", stringify!($name));
//                 res.push((
//                     String::from(stringify!($name)),
//                     $fn(name, stringify!($name), a, layout.longpress.as_ref(), layout),
//                 ));
//             }
//         };
//     }

//     mode!(mobile: android);
//     mode!(mobile: ios);
//     mode!(mobile: mobile);
//     mode!(desktop: win);
//     mode!(desktop: mac);
//     mode!(desktop: chrome);
//     mode!(desktop: x11);
//     mode!(desktop: desktop);

//     Ok(res)
// }

// fn desktop_mode_to_keyboard(
//     name: &str,
//     target: &str,
//     desktop: &DesktopModes,
//     long_presses: Option<&IndexMap<String, String>>,
//     layout: &crate::models::Layout,
// ) -> Keyboard {
//     let mut key_maps = vec![];

//     for (modifiers, mapping) in desktop {
//         let keys = mapping
//             .iter()
//             .filter_map(|(iso, value)| {
//                 if let Some(value) = value.as_ref() {
//                     Some((iso, value))
//                 } else {
//                     None
//                 }
//             })
//             .map(|(iso, value)| {
//                 let long_press = long_presses.and_then(|l| l.get(value.as_str())).cloned();
//                 Map {
//                     iso: iso.to_string(),
//                     to: value.to_string(),
//                     transform: None,
//                     long_press,
//                 }
//             })
//             .collect();

//         key_maps.push(KeyMap {
//             keys,
//             modifiers: Some(modifiers.to_string()),
//         })
//     }

//     Keyboard {
//         locale: format!("{}-t-k0-{}", name, target),
//         names: vec![Names {
//             values: vec![Name {
//                 value: pick_name_from_display_names(&layout.display_names),
//             }],
//         }],
//         key_maps,
//         ..Keyboard::default()
//     }
// }

// fn mobile_mode_to_keyboard(
//     name: &str,
//     target: &str,
//     mobile: &MobileModes,
//     long_presses: Option<&IndexMap<String, String>>,
//     layout: &crate::models::Layout,
// ) -> Keyboard {
//     let mut key_maps = vec![];

//     for (modifiers, mapping) in mobile {
//         use strum::IntoEnumIterator;
//         let keys = IsoKey::iter()
//             .zip(mapping.iter())
//             .map(|(iso, value)| {
//                 let long_press = long_presses.and_then(|l| l.get(value)).cloned();
//                 Map {
//                     iso: iso.to_string(),
//                     to: value.to_string(),
//                     transform: None,
//                     long_press,
//                 }
//             })
//             .collect();

//         key_maps.push(KeyMap {
//             keys,
//             modifiers: Some(modifiers.to_string()),
//         })
//     }

//     Keyboard {
//         locale: format!("{}-t-k0-{}", name, target),
//         names: vec![Names {
//             values: vec![Name {
//                 value: pick_name_from_display_names(&layout.display_names),
//             }],
//         }],
//         key_maps,
//         ..Keyboard::default()
//     }
// }

// fn pick_name_from_display_names(names: &IndexMap<String, String>) -> String {
//     names
//         .get("en")
//         .or_else(|| names.values().next())
//         .cloned()
//         .unwrap_or_default()
// }

// #[derive(Snafu, SnafuCliDebug)]
// pub enum Error {
//     #[snafu(display("Could not load kbdgen bundle"))]
//     CannotLoad {
//         source: crate::LoadError,
//         backtrace: backtrace::Backtrace,
//     },
//     #[snafu(display("Could not write CLDR file"))]
//     CannotBeSaved {
//         source: SavingError,
//         backtrace: backtrace::Backtrace,
//     },
// }

// #[derive(Snafu, Debug)]
// pub enum SavingError {
//     #[snafu(display("Could not create file `{}`", path.display()))]
//     CannotCreateFile {
//         path: PathBuf,
//         source: std::io::Error,
//         backtrace: backtrace::Backtrace,
//     },
//     #[snafu(display("Could transform to xml"))]
//     CannotSerializeXml {
//         source: std::io::Error,
//         backtrace: backtrace::Backtrace,
//     },
// }
