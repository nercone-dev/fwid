use crate::error::Error;

/// Base32 Hex (RFC 4648 section 7) with `Z` as the padding character.
pub struct Base32Hex;

impl Base32Hex {
    pub const ALPHABET: &'static [u8; 32] = b"0123456789ABCDEFGHIJKLMNOPQRSTUV";
    pub const PAD: u8 = b'Z';

    /// Bytes carried by a block with this many non-padding characters.
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
        match c {
            b'0'..=b'9' => Some(u64::from(c - b'0')),
            b'A'..=b'V' => Some(u64::from(c - b'A' + 10)),
            _ => None,
        }
    }

    pub fn encode(data: &[u8]) -> String {
        let mut out = String::with_capacity(data.len().div_ceil(5) * 8);
        for chunk in data.chunks(5) {
            let n = chunk.len();
            let mut value = chunk.iter().fold(0u64, |acc, &b| acc << 8 | u64::from(b));
            value <<= 8 * (5 - n);
            let chars = (n * 8 + 4) / 5;
            for j in 0..chars {
                out.push(char::from(Self::ALPHABET[((value >> (35 - 5 * j)) & 31) as usize]));
            }
            for _ in chars..8 {
                out.push(char::from(Self::PAD));
            }
        }
        out
    }

    pub fn decode(text: &str) -> Result<Vec<u8>, Error> {
        let text = text.as_bytes();
        if text.len() % 8 != 0 {
            return Err(Error::Base32HexLength);
        }
        let blocks = text.len() / 8;
        let mut out = Vec::with_capacity(blocks * 5);
        for (b, block) in text.chunks_exact(8).enumerate() {
            let body_len = block
                .iter()
                .rposition(|&c| c != Self::PAD)
                .map_or(0, |i| i + 1);
            if body_len != 8 && b != blocks - 1 {
                return Err(Error::Base32HexPaddingPosition);
            }
            let n = Self::bytes_from_chars(body_len).ok_or(Error::Base32HexPaddingLength)?;
            let mut value = 0u64;
            for &c in &block[..body_len] {
                let index = Self::index(c).ok_or_else(|| {
                    let body = String::from_utf8_lossy(&block[..body_len]);
                    Error::Character(
                        body.chars()
                            .find(|&ch| !ch.is_ascii() || Self::index(ch as u8).is_none())
                            .unwrap_or('\u{FFFD}'),
                    )
                })?;
                value = value << 5 | index;
            }
            let extra = body_len * 5 - n * 8;
            if value & ((1u64 << extra) - 1) != 0 {
                return Err(Error::Base32HexTrailingBits);
            }
            let value = value >> extra;
            out.extend((0..n).map(|i| (value >> (8 * (n - 1 - i))) as u8));
        }
        Ok(out)
    }
}
