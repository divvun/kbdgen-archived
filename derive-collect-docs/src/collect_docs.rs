use proc_macro::TokenStream;
use quote::{quote, quote_spanned};
use std::{fs::File, io::BufWriter, path::PathBuf};
use syn::{parse_macro_input, spanned::Spanned, Data, DataStruct, DeriveInput};

use crate::to_adoc::ToAdoc;

pub fn derive(input: TokenStream) -> TokenStream {
    let input = parse_macro_input!(input as DeriveInput);

    // Write some nice AsciiDoc output
    let r#struct = Struct {
        name: input.ident.to_string(),
        docs: collect_docs_from_attrs(&input.attrs),
        examples: collect_examples_from_attrs(&input.attrs),
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

    // Let's test those examples
    let struct_examples = r#struct.examples.iter().enumerate().map(|(idx, ex)| {
        let typ = &input.ident;
        let test_fn_name = syn::Ident::new(
            &format!("test_{}_example_{}", input.ident, idx),
            input.ident.span(),
        );
        let content = &ex.content;
        match ex.lang.as_str() {
            "yaml" | "yml" => {
                quote! {
                    #[test]
                    fn #test_fn_name() {
                        let input = #content;
                        let _result: #typ = serde_yaml::from_str(&input).unwrap();
                    }
                }
            }
            _ => quote! {},
        }
    });
    let field_examples = r#struct
        .fields
        .iter()
        .flat_map(|field| field.examples.iter().map(move |ex| (field, ex)))
        .enumerate()
        .map(|(idx, (field, ex))| {
            let typ = &field.raw_type;
            let test_fn_name = syn::Ident::new(
                &format!("test_{}_{}_example_{}", input.ident, field.name, idx),
                input.ident.span(),
            );
            let field_name = syn::Ident::new(&field.name, field.span);
            let attrs = &field.serde_attrs;
            let content = &ex.content;
            match ex.lang.as_str() {
                "yaml" | "yml" => {
                    quote_spanned! { field.span =>
                        #[test]
                        fn #test_fn_name() {
                            #[derive(Debug, Serialize, Deserialize)]
                            struct TestHelper {
                                #(#attrs)*
                                #field_name: #typ,
                            }

                            let input = #content;
                            let _result: TestHelper = serde_yaml::from_str(&input).unwrap();
                        }
                    }
                }
                _ => quote! {},
            }
        });

    TokenStream::from(quote! {
        #(#struct_examples)*
        #(#field_examples)*
    })
}

#[derive(Debug)]
pub(crate) struct Struct {
    pub(crate) name: String,
    pub(crate) docs: String,
    pub(crate) examples: Vec<Example>,
    pub(crate) fields: Vec<Field>,
}

#[derive(Debug)]
pub(crate) struct Field {
    pub(crate) name: String,
    pub(crate) docs: String,
    pub(crate) examples: Vec<Example>,
    pub(crate) required: bool,
    pub(crate) r#type: Type,
    // some helper fields for generating tests for examples
    raw_type: syn::Type,
    span: proc_macro2::Span,
    serde_attrs: Vec<syn::Attribute>,
}

#[derive(Debug)]
pub(crate) struct Example {
    pub(crate) lang: String,
    pub(crate) content: String,
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
            fields: fields @ syn::Fields::Unnamed(..),
            ..
        })
        | Data::Struct(DataStruct {
            fields: fields @ syn::Fields::Named(..),
            ..
        }) => fields
            .iter()
            .filter(|f| {
                if let syn::Visibility::Public(..) = f.vis {
                    true
                } else {
                    false
                }
            })
            .enumerate()
            .map(|(idx, field)| {
                let (required, r#type) = Type::toplevel_from_syn(&field.ty);
                Field {
                    name: field
                        .ident
                        .as_ref()
                        .map(|f| f.to_string())
                        .unwrap_or(format!("unnamed internal field #{}", idx)),
                    docs: collect_docs_from_attrs(&field.attrs),
                    examples: collect_examples_from_attrs(&field.attrs),
                    required,
                    r#type,
                    raw_type: field.ty.clone(),
                    span: field.span(),
                    serde_attrs: field
                        .attrs
                        .iter()
                        .filter(|attr| attr.path.is_ident("serde"))
                        .cloned()
                        .collect(),
                }
            })
            .collect(),
        _ => vec![],
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

            // dbg!(attr.parse_meta());

            let doc = TokenStream::from(attr.tokens.clone()).to_string();

            static RE: Lazy<Regex> =
                Lazy::new(|| regex::Regex::new(r#"^\s*=\s*"\s?(?P<content>.*?)"\s*$"#).unwrap());
            let doc = RE.replace_all(&doc, "$content");

            writeln!(&mut res, "{}", unescape_literal(&doc)).unwrap();
            res
        })
}

fn collect_examples_from_attrs(attrs: &[syn::Attribute]) -> Vec<Example> {
    use unindent::unindent;

    attrs
        .iter()
        .filter(|attr| attr.path.is_ident("example"))
        .map(|attr| {
            let list: Vec<syn::NestedMeta> = match attr.parse_meta() {
                Ok(syn::Meta::List(syn::MetaList { nested, .. })) => {
                    nested.iter().cloned().collect()
                }
                _ => unimplemented!("can't parse example attribute"),
            };
            assert_eq!(
                list.len(),
                2,
                "example attribute must be of form `#[example(lang_ident, \"lorem: ipsum\")]`"
            );
            // let (lang, example) = (&list[0], &list[1]);
            let lang = match &list[0] {
                syn::NestedMeta::Meta(syn::Meta::Path(syn::Path { segments, .. })) => {
                    segments.iter().next().unwrap().ident.to_string()
                }
                _ => unimplemented!("can't read lang of {:?}", list[0]),
            };
            let content = match &list[1] {
                syn::NestedMeta::Lit(syn::Lit::Str(val)) => unindent(&val.value()),
                _ => unimplemented!("can't content lang of {:?}", list[1]),
            };

            Example { lang, content }
        })
        .collect()
}

fn unescape_literal(lit: &str) -> String {
    lit.replace("\\\"", "\"")
        .replace("\\'", "'")
        .replace(r"\\", r"\")
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
