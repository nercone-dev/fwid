use crate::error::Error;

/// Crockford's Base32 without check symbols and without padding.
///
/// Encoding emits uppercase symbols. Decoding is case-insensitive and maps
/// the look-alike symbols `I` and `L` to `1` and `O` to `0`, as Crockford specifies.
pub struct Base32Crockford;

impl Base32Crockford {
    pub const ALPHABET: &'static [u8; 32] = b"0123456789ABCDEFGHJKMNPQRSTVWXYZ";

    /// Bytes carried by a block with this many characters.
    fn bytes_from_chars(chars: usize) -> Option<usize> {
        match chars {
            8 => Some(5),
            7 => Some(4),
            5 => Some(3),
            4 => Some(2),
            2 => Some(1),
            _ => None,
        }
    }

    fn index(c: u8) -> Option<u64> {
        let c = match c.to_ascii_uppercase() {
            b'I' | b'L' => b'1',
            b'O' => b'0',
            c => c,
        };
        Self::ALPHABET.iter().position(|&a| a == c).map(|i| i as u64)
    }

    pub fn encode(data: &[u8]) -> String {
        let mut out = String::with_capacity((data.len() * 8).div_ceil(5));
        for chunk in data.chunks(5) {
            let n = chunk.len();
            let mut value = chunk.iter().fold(0u64, |acc, &b| acc << 8 | u64::from(b));
            value <<= 8 * (5 - n);
            let chars = (n * 8 + 4) / 5;
            for j in 0..chars {
                out.push(char::from(Self::ALPHABET[((value >> (35 - 5 * j)) & 31) as usize]));
            }
        }
        out
    }

    pub fn decode(text: &str) -> Result<Vec<u8>, Error> {
        let mut out = Vec::with_capacity(text.len() / 8 * 5 + 4);
        for block in text.as_bytes().chunks(8) {
            let n = Self::bytes_from_chars(block.len()).ok_or(Error::Base32CrockfordLength)?;
            let mut value = 0u64;
            for &c in block {
                let index = Self::index(c).ok_or_else(|| {
                    Error::Character(
                        String::from_utf8_lossy(block)
                            .chars()
                            .find(|&ch| !ch.is_ascii() || Self::index(ch as u8).is_none())
                            .unwrap_or('\u{FFFD}'),
                    )
                })?;
                value = value << 5 | index;
            }
            let extra = block.len() * 5 - n * 8;
            if value & ((1u64 << extra) - 1) != 0 {
                return Err(Error::Base32CrockfordTrailingBits);
            }
            let value = value >> extra;
            out.extend((0..n).map(|i| (value >> (8 * (n - 1 - i))) as u8));
        }
        Ok(out)
    }
}
