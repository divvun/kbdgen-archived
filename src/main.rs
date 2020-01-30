use pyembed::{default_python_config, ExtensionModule, MainPythonInterpreter};
use std::path::PathBuf;
use structopt::StructOpt;
use structopt::clap::AppSettings::*;

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

        #[structopt(long = "kbd-branch", default_value = "develop")]
        kbd_branch: String,

        #[structopt(long = "divvunspell-repo", default_value = "divvun/divvunspell")]
        divvunspell_repo: String,

        #[structopt(long = "divvunspell-branch", default_value = "develop")]
        divvunspell_branch: String,

        #[structopt(flatten)]
        in_out: InOutPaths,

        #[structopt(short = "D", long = "dry-run")]
        dry_run: bool,

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

        #[structopt(long = "kbd-branch", default_value = "develop")]
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

    #[structopt(about = "Generates X11 output suitable for upstreaming")]
    X11 {
        #[structopt(flatten)]
        in_out: InOutPaths,

        #[structopt(flatten)]
        build_mode: BuildMode,
    },
    X11RS {
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

    #[structopt(setting(Hidden))]
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
enum Commands {
    #[structopt(about = "Generate output for a given .kbdgen bundle", setting(DisableHelpSubcommand))]
    Build {
        #[structopt(long = "github-username")]
        github_username: Option<String>,

        #[structopt(long = "github-token")]
        github_token: Option<String>,

        #[structopt(subcommand)]
        command: BuildCommands,
    },
    #[structopt(about = "Generate new bundles or layout templates", setting(DisableHelpSubcommand))]
    New {
        #[structopt(subcommand)]
        command: NewCommands,
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

                args.push(&*project_path.to_str().unwrap());

                args
            }
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
            M17n {
                in_out:
                    InOutPaths {
                        output_path,
                        project_path,
                    },
                build_mode: BuildMode { release, ci },
            } => return Err(From::from("M17n isn't supported in Python".to_string())),
            X11 {
                in_out:
                    InOutPaths {
                        output_path,
                        project_path,
                    },
                build_mode: BuildMode { release, ci },
            } => return Err(From::from("X11 isn't supported in Python".to_string())),
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
            ErrorModel {
                in_out:
                    InOutPaths {
                        output_path,
                        project_path,
                    },
                layout,
            } => vec![
                "-t",
                "errormodel",
                "-o",
                &*output_path.to_str().unwrap(),
                "--command",
                layout,
                &*project_path.to_str().unwrap(),
            ],
            X11RS { .. } => unreachable!("covered in previous match"),
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

fn launch_py_kbdgen(args: &[&str]) -> i32 {
    // Load the default Python configuration as derived by the PyOxidizer config
    // file used at build time.
    let mut config = default_python_config();

    let mod_language_tags = ExtensionModule {
        name: std::ffi::CString::new("language_tags").unwrap(),
        init_func: py_language_tags::PyInit_language_tags,
    };

    let mod_logger = ExtensionModule {
        name: std::ffi::CString::new("rust_logger").unwrap(),
        init_func: py_logger::PyInit_rust_logger,
    };

    config.extra_extension_modules = vec![mod_language_tags, mod_logger];

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

fn main() {
    env_logger::Builder::from_default_env()
        .filter(Some("kbdgen"), log::LevelFilter::Info)
        .target(env_logger::Target::Stderr)
        .init();

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

    std::env::set_var("RUST_LOG", logging.to_string());

    match opt.command {
        Commands::Build {
            github_username,
            github_token,
            command,
        } => match command {
            BuildCommands::X11RS {
                in_out:
                    InOutPaths {
                        output_path,
                        project_path,
                    },
                build_mode: BuildMode { release, ci },
                standalone,
            } => kbdgen::cli::to_xkb::kbdgen_to_xkb(
                &project_path,
                &output_path,
                &kbdgen::cli::to_xkb::Options { standalone },
            )
            .unwrap(),
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
            NewCommands::Layout {
                project_path,
                output_path,
            } => {
                eprintln!("Not yet supported.");
                std::process::exit(1)
            }
        },
    }
}
