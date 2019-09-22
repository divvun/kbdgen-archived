use kbdgen_cli::to_m17n_mim::{kbdgen_to_mim, Cli, Error};
use structopt::StructOpt;

fn main() -> Result<(), Error> {
    let opts = Cli::from_args();
    kbdgen_to_mim(&opts)
}
