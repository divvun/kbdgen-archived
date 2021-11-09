use std::path::PathBuf;
use structopt::{clap::AppSettings::*, StructOpt};

#[derive(Debug, StructOpt)]
enum IOSCommands {
    Init,
    Ids,
}

#[derive(Debug, StructOpt)]
enum BuildCommands {
    #[structopt(about = "Demonstration SVG output for debugging")]
    Svg {
        #[structopt(flatten)]
        in_out: InOutPaths,
    },

    #[structopt(about = "Generates an .apk for Android")]
    Android {
        #[structopt(long = "kbd-repo", default_value = "divvun/giellakbd-android")]
        kbd_repo: String,

        #[structopt(long = "kbd-branch", default_value = "main")]
        kbd_branch: String,

        #[structopt(long = "divvunspell-repo", default_value = "divvun/divvunspell")]
        divvunspell_repo: String,

        #[structopt(long = "divvunspell-branch", default_value = "main")]
        divvunspell_branch: String,

        #[structopt(flatten)]
        in_out: InOutPaths,

        #[structopt(short = "D", long = "dry-run")]
        dry_run: bool,

        #[structopt(long)]
        local: bool,

        #[structopt(flatten)]
        build_mode: BuildMode,
    },

    #[cfg(target_os = "macos")]
    #[structopt(about = "Generates an .ipa for iOS")]
    IOS {
        #[structopt(subcommand)]
        command: Option<IOSCommands>,

        #[structopt(long = "kbd-repo", default_value = "divvun/giellakbd-ios")]
        kbd_repo: String,

        #[structopt(long = "kbd-branch", default_value = "main")]
        kbd_branch: String,

        #[structopt(flatten)]
        in_out: InOutPaths,

        #[structopt(short = "D", long = "dry-run")]
        dry_run: bool,

        #[structopt(flatten)]
        build_mode: BuildMode,
    },

    #[structopt(about = "Generates installers for Windows.")]
    Win {
        #[structopt(flatten)]
        in_out: InOutPaths,

        #[structopt(short = "D", long = "dry-run")]
        dry_run: bool,

        #[structopt(flatten)]
        build_mode: BuildMode,

        #[structopt(long = "legacy", help = "Build installers for Windows 8 and older.")]
        build_legacy: bool,
    },

    #[cfg(target_os = "macos")]
    #[structopt(about = "Generates installers for macOS")]
    Mac {
        #[structopt(flatten)]
        in_out: InOutPaths,

        #[structopt(short = "D", long = "dry-run")]
        dry_run: bool,

        #[structopt(flatten)]
        build_mode: BuildMode,
    },

    #[structopt(about = "Generates X11 (XKB) output")]
    X11 {
        #[structopt(flatten)]
        in_out: InOutPaths,

        #[structopt(flatten)]
        build_mode: BuildMode,

        #[structopt(long = "standalone")]
        standalone: bool,
    },

    #[structopt(about = "Generates m17n output")]
    M17n {
        #[structopt(flatten)]
        in_out: InOutPaths,

        #[structopt(flatten)]
        build_mode: BuildMode,
    },

    #[structopt(about = "Generates Chrome OS bundles for putting on the Chrome App Store")]
    Chrome {
        #[structopt(flatten)]
        in_out: InOutPaths,

        #[structopt(flatten)]
        build_mode: BuildMode,
    },

    #[structopt(setting(Hidden))]
    Qr {
        #[structopt(flatten)]
        in_out: InOutPaths,

        #[structopt(short, long = "layout")]
        layout: String,
    },

    #[structopt(
        about = "Generates a key distance error model from the ios default layout of the input kbdgen project and outputs it in ATT format"
    )]
    ErrorModel {
        #[structopt(flatten)]
        in_out: InOutPaths,

        #[structopt(short, long = "layout")]
        layout: String,
    },
}

#[derive(Debug, StructOpt)]
struct InOutPaths {
    #[structopt(short, long = "output", default_value = ".", parse(from_os_str))]
    output_path: PathBuf,

