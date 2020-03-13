use derive_collect_docs::CollectDocs;
use std::collections::HashMap;

/// Very essential type to out application
#[example(
    yaml,
    "
    bar: 42
    baz:
      great_examples_so_far: 2
    "
)]
#[derive(Debug, serde::Deserialize, CollectDocs)]
pub struct Foo {
    /// Amount of pressure to apply
    ///
    /// CAUTION: Will be renamed to appropriate SI unit in next release.
    pub bar: usize,
    /// Description of this Foo
    #[example(
        yaml,
        "
    baz:
      great_examples_so_far: 2
    "
    )]
    pub baz: HashMap<String, i32>,
}

fn main() {}
