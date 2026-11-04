use std::ffi::OsString;
use std::io::{self, BufRead, Write};
use std::time::SystemTime;

use clap::{Parser, Subcommand, ValueEnum};
use fwid::{Format, ISO8601, FWID};

/// Text formats selectable on the command line.
#[derive(Clone, Copy, ValueEnum)]
enum TextFormat {
    Standard,
    Readable,
    Compact,
}

impl From<TextFormat> for Format {
    fn from(format: TextFormat) -> Self {
        match format {
            TextFormat::Standard => Format::StandardText,
            TextFormat::Readable => Format::ReadableText,
            TextFormat::Compact => Format::CompactText,
        }
    }
}

/// Generate and inspect FWIDs (FourWord Identifiers).
#[derive(Parser)]
#[command(name = "fwid", subcommand_required = true, arg_required_else_help = true)]
struct Arguments {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// generate FWIDs
    #[command(visible_alias = "g")]
    Generate {
        /// total bit length, a multiple of 32 (default: the smallest that fits the timestamp)
        #[arg(short, long, value_parser = clap::value_parser!(u64).range(1..))]
        bits: Option<u64>,
        /// text format
        #[arg(short, long, value_enum, default_value = "standard")]
        format: TextFormat,
        /// number of FWIDs to generate
        #[arg(short = 'n', long, default_value_t = 1, value_parser = clap::value_parser!(u64).range(1..))]
        count: u64,
        /// ISO 8601 timestamp to embed; naive values are UTC (default: now)
        #[arg(short, long, value_parser = parse_time)]
        time: Option<SystemTime>,
    },
    /// show the contents of FWIDs
    #[command(visible_alias = "i")]
    Inspect {
        /// FWIDs in any text format; read from standard input, one per line, if omitted or '-'
        ids: Vec<String>,
    },
}

fn parse_time(text: &str) -> Result<SystemTime, String> {
    ISO8601::parse(text).map_err(|_| format!("invalid ISO 8601 datetime: {text:?}"))
}

pub struct CLI;

impl CLI {
    fn generate(
        bits: Option<usize>,
        format: Format,
        count: u64,
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
        args: impl IntoIterator<Item = OsString>,
        stdin: &mut impl BufRead,
        out: &mut impl Write,
        err: &mut impl Write,
    ) -> i32 {
        let program = OsString::from("fwid");
        let parsed = match Arguments::try_parse_from(std::iter::once(program).chain(args)) {
            Ok(parsed) => parsed,
            Err(e) => {
                let status = e.exit_code();
                let text = e.render().to_string();
                let _ = if status == 0 { write!(out, "{text}") } else { write!(err, "{text}") };
                return status;
            }
        };
        let result = match parsed.command {
            Command::Generate { bits, format, count, time } => {
                let Ok(bits) = bits.map(usize::try_from).transpose() else {
                    let _ = writeln!(err, "fwid: bits out of range");
                    return 2;
                };
                Self::generate(bits, format.into(), count, time, out, err)
            }
            Command::Inspect { ids } => Self::inspect(ids, stdin, out, err),
        };
        // A closed pipe or unwritable stdout is a failure, but not worth a message.
        result.unwrap_or(1)
    }
}
