use std::io::{self, BufRead, Write};
use std::time::SystemTime;

use fwid::{Format, ISO8601, FWID};

const USAGE: &str = "usage: fwid [-h] COMMAND ...";

const HELP: &str = "usage: fwid [-h] COMMAND ...

Generate and inspect FWIDs (FourWord Identifiers).

commands:
  generate, g   generate FWIDs
  inspect, i    show the contents of FWIDs

options:
  -h, --help    show this help message and exit

generate options:
  -b, --bits BITS       total bit length, a multiple of 32
                        (default: the smallest that fits the timestamp)
  -f, --format FORMAT   standard, readable or compact (default: standard)
  -n, --count COUNT     number of FWIDs to generate (default: 1)
  -t, --time DATETIME   ISO 8601 timestamp to embed; naive values are UTC
                        (default: now)

inspect arguments:
  FWID                  FWIDs in any text format; read from standard input,
                        one per line, if omitted or '-'
";

enum Command {
    Help,
    Generate {
        bits: Option<usize>,
        format: Format,
        count: usize,
        time: Option<SystemTime>,
    },
    Inspect {
        ids: Vec<String>,
    },
}

pub struct CLI;

impl CLI {
    fn positive(text: &str) -> Result<usize, String> {
        match text.parse::<usize>() {
            Ok(0) => Err("must be 1 or greater".into()),
            Ok(n) => Ok(n),
            Err(_) => Err(format!("invalid integer: {text:?}")),
        }
    }

    fn format(text: &str) -> Result<Format, String> {
        match text {
            "standard" => Ok(Format::StandardText),
            "readable" => Ok(Format::ReadableText),
            "compact" => Ok(Format::CompactText),
            _ => Err(format!(
                "invalid choice: {text:?} (choose from compact, readable, standard)"
            )),
        }
    }

