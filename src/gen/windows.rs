mod cap_mode;
mod consts;
mod deadkey;
mod key;
mod layout;
mod ligature;

use codecs::utf16::Utf16Ext;
use indexmap::IndexMap;
use language_tags::LanguageTag;
use std::{fmt::Display, path::PathBuf};

use crate::{
    gen::windows::layout::derive_rows,
    models::{DesktopModes, Layout},
    ProjectBundle,
};

use self::{deadkey::DeadkeySection, key::Char, layout::LayoutSection, ligature::LigatureSection};

struct KlcFile {
    tag: LanguageTag,
    kbd: String,
    description: String,
    copyright: String,
    company: String,
    locale_name: String,
    locale_id: u32,
    layout: LayoutSection,
    ligatures: LigatureSection,
    deadkeys: DeadkeySection,
}

impl Display for KlcFile {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_fmt(format_args!(
            "KBD\t{}\t\"{}\"\n\n",
            self.kbd, self.description
        ))?;
        f.write_fmt(format_args!("COPYRIGHT\t\"{}\"\n\n", self.copyright))?;
        f.write_fmt(format_args!("COMPANY\t\"{}\"\n\n", self.company))?;
        f.write_fmt(format_args!("LOCALENAME\t\"{}\"\n\n", self.locale_name))?;
        f.write_fmt(format_args!("LOCALEID\t\"{:08x}\"\n\n", self.locale_id))?;
        f.write_str("VERSION\t1.0\n\n")?;

        f.write_fmt(format_args!("{}", self.layout))?;
        f.write_fmt(format_args!("{}", self.ligatures))?;
        f.write_fmt(format_args!("{}", self.deadkeys))?;

        f.write_str(consts::FOOTER_CONTENT)?;

        f.write_str("\nDESCRIPTIONS\n\n")?;
        f.write_fmt(format_args!(
            "{:04x}\t{}\n\n",
            self.locale_id, self.description
        ))?;

        f.write_str("LANGUAGENAMES\n\n")?;
        let autonym = iso639::autonym::get(self.tag.primary_language())
            .map(|x| x.autonym.unwrap_or_else(|| x.name))
            .unwrap_or("Undefined");
        f.write_fmt(format_args!("{:04x}\t{}\n\n", self.locale_id, autonym))?;

        f.write_str("ENDKBD\n")?;
        Ok(())
    }
}

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("IO error")]
    Io(#[from] std::io::Error),
}

pub fn generate(bundle: ProjectBundle, output_path: PathBuf) -> Result<(), Error> {
    std::fs::create_dir_all(&output_path)?;

    let klcs = bundle
        .layouts
        .iter()
        .filter(|(_, v)| v.modes.win.is_some())
        .map(|(name, layout)| {
            (
                name.clone(),
                generate_layout(&bundle, &name, &layout, layout.modes.win.as_ref().unwrap()),
            )
        })
        .collect::<IndexMap<_, _>>();

    for (tag, klc) in klcs {
        let bytes = klc.to_string().encode_utf16_le_bom();

        let klc_path = output_path.join(format!("{}.klc", klc.kbd));
        std::fs::write(klc_path, bytes)?;
    }

    Ok(())
}

pub fn build(bundle: ProjectBundle, project_path: PathBuf) {}

fn generate_layout(
    bundle: &ProjectBundle,
    tag: &LanguageTag,
    layout: &Layout,
    mode: &DesktopModes,
) -> KlcFile {
    log::trace!("Name: {:?} mode: {:?}", &tag, &mode);

    let target = layout.targets.as_ref().and_then(|x| x.win.as_ref());
    let rows = derive_rows(layout, mode);

    let mut ligatures = vec![];
    let mut dead_keys = vec![];

    for row in rows.iter() {
        ligatures.append(&mut row.ligatures());
        dead_keys.append(&mut row.dead_keys());
    }

    let ligature_section = LigatureSection { ligatures };
    let deadkey_section = DeadkeySection {
        dead_keys,
        transforms: layout.transforms.clone(),
    };
    let layout_section = LayoutSection {
        rows,
        decimal: Char::new(
            layout
                .decimal
                .as_ref()
                .map(|x| x.chars().next().unwrap())
                .unwrap_or('.'),
        ),
    };

    let description = layout.native_name(tag.as_str()).unwrap();
    let copyright = bundle.project.copyright.to_string();
    let company = bundle.project.organisation.to_string();
    let kbd = format!(
        "kbd{}",
        target
            .and_then(|t| t.id.as_ref())
            .map(|x| x.to_string())
            .unwrap_or_else(|| tag.as_str().chars().take(5).collect::<String>())
    );

    let lcid = iso639::lcid::get(tag.primary_language(), tag.script(), tag.region());

    let locale_id = match lcid {
        Some(r) => r.lcid,
        None => 0x2000,
    };

    let locale_name = target
        .map(|t| t.locale.to_string())
        .unwrap_or_else(|| match lcid {
            Some(_) => tag.to_string(),
            None => format!(
                "{}-{}-{}",
                tag.primary_language(),
                tag.script().unwrap_or("Latn"),
                tag.region().unwrap_or("001")
            ),
        });

    KlcFile {
        tag: tag.to_owned(),
        kbd,
        description,
        copyright,
        company,
        locale_name,
        locale_id,
        layout: layout_section,
        ligatures: ligature_section,
        deadkeys: deadkey_section,
    }
}
