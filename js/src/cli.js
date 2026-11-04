import { FWIDError } from "./errors.js";
import { FWID, FWIDFormat } from "./fwid.js";
import { ISO8601 } from "./iso8601.js";

class UsageError extends Error {}

export class CLI {
  static USAGE = "usage: fwid [-h] COMMAND ...";

  static HELP = `usage: fwid [-h] COMMAND ...

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
`;

  static FORMATS = {
    standard: FWIDFormat.STANDARD_TEXT,
    readable: FWIDFormat.READABLE_TEXT,
    compact: FWIDFormat.COMPACT_TEXT,
  };

  static #positive(text) {
    if (!/^[+-]?\d+$/.test(text)) throw new UsageError(`invalid integer: ${JSON.stringify(text)}`);
    const value = Number(text);
    if (!Number.isSafeInteger(value)) throw new UsageError(`invalid integer: ${JSON.stringify(text)}`);
    if (value < 1) throw new UsageError("must be 1 or greater");
    return value;
  }

  static #format(text) {
    if (!Object.hasOwn(CLI.FORMATS, text)) {
      throw new UsageError(`invalid choice: ${JSON.stringify(text)} (choose from compact, readable, standard)`);
    }
    return CLI.FORMATS[text];
  }

  /** Matches `-bVALUE`, `--bits=VALUE`, `-b VALUE` and `--bits VALUE`; null if `arg` is another option. */
  static #value(arg, short, long, rest) {
    if (arg.startsWith(`--${long}=`)) return arg.slice(long.length + 3);
    if (arg.length > 2 && arg.startsWith(`-${short}`) && !arg.startsWith("--")) return arg.slice(2);
    if (arg === `--${long}` || arg === `-${short}`) {
      if (rest.length === 0) throw new UsageError(`argument -${short}/--${long}: expected one argument`);
      return rest.shift();
    }
    return null;
  }

  static #option(name, parse, value) {
    try {
      return parse(value);
    } catch (e) {
      if (e instanceof UsageError) throw new UsageError(`argument ${name}: ${e.message}`);
      throw e;
    }
  }

  static #parse(args) {
    const rest = [...args];
    const name = rest.shift();
    if (name === undefined) throw new UsageError("the following arguments are required: COMMAND");
    if (name === "-h" || name === "--help") return { command: "help" };
    if (name === "generate" || name === "g") {
      const options = { command: "generate", bits: null, format: FWIDFormat.STANDARD_TEXT, count: 1, time: null };
      while (rest.length > 0) {
        const arg = rest.shift();
        let v;
        if (arg === "-h" || arg === "--help") return { command: "help" };
        if ((v = CLI.#value(arg, "b", "bits", rest)) !== null) {
          options.bits = CLI.#option("-b/--bits", CLI.#positive, v);
        } else if ((v = CLI.#value(arg, "f", "format", rest)) !== null) {
          options.format = CLI.#option("-f/--format", CLI.#format, v);
        } else if ((v = CLI.#value(arg, "n", "count", rest)) !== null) {
          options.count = CLI.#option("-n/--count", CLI.#positive, v);
        } else if ((v = CLI.#value(arg, "t", "time", rest)) !== null) {
          options.time = CLI.#option(
            "-t/--time",
            (text) => {
              try {
                return ISO8601.parse(text);
              } catch {
                throw new UsageError(`invalid ISO 8601 datetime: ${JSON.stringify(text)}`);
              }
            },
            v,
          );
        } else {
          throw new UsageError(`unrecognized arguments: ${arg}`);
        }
      }
      return options;
    }
    if (name === "inspect" || name === "i") {
      const ids = [];
      let optionsDone = false;
      for (const arg of rest) {
        if (!optionsDone && arg === "--") optionsDone = true;
        else if (!optionsDone && (arg === "-h" || arg === "--help")) return { command: "help" };
        else if (!optionsDone && arg.length > 1 && arg.startsWith("-")) throw new UsageError(`unrecognized arguments: ${arg}`);
        else ids.push(arg);
      }
      return { command: "inspect", ids };
    }
    throw new UsageError(`argument COMMAND: invalid choice: ${JSON.stringify(name)} (choose from generate, g, inspect, i)`);
  }

  static #hex(bytes) {
    return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  }

  static #describe(text) {
    const { format, id } = FWID.parse(text);
    const ms = id.timestampMS;
    return [
      `Format:     ${format}`,
      `Bits:       ${id.bits} (timestamp ${id.bitsTimestamp}, random ${id.bitsRandom})`,
      `Timestamp:  ${ISO8601.format(id.timestamp)} (${ms} ms)`,
      `Hex:        ${CLI.#hex(id.raw)}`,
      `Standard:   ${id.standardText}`,
      `Readable:   ${id.readableText}`,
      `Compact:    ${id.compactText}`,
      "",
    ].join("\n");
  }

  /**
   * Runs the CLI with `args` (without the program name) and returns the exit status.
   * @param {string[]} args
   * @param {{ readStdin: () => string, out: (text: string) => void, err: (text: string) => void }} io
   */
  static run(args, io) {
    let options;
    try {
      options = CLI.#parse(args);
    } catch (e) {
      if (!(e instanceof UsageError)) throw e;
      io.err(`${CLI.USAGE}\nfwid: error: ${e.message}\n`);
      return 2;
    }
    if (options.command === "help") {
      io.out(CLI.HELP);
      return 0;
    }
    try {
      if (options.command === "generate") {
        for (let i = 0; i < options.count; i++) {
          io.out(`${new FWID(options.bits, options.time).text(options.format)}\n`);
        }
        return 0;
      }
      let texts = options.ids;
      if (texts.length === 0 || (texts.length === 1 && texts[0] === "-")) {
        texts = io.readStdin().split(/\r?\n/).map((line) => line.trim()).filter((line) => line !== "");
      }
      let status = 0;
      texts.forEach((text, i) => {
        if (i > 0) io.out("\n");
        try {
          io.out(CLI.#describe(text));
        } catch (e) {
          if (!(e instanceof FWIDError)) throw e;
          io.err(`fwid: ${text}: ${e.message}\n`);
          status = 1;
        }
      });
      return status;
    } catch (e) {
      if (!(e instanceof FWIDError)) throw e;
      io.err(`fwid: ${e.message}\n`);
      return 1;
    }
  }
}
