use crate::{utils::UnwrapOrUnknownExt, xkb::*, Load, ProjectBundle};
use log::{debug, log_enabled};
use snafu::{ResultExt, Snafu};
use snafu_cli_debug::SnafuCliDebug;
use std::{
    fs::File,
    io::BufWriter,
    path::{Path, PathBuf},
};

pub fn kbdgen_to_xkb(input: &Path, output: &Path, _options: &Options) -> Result<(), Error> {
    let bundle = ProjectBundle::load(input).context(CannotLoad)?;
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
        .map(|(name, layout)| (name, layout_to_xkb_symbols(&name, layout, &bundle)))
        .try_for_each(|(name, symbols)| {
            let path = output.join(name).join("linux").with_extension("xkb");
            std::fs::create_dir_all(path.parent().unwrap())
                .context(CannotCreateFile { path: path.clone() })?;
            let file = File::create(&path).context(CannotCreateFile { path: path.clone() })?;
            debug!("Created file `{}`", path.display());
            let mut writer = BufWriter::new(file);
            symbols?
                .write_xkb(&mut writer)
                .context(CannotSerializeXkb)?;
            log::info!("Wrote to file `{}`", path.display());
            Ok(())
        })
        .context(CannotBeSaved)?;

    Ok(())
}

fn layout_to_xkb_symbols(
    name: &str,
    layout: &crate::models::Layout,
    project: &crate::ProjectBundle,
) -> Result<XkbFile, SavingError> {
    XkbFile::from_layout(name, layout.clone()).context(CannotConvertToXkb {
        project: project
            .path
            .clone()
            .map(|x| format!("{}", x.display()))
            .unwrap_or_unknown(),
        layout: layout.name().unwrap_or_unknown(),
    })
}

#[derive(Debug, Clone)]
pub struct Options {
    pub standalone: bool,
}

#[derive(Snafu, SnafuCliDebug)]
pub enum Error {
    #[snafu(display("Could not load kbdgen bundle"))]
    CannotLoad {
        source: crate::LoadError,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("Could not write XKB file"))]
    CannotBeSaved {
        source: SavingError,
        backtrace: snafu::Backtrace,
    },
}

#[derive(Snafu, Debug)]
pub enum SavingError {
    #[snafu(display("Could not convert `{}` in `{}` to xkb", layout, project))]
    CannotConvertToXkb {
        project: String,
        layout: String,
        source: ConversionError,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("Could not create file `{}`", path.display()))]
    CannotCreateFile {
        path: PathBuf,
        source: std::io::Error,
        backtrace: snafu::Backtrace,
    },
    #[snafu(display("Could transform to XKB"))]
    CannotSerializeXkb {
        source: std::io::Error,
        backtrace: snafu::Backtrace,
    },
}
