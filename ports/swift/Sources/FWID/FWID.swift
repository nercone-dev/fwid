import Foundation

public enum FWIDFormat: Equatable, Hashable, Sendable {
    case unformatted
    case standardText
    case readableText
    case compactText

    public var name: String {
        switch self {
        case .unformatted: return "Unformatted"
        case .standardText: return "Standard Text"
        case .readableText: return "Readable Text"
        case .compactText: return "Compact Text"
        }
    }

    /// Detects the text format of `text`; the first format that parses wins,
    /// in the order Standard, Readable, Compact.
    public static func detect(_ text: String) throws -> FWIDFormat {
        try FWID.parse(text).format
    }
}

/// A FourWord Identifier: a quarter timestamp (milliseconds since
/// 2001-01-01 00:00:00 UTC) followed by three quarters of CSPRNG output.
public struct FWID: Hashable, Comparable, CustomStringConvertible, Sendable {
    /// The FWID epoch, 2001-01-01 00:00:00 UTC, in Unix milliseconds.
    public static let epochUnixMS: UInt64 = 978_307_200_000
    /// Largest Unix millisecond count that `ISO8601.format` can print (Int64 microseconds).
    static let maxFormattableUnixMS: UInt64 = 9_000_000_000_000_000
    public static let bitsAlign = 32

    public let raw: [UInt8]

    /// Generates an FWID of the smallest size that fits the current time.
    public init() throws {
        self = try FWID.generate()
    }

    public init(bytes: [UInt8]) throws {
        guard !bytes.isEmpty, bytes.count % (FWID.bitsAlign / 8) == 0 else { throw FWIDError.bits }
        raw = bytes
    }

    /// Parses `text` in any text format.
    public init(text: String) throws {
        self = try FWID.parse(text).id
    }

    public static func fromStandardText(_ text: String) throws -> FWID {
        try FWID(bytes: Base32Hex.decode(text))
    }

    public static func fromReadableText(_ text: String) throws -> FWID {
        if text.utf8.contains(where: { $0 >= UInt8(ascii: "A") && $0 <= UInt8(ascii: "Z") }) {
            throw FWIDError.readableCase
        }
        var joined = [UInt8]()
        joined.reserveCapacity(text.utf8.count)
        let groups = text.utf8.split(separator: UInt8(ascii: "-"), omittingEmptySubsequences: false)
        for (i, group) in groups.enumerated() {
            let valid = i == groups.count - 1 ? (1...8).contains(group.count) : group.count == 8
            guard valid else { throw FWIDError.readableGroups }
            joined.append(contentsOf: group)
        }
        return try FWID(bytes: Base32Crockford.decode(String(decoding: joined, as: UTF8.self)))
    }

    public static func fromCompactText(_ text: String) throws -> FWID {
        try FWID(bytes: Base62.decode(text))
    }

    /// Parses `text` in any text format and reports which one matched.
    public static func parse(_ text: String) throws -> (format: FWIDFormat, id: FWID) {
        if let id = try? fromStandardText(text) { return (.standardText, id) }
        if let id = try? fromReadableText(text) { return (.readableText, id) }
        if let id = try? fromCompactText(text) { return (.compactText, id) }
        throw FWIDError.unknownFormat
    }

    public static func checkBits(_ bits: Int) throws {
        guard bits >= bitsAlign, bits % bitsAlign == 0 else { throw FWIDError.bits }
    }

    /// Milliseconds from the FWID epoch to `date` (default: now).
    ///
    /// `Date` is a `Double`; the value is rounded to microseconds before the
    /// milliseconds are floored, so dates built from whole milliseconds are exact.
    public static func epochMS(_ date: Date? = nil) throws -> UInt64 {
        let seconds = (date ?? Date()).timeIntervalSince1970
        guard seconds.isFinite else { throw FWIDError.timeOutOfRange }
        let unixMS = ((seconds * 1e6).rounded() / 1000).rounded(.down)
        guard unixMS >= Double(epochUnixMS) else { throw FWIDError.beforeEpoch }
        guard unixMS < 18_446_744_073_709_551_616.0 else { throw FWIDError.timestampOverflow }
        return UInt64(unixMS) - epochUnixMS
    }

    private static func bytes(for ms: UInt64) -> Int {
        max(1, (UInt64.bitWidth - ms.leadingZeroBitCount + 7) / 8)
    }

    /// Smallest bit length that fits the timestamp of `date` (default: now).
    public static func minBits(_ date: Date? = nil) throws -> Int {
        bytes(for: try epochMS(date)) * bitsAlign
    }

    /// Generates an FWID of `bits` bits (default: the smallest that fits).
    public static func generate(bits: Int? = nil, date: Date? = nil) throws -> FWID {
        let ms = try epochMS(date)
        let required = bytes(for: ms) * bitsAlign
        let bits = bits ?? required
        try checkBits(bits)
        guard bits >= required else { throw FWIDError.timestampTooLarge(bits: bits, required: required) }
        let length = bits / 8
        let timestampLength = length / 4
        var raw = [UInt8](repeating: 0, count: length)
        for i in 0..<min(8, timestampLength) {
            raw[timestampLength - 1 - i] = UInt8(truncatingIfNeeded: ms >> UInt64(8 * i))
        }
        var rng = SystemRandomNumberGenerator()
        for i in timestampLength..<length {
            raw[i] = UInt8.random(in: .min ... .max, using: &rng)
        }
        return try FWID(bytes: raw)
    }

    public var bits: Int { raw.count * 8 }
    public var bitsTimestamp: Int { raw.count * 2 }
    public var bitsRandom: Int { raw.count * 6 }

    /// Milliseconds from the FWID epoch stored in the timestamp field.
    public var timestampMS: UInt64 {
        get throws {
            let field = raw[..<(raw.count / 4)]
            let split = field.endIndex - min(8, field.count)
            if field[..<split].contains(where: { $0 != 0 }) { throw FWIDError.timestampOverflow }
            return field[split...].reduce(0) { $0 << 8 | UInt64($1) }
        }
    }

    public var timestamp: Date {
        get throws {
            let (unixMS, overflow) = try timestampMS.addingReportingOverflow(FWID.epochUnixMS)
            // ISO8601.format works in Int64 microseconds; reject what it cannot represent.
            guard !overflow, unixMS <= FWID.maxFormattableUnixMS else { throw FWIDError.timeOutOfRange }
            return Date(timeIntervalSince1970: Double(unixMS) / 1000)
        }
    }

    public func text(_ format: FWIDFormat = .standardText) throws -> String {
        switch format {
        case .standardText: return standardText
        case .readableText: return readableText
        case .compactText: return compactText
        case .unformatted: throw FWIDError.notTextFormat
        }
    }

    public var standardText: String { Base32Hex.encode(raw) }

    public var readableText: String {
        let standard = Array(Base32Crockford.encode(raw).lowercased().utf8)
        var out = [UInt8]()
        out.reserveCapacity(standard.count + standard.count / 8)
        for start in stride(from: 0, to: standard.count, by: 8) {
            if start > 0 { out.append(UInt8(ascii: "-")) }
            out.append(contentsOf: standard[start..<min(start + 8, standard.count)])
        }
        return String(decoding: out, as: UTF8.self)
    }

    public var compactText: String { Base62.encode(raw) }

    public var description: String { standardText }

    public static func < (lhs: FWID, rhs: FWID) -> Bool {
        lhs.raw.lexicographicallyPrecedes(rhs.raw)
    }
}
