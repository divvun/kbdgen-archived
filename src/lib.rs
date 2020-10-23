pub mod bundle;
pub mod cldr;
pub mod cli;
pub mod m17n_mim;
pub mod xkb;

pub use bundle::*;

pub(crate) mod pad;
pub(crate) mod utils;

use std::{convert::TryFrom, convert::TryInto, path::PathBuf, sync::Arc};

use pahkat_client::{PackageStore, InstallTarget, config::RepoRecord, package_store::prefix::PrefixPackageStore, types::package_key::PackageKeyParams};
use pahkat_client::transaction::{PackageAction, PackageTransaction};
use pahkat_client::types::{repo::RepoUrl, PackageKey};

use futures::stream::StreamExt;

pub fn prefix_dir() -> PathBuf {
    let kbdgen_data = pathos::user::app_data_dir("kbdgen").unwrap();
    kbdgen_data.join("prefix")
}

async fn create_prefix() -> Arc<PrefixPackageStore> {
    let prefix_path = prefix_dir();
    let mut prefix = PrefixPackageStore::open_or_create(prefix_path).await.unwrap();
    let mut config = prefix.config();
    let mut config = config.write().unwrap();
    let mut repos = config.repos_mut();
    repos.insert("https://pahkat.uit.no/devtools/".parse().unwrap(), RepoRecord { channel: Some("nightly".into()) }).unwrap();
    
    Arc::new(prefix)
}

async fn install_kbdi() {
    log::info!("Updating 'kbdi' and 'kbdi-legacy'...");

    let store = create_prefix().await;
    
    let repo_url: RepoUrl = "https://pahkat.uit.no/devtools/".parse().unwrap();
    
    let pkg_key_kbdi = PackageKey::new_unchecked(repo_url.clone(), "kbdi".to_string(), Some(PackageKeyParams {
        channel: Some("nightly".to_string()),
        ..Default::default()
    }));
    let pkg_key_kbdi_legacy = PackageKey::new_unchecked(repo_url.clone(), "kbdi-legacy".to_string(), Some(PackageKeyParams {
        channel: Some("nightly".to_string()),
        ..Default::default()
    }));

    let actions = vec![
        PackageAction::install(pkg_key_kbdi, InstallTarget::System),
        PackageAction::install(pkg_key_kbdi_legacy, InstallTarget::System)
    ];

    let tx = PackageTransaction::new(store, actions).unwrap();
    let (_, mut stream) = tx.process();
    
    while let Some(value) = stream.next().await {
        println!("{:?}", value);
    }
}

pub fn install_kbdi_blocking() {
    let mut rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(install_kbdi());
}
