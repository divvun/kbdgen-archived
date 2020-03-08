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
    Flat(TypeName),
    Nested {
        container_name: TypeName,
        nested: Vec<Type>,
    },
}

#[derive(Debug)]
pub enum TypeName {
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
                let (required, r#type) = Type::toplevel_from_syn(&field.ty);
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
            use once_cell::sync::Lazy;
            use regex::Regex;
            use std::fmt::Write;

            let doc = TokenStream::from(attr.tokens.clone()).to_string();

            static RE: Lazy<Regex> =
                Lazy::new(|| regex::Regex::new(r#"^\s*=\s*"\s?(?P<content>.*?)"\s*$"#).unwrap());
            let doc = RE.replace_all(&doc, "$content");

            let doc = doc
                .replace("\\\"", "\"")
                .replace("\\'", "'")
                .replace(r"\\", r"\");
            writeln!(&mut res, "{}", doc).unwrap();
            res
        })
}

impl TypeName {
    fn from_ident(ident: &str) -> Self {
        match ident {
            "bool" | "u8" | "i8" | "u16" | "i16" | "u32" | "i32" | "u64" | "i64" | "usize"
            | "isize" | "String" | "PathBuf" | "Vec" | "HashMap" | "BTreeMap" | "T" => {
                Self::Primitive(ident.to_string())
            }
            _ => Self::Link(ident.to_string()),
        }
    }
}

impl Type {
    fn toplevel_from_syn(t: &syn::Type) -> (bool, Type) {
        use syn::Type as T;
        let mut required = true;

        let type_name = match t {
            T::Path(syn::TypePath {
                path: syn::Path { segments, .. },
                ..
            }) => {
                let syn::PathSegment { ident, arguments } =
                    segments.last().expect("type path was empty");

                // Do a little dance to not print the other `Option` wrapper but emit `required=false`
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
                            Type::from_syn(&type_arg)
                        }
                        _ => unimplemented!(
                            "only type paths with regular `<T>`-style generics implemented so far"
                        ),
                    }
                } else {
                    Type::from_syn(t)
                }
            }
            _ => unimplemented!("only type paths implemented so far"),
        };

        (required, type_name)
    }

    fn from_syn(t: &syn::Type) -> Self {
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
                        .map(Type::from_syn)
                        .collect::<Vec<_>>(),
                    _ => unimplemented!(
                        "only type paths with regular `<T>`-style generics implemented so far"
                    ),
                };

                let name = TypeName::from_ident(&ident.to_string());

                if args.is_empty() {
                    Type::Flat(name)
                } else {
                    Type::Nested {
                        container_name: name,
                        nested: args,
                    }
                }
            }
            _ => unimplemented!("only type paths implemented so far"),
        }
    }
}
