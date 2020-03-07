use proc_macro::TokenStream;
use quote::quote;
use std::{fs::File, io::BufWriter, path::PathBuf};
use syn::{parse_macro_input, Data, DataStruct, DeriveInput};

use crate::to_adoc::ToAdoc;

pub fn derive(input: TokenStream) -> TokenStream {
    let input = parse_macro_input!(input as DeriveInput);

    let r#struct = Struct {
        name: input.ident.to_string(),
        docs: collect_docs_from_attrs(&input.attrs),
        fields: collect_fields(&input.data),
    };
    let adoc = adoc_output_path(&input.ident);
    let mut file =
        BufWriter::new(File::create(&adoc).expect(&format!("cannot write to {}", adoc.display())));
    r#struct.write_adoc(&mut file).expect(&format!(
        "cannot write {} as asciidoc to {}",
        r#struct.name,
        adoc.display()
    ));

    TokenStream::from(quote! {})
}

#[derive(Debug)]
pub(crate) struct Struct {
    pub(crate) name: String,
    pub(crate) docs: String,
    pub(crate) fields: Vec<Field>,
}

#[derive(Debug)]
pub(crate) struct Field {
    pub(crate) name: String,
    pub(crate) docs: String,
    pub(crate) required: bool,
    pub(crate) r#type: Type,
}

#[derive(Debug)]
pub(crate) enum Type {
    Primitive(String),
    Link(String),
}

fn adoc_output_path(name: &syn::Ident) -> PathBuf {
    let target = std::env::var("COLLECT_DOCS_TARGET").unwrap_or("./docs/generated".into());
    std::fs::create_dir_all(&target).expect(&format!("could not create directory {}", target));
    PathBuf::from(&target)
        .join(name.to_string())
        .with_extension("adoc")
}

fn collect_fields(data: &Data) -> Vec<Field> {
    match data {
        Data::Struct(DataStruct {
            fields: syn::Fields::Unit,
            ..
        }) => vec![],
        Data::Struct(DataStruct {
            fields: syn::Fields::Unnamed(..),
            ..
        }) => vec![],
        Data::Struct(DataStruct {
            fields: syn::Fields::Named(fields),
            ..
        }) => fields
            .named
            .iter()
            .map(|field| {
                let (required, r#type) = Type::from_syn(&field.ty);
                Field {
                    name: field
                        .ident
                        .as_ref()
                        .expect(&format!("struct field `{:?}` has no name", field))
                        .to_string(),
                    docs: collect_docs_from_attrs(&field.attrs),
                    required,
                    r#type,
                }
            })
            .collect(),
        _ => unimplemented!("Can only collect docs for structs for now"),
    }
}

fn collect_docs_from_attrs(attrs: &[syn::Attribute]) -> String {
    attrs
        .iter()
        .filter(|attr| attr.path.is_ident("doc"))
        .fold(String::new(), |mut res, attr| {
            use std::fmt::Write;

            let doc = attr
                .tokens
                .clone()
                .into_iter()
                .nth(1)
                .map(|lit| lit.to_string())
                .unwrap_or_default();
            let doc = doc.trim_start_matches("\"").trim().trim_end_matches("\"");
            writeln!(&mut res, "{}", doc).unwrap();
            res
        })
}

impl Type {
    fn from_ident(ident: &str) -> Self {
        match ident {
            "bool"
            | "u8" | "i8" | "u16" | "i16" | "u32" | "i32" | "u64" | "i64" | "usize" | "isize"
            | "String" | "PathBuf"
            | "HashMap" | "BTreeMap"
            | "T"
            => Type::Primitive(ident.to_string()),
            _ => Type::Link(ident.to_string()),
        }
    }

    fn from_syn(t: &syn::Type) -> (bool, Type) {
        use syn::Type as T;
        let mut required = true;

        let type_name = match t {
            T::Path(syn::TypePath {
                path: syn::Path { segments, .. },
                ..
            }) => {
                let syn::PathSegment { ident, arguments } =
                    segments.last().expect("type path was empty");

                if ident == "Option" {
                    required = false;
                    match arguments {
                        syn::PathArguments::AngleBracketed(
                            syn::AngleBracketedGenericArguments { args, .. },
                        ) => {
                            let type_arg = args
                                .iter()
                                .filter_map(|arg| {
                                    if let syn::GenericArgument::Type(t) = arg {
                                        Some(t)
                                    } else {
                                        None
                                    }
                                })
                                .next()
                                .expect("no type param on `Option`");
                            Type::from_ident(&syn_type_to_string(&type_arg))
                        }
                        _ => unimplemented!(
                            "only type paths with regular `<T>`-style generics implemented so far"
                        ),
                    }
                } else {
                    Type::from_ident(&ident.to_string())
                }
            }
            _ => unimplemented!("only type paths implemented so far"),
        };

        (required, type_name)
    }
}

fn syn_type_to_string(t: &syn::Type) -> String {
    use syn::Type as T;

    match t {
        T::Path(syn::TypePath {
            path: syn::Path { segments, .. },
            ..
        }) => {
            let syn::PathSegment { ident, arguments } =
                segments.last().expect("type path was empty");

            let args = match arguments {
                syn::PathArguments::None => vec![],
                syn::PathArguments::AngleBracketed(syn::AngleBracketedGenericArguments {
                    args,
                    ..
                }) => args
                    .iter()
                    .filter_map(|arg| {
                        if let syn::GenericArgument::Type(t) = arg {
                            Some(t)
                        } else {
                            None
                        }
                    })
                    .map(syn_type_to_string)
                    .collect::<Vec<_>>(),
                _ => unimplemented!(
                    "only type paths with regular `<T>`-style generics implemented so far"
                ),
            };
            if args.is_empty() {
                ident.to_string()
            } else {
                format!("{}<{}>", ident, args.join(","))
            }
        }
        _ => unimplemented!("only type paths implemented so far"),
    }
}
