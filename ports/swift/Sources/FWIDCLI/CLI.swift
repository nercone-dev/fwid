import Foundation
import FWID

public enum CLI {
    static let usage = "usage: fwid [-h] COMMAND ..."

    static let help = """
    usage: fwid [-h] COMMAND ...

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

    enum Command {
        case help
        case generate(bits: Int?, format: FWIDFormat, count: Int, time: Date?)
        case inspect(ids: [String])
    }

    struct UsageError: Error { let message: String }

    static func positive(_ text: String) throws -> Int {
        guard let value = Int(text) else { throw UsageError(message: "invalid integer: \(String(reflecting: text))") }
        guard value >= 1 else { throw UsageError(message: "must be 1 or greater") }
        return value
    }

    static func format(_ text: String) throws -> FWIDFormat {
        switch text {
        case "standard": return .standardText
        case "readable": return .readableText
        case "compact": return .compactText
        default:
            throw UsageError(message: "invalid choice: \(String(reflecting: text)) (choose from compact, readable, standard)")
        }
    }

    /// Matches `-bVALUE`, `--bits=VALUE`, `-b VALUE` and `--bits VALUE`.
    /// Returns nil if `arg` is not this option.
    static func value(of arg: String, short: Character, long: String, rest: inout IndexingIterator<[String]>) throws -> String? {
        if arg.hasPrefix("--\(long)=") { return String(arg.dropFirst(long.count + 3)) }
        if arg.count > 2, arg.hasPrefix("-\(short)"), !arg.hasPrefix("--") { return String(arg.dropFirst(2)) }
        if arg == "--\(long)" || arg == "-\(short)" {
            guard let next = rest.next() else {
                throw UsageError(message: "argument -\(short)/--\(long): expected one argument")
            }
            return next
        }
        return nil
    }

    static func parse(_ args: [String]) throws -> Command {
        var it = args.makeIterator()
        guard let name = it.next() else { throw UsageError(message: "the following arguments are required: COMMAND") }
        switch name {
        case "-h", "--help":
            return .help
        case "generate", "g":
            var bits: Int?
            var format = FWIDFormat.standardText
            var count = 1
            var time: Date?
            while let arg = it.next() {
                if arg == "-h" || arg == "--help" { return .help }
                if let v = try value(of: arg, short: "b", long: "bits", rest: &it) {
                    bits = try wrap("-b/--bits") { try positive(v) }
                } else if let v = try value(of: arg, short: "f", long: "format", rest: &it) {
                    format = try wrap("-f/--format") { try self.format(v) }
                } else if let v = try value(of: arg, short: "n", long: "count", rest: &it) {
                    count = try wrap("-n/--count") { try positive(v) }
                } else if let v = try value(of: arg, short: "t", long: "time", rest: &it) {
                    guard let parsed = try? ISO8601.parse(v) else {
                        throw UsageError(message: "argument -t/--time: invalid ISO 8601 datetime: \(String(reflecting: v))")
                    }
                    time = parsed
                } else {
                    throw UsageError(message: "unrecognized arguments: \(arg)")
                }
            }
            return .generate(bits: bits, format: format, count: count, time: time)
        case "inspect", "i":
            var ids = [String]()
            var optionsDone = false
            while let arg = it.next() {
                if !optionsDone && arg == "--" {
                    optionsDone = true
                } else if !optionsDone && (arg == "-h" || arg == "--help") {
                    return .help
                } else if !optionsDone && arg.count > 1 && arg.hasPrefix("-") {
                    throw UsageError(message: "unrecognized arguments: \(arg)")
                } else {
                    ids.append(arg)
                }
            }
            return .inspect(ids: ids)
        default:
            throw UsageError(message: "argument COMMAND: invalid choice: \(String(reflecting: name)) (choose from generate, g, inspect, i)")
        }
    }

    static func wrap<T>(_ option: String, _ body: () throws -> T) throws -> T {
        do { return try body() } catch let e as UsageError {
            throw UsageError(message: "argument \(option): \(e.message)")
        }
    }

    static func hex(_ bytes: [UInt8]) -> String {
        let digits = Array("0123456789abcdef".utf8)
        var out = [UInt8]()
        out.reserveCapacity(bytes.count * 2)
        for b in bytes {
            out.append(digits[Int(b >> 4)])
            out.append(digits[Int(b & 15)])
        }
        return String(decoding: out, as: UTF8.self)
    }

    /// Runs the CLI with `args` (without the program name) and returns the exit status.
    public static func run(
        _ args: [String],
        readLine: () -> String?,
        out: (String) -> Void,
        err: (String) -> Void
    ) -> Int32 {
        let command: Command
        do {
            command = try parse(args)
        } catch let e as UsageError {
            err("\(usage)\nfwid: error: \(e.message)\n")
            return 2
        } catch {
            err("fwid: \(error)\n")
            return 2
        }
        switch command {
        case .help:
            out(help)
            return 0
        case let .generate(bits, format, count, time):
            for _ in 0..<count {
                do {
                    out(try FWID.generate(bits: bits, date: time).text(format) + "\n")
                } catch {
                    err("fwid: \(error)\n")
                    return 1
                }
            }
            return 0
        case let .inspect(ids):
            var texts = ids
            if ids.isEmpty || ids == ["-"] {
                texts = []
                while let line = readLine() {
                    let trimmed = line.trimmingCharacters(in: .whitespacesAndNewlines)
                    if !trimmed.isEmpty { texts.append(trimmed) }
                }
            }
            var status: Int32 = 0
            for (i, text) in texts.enumerated() {
                if i > 0 { out("\n") }
                do {
                    let (format, id) = try FWID.parse(text)
                    let ms = try id.timestampMS
                    out("""
                    Format:     \(format.name)
                    Bits:       \(id.bits) (timestamp \(id.bitsTimestamp), random \(id.bitsRandom))
                    Timestamp:  \(ISO8601.format(try id.timestamp)) (\(ms) ms)
                    Hex:        \(hex(id.raw))
                    Standard:   \(id.standardText)
                    Readable:   \(id.readableText)
                    Compact:    \(id.compactText)

                    """)
                } catch {
                    err("fwid: \(text): \(error)\n")
                    status = 1
                }
            }
            return status
        }
    }
}
