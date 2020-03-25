use assert_cmd::Command;
use tempfile::tempdir;

#[test]
fn build_x11() {
    logger();
    let tmp = tempdir().unwrap();

    Command::cargo_bin("kbdgen")
        .unwrap()
        .arg("build")
        .arg("x11")
        .arg("examples/sme.kbdgen")
        .arg("--output")
        .arg(tmp.path())
        .assert()
        .success();

    assert!(tmp.path().join("linux").join("se-SE.xkb").exists());
}

#[test]
fn build_m17n() {
    logger();
    let tmp = tempdir().unwrap();

    Command::cargo_bin("kbdgen")
        .unwrap()
        .arg("build")
        .arg("m17n")
        .arg("examples/sme.kbdgen")
        .arg("--output")
        .arg(tmp.path())
        .assert()
        .success();

    assert!(tmp.path().join("se-SE").join("win.mim").exists());
}

pub fn logger() {
    let _ = env_logger::Builder::from_default_env()
        .filter(None, log::LevelFilter::Debug)
        .target(env_logger::Target::Stderr)
        .is_test(true)
        .try_init();
}
