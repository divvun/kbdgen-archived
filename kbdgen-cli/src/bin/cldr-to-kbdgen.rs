use kbdgen_cli::from_cldr::{cldr_to_kbdgen, Cli, Error};
use structopt::StructOpt;

fn main() -> Result<(), Error> {
    let opts = Cli::from_args();
    cldr_to_kbdgen(&opts)
}