    #[structopt(parse(from_os_str))]
    project_path: PathBuf,
}

#[derive(Debug, StructOpt)]
struct BuildMode {
    /// Compile in 'release' mode (where necessary).
    #[structopt(short = "R", long = "release")]
    release: bool,

    /// Continuous integration build
    #[structopt(long = "ci")]
    ci: bool,
}

#[derive(Debug, StructOpt)]
enum NewCommands {
    Layout {
        #[structopt(short, long = "output", default_value = ".", parse(from_os_str))]
        output_path: PathBuf,

        #[structopt(parse(from_os_str))]
        project_path: PathBuf,
    },
    Bundle {
        #[structopt(short, long = "output", default_value = ".", parse(from_os_str))]
        output_path: PathBuf,

        bundle_name: String,
    },
}

#[derive(Debug, StructOpt)]
enum MetaCommands {
    Fetch { target: PathBuf },
}

#[derive(Debug, StructOpt)]
enum Commands {
    #[structopt(
        about = "Generate output for a given .kbdgen bundle",
        setting(DisableHelpSubcommand)
    )]
    Build {
        #[structopt(long = "github-username")]
        github_username: Option<String>,

        #[structopt(long = "github-token")]
        github_token: Option<String>,

        #[structopt(subcommand)]
        command: BuildCommands,
    },
    #[structopt(
        about = "Generate new bundles or layout templates",
        setting(DisableHelpSubcommand)
    )]
    New {
        #[structopt(subcommand)]
        command: NewCommands,
    },
    #[structopt(about = "Manage meta-bundles", setting(DisableHelpSubcommand))]
    Meta {
        #[structopt(subcommand)]
        command: MetaCommands,
    },
}

#[derive(Debug, StructOpt)]
#[structopt(
    name = "kbdgen",
    about = "The best solution to generating keyboards.",
    setting(DisableHelpSubcommand)
)]
struct Opts {
    #[structopt(long = "logging", default_value = "info")]
    logging: String,

    #[structopt(subcommand)]
    command: Commands,
}

#[tokio::main]
async fn main() {
    let opt = Opts::from_args();

    let logging = match &*opt.logging {
        "trace" => log::Level::Trace,
        "debug" => log::Level::Debug,
        "info" => log::Level::Info,
        "warn" => log::Level::Warn,
        "error" => log::Level::Error,
        x => {
            eprintln!("Invalid logging level: {}", x);
            std::process::exit(1);
        }
    };

    env_logger::Builder::from_default_env()
        .filter(Some("kbdgen"), logging.to_level_filter())
        .target(env_logger::Target::Stderr)
        .init();

    // info!("logging mode {}", logging);

    std::env::set_var("RUST_LOG", logging.to_string());

    match opt.command {
        Commands::Build {
            github_username,
            github_token,
            command,
        } => match command {
            BuildCommands::X11 {
                in_out:
                    InOutPaths {
                        output_path,
                        project_path,
                    },
                build_mode: BuildMode { .. },
                standalone,
            } => kbdgen::cli::to_xkb::kbdgen_to_xkb(
                &project_path,
                &output_path,
                &kbdgen::cli::to_xkb::Options { standalone },
            )
            .unwrap(),
            BuildCommands::M17n {
                in_out:
                    InOutPaths {
                        output_path,
                        project_path,
                    },
                build_mode: BuildMode { .. },
            } => kbdgen::cli::to_m17n_mim::kbdgen_to_mim(&project_path, &output_path).unwrap(),
            BuildCommands::ErrorModel {
                in_out:
                    InOutPaths {
                        output_path,
                        project_path,
                    },
                layout,
            } => kbdgen::cli::to_errormodel::kbdgen_to_errormodel(
                &project_path,
                &output_path,
                &kbdgen::cli::to_errormodel::Options { layout },
            )
            .unwrap(),
            BuildCommands::Svg { in_out } => todo!(),
            BuildCommands::Android {
                kbd_repo,
                kbd_branch,
                divvunspell_repo,
                divvunspell_branch,
                in_out,
                dry_run,
                local,
                build_mode,
            } => todo!(),
            BuildCommands::IOS {
                command,
                kbd_repo,
                kbd_branch,
                in_out,
                dry_run,
                build_mode,
            } => todo!(),
            BuildCommands::Win {
                in_out,
                dry_run,
                build_mode,
                build_legacy,
            } => todo!(),
            BuildCommands::Mac {
                in_out,
                dry_run,
                build_mode,
            } => todo!(),
            BuildCommands::Chrome { in_out, build_mode } => todo!(),
            BuildCommands::Qr { in_out, layout } => todo!(),
        },

        Commands::New { command } => match command {
            NewCommands::Bundle {
                bundle_name,
                output_path,
            } => match kbdgen::cli::from_cldr::cldr_to_kbdgen(&*output_path, &*bundle_name) {
                Ok(_) => std::process::exit(0),
                Err(e) => {
                    eprintln!("{:?}", e);
                    std::process::exit(1);
                }
            },
            NewCommands::Layout { .. } => {
                eprintln!("Not yet supported.");
                std::process::exit(1)
            }
        },

        Commands::Meta { command } => match command {
            MetaCommands::Fetch { target } => match meta::fetch(target).await {
                Ok(_) => {}
                Err(e) => {
                    eprintln!("ERROR: {:?}", e);
                    std::process::exit(1)
                }
            },
        },
    }
}

