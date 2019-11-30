use kbdgen_cli::from_xkb::{xkb_to_kbdgen, Cli, Error};
use structopt::StructOpt;

fn main() -> Result<(), Error> {
    let opts = Cli::from_args();
    xkb_to_kbdgen(&opts)
}
