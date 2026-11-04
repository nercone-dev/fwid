use std::fmt;

/// Every failure the FWID library can report. No variant allocates.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Error {
    /// The bit length is not a positive multiple of 32.
    Bits,
    /// The timestamp does not fit in the timestamp field.
    TimestampTooLarge { bits: usize, required: usize },
    /// The timestamp is before 2001-01-01 00:00:00 UTC.
    BeforeEpoch,
    /// The timestamp field holds a value that does not fit in 64 bits.
    TimestampOverflow,
    /// The point in time cannot be represented.
    TimeOutOfRange,
    /// The text is not a valid ISO 8601 datetime.
    InvalidDatetime,
    /// The text is not in any known FWID text format.
    UnknownFormat,
    /// The requested format is not a text format.
    NotTextFormat,
    /// The requested size cannot be allocated.
    Allocation,
    /// The system random number generator failed.
    Random,
    /// Base32Hex length is not a multiple of 8.
    Base32HexLength,
    /// Base32Hex padding appears in a block other than the last.
    Base32HexPaddingPosition,
    /// Base32Hex padding has an impossible length.
    Base32HexPaddingLength,
    /// Base32Hex trailing bits are not zero.
    Base32HexTrailingBits,
    /// Base62 length matches no byte length.
    Base62Length,
    /// Base62 value does not fit in the byte length its text length implies.
    Base62Range,
    /// A character outside the alphabet.
    Character(char),
    /// Readable Text contains uppercase characters.
    ReadableCase,
    /// Readable Text groups are not 8 characters long.
    ReadableGroups,
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Error::Bits => f.write_str("Bits must be a positive multiple of 32"),
            Error::TimestampTooLarge { bits, required } => write!(
                f,
                "{bits} bits is too small for this timestamp (need at least {required})"
            ),
            Error::BeforeEpoch => f.write_str(
                "datetime must not be before the FWID epoch (2001-01-01 00:00:00 UTC)",
            ),
            Error::TimestampOverflow => f.write_str("timestamp does not fit in 64 bits"),
            Error::TimeOutOfRange => f.write_str("datetime is out of range"),
            Error::InvalidDatetime => f.write_str("invalid ISO 8601 datetime"),
            Error::UnknownFormat => f.write_str("Unknown Format"),
            Error::NotTextFormat => f.write_str("Format is not Text-based Format"),
            Error::Allocation => f.write_str("size is too large"),
            Error::Random => f.write_str("random number generator failed"),
            Error::Base32HexLength => f.write_str("Base32Hex length must be a multiple of 8"),
            Error::Base32HexPaddingPosition => {
                f.write_str("Padding is only allowed in the last block")
            }
            Error::Base32HexPaddingLength => f.write_str("Invalid padding length"),
            Error::Base32HexTrailingBits => f.write_str("Non-zero trailing bits"),
            Error::Base62Length => f.write_str("Invalid Base62 length"),
            Error::Base62Range => f.write_str("Value out of range"),
            Error::Character(c) => write!(f, "Invalid character: {c:?}"),
            Error::ReadableCase => f.write_str("Readable Text must be lowercase"),
            Error::ReadableGroups => {
                f.write_str("Readable Text must be split into groups of 8 characters")
            }
        }
    }
}

impl std::error::Error for Error {}
