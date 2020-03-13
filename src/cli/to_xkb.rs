use crate::{utils::UnwrapOrUnknownExt, xkb::*, Load, ProjectBundle};
use log::{debug, log_enabled};
use std::{
    fs::File,
    io::BufWriter,
    path::{Path, PathBuf},
};

pub fn kbdgen_to_xkb(input: &Path, output: &Path, _options: &Options) -> Result<(), Error> {
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
        .filter(|(_, layout)| {
            let can_be_converted = layout.modes.win.is_some() || layout.modes.x11.is_some();
            if !can_be_converted {
                log::info!(
                    "skipping {}, no modes that can be converted to xkb",
                    layout.name().unwrap_or_unknown()
                );
                log::trace!("modes found: {}", layout.modes.available_modes().join(", "));
            }
            can_be_converted
        })
        .map(|(name, layout)| (name, XkbFile::from_layout(name, layout.clone())))
        .try_for_each(|(name, symbols)| {
            let symbols = match symbols {
                Ok(symbols) => symbols,
                Err(ConversionError::NoXkbCompatibleModes {
                    available_modes, ..
                }) => {
                    log::info!("skipping {}, no modes that can be converted to xkb", name);
                    log::debug!("modes found: {}", available_modes.join(", "));
                    return Ok(());
                }
                Err(e) => Err(e).map_err(|source| SavingError::CannotConvertToXkb {
                    project: bundle
                        .path
                        .clone()
                        .map(|x| format!("{}", x.display()))
                        .unwrap_or_unknown(),
                    layout: name.clone(),
                    source,
                })?,
            };

            let path = output.join("linux").join(name).with_extension("xkb");
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
            symbols
                .write_xkb(&mut writer)
                .map_err(|source| SavingError::CannotSerializeXkb { source })?;
            log::info!("Wrote to file `{}`", path.display());
            Ok(())
        })
        .map_err(|source| Error::CannotBeSaved { source })?;

    Ok(())
}

#[derive(Debug, Clone)]
pub struct Options {
    pub standalone: bool,
}

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("Could not load kbdgen bundle")]
    CannotLoad { source: crate::LoadError },
    #[error("Could not write XKB file")]
    CannotBeSaved { source: SavingError },
}

#[derive(Debug, thiserror::Error)]
pub enum SavingError {
    #[error("Could not convert `{}` in `{}` to xkb", layout, project)]
    CannotConvertToXkb {
        project: String,
        layout: String,
        source: ConversionError,
    },
    #[error("Could not create file `{}`", path.display())]
    CannotCreateFile {
        path: PathBuf,
        source: std::io::Error,
    },
    #[error("Could not transform to XKB")]
    CannotSerializeXkb { source: std::io::Error },
}
