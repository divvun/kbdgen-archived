# kbdgen-rs

Rust implementation of parts of [kbdgen] (keyboard generator).

## Implemented features

The main functionality of this crate is loading and saving of `*.kbdgen`
bundles.

Using `ProjectBundle::load`, you can easily read in a given keyboard package and
get its representation as Rust struct. Writing such a structure to disk (using
`ProjectBundle::save`) will generate a valid `.kbdgen` bundle that should
consist of human-readable YAML (d͡ʒæ​mɭ) files.

See the `examples/` for a working and tested API demonstration.

## License

Licensed under either of

 * Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE) or http://www.apache.org/licenses/LICENSE-2.0)
 * MIT license ([LICENSE-MIT](LICENSE-MIT) or http://opensource.org/licenses/MIT)

at your option.

## Contribution

Fork & PR on Github.

Unless you explicitly state otherwise, any contribution intentionally submitted
for inclusion in the work by you, as defined in the Apache-2.0 license, shall be dual licensed as above, without any
additional terms or conditions.


[kbdgen]: https://github.com/divvun/kbdgen
