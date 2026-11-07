import sys

from .helpers import ISO8601
from .lib import FWID, FWIDFormat


class UsageError(ValueError):
    """A malformed command line."""


class Command:
    """A parsed command line."""

    name: str
    bits: int | None
    fmt: int
    count: int
    unix_ms: int | None
    ids: list[str]

    def __init__(self, name: str) -> None:
        self.name = name
        self.bits = None
        self.fmt = FWIDFormat.STANDARD_TEXT
        self.count = 1
        self.unix_ms = None
        self.ids = []


class CLI:
    USAGE: str = "usage: fwid [-h] COMMAND ..."

    HELP: str = """usage: fwid [-h] COMMAND ...

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
"""

    @staticmethod
    def positive_int(text: str) -> int:
        try:
            value = int(text)
        except ValueError:
            raise UsageError("invalid integer: " + repr(text))
        if value < 1:
            raise UsageError("must be 1 or greater")
        return value

    @staticmethod
    def parse_format(text: str) -> int:
        if text == "standard":
            return FWIDFormat.STANDARD_TEXT
        if text == "readable":
            return FWIDFormat.READABLE_TEXT
        if text == "compact":
            return FWIDFormat.COMPACT_TEXT
        raise UsageError("invalid choice: " + repr(text) + " (choose from compact, readable, standard)")

    @staticmethod
    def parse_time(text: str) -> int:
        try:
            return ISO8601.parse(text)
        except ValueError as e:
            raise UsageError(str(e))

    @staticmethod
    def apply_option(command: Command, short: str, text: str) -> None:
        """Set the generate option named by its short letter from its text value. Raises UsageError."""
        try:
            if short == "b":
                command.bits = CLI.positive_int(text)
            elif short == "f":
                command.fmt = CLI.parse_format(text)
            elif short == "n":
                command.count = CLI.positive_int(text)
            else:
                command.unix_ms = CLI.parse_time(text)
        except UsageError as e:
            long = "bits" if short == "b" else "format" if short == "f" else "count" if short == "n" else "time"
            raise UsageError("argument -" + short + "/--" + long + ": " + str(e))

    @staticmethod
    def long_name(short: str) -> str:
        if short == "b":
            return "bits"
        if short == "f":
            return "format"
        if short == "n":
            return "count"
        return "time"

    @staticmethod
    def parse(argv: list[str]) -> Command:
        """Parse the command line (without the program name). Raises UsageError."""
        if len(argv) == 0:
            raise UsageError("the following arguments are required: COMMAND")
        name = argv[0]
        if name == "-h" or name == "--help":
            return Command("help")
        if name == "generate" or name == "g":
            command = Command("generate")
            i = 1
            while i < len(argv):
                arg = argv[i]
                i += 1
                if arg == "-h" or arg == "--help":
                    return Command("help")
                short = ""
                value = ""
                found = False
                for letter in ("b", "f", "n", "t"):
                    long = CLI.long_name(letter)
                    if arg.startswith("--" + long + "="):
                        short, value, found = letter, arg[len(long) + 3:], True
                    elif len(arg) > 2 and arg.startswith("-" + letter):
                        short, value, found = letter, arg[2:], True
                    elif arg == "--" + long or arg == "-" + letter:
                        if i >= len(argv):
                            raise UsageError("argument -" + letter + "/--" + long + ": expected one argument")
                        short, value, found = letter, argv[i], True
                        i += 1
                    if found:
                        break
                if not found:
                    raise UsageError("unrecognized arguments: " + arg)
                CLI.apply_option(command, short, value)
            return command
        if name == "inspect" or name == "i":
            command = Command("inspect")
            options_done = False
            for arg in argv[1:]:
                if not options_done and arg == "--":
                    options_done = True
                elif not options_done and (arg == "-h" or arg == "--help"):
                    return Command("help")
                elif not options_done and len(arg) > 1 and arg[0] == "-":
                    raise UsageError("unrecognized arguments: " + arg)
                else:
                    command.ids.append(arg)
            return command
        raise UsageError("argument COMMAND: invalid choice: " + repr(name) + " (choose from generate, g, inspect, i)")

    @staticmethod
    def describe(text: str, out: list[str]) -> None:
        """Append the description of one FWID to out. Raises ValueError."""
        fmt, fwid = FWID.parse(text)
        out.append("Format:     " + FWIDFormat.name(fmt))
        out.append("Bits:       " + str(fwid.bits) + " (timestamp " + str(fwid.bits_timestamp) + ", random " + str(fwid.bits_random) + ")")
        out.append("Timestamp:  " + ISO8601.format(fwid.timestamp) + " (" + str(fwid.timestamp_ms) + " ms)")
        out.append("Hex:        " + fwid.raw.hex())
        out.append("Standard:   " + fwid.standard_text)
        out.append("Readable:   " + fwid.readable_text)
        out.append("Compact:    " + fwid.compact_text)

    @staticmethod
    def generate(command: Command, out: list[str]) -> None:
        for _ in range(command.count):
            out.append(FWID.generate(command.bits, command.unix_ms).text(command.fmt))

    @staticmethod
    def inspect(texts: list[str], out: list[str], err: list[str]) -> int:
        status = 0
        for i, text in enumerate(texts):
            if i > 0:
                out.append("")
            try:
                CLI.describe(text, out)
            except ValueError as e:
                err.append("fwid: " + text + ": " + str(e))
                status = 1
        return status

    @staticmethod
    def needs_stdin(command: Command) -> bool:
        return command.name == "inspect" and (len(command.ids) == 0 or (len(command.ids) == 1 and command.ids[0] == "-"))

    @staticmethod
    def split_lines(stdin: str) -> list[str]:
        """The non-blank lines of stdin, stripped."""
        texts: list[str] = []
        for line in stdin.split("\n"):
            stripped = line.strip()
            if stripped != "":
                texts.append(stripped)
        return texts

    @staticmethod
    def execute(command: Command, stdin_lines: list[str], out: list[str], err: list[str]) -> int:
        """Run a parsed command, appending its output lines to out and err. Returns the exit status."""
        if command.name == "help":
            out.append(CLI.HELP.rstrip("\n"))
            return 0
        try:
            if command.name == "generate":
                CLI.generate(command, out)
                return 0
            if CLI.needs_stdin(command):
                return CLI.inspect(stdin_lines, out, err)
            return CLI.inspect(command.ids, out, err)
        except ValueError as e:
            err.append("fwid: " + str(e))
            return 1

    @staticmethod
    def run(argv: list[str], stdin: str, out: list[str], err: list[str]) -> int:
        """Run the command line with argv (without the program name) and the whole of stdin. Returns the exit status."""
        try:
            command = CLI.parse(argv)
        except UsageError as e:
            err.append(CLI.USAGE)
            err.append("fwid: error: " + str(e))
            return 2
        return CLI.execute(command, CLI.split_lines(stdin), out, err)

    @staticmethod
    def read_stdin() -> str:
        lines: list[str] = []
        while True:
            try:
                lines.append(input())
            except EOFError:
                break
        return "\n".join(lines)

    @staticmethod
    def main(argv: list[str] | None = None) -> int:
        """Run the command line and return the exit status. argv defaults to sys.argv[1:]."""
        if argv is None:
            argv = sys.argv[1:]
        out: list[str] = []
        err: list[str] = []
        try:
            command = CLI.parse(argv)
        except UsageError as e:
            print(CLI.USAGE, file=sys.stderr)
            print("fwid: error: " + str(e), file=sys.stderr)
            return 2
        stdin_lines: list[str] = []
        if CLI.needs_stdin(command):
            stdin_lines = CLI.split_lines(CLI.read_stdin())
        status = CLI.execute(command, stdin_lines, out, err)
        for line in out:
            print(line)
        for line in err:
            print(line, file=sys.stderr)
        return status