pub(crate) mod meta {
    use super::*;
    use indexmap::IndexMap;
    use serde::{Deserialize, Serialize};

    pub async fn fetch(target: PathBuf) -> anyhow::Result<()> {
        let config = target.join("meta.toml");
        log::info!("Fetching {} for {}...", config.display(), target.display());
        log::debug!("Reading config");
        let config = std::fs::read_to_string(config)?;
        log::debug!("Parsing config");
        let config: meta::MetaBundle = toml::from_str(&config)?;

        log::debug!("Create layouts dir");
        std::fs::create_dir_all(target.join("layouts"))?;

        for (id, bundle) in config.bundle {
            log::debug!("id: {}, bundle: {:?}", &id, &bundle);
            let branch = bundle.branch.unwrap_or_else(|| "main".into());
            let url = format!(
                "https://github.com/{}/archive/{}.zip",
                bundle.github, &branch
            );

            let tempdir = tempfile::tempdir()?;

            log::info!("Downloading {}...", id);
            let bytes = reqwest::get(url).await?.bytes().await?;
            let bytes = std::io::Cursor::new(bytes);
            let mut zipfile = zip::ZipArchive::new(bytes)?;

            log::info!("Unzipping {}...", id);
            zipfile.extract(tempdir.path())?;

            let kbdgen_path = tempdir
                .path()
                .join(format!(
                    "{}-{}",
                    bundle.github.split("/").nth(1).unwrap(),
                    branch.replace("/", "-")
                ))
                .join(format!("{}.kbdgen", id));

            for layout in bundle.layouts {
                let from_path = kbdgen_path.join("layouts").join(format!("{}.yaml", layout));
                let to_path = target.join("layouts").join(format!("{}.yaml", layout));
                log::info!(
                    "Copying {} to {}...",
                    from_path.display(),
                    to_path.display()
                );
                std::fs::copy(from_path, to_path)?;
            }
        }

        Ok(())
    }

    #[derive(Debug, Serialize, Deserialize)]
    pub struct MetaRecord {
        github: String,
        layouts: Vec<String>,
        branch: Option<String>,
        #[serde(rename = "ref")]
        ref_: Option<String>,
    }

    #[derive(Debug, Serialize, Deserialize)]
    pub struct MetaBundle {
        bundle: IndexMap<String, MetaRecord>,
    }
}
