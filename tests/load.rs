use kbdgen::{Load, ProjectBundle};

#[test]
fn load_fixtures() {
    let bundle = ProjectBundle::load("examples/sme.kbdgen").unwrap();
    eprintln!("{:?}", bundle);
}
