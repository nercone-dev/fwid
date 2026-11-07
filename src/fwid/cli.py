from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from typing import Optional, Sequence

from .lib import FWID, FWIDFormat

class CLI:
    FORMATS = {
        "standard": FWIDFormat.STANDARD_TEXT,
        "readable": FWIDFormat.READABLE_TEXT,
        "compact": FWIDFormat.COMPACT_TEXT,
    }

    @staticmethod
    def parse_datetime(text: str) -> datetime:
        try:
            dt = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text)
        except ValueError:
            raise argparse.ArgumentTypeError(f"invalid ISO 8601 datetime: {text!r}")
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    @staticmethod
    def positive_int(text: str) -> int:
        try:
            value = int(text)
        except ValueError:
            raise argparse.ArgumentTypeError(f"invalid integer: {text!r}")
        if value < 1:
            raise argparse.ArgumentTypeError("must be 1 or greater")
        return value

    @staticmethod
    def parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog="fwid", description="Generate and inspect FWIDs (FourWord Identifiers).")
        sub = parser.add_subparsers(dest="command", metavar="COMMAND")
        sub.required = True

        gen = sub.add_parser("generate", aliases=("g",), help="generate FWIDs")
        gen.add_argument("-b", "--bits", type=CLI.positive_int, default=None,
                         help="total bit length, a multiple of %d (default: the smallest that fits the timestamp)" % FWID.BITS_ALIGN)
        gen.add_argument("-f", "--format", choices=sorted(CLI.FORMATS), default="standard",
                         help="output format (default: standard)")
        gen.add_argument("-n", "--count", type=CLI.positive_int, default=1,
                         help="number of FWIDs to generate (default: 1)")
        gen.add_argument("-t", "--time", type=CLI.parse_datetime, default=None, metavar="DATETIME",
                         help="ISO 8601 timestamp to embed; naive values are UTC (default: now)")
        gen.set_defaults(run=CLI.generate)

        ins = sub.add_parser("inspect", aliases=("i",), help="show the contents of FWIDs")
        ins.add_argument("ids", nargs="*", metavar="FWID",
                         help="FWIDs in any text format; read from standard input, one per line, if omitted or '-'")
        ins.set_defaults(run=CLI.inspect)
        return parser

    @staticmethod
    def generate(args: argparse.Namespace) -> int:
        fmt = CLI.FORMATS[args.format]
        for _ in range(args.count):
            print(FWID(args.bits, args.time).text(fmt))
        return 0

    @staticmethod
    def inspect(args: argparse.Namespace) -> int:
        if not args.ids or args.ids == ["-"]:
            texts = [line.strip() for line in sys.stdin if line.strip()]
        else:
            texts = args.ids
        status = 0
        for i, text in enumerate(texts):
            if i > 0:
                print()
            try:
                fmt = FWIDFormat.detect(text)
                fwid = FWID.from_text(text)
                timestamp = fwid.timestamp.isoformat(timespec="milliseconds")
            except ValueError as e:
                print(f"fwid: {text}: {e}", file=sys.stderr)
                status = 1
                continue
            print(f"Format:     {fmt.value}")
            print(f"Bits:       {fwid.bits} (timestamp {fwid.bits_timestamp}, random {fwid.bits_random})")
            print(f"Timestamp:  {timestamp} ({fwid.timestamp_ms} ms)")
            print(f"Hex:        {fwid.raw.hex()}")
            print(f"Standard:   {fwid.standard_text}")
            print(f"Readable:   {fwid.readable_text}")
            print(f"Compact:    {fwid.compact_text}")
        return status

    @staticmethod
    def main(argv: Optional[Sequence[str]] = None) -> None:
        args = CLI.parser().parse_args(argv)
        try:
            code = args.run(args)
        except ValueError as e:
            print(f"fwid: {e}", file=sys.stderr)
            code = 1
        except BrokenPipeError:
            code = 1
        sys.exit(code)

def main(argv: Optional[Sequence[str]] = None) -> None:
    CLI.main(argv)
