use kbdgen::{Load, ProjectBundle};
use snafu::ErrorCompat;

fn main() {
    let path = std::env::args()
        .nth(1)
        .expect("Pass path to `.kbdgen` bundle as argument");

    match ProjectBundle::load(&path) {
        Ok(bundle) => eprintln!("{:#?}", bundle),
        Err(e) => {
            eprintln!("An error occurred: {}", e);
            if let Some(backtrace) = ErrorCompat::backtrace(&e) {
                println!("{}", backtrace);
            }
        }
    }
}