    /// Splits `-bVALUE`, `--bits=VALUE`, `-b VALUE` and `--bits VALUE`.
    fn option_value<'a>(
        arg: &'a str,
        short: char,
        long: &str,
        rest: &mut impl Iterator<Item = &'a String>,
    ) -> Option<Result<&'a str, String>> {
        let inline = if let Some(v) = arg.strip_prefix(&format!("--{long}=")) {
            Some(v)
        } else if arg.len() > 2 && arg.starts_with(&format!("-{short}")) {
            Some(&arg[2..])
        } else {
            None
        };
        if let Some(v) = inline {
            return Some(Ok(v));
        }
        if arg == format!("--{long}") || arg == format!("-{short}") {
            return Some(
                rest.next()
                    .map(String::as_str)
                    .ok_or_else(|| format!("argument -{short}/--{long}: expected one argument")),
            );
        }
        None
    }

    fn parse(args: &[String]) -> Result<Command, String> {
        let mut it = args.iter();
        let name = match it.next().map(String::as_str) {
            Some("-h" | "--help") => return Ok(Command::Help),
            Some(name) => name,
            None => return Err("the following arguments are required: COMMAND".into()),
        };
        match name {
            "generate" | "g" => {
                let (mut bits, mut format, mut count, mut time) =
                    (None, Format::StandardText, 1, None);
                while let Some(arg) = it.next() {
                    if arg == "-h" || arg == "--help" {
                        return Ok(Command::Help);
                    }
                    if let Some(v) = Self::option_value(arg, 'b', "bits", &mut it) {
                        bits = Some(Self::positive(v?).map_err(|e| format!("argument -b/--bits: {e}"))?);
                    } else if let Some(v) = Self::option_value(arg, 'f', "format", &mut it) {
                        format = Self::format(v?).map_err(|e| format!("argument -f/--format: {e}"))?;
                    } else if let Some(v) = Self::option_value(arg, 'n', "count", &mut it) {
                        count = Self::positive(v?).map_err(|e| format!("argument -n/--count: {e}"))?;
                    } else if let Some(v) = Self::option_value(arg, 't', "time", &mut it) {
                        let v = v?;
                        time = Some(ISO8601::parse(v).map_err(|_| {
                            format!("argument -t/--time: invalid ISO 8601 datetime: {v:?}")
                        })?);
                    } else {
                        return Err(format!("unrecognized arguments: {arg}"));
                    }
                }
                Ok(Command::Generate { bits, format, count, time })
            }
            "inspect" | "i" => {
                let mut ids = Vec::new();
                let mut options_done = false;
                for arg in it {
                    if !options_done && arg == "--" {
                        options_done = true;
                    } else if !options_done && (arg == "-h" || arg == "--help") {
                        return Ok(Command::Help);
                    } else if !options_done && arg.len() > 1 && arg.starts_with('-') {
                        return Err(format!("unrecognized arguments: {arg}"));
                    } else {
                        ids.push(arg.clone());
                    }
                }
                Ok(Command::Inspect { ids })
            }
            _ => Err(format!(
                "argument COMMAND: invalid choice: {name:?} (choose from generate, g, inspect, i)"
            )),
        }
    }

    fn generate(
        bits: Option<usize>,
        format: Format,
        count: usize,
        time: Option<SystemTime>,
        out: &mut impl Write,
        err: &mut impl Write,
    ) -> io::Result<i32> {
        for _ in 0..count {
            let text = FWID::generate(bits, time).and_then(|id| id.text(format));
            match text {
                Ok(text) => writeln!(out, "{text}")?,
                Err(e) => {
                    writeln!(err, "fwid: {e}")?;
                    return Ok(1);
                }
            }
        }
        Ok(0)
    }

    fn describe(text: &str, out: &mut impl Write) -> Result<(), Result<fwid::Error, io::Error>> {
        let (format, id) = FWID::parse(text).map_err(Ok)?;
        let ms = id.timestamp_ms().map_err(Ok)?;
        let time = id.timestamp().map_err(Ok)?;
        let hex: String = id.as_bytes().iter().map(|b| format!("{b:02x}")).collect();
        let result = writeln!(out, "Format:     {}", format.name())
            .and_then(|_| {
                writeln!(
                    out,
                    "Bits:       {} (timestamp {}, random {})",
                    id.bits(),
                    id.bits_timestamp(),
                    id.bits_random()
                )
            })
            .and_then(|_| writeln!(out, "Timestamp:  {} ({ms} ms)", ISO8601::format(time)))
            .and_then(|_| writeln!(out, "Hex:        {hex}"))
            .and_then(|_| writeln!(out, "Standard:   {}", id.standard_text()))
            .and_then(|_| writeln!(out, "Readable:   {}", id.readable_text()))
            .and_then(|_| writeln!(out, "Compact:    {}", id.compact_text()));
        result.map_err(Err)
    }

    fn inspect(
        ids: Vec<String>,
        stdin: &mut impl BufRead,
        out: &mut impl Write,
        err: &mut impl Write,
    ) -> io::Result<i32> {
        let texts = if ids.is_empty() || ids == ["-"] {
            let mut texts = Vec::new();
            for line in stdin.lines() {
                let line = line?;
                let line = line.trim();
                if !line.is_empty() {
                    texts.push(line.to_owned());
                }
            }
            texts
        } else {
            ids
        };
        let mut status = 0;
        for (i, text) in texts.iter().enumerate() {
            if i > 0 {
                writeln!(out)?;
            }
            match Self::describe(text, out) {
                Ok(()) => {}
                Err(Ok(e)) => {
                    writeln!(err, "fwid: {text}: {e}")?;
                    status = 1;
                }
                Err(Err(e)) => return Err(e),
            }
        }
        Ok(status)
    }

    /// Runs the CLI with `args` (without the program name); returns the exit status.
    pub fn run(
        args: &[String],
        stdin: &mut impl BufRead,
        out: &mut impl Write,
        err: &mut impl Write,
    ) -> i32 {
        let command = match Self::parse(args) {
            Ok(command) => command,
            Err(message) => {
                let _ = writeln!(err, "{USAGE}\nfwid: error: {message}");
                return 2;
            }
        };
        let result = match command {
            Command::Help => write!(out, "{HELP}").map(|_| 0),
            Command::Generate { bits, format, count, time } => {
                Self::generate(bits, format, count, time, out, err)
            }
            Command::Inspect { ids } => Self::inspect(ids, stdin, out, err),
        };
        // A closed pipe or unwritable stdout is a failure, but not worth a message.
        result.unwrap_or(1)
    }
}
