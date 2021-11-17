use std::fmt::Display;

use crate::models::{DesktopModes, IsoKey, Layout};

use super::{
    cap_mode::{derive_cap_mode, CapMode},
    consts::MSKLC_KEYS,
    key::{derive_key, Char, Key},
    ligature::Ligature,
};

pub(super) struct LayoutSection {
    pub rows: Vec<Row>,
    pub decimal: super::key::Char,
}

#[derive(Debug, Clone)]
pub(super) struct Row {
    pub key: IsoKey,
    pub sc: &'static str,
    pub vk: &'static str,
    pub cap_mode: CapMode,
    pub default: Key,
    pub shift: Key,
    pub ctrl: Key,
    pub alt: Key,
    pub alt_shift: Key,
    pub caps: Key,
    pub caps_shift: Key,
    pub alt_caps: Key,
}

impl Row {
    pub fn ligatures(&self) -> Vec<Ligature> {
        vec![
            self.default.ligature(),
            self.shift.ligature(),
            self.ctrl.ligature(),
            self.alt.ligature(),
            self.alt_shift.ligature(),
        ]
        .into_iter()
        .filter_map(|x| x)
        .collect()
    }

    pub fn dead_keys(&self) -> Vec<Char> {
        vec![
            self.default.dead_key(),
            self.shift.dead_key(),
            self.ctrl.dead_key(),
            self.alt.dead_key(),
            self.alt_shift.dead_key(),
        ]
        .into_iter()
        .filter_map(|x| x)
        .collect()
    }
}

pub(super) fn derive_rows(layout: &Layout, mode: &DesktopModes) -> Vec<Row> {
    mode.keys()
        .map(|(k, v)| {
            let (sc, vk) = MSKLC_KEYS[&k];
            let mut row = Row {
                key: k,
                sc,
                vk,
                cap_mode: CapMode::Column(0),
                default: derive_key(vk, CapMode::Column(0), layout, "default", &v),
                shift: derive_key(vk, CapMode::Column(1), layout, "shift", &v),
                ctrl: derive_key(vk, CapMode::Column(2), layout, "ctrl", &v),
                alt: derive_key(vk, CapMode::Column(3), layout, "alt", &v),
                alt_shift: derive_key(vk, CapMode::Column(4), layout, "alt+shift", &v),
                alt_caps: derive_key(vk, CapMode::SGCap, layout, "alt+caps", &v),
                caps: derive_key(vk, CapMode::SGCap, layout, "caps", &v),
                caps_shift: derive_key(vk, CapMode::SGCap, layout, "caps+shift", &v),
            };
            let cap_mode = derive_cap_mode(&row);
            row.cap_mode = cap_mode;
            row
        })
        .collect::<Vec<_>>()
}

impl Display for Row {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_fmt(format_args!(
            "{}\t{}\t{}\t",
            self.sc, self.vk, self.cap_mode
        ))?;
        f.write_fmt(format_args!(
            "{}\t{}\t{}\t{}\t{}",
            self.default, self.shift, self.ctrl, self.alt, self.alt_shift
        ))?;
        Ok(())
    }
}

impl Display for LayoutSection {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("SHIFTSTATE\n\n0\n1\n2\n6\n7\n\n")?;
        f.write_str("LAYOUT\n\n")?;
        for row in self.rows.iter() {
            f.write_fmt(format_args!("{}\n", &row))?;
            if row.cap_mode.is_sgcap() {
                f.write_fmt(format_args!(
                    "-1\t-1\t0\t{}\t{}\n",
                    row.caps, row.caps_shift
                ))?;
            }
        }

        // Space key
        f.write_str("39\tSPACE\t0\t0020\t0020\t0020\t-1\t-1\n")?;

        // Decimal key
        f.write_fmt(format_args!(
            "53\tDECIMAL\t0\t{x}\t{x}\t-1\t-1\t-1\n\n",
            x = self.decimal
        ))?;

        Ok(())
    }
}
