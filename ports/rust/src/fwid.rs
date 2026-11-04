use std::fmt;
use std::str::FromStr;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use crate::base32hex::Base32Hex;
use crate::base62::Base62;
use crate::error::Error;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum Format {
    Unformatted,
    StandardText,
    ReadableText,
    CompactText,
}

impl Format {
    pub fn name(self) -> &'static str {
        match self {
            Format::Unformatted => "Unformatted",
            Format::StandardText => "Standard Text",
            Format::ReadableText => "Readable Text",
            Format::CompactText => "Compact Text",
        }
    }

    /// Detects the text format of `text`; the first format that parses wins,
    /// in the order Standard, Readable, Compact.
    pub fn detect(text: &str) -> Result<Format, Error> {
        FWID::parse(text).map(|(format, _)| format)
    }
}

/// A FourWord Identifier: a quarter timestamp (milliseconds since
/// 2001-01-01 00:00:00 UTC) followed by three quarters of CSPRNG output.
#[derive(Clone, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct FWID {
    raw: Vec<u8>,
}

impl FWID {
    /// The FWID epoch, 2001-01-01 00:00:00 UTC, in Unix milliseconds.
    pub const EPOCH_UNIX_MS: u64 = 978_307_200_000;
    pub const BITS_ALIGN: usize = 32;

    /// Generates an FWID of the smallest size that fits the current time.
    pub fn new() -> Result<FWID, Error> {
        Self::generate(None, None)
    }

    pub fn from_bytes(raw: Vec<u8>) -> Result<FWID, Error> {
        if raw.is_empty() || raw.len() % (Self::BITS_ALIGN / 8) != 0 {
            return Err(Error::Bits);
        }
        Ok(FWID { raw })
    }

    pub fn from_standard_text(text: &str) -> Result<FWID, Error> {
        Self::from_bytes(Base32Hex::decode(text)?)
    }

    pub fn from_readable_text(text: &str) -> Result<FWID, Error> {
        if text.bytes().any(|b| b.is_ascii_uppercase()) {
            return Err(Error::ReadableCase);
        }
        let mut joined = String::with_capacity(text.len());
        for group in text.split('-') {
            if group.len() != 8 {
                return Err(Error::ReadableGroups);
            }
            joined.push_str(&group.to_ascii_uppercase());
        }
        Self::from_bytes(Base32Hex::decode(&joined)?)
    }

    pub fn from_compact_text(text: &str) -> Result<FWID, Error> {
        Self::from_bytes(Base62::decode(text)?)
    }

    /// Parses `text` in any text format and reports which one matched.
    pub fn parse(text: &str) -> Result<(Format, FWID), Error> {
        if let Ok(id) = Self::from_standard_text(text) {
            return Ok((Format::StandardText, id));
        }
        if let Ok(id) = Self::from_readable_text(text) {
            return Ok((Format::ReadableText, id));
        }
        if let Ok(id) = Self::from_compact_text(text) {
            return Ok((Format::CompactText, id));
        }
        Err(Error::UnknownFormat)
    }

    pub fn from_text(text: &str) -> Result<FWID, Error> {
        Self::parse(text).map(|(_, id)| id)
    }

    pub fn check_bits(bits: usize) -> Result<(), Error> {
        if bits < Self::BITS_ALIGN || bits % Self::BITS_ALIGN != 0 {
            return Err(Error::Bits);
        }
        Ok(())
    }

    /// Milliseconds from the FWID epoch to `time` (default: now).
    pub fn epoch_ms(time: Option<SystemTime>) -> Result<u64, Error> {
        let time = time.unwrap_or_else(SystemTime::now);
        let unix_ms = time
            .duration_since(UNIX_EPOCH)
            .map_err(|_| Error::BeforeEpoch)?
            .as_millis();
        let ms = unix_ms
            .checked_sub(u128::from(Self::EPOCH_UNIX_MS))
            .ok_or(Error::BeforeEpoch)?;
        u64::try_from(ms).map_err(|_| Error::TimestampOverflow)
    }

    fn bytes_for(ms: u64) -> usize {
        (((64 - ms.leading_zeros()) as usize).div_ceil(8)).max(1)
    }

