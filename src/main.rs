use pyembed::{ExtensionModule, MainPythonInterpreter};
use std::path::PathBuf;
use structopt::{clap::AppSettings::*, StructOpt};

include!(env!("PYOXIDIZER_DEFAULT_PYTHON_CONFIG_RS"));

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

    #[structopt(about = "Generates installers for Windows 7/8 and 8.1+")]
    Win {
        #[structopt(flatten)]
        in_out: InOutPaths,

        #[structopt(short = "D", long = "dry-run")]
        dry_run: bool,

        #[structopt(flatten)]
        build_mode: BuildMode,
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
    Fetch {
        #[structopt(short, long)]
        config: PathBuf,
        target: PathBuf,
    }
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
    #[structopt(
        about = "Manage meta-bundles",
        setting(DisableHelpSubcommand)
    )]
    Meta {
        #[structopt(subcommand)]
        command: MetaCommands,
    },
    #[structopt(setting(Hidden))]
    Repl,
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

impl BuildCommands {
    fn to_py_args<'a>(
        &'a self,
        github_username: Option<&'a str>,
        github_token: Option<&'a str>,
        logging: &'a str,
    ) -> Result<Vec<&'a str>, Box<dyn std::error::Error>> {
        use BuildCommands::*;

        let mut args = match self {
            Svg {
                in_out:
                    InOutPaths {
                        output_path,
                        project_path,
                    },
            } => vec![
                "-t",
                "svg",
                "-o",
                &*output_path.to_str().unwrap(),
                &*project_path.to_str().unwrap(),
            ],
            Android {
                kbd_repo,
                kbd_branch,
                divvunspell_repo,
                divvunspell_branch,
                in_out:
                    InOutPaths {
                        output_path,
                        project_path,
                    },
                dry_run,
                local,
                build_mode: BuildMode { release, ci },
            } => {
                let mut args = vec![
                    "-t",
                    "android",
                    "--kbd-repo",
                    kbd_repo,
                    "--kbd-branch",
                    kbd_branch,
                    "--divvunspell-repo",
                    divvunspell_repo,
                    "--divvunspell-branch",
                    divvunspell_branch,
                    "-o",
                    &*output_path.to_str().unwrap(),
                ];

                if *release {
                    args.push("-R");
                }

                if *dry_run {
                    args.push("-D");
                }

                if *ci {
                    args.push("--ci");
                }

                if *local {
                    args.push("--local");
                }

                args.push(&*project_path.to_str().unwrap());

                args
            }
            #[cfg(target_os = "macos")]
            IOS {
                command,
                kbd_repo,
                kbd_branch,
                in_out:
                    InOutPaths {
                        output_path,
                        project_path,
                    },
                dry_run,
                build_mode: BuildMode { release, ci },
            } => {
                let mut args = vec![
                    "-t",
                    "ios",
                    "--kbd-repo",
                    kbd_repo,
                    "--kbd-branch",
                    kbd_branch,
                    "-o",
                    &*output_path.to_str().unwrap(),
                ];

                if *release {
                    args.push("-R");
                }

                if *dry_run {
                    args.push("-D");
                }

                if *ci {
                    args.push("--ci");
                }

                match command {
                    Some(IOSCommands::Init) => {
                        args.push("--command");
                        args.push("init");
                    }
                    Some(IOSCommands::Ids) => {
                        args.push("--command");
                        args.push("ids");
                    }
                    _ => {}
                }

                args.push(&*project_path.to_str().unwrap());
                args
            }
            Chrome {
                in_out:
                    InOutPaths {
                        output_path,
                        project_path,
                    },
                build_mode: BuildMode { release, ci },
            } => {
                let mut args = vec!["-t", "chrome", "-o", &*output_path.to_str().unwrap()];

                if *release {
                    args.push("-R");
                }

                if *ci {
                    args.push("--ci");
                }

                args.push(&*project_path.to_str().unwrap());
                args
            }
            Win {
                in_out:
                    InOutPaths {
                        output_path,
                        project_path,
                    },
                dry_run,
                build_mode: BuildMode { release, ci },
            } => {
                kbdgen::install_kbdi_blocking();

                let prefix_dir  = kbdgen::prefix_dir();
                let mut kbdi_pkg_path = prefix_dir.join("pkg").join("kbdi").join("bin").join("kbdi");
                let mut kbdi_legacy_pkg_path = prefix_dir.join("pkg").join("kbdi-legacy").join("bin").join("kbdi-legacy");

                if cfg!(windows) {
                    kbdi_pkg_path.set_extension("exe");
                    kbdi_legacy_pkg_path.set_extension("exe");
                }
                std::env::set_var("KBDI", kbdi_pkg_path);
                std::env::set_var("KBDI_LEGACY", kbdi_legacy_pkg_path);

                let mut args = vec!["-t", "win", "-o", &*output_path.to_str().unwrap()];

                if *release {
                    args.push("-R");
                }

                if *dry_run {
                    args.push("-D");
                }

                if *ci {
                    args.push("--ci");
                }

                args.push(&*project_path.to_str().unwrap());
                args
            }
            #[cfg(target_os = "macos")]
            Mac {
                in_out:
                    InOutPaths {
                        output_path,
                        project_path,
                    },
                dry_run,
                build_mode: BuildMode { release, ci },
            } => {
                let mut args = vec!["-t", "mac", "-o", &*output_path.to_str().unwrap()];

                if *release {
                    args.push("-R");
                }

                if *dry_run {
                    args.push("-D");
                }

                if *ci {
                    args.push("--ci");
                }

                args.push(&*project_path.to_str().unwrap());
                args
            }
            Qr {
                in_out:
                    InOutPaths {
                        output_path,
                        project_path,
                    },
                layout,
            } => vec![
                "-t",
                "qr",
                "-o",
                &*output_path.to_str().unwrap(),
                "--command",
                layout,
                &*project_path.to_str().unwrap(),
            ],
            ErrorModel { .. } | M17n { .. } | X11 { .. } => {
                unreachable!("covered in previous match")
            }
        };

        if let Some(gh_username) = github_username {
            args.push("--github-username");
            args.push(&*gh_username);
        }

        if let Some(gh_token) = github_token {
            args.push("--github-token");
            args.push(&*gh_token);
        }

        args.push("--logging");
        args.push(logging);

        Ok(args)
    }
}

