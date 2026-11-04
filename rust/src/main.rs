mod cli;

use std::io::{self, Write};
use std::process::ExitCode;

fn main() -> ExitCode {
    let mut args = Vec::new();
    for arg in std::env::args_os().skip(1) {
        match arg.into_string() {
            Ok(arg) => args.push(arg),
            Err(_) => {
                eprintln!("fwid: arguments must be valid UTF-8");
                return ExitCode::from(2);
            }
        }
    }
    let mut out = io::BufWriter::new(io::stdout().lock());
    let status = cli::CLI::run(&args, &mut io::stdin().lock(), &mut out, &mut io::stderr().lock());
    let flushed = out.flush();
    ExitCode::from(if status == 0 && flushed.is_err() { 1 } else { status as u8 })
}
