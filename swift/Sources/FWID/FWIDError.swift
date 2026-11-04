/// Every failure the FWID library can report.
public enum FWIDError: Error, Equatable, CustomStringConvertible {
    /// The bit length is not a positive multiple of 32.
    case bits
    /// The timestamp does not fit in the timestamp field.
    case timestampTooLarge(bits: Int, required: Int)
    /// The timestamp is before 2001-01-01 00:00:00 UTC.
    case beforeEpoch
    /// The timestamp field holds a value that does not fit in 64 bits.
    case timestampOverflow
    /// The point in time cannot be represented.
    case timeOutOfRange
    /// The text is not a valid ISO 8601 datetime.
    case invalidDatetime
    /// The text is not in any known FWID text format.
    case unknownFormat
    /// The requested format is not a text format.
    case notTextFormat
    /// Base32Hex length is not a multiple of 8.
    case base32HexLength
    /// Base32Hex padding appears in a block other than the last.
    case base32HexPaddingPosition
    /// Base32Hex padding has an impossible length.
    case base32HexPaddingLength
    /// Base32Hex trailing bits are not zero.
    case base32HexTrailingBits
    /// Base62 length matches no byte length.
    case base62Length
    /// Base62 value does not fit in the byte length its text length implies.
    case base62Range
    /// A character outside the alphabet.
    case character(Character)
    /// Readable Text contains uppercase characters.
    case readableCase
    /// Readable Text groups are not 8 characters long.
    case readableGroups

    public var description: String {
        switch self {
        case .bits: return "Bits must be a positive multiple of 32"
        case let .timestampTooLarge(bits, required):
            return "\(bits) bits is too small for this timestamp (need at least \(required))"
        case .beforeEpoch:
            return "datetime must not be before the FWID epoch (2001-01-01 00:00:00 UTC)"
        case .timestampOverflow: return "timestamp does not fit in 64 bits"
        case .timeOutOfRange: return "datetime is out of range"
        case .invalidDatetime: return "invalid ISO 8601 datetime"
        case .unknownFormat: return "Unknown Format"
        case .notTextFormat: return "Format is not Text-based Format"
        case .base32HexLength: return "Base32Hex length must be a multiple of 8"
        case .base32HexPaddingPosition: return "Padding is only allowed in the last block"
        case .base32HexPaddingLength: return "Invalid padding length"
        case .base32HexTrailingBits: return "Non-zero trailing bits"
        case .base62Length: return "Invalid Base62 length"
        case .base62Range: return "Value out of range"
        case let .character(c): return "Invalid character: \(String(reflecting: c))"
        case .readableCase: return "Readable Text must be lowercase"
        case .readableGroups: return "Readable Text must be split into groups of 8 characters"
        }
    }
}
