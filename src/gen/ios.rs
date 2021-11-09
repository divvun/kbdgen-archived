use std::collections::HashMap;

use once_cell::sync::Lazy;

static LEGACY_NAMES: Lazy<HashMap<String, String>> = Lazy::new(|| HashMap::new());
