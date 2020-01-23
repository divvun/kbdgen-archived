use pyembed::{default_python_config, ExtensionModule, MainPythonInterpreter};
use std::path::PathBuf;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
enum IOSCommands {
    Init,
    Ids
}

#[derive(Debug, StructOpt)]
enum BuildCommands {
    Svg {
        #[structopt(short, long = "output", default_value = ".", parse(from_os_str))]
        output_path: PathBuf,

        #[structopt(parse(from_os_str))]
        project_path: PathBuf,
    },
    Android {
        #[structopt(long = "kbd-repo", default_value = "divvun/giellakbd-android")]
        kbd_repo: String,

        #[structopt(long = "kbd-branch", default_value = "develop")]
        kbd_branch: String,

        #[structopt(long = "divvunspell-repo", default_value = "divvun/divvunspell")]
        divvunspell_repo: String,

        #[structopt(long = "divvunspell-branch", default_value = "develop")]
        divvunspell_branch: String,

        #[structopt(short, long = "output", parse(from_os_str))]
        output_path: PathBuf,

        #[structopt(short = "D", long = "dry-run")]
        dry_run: bool,

        #[structopt(short = "R", long = "release")]
        release: bool,

        #[structopt(long = "ci")]
        ci: bool,

        #[structopt(parse(from_os_str))]
        project_path: PathBuf,
    },
    IOS {
        #[structopt(subcommand)]
        command: Option<IOSCommands>,

        #[structopt(long = "kbd-repo", default_value = "divvun/giellakbd-ios")]
        kbd_repo: String,

        #[structopt(long = "kbd-branch", default_value = "develop")]
        kbd_branch: String,

        #[structopt(short, long = "output", default_value = ".", parse(from_os_str))]
        output_path: PathBuf,

        #[structopt(short = "D", long = "dry-run")]
        dry_run: bool,

        #[structopt(short = "R", long = "release")]
        release: bool,

        #[structopt(long = "ci")]
        ci: bool,

        #[structopt(parse(from_os_str))]
        project_path: PathBuf,
    },
    Win {
        #[structopt(short, long = "output", default_value = ".", parse(from_os_str))]
        output_path: PathBuf,

        #[structopt(short = "D", long = "dry-run")]
        dry_run: bool,

        #[structopt(short = "R", long = "release")]
        release: bool,

        #[structopt(long = "ci")]
        ci: bool,

        #[structopt(parse(from_os_str))]
        project_path: PathBuf,
    },
    Mac {
        #[structopt(short, long = "output", default_value = ".", parse(from_os_str))]
        output_path: PathBuf,

        #[structopt(short = "D", long = "dry-run")]
        dry_run: bool,

        #[structopt(short = "R", long = "release")]
        release: bool,

        #[structopt(long = "ci")]
        ci: bool,

        #[structopt(parse(from_os_str))]
        project_path: PathBuf,
    },
    X11 {
        #[structopt(short, long = "output", default_value = ".", parse(from_os_str))]
        output_path: PathBuf,

        #[structopt(short = "R", long = "release")]
        release: bool,

        #[structopt(long = "ci")]
        ci: bool,

        #[structopt(parse(from_os_str))]
        project_path: PathBuf,
    },
    M17n {
        #[structopt(short, long = "output", default_value = ".", parse(from_os_str))]
        output_path: PathBuf,

        #[structopt(short = "R", long = "release")]
        release: bool,

        #[structopt(long = "ci")]
        ci: bool,

        #[structopt(parse(from_os_str))]
        project_path: PathBuf,
    },
    Chrome {
        #[structopt(short, long = "output", default_value = ".", parse(from_os_str))]
        output_path: PathBuf,

        #[structopt(short = "R", long = "release")]
        release: bool,

        #[structopt(long = "ci")]
        ci: bool,

        #[structopt(parse(from_os_str))]
        project_path: PathBuf,
    },
    Qr {
        #[structopt(short, long = "output", default_value = ".", parse(from_os_str))]
        output_path: PathBuf,

        #[structopt(short, long = "layout")]
        layout: String,

        #[structopt(parse(from_os_str))]
        project_path: PathBuf,
    },
    ErrorModel {
        #[structopt(short, long = "output", default_value = ".", parse(from_os_str))]
        output_path: PathBuf,

        #[structopt(short, long = "layout")]
        layout: String,

        #[structopt(parse(from_os_str))]
        project_path: PathBuf,
    },
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

        bundle_name: String
    }
}

#[derive(Debug, StructOpt)]
enum Commands {
    Build {
        #[structopt(long = "github-username")]
        github_username: Option<String>,
    
        #[structopt(long = "github-token")]
        github_token: Option<String>,
    
        #[structopt(subcommand)]
        command: BuildCommands,
    },
    New {
        #[structopt(subcommand)]
        command: NewCommands,
    }
}

#[derive(Debug, StructOpt)]
#[structopt(name = "kbdgen", about = "An example of StructOpt usage.")]
struct Opts {
    #[structopt(long = "logging", default_value = "info")]
    logging: String,

    #[structopt(subcommand)]
    command: Commands
}

impl BuildCommands {
    fn to_py_args<'a>(&'a self, github_username: Option<&'a str>, github_token: Option<&'a str>, logging: &'a str) -> Result<Vec<&'a str>, Box<dyn std::error::Error>> {
        use BuildCommands::*;

        let mut args = match self {
            Svg {
                output_path,
                project_path,
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
                output_path,
                dry_run,
                release,
                ci,
                project_path,
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
                output_path,
                dry_run,
                release,
                ci,
                project_path,
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
                    },
                    _ => {}
                }

                args.push(&*project_path.to_str().unwrap());
                args
            }
            Chrome {
                output_path,
                release,
                ci,
                project_path,
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
                output_path,
                dry_run,
                release,
                ci,
                project_path,
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
                output_path,
                dry_run,
                release,
                ci,
                project_path,
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
                output_path,
                release,
                ci,
                project_path,
            } => return Err(From::from("M17n isn't supported in Python".to_string())),
            X11 {
                output_path,
                release,
                ci,
                project_path,
            } => return Err(From::from("X11 isn't supported in Python".to_string())),
            Qr {
                output_path,
                layout,
                project_path,
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
                output_path,
                layout,
                project_path,
            } => vec![
                "-t",
                "errormodel",
                "-o",
                &*output_path.to_str().unwrap(),
                "--command",
                layout,
                &*project_path.to_str().unwrap(),
            ],
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

    config.extra_extension_modules = vec![
        mod_language_tags,
        mod_logger,
    ];

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
    env_logger::init();

    let opt = Opts::from_args();

    match opt.command {
        Commands::Build { github_username, github_token, command } => {
            match command.to_py_args(github_username.as_ref().map(|x| &**x), github_token.as_ref().map(|x| &**x), &opt.logging) {
                Ok(args) => std::process::exit(launch_py_kbdgen(&args)),
                Err(e) => {
                    eprintln!("{:?}", e);
                    std::process::exit(1);
                }
            }
        },
        
        Commands::New { command } => match command {
            NewCommands::Bundle { bundle_name, output_path } => {
                match kbdgen::cli::from_cldr::cldr_to_kbdgen(&*output_path, &*bundle_name) {
                    Ok(_) => std::process::exit(0),
                    Err(e) => {
                        eprintln!("{:?}", e);
                        std::process::exit(1);
                    }
                }
            }
            NewCommands::Layout { project_path, output_path } => {
                eprintln!("Not yet supported.");
                std::process::exit(1)
            }
        }
    }
}
