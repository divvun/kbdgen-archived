extern crate proc_macro;
use proc_macro::TokenStream;

mod collect_docs;
mod to_adoc;

#[proc_macro_derive(CollectDocs, attributes(example, doc))]
pub fn collect_docs(input: TokenStream) -> TokenStream {
    collect_docs::derive(input)
}
