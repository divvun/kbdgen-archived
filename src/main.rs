use pyembed::{default_python_config, ExtensionModule, MainPythonInterpreter};
use std::path::PathBuf;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
enum IOSCommands {
    Init,
    Ids
}

#[derive(Debug, StructOpt)]
enum KbdgenCommands {
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
#[structopt(name = "kbdgen", about = "An example of StructOpt usage.")]
struct KbdgenOpts {
    #[structopt(long = "github-username")]
    github_username: Option<String>,

    #[structopt(long = "github-token")]
    github_token: Option<String>,

    #[structopt(long = "logging", default_value = "info")]
    logging: String,

    #[structopt(subcommand)]
    command: KbdgenCommands,
}

impl KbdgenOpts {
    fn to_py_args<'a>(&'a self) -> Result<Vec<&'a str>, Box<dyn std::error::Error>> {
        use KbdgenCommands::*;

        let mut args = match &self.command {
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

        if let Some(gh_username) = self.github_username.as_ref() {
            args.push("--github-username");
            args.push(&*gh_username);
        }

        if let Some(gh_token) = self.github_token.as_ref() {
            args.push("--github-token");
            args.push(&*gh_token);
        }

        args.push("--logging");
        args.push(&self.logging);

        Ok(args)
    }
}

/*
$ python -m kbdgen --help
usage: kbdgen [-h] [--version] [--logging LOGGING]
              [-K [CFG_PAIRS [CFG_PAIRS ...]]] [-D] [-R] [-G GLOBAL] [-r REPO]
              [-b BRANCH] -t
              {win,mac,x11,svg,android,ios,json,qr,errormodel,chrome}
              [-o OUTPUT] [-f [FLAGS [FLAGS ...]]] [-l LAYOUT]
              [--github-username GITHUB_USERNAME]
              [--github-token GITHUB_TOKEN] [-c COMMAND] [--ci]
              project

positional arguments:
  project               Keyboard generation bundle (.kbdgen)

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  --logging LOGGING     Logging level
  -K [CFG_PAIRS [CFG_PAIRS ...]], --key [CFG_PAIRS [CFG_PAIRS ...]]
                        Key-value overrides (eg -K target.thing.foo=42)
  -D, --dry-run         Don't build, just do requirement validation.
  -R, --release         Compile in 'release' mode (where necessary).
  -G GLOBAL, --global GLOBAL
                        Override the global.yaml file
  -r REPO, --repo REPO  Git repo to generate output from
  -b BRANCH, --branch BRANCH
                        Git branch (default: master)
  -t {win,mac,x11,svg,android,ios,json,qr,errormodel,chrome}, --target {win,mac,x11,svg,android,ios,json,qr,errormodel,chrome}
                        Target output.
  -o OUTPUT, --output OUTPUT
                        Output directory (default: current working directory)
  -f [FLAGS [FLAGS ...]], --flag [FLAGS [FLAGS ...]]
                        Generator-specific flags (for debugging)
  -l LAYOUT, --layout LAYOUT
                        Apply target to specified layout only (EXPERIMENTAL)
  --github-username GITHUB_USERNAME
                        GitHub username for source getting
  --github-token GITHUB_TOKEN
                        GitHub token for source getting
  -c COMMAND, --command COMMAND
                        Command to run for a given generators
  --ci                  Continuous integration build
*/

fn py_main(args: &[&str]) -> i32 {
    // Load the default Python configuration as derived by the PyOxidizer config
    // file used at build time.
    let mut config = default_python_config();
    config.extra_extension_modules = vec![ExtensionModule {
        name: std::ffi::CString::new("language_tags").unwrap(),
        init_func: py_language_tags::PyInit_language_tags,
    }];

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
    let opt = KbdgenOpts::from_args();

    println!("{:?}", &opt.to_py_args());

    match opt.to_py_args() {
        Ok(args) => std::process::exit(py_main(&args)),
        Err(e) => {
            eprintln!("{:?}", e);
            std::process::exit(1);
        }
    }
}
