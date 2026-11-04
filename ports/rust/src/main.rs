mod cli;

use std::io::{self, Write};
use std::process::ExitCode;

fn main() -> ExitCode {
    let mut out = io::BufWriter::new(io::stdout().lock());
    let status = cli::CLI::run(std::env::args_os().skip(1), &mut io::stdin().lock(), &mut out, &mut io::stderr().lock());
    let flushed = out.flush();
    ExitCode::from(if status == 0 && flushed.is_err() { 1 } else { status as u8 })
}