fn python_config() -> pyembed::PythonConfig {
    let mut config = default_python_config();

    let mod_language_tags = ExtensionModule {
        name: std::ffi::CString::new("language_tags").unwrap(),
        init_func: py_language_tags::PyInit_language_tags,
    };

    let mod_logger = ExtensionModule {
        name: std::ffi::CString::new("rust_logger").unwrap(),
        init_func: py_logger::PyInit_rust_logger,
    };

    let mod_reqwest = ExtensionModule {
        name: std::ffi::CString::new("reqwest").unwrap(),
        init_func: py_reqwest::PyInit_reqwest,
    };

    config.extra_extension_modules = vec![mod_language_tags, mod_logger, mod_reqwest];
    config
}

fn launch_py_kbdgen(args: &[&str]) -> i32 {
    // Load the default Python configuration as derived by the PyOxidizer config
    // file used at build time.
    let config = python_config();

    // Construct a new Python interpreter using that config, handling any errors
    // from construction.
    match MainPythonInterpreter::new(config) {
        Ok(mut interp) => {
            // And run it using the default run configuration as specified by the
            // configuration. If an uncaught Python exception is raised, handle it.
            // This includes the special SystemExit, which is a request to terminate the
            // process.
            let args = format!(
                "[{}]",
                args.iter()
                    .map(|x| format!("{:?}", x))
                    .collect::<Vec<_>>()
                    .join(", ")
            );
            match interp.run_code(&format!("import kbdgen.cli; kbdgen.cli.run_cli({})", args)) {
                Ok(_) => 0,
                Err(msg) => {
                    let py = interp.acquire_gil();
                    msg.print(py);
                    1
                }
            }
        }
        Err(msg) => {
            eprintln!("{}", msg);
            1
        }
    }
}

