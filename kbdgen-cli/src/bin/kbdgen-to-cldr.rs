use kbdgen_cli::to_cldr::{kbdgen_to_cldr, Cli, Error};
use structopt::StructOpt;

fn main() -> Result<(), Error> {
    let opts = Cli::from_args();
    kbdgen_to_cldr(&opts)
}
