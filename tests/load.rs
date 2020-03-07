use kbdgen::{Load, ProjectBundle};

#[test]
fn load_fixtures() {
    let bundle = ProjectBundle::load("tests/fixtures/sme.kbdgen").unwrap();
    eprintln!("{:?}", bundle);
}
