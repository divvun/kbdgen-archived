pub trait UnwrapOrUnknownExt {
    fn unwrap_or_unknown(self) -> String;
}

impl UnwrapOrUnknownExt for Option<String> {
    fn unwrap_or_unknown(self) -> String {
        self.unwrap_or_else(|| "<unknown>".into())
    }
}
