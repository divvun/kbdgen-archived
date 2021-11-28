pub mod bundle;
pub mod cldr;
pub mod cli;
pub mod m17n_mim;
pub mod xkb;

pub mod gen;

pub use bundle::*;

pub(crate) mod pad;
pub(crate) mod utils;

use std::{convert::TryInto, path::PathBuf, sync::Arc};

use pahkat_client::transaction::{PackageAction, PackageTransaction};
use pahkat_client::types::{repo::RepoUrl, PackageKey};
use pahkat_client::{
    config::RepoRecord, package_store::prefix::PrefixPackageStore,
    types::package_key::PackageKeyParams, InstallTarget, PackageStore,
};

use futures::stream::StreamExt;

pub fn prefix_dir() -> PathBuf {
    let kbdgen_data = pathos::user::app_data_dir("kbdgen").unwrap();
    kbdgen_data.join("prefix")
}

async fn create_prefix() -> Arc<dyn PackageStore> {
    let prefix_path = prefix_dir();
    let prefix = PrefixPackageStore::open_or_create(&prefix_path)
        .await
        .unwrap();
    let config = prefix.config();

    let mut config = config.write().unwrap();
    let settings = config.settings_mut();
    settings
        .set_cache_dir(
            pathos::user::app_cache_dir("kbdgen")
                .unwrap()
                .try_into()
                .unwrap(),
        )
        .unwrap();
    settings
        .set_tmp_dir(
            pathos::user::app_temporary_dir("kbdgen")
                .unwrap()
                .try_into()
                .unwrap(),
        )
        .unwrap();

    let repos = config.repos_mut();
    repos
        .insert(
            "https://pahkat.uit.no/devtools/".parse().unwrap(),
            RepoRecord {
                channel: Some("nightly".into()),
            },
        )
        .unwrap();
    drop(prefix);

    // We can't just refresh repos because it locks up, reason unknown.
    let prefix = PrefixPackageStore::open(&prefix_path).await.unwrap();
    Arc::new(prefix)
}