fn launch_repl() -> i32 {
    let config = python_config();
    match MainPythonInterpreter::new(config) {
        Ok(mut interp) => match interp.run_repl() {
            Ok(_) => 0,
            Err(msg) => {
                let py = interp.acquire_gil();
                msg.print(py);
                1
            }
        },
        Err(msg) => {
            eprintln!("{}", msg);
            1
        }
    }
}

fn main() {
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
            } => {
                kbdgen::cli::to_errormodel::kbdgen_to_errormodel(
                    &project_path,
                    &output_path,
                    &kbdgen::cli::to_errormodel::Options { layout },
                )
                .unwrap()
            }
            command => match command.to_py_args(
                github_username.as_ref().map(|x| &**x),
                github_token.as_ref().map(|x| &**x),
                &opt.logging,
            ) {
                Ok(args) => std::process::exit(launch_py_kbdgen(&args)),
                Err(e) => {
                    eprintln!("{:?}", e);
                    std::process::exit(1);
                }
            },
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
            MetaCommands::Fetch {
                config,
                target,
            } => {
                match meta::fetch(config, target) {
                    Ok(_) => {},
                    Err(e) => {
                        eprintln!("ERROR: {:?}", e);
                        std::process::exit(1)
                    }
                }
            }
        }

        Commands::Repl => std::process::exit(launch_repl()),
    }
}

pub(crate) mod meta {
    use super::*;
    use serde::{Deserialize, Serialize};
    use std::collections::BTreeMap;

    pub fn fetch(config: PathBuf, target: PathBuf) -> anyhow::Result<()> {
        log::info!("Fetching {} for {}...", config.display(), target.display());
        log::debug!("Reading config");
        let config = std::fs::read_to_string(config)?;
        log::debug!("Parsing config");
        let config: meta::MetaBundle = toml::from_str(&config)?;

        log::debug!("Create layouts dir");
        std::fs::create_dir_all(target.join("layouts"))?;

        for (id, bundle) in config.bundle {
            log::debug!("id: {}, bundle: {:?}", &id, &bundle);
            let branch = 
                bundle.branch.unwrap_or_else(|| "master".into());
            let url = format!("https://github.com/{}/archive/{}.zip",
                bundle.github, &branch);

            let _ = std::fs::remove_dir_all("/tmp/kbdgen");
            std::fs::create_dir_all("/tmp/kbdgen")?;

            log::info!("Downloading {}...", id);
            let mut proc = std::process::Command::new("wget")
                .args(&[&*url, "-O", "kbdgen-layout.zip"])
                .current_dir("/tmp/kbdgen")
                .spawn()
                .unwrap();
            proc.wait().unwrap();

            log::info!("Unzipping {}...", id);
            let mut proc = std::process::Command::new("unzip")
                .args(&["kbdgen-layout.zip"])
                .current_dir("/tmp/kbdgen")
                .spawn()
                .unwrap();
            proc.wait().unwrap();

            let unzip_path = std::path::PathBuf::from(format!("/tmp/kbdgen/{}-{}/{}.kbdgen", bundle.github.split("/").nth(1).unwrap(), branch.replace("/", "-"), id));
            for layout in bundle.layouts {
                let from_path = unzip_path.join("layouts").join(format!("{}.yaml", layout));
                let to_path = target.join("layouts").join(format!("{}.yaml", layout));
                log::info!("Copying {} to {}...", from_path.display(), to_path.display());
                std::fs::copy(from_path, to_path)?;
            }
        }

        std::fs::remove_dir_all("/tmp/kbdgen")?;
        Ok(())
    }

    #[derive(Debug, Serialize, Deserialize)]
    pub struct MetaRecord {
        github: String,
        layouts: Vec<String>,
        branch: Option<String>,
        #[serde(rename = "ref")]
        ref_: Option<String>
    }

    #[derive(Debug, Serialize, Deserialize)]
    pub struct MetaBundle {
        bundle: BTreeMap<String, MetaRecord>,
    }
}
