use std::fmt::Display;

use indexmap::IndexMap;

use super::key::Char;

pub(super) struct DeadkeySection {
    pub transforms: IndexMap<String, IndexMap<String, String>>,
    pub dead_keys: Vec<Char>,
}

impl Display for DeadkeySection {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        if self.dead_keys.is_empty() {
            return Ok(());
        }

        for dk in &self.dead_keys {
            let transforms = match self.transforms.get(&dk.into_inner().to_string()) {
                Some(v) => v,
                None => {
                    log::error!("No transforms for deadkey {}", dk);
                    continue;
                }
            };

            f.write_fmt(format_args!("DEADKEY {:x}\n\n", dk))?;

            for (k, v) in transforms {
                if k == " " {
                    continue;
                }

                let k16 = k.encode_utf16().collect::<Vec<_>>();
                let v16 = v.encode_utf16().collect::<Vec<_>>();

                if k16.len() > 1 || v16.len() > 1 {
                    // log::error!("Key or value of transform too long: {} {}", k, v);
                    continue;
                }

                f.write_fmt(format_args!("{:04x}\t{:04x}\n", k16[0], v16[0]))?;
            }

            let default = transforms
                .get(" ")
                .and_then(|x| x.encode_utf16().nth(0))
                .unwrap_or_else(|| dk.into_inner().to_string().encode_utf16().nth(0).unwrap());
            f.write_fmt(format_args!("0020\t{:04x}\n\n", default))?;
        }

        Ok(())
    }
}