    /// Smallest bit length that fits the timestamp of `time` (default: now).
    pub fn min_bits(time: Option<SystemTime>) -> Result<usize, Error> {
        Ok(Self::bytes_for(Self::epoch_ms(time)?) * Self::BITS_ALIGN)
    }

    /// Generates an FWID of `bits` bits (default: the smallest that fits).
    pub fn generate(bits: Option<usize>, time: Option<SystemTime>) -> Result<FWID, Error> {
        let ms = Self::epoch_ms(time)?;
        let required = Self::bytes_for(ms) * Self::BITS_ALIGN;
        let bits = bits.unwrap_or(required);
        Self::check_bits(bits)?;
        if bits < required {
            return Err(Error::TimestampTooLarge { bits, required });
        }
        let len = bits / 8;
        let timestamp_len = len / 4;
        let mut raw = Vec::new();
        raw.try_reserve_exact(len).map_err(|_| Error::Allocation)?;
        raw.resize(len, 0);
        let be = ms.to_be_bytes();
        if timestamp_len >= be.len() {
            raw[timestamp_len - be.len()..timestamp_len].copy_from_slice(&be);
        } else {
            raw[..timestamp_len].copy_from_slice(&be[be.len() - timestamp_len..]);
        }
        getrandom::fill(&mut raw[timestamp_len..]).map_err(|_| Error::Random)?;
        Ok(FWID { raw })
    }

    pub fn as_bytes(&self) -> &[u8] {
        &self.raw
    }

    pub fn into_bytes(self) -> Vec<u8> {
        self.raw
    }

    pub fn bits(&self) -> usize {
        self.raw.len() * 8
    }

    pub fn bits_timestamp(&self) -> usize {
        self.raw.len() * 2
    }

    pub fn bits_random(&self) -> usize {
        self.raw.len() * 6
    }

    /// Milliseconds from the FWID epoch stored in the timestamp field.
    pub fn timestamp_ms(&self) -> Result<u64, Error> {
        let field = &self.raw[..self.raw.len() / 4];
        let split = field.len().saturating_sub(8);
        if field[..split].iter().any(|&b| b != 0) {
            return Err(Error::TimestampOverflow);
        }
        Ok(field[split..].iter().fold(0, |acc, &b| acc << 8 | u64::from(b)))
    }

    pub fn timestamp(&self) -> Result<SystemTime, Error> {
        let unix_ms = self
            .timestamp_ms()?
            .checked_add(Self::EPOCH_UNIX_MS)
            .ok_or(Error::TimeOutOfRange)?;
        UNIX_EPOCH
            .checked_add(Duration::from_millis(unix_ms))
            .ok_or(Error::TimeOutOfRange)
    }

    pub fn text(&self, format: Format) -> Result<String, Error> {
        match format {
            Format::StandardText => Ok(self.standard_text()),
            Format::ReadableText => Ok(self.readable_text()),
            Format::CompactText => Ok(self.compact_text()),
            Format::Unformatted => Err(Error::NotTextFormat),
        }
    }

    pub fn standard_text(&self) -> String {
        Base32Hex::encode(&self.raw)
    }

    pub fn readable_text(&self) -> String {
        let standard = self.standard_text().to_ascii_lowercase();
        let mut out = String::with_capacity(standard.len() + standard.len() / 8);
        for (i, chunk) in standard.as_bytes().chunks(8).enumerate() {
            if i > 0 {
                out.push('-');
            }
            out.extend(chunk.iter().map(|&b| char::from(b)));
        }
        out
    }

    pub fn compact_text(&self) -> String {
        Base62::encode(&self.raw)
    }
}

impl fmt::Display for FWID {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.standard_text())
    }
}

impl FromStr for FWID {
    type Err = Error;

    fn from_str(text: &str) -> Result<FWID, Error> {
        Self::from_text(text)
    }
}

impl TryFrom<&[u8]> for FWID {
    type Error = Error;

    fn try_from(raw: &[u8]) -> Result<FWID, Error> {
        Self::from_bytes(raw.to_vec())
    }
}

impl AsRef<[u8]> for FWID {
    fn as_ref(&self) -> &[u8] {
        &self.raw
    }
}
