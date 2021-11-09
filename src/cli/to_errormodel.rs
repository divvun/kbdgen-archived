use crate::{bundle::keys::KeyValue, Load, ProjectBundle};
use log::{debug, log_enabled};
use rust_decimal::prelude::ToPrimitive;
use std::{
    fs::File,
    io::Write,
    path::{Path, PathBuf},
};

fn key_width(key: &KeyValue) -> f32 {
    match key {
        KeyValue::Special { width, .. } => width.to_f32().unwrap(),
        _ => 1.0,
    }
}

fn calc_row_width(row: &[KeyValue]) -> f32 {
    row.iter().map(key_width).sum()
}

const MAX_DIST: f32 = 1.5;

#[derive(Debug, Clone)]
struct KeyCoordinate {
    pub key: KeyValue,
    pub x: f32,
    pub y: f32,
}

impl KeyCoordinate {
    pub fn dist(&self, other: &KeyCoordinate) -> f32 {
        ((self.x - other.x).powi(2) + (self.y - other.y).powi(2)).sqrt()
    }
}

pub fn kbdgen_to_errormodel(input: &Path, output: &Path, _options: &Options) -> Result<(), Error> {
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

    let layout = bundle
        .layouts
        .get(&_options.layout)
        .ok_or_else(|| Error::CouldNotFindLayout {
            layout: _options.layout.to_owned(),
        })?;

    let ios = layout.modes.ios.as_ref().unwrap();
    let mode = ios.get("default").ok_or_else(|| Error::CouldNotFindMode {
        mode: "default".into(),
    })?;

    let longest = mode
        .0
        .iter()
        .map(|row| calc_row_width(row))
        .fold(0.0, f32::max);

    // Determine starting offset of each row in case some rows are shorter than others
    let offsets: Vec<f32> = mode
        .0
        .iter()
        .map(|row| (longest - calc_row_width(row)) as f32 / 2.0)
        .collect();

    // Get x/y coordinates to the center for each key
    let coordinates: Vec<_> = mode
        .0
        .iter()
        .enumerate()
        .flat_map(|(y, row)| {
            let mut row_positions = vec![];
            let mut current_x = offsets[y];
            for key in row {
                // Add position in center of key
                row_positions.push(KeyCoordinate {
                    key: key.to_owned(),
                    x: current_x + key_width(key) / 2.0,
                    y: y as f32,
                });
                current_x += key_width(key);
            }
            row_positions
        })
        .collect();

    // Calculate distances between all keys
    let distances: Vec<_> = coordinates
        .iter()
        .flat_map(|a| {
            coordinates
                .iter()
                .map(move |b| (a.to_owned(), b.to_owned(), a.dist(b)))
        })
        .collect();

    // Filter lines to be output
    let att_lines: Vec<_> = distances
        .iter()
        .filter(|d| d.2 <= MAX_DIST)
        .filter_map(|dist| match (&dist.0.key, &dist.1.key) {
            (KeyValue::Symbol(ref a), KeyValue::Symbol(ref b)) => {
                Some((a.to_owned(), b.to_owned(), dist.2))
            }
            _ => None,
        })
        .collect();

    let mut file = File::create(output).map_err(|io| Error::CouldNotCreateFile {
        path: output.to_owned(),
        source: io,
    })?;

    for (a, b, dist) in att_lines.iter() {
        writeln!(file, "0\t{}\t{}\t{}\t{:6}", att_lines.len(), a, b, dist)
            .map_err(|source| Error::CouldNotWriteToFile { source })?;
    }

    writeln!(file, "{} 0.0", att_lines.len())
        .map_err(|source| Error::CouldNotWriteToFile { source })?;
    Ok(())
}

#[derive(Debug, Clone)]
pub struct Options {
    pub layout: String,
}

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("Could not load kbdgen bundle")]
    CannotLoad { source: crate::LoadError },
    #[error("Could not find layout {layout:?}")]
    CouldNotFindLayout { layout: String },
    #[error("Could not find mode {mode:?}")]
    CouldNotFindMode { mode: String },
    #[error("Could not create file {path:?}")]
    CouldNotCreateFile {
        path: PathBuf,
        source: std::io::Error,
    },
    #[error("Could not write to file")]
    CouldNotWriteToFile { source: std::io::Error },
}
