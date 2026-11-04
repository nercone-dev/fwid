import Foundation
import Testing
@testable import FWID
@testable import FWIDCLI

enum TestData {
    static let directory = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        .appendingPathComponent("testdata")

    static func rows(_ name: String) throws -> [[String]] {
        try String(contentsOf: directory.appendingPathComponent(name), encoding: .utf8)
            .split(separator: "\n", omittingEmptySubsequences: true)
            .filter { !$0.hasPrefix("#") }
            .map { $0.split(separator: "\t", omittingEmptySubsequences: false).map(String.init) }
    }

    static func unhex(_ hex: String) -> [UInt8] {
        stride(from: 0, to: hex.count, by: 2).map { i in
            let start = hex.index(hex.startIndex, offsetBy: i)
            return UInt8(hex[start..<hex.index(start, offsetBy: 2)], radix: 16)!
        }
    }
}

func at(_ unixMS: Int64) -> Date { Date(timeIntervalSince1970: Double(unixMS) / 1000) }

@Test func sharedVectors() throws {
    let rows = try TestData.rows("vectors.tsv")
    #expect(!rows.isEmpty)
    for f in rows {
        let raw = TestData.unhex(f[0])
        let id = try FWID(bytes: raw)
        #expect(id.standardText == f[1])
        #expect(id.readableText == f[2])
        #expect(id.compactText == f[3])
        if f[4] != "-" { #expect(try String(id.timestampMS) == f[4]) }
        for (text, format) in [(f[1], FWIDFormat.standardText), (f[2], .readableText), (f[3], .compactText)] {
            let parsed = try FWID.parse(text)
            #expect(parsed.format == format, "\(text)")
            #expect(parsed.id.raw == raw, "\(text)")
        }
    }
}

@Test func invalidTextsAreRejected() throws {
    #expect(throws: FWIDError.self) { try FWID(text: "") }
    for row in try TestData.rows("invalid.tsv") {
        #expect(throws: FWIDError.self) { try FWID(text: row[0]) }
        #expect(throws: FWIDError.unknownFormat) { try FWIDFormat.detect(row[0]) }
    }
}

// RFC 4648 section 10, with '=' replaced by 'Z'.
@Test func base32CrockfordUnpaddedWithAliases() throws {
    #expect(Base32Crockford.encode([0xff, 0xff, 0xff, 0xff]) == "ZZZZZZR")
    #expect(try Base32Crockford.decode("zzzzzzr") == [0xff, 0xff, 0xff, 0xff])
    #expect(try Base32Crockford.decode("OILOILO") == Base32Crockford.decode("0110110"))
    for text in ["U0000000", "000000", "ZZZZZZZ"] {
        #expect(throws: FWIDError.self, "\(text)") { try Base32Crockford.decode(text) }
    }
}

@Test func base32HexRFC4648Vectors() throws {
    for (plain, encoded) in [
        ("", ""), ("f", "COZZZZZZ"), ("fo", "CPNGZZZZ"), ("foo", "CPNMUZZZ"),
        ("foob", "CPNMUOGZ"), ("fooba", "CPNMUOJ1"), ("foobar", "CPNMUOJ1E8ZZZZZZ"),
    ] {
        #expect(Base32Hex.encode(Array(plain.utf8)) == encoded)
        #expect(try Base32Hex.decode(encoded) == Array(plain.utf8))
    }
}

@Test func base32HexRejectsMalformedInput() {
    for text in ["C", "COZZZZZ", "CZZZZZZZ", "COZZZZZZCOZZZZZZ", "COzzzzzz", "C1ZZZZZZ", "CPNMUOJ\u{e9}"] {
        #expect(throws: FWIDError.self, "\(text)") { try Base32Hex.decode(text) }
    }
}

@Test func base62LengthsAndRoundTrip() throws {
    #expect(Base62.length(0) == 0)
    #expect(Base62.length(1) == 2)
    #expect(Base62.length(4) == 6)
    #expect(Base62.length(16) == 22)
    #expect(Base62.length(32) == 43)
    for size in 0..<40 {
        let data = (0..<size).map { UInt8(truncatingIfNeeded: $0 * 37 + 11) }
        let text = Base62.encode(data)
        #expect(text.utf8.count == Base62.length(size))
        #expect(try Base62.decode(text) == data)
    }
}

@Test func base62RejectsMalformedInput() {
    for text in ["0", "zzzzzz", "00000-", "00000\u{e9}"] {
        #expect(throws: FWIDError.self, "\(text)") { try Base62.decode(text) }
    }
}

@Test func generateLayout() throws {
    let t = at(1_704_067_200_000)
    let ms: UInt64 = 725_760_000_000
    #expect(try FWID.epochMS(t) == ms)
    #expect(try FWID.minBits(t) == 160)
    for bits in stride(from: 160, through: 512, by: 32) {
        let id = try FWID.generate(bits: bits, date: t)
        #expect(id.bits == bits)
        #expect(id.bitsTimestamp == bits / 4)
        #expect(id.bitsRandom == bits / 4 * 3)
        #expect(try id.timestampMS == ms)
        #expect(try id.timestamp == t)
        let field = Array(id.raw[..<(bits / 32)])
        #expect(Array(field.suffix(5)) == [0xA8, 0xFA, 0xAA, 0xC0, 0x00])
        #expect(field.dropLast(5).allSatisfy { $0 == 0 })
    }
}

@Test func generateRejectsBadSizes() throws {
    let t = at(1_704_067_200_000)
    for bits in [0, 31, 33, 161] {
        #expect(throws: FWIDError.bits) { try FWID.generate(bits: bits, date: t) }
    }
    #expect(throws: FWIDError.timestampTooLarge(bits: 128, required: 160)) { try FWID.generate(bits: 128, date: t) }
    #expect(throws: FWIDError.beforeEpoch) { try FWID.generate(date: at(978_307_199_999)) }
    _ = try FWID.generate(date: at(978_307_200_000))
    #expect(throws: FWIDError.bits) { try FWID(bytes: [0, 0, 0]) }
    #expect(throws: FWIDError.bits) { try FWID(bytes: []) }
}

@Test func idsSortByTime() throws {
    let a = try FWID.generate(bits: 256, date: at(1_000_000_000_000))
    let b = try FWID.generate(bits: 256, date: at(1_000_000_000_001))
    #expect(a < b)
    #expect(a.standardText < b.standardText)
    #expect(try FWID() != FWID())
}

@Test func iso8601ParseAndFormat() throws {
    for (text, unixMS) in [
        ("2024-01-01T00:00:00Z", Int64(1_704_067_200_000)),
        ("2024-01-01", 1_704_067_200_000),
        ("2024-01-01 00:00", 1_704_067_200_000),
        ("2024-01-01T09:00:00+09:00", 1_704_067_200_000),
        ("2024-01-01T09:00:00+0900", 1_704_067_200_000),
        ("2023-12-31T19:00:00-05", 1_704_067_200_000),
        ("2024-02-29T12:34:56.789123Z", 1_709_210_096_789),
        ("2024-02-29T12:34:56.5", 1_709_210_096_500),
        ("1970-01-01T00:00:00Z", 0),
    ] {
        #expect(try ISO8601.parse(text) == at(unixMS), "\(text)")
    }
    #expect(ISO8601.format(at(1_709_210_096_789)) == "2024-02-29T12:34:56.789+00:00")
    for text in [
        "", "2024", "2024-13-01", "2023-02-29", "2024-04-31", "2024-01-01T24:00", "2024-01-01T00:60",
        "2024-01-01T00:00:60", "2024-01-01T00", "2024-01-01T00:00:00.", "2024-01-01T00:00:00+24:00",
        "2024-01-01T00:00:00Zx", "2024-01-01Z", "24-01-01", "2024-01-01T00:00:00 +09:00",
    ] {
        #expect(throws: FWIDError.invalidDatetime, "\(text)") { try ISO8601.parse(text) }
    }
}

@Test func textRejectsUnformatted() throws {
    let id = try FWID()
    #expect(throws: FWIDError.notTextFormat) { try id.text(.unformatted) }
    #expect(try id.text(.standardText) == id.description)
}

func runCLI(_ args: [String], stdin: [String] = []) -> (status: Int32, out: String, err: String) {
    var lines = stdin[...]
    var out = "", err = ""
    let status = CLI.run(args, readLine: { lines.popFirst() }, out: { out += $0 }, err: { err += $0 })
    return (status, out, err)
}

@Test func cliGenerateAndInspect() throws {
    let g = runCLI(["g", "-t", "2024-01-01T00:00:00Z", "-b", "256", "-f", "compact", "-n", "3"])
    #expect(g.status == 0)
    let lines = g.out.split(separator: "\n").map(String.init)
    #expect(lines.count == 3)
    let i = runCLI(["i", lines[0]])
    #expect(i.status == 0)
    #expect(i.out.contains("Format:     Compact Text\n"))
    #expect(i.out.contains("Bits:       256 (timestamp 64, random 192)\n"))
    #expect(i.out.contains("Timestamp:  2024-01-01T00:00:00.000+00:00 (725760000000 ms)\n"))
    let fromStdin = runCLI(["inspect"], stdin: [lines[1] + "  ", "", "bogus", lines[2]])
    #expect(fromStdin.status == 1)
    #expect(fromStdin.err.hasPrefix("fwid: bogus: "))
    #expect(fromStdin.out.components(separatedBy: "Format:").count == 3)
}

@Test func cliUsageErrors() {
    for args in [[], ["x"], ["g", "-b", "0"], ["g", "-b", "x"], ["g", "-f", "nope"], ["g", "-t", "yesterday"], ["g", "-n"], ["g", "--zzz"]] {
        #expect(runCLI(args).status == 2, "\(args)")
    }
    #expect(runCLI(["g", "-b", "128"]).status == 1)
    #expect(runCLI(["-h"]).status == 0)
}
