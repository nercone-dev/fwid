use crate::error::Error;

/// Base62 (`0-9A-Za-z`) over a big-endian arbitrary-precision integer,
/// zero-padded to a length that depends only on the byte length.
pub struct Base62;

impl Base62 {
    pub const ALPHABET: &'static [u8; 62] =
        b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";

    fn index(c: u8) -> Option<u32> {
        match c {
            b'0'..=b'9' => Some(u32::from(c - b'0')),
            b'A'..=b'Z' => Some(u32::from(c - b'A' + 10)),
            b'a'..=b'z' => Some(u32::from(c - b'a' + 36)),
            _ => None,
        }
    }

    /// Divides the big-endian number in place and returns the remainder.
    fn divmod(num: &mut [u8], divisor: u32) -> u32 {
        let mut rem = 0u32;
        for b in num {
            let cur = rem << 8 | u32::from(*b);
            *b = (cur / divisor) as u8;
            rem = cur % divisor;
        }
        rem
    }

    fn skip_zeros(num: &[u8], mut start: usize) -> usize {
        while start < num.len() && num[start] == 0 {
            start += 1;
        }
        start
    }

    /// Smallest `n` such that `62^n >= 256^size`, i.e. the number of base-62
    /// digits of the largest `size`-byte value.
    pub fn length(size: usize) -> usize {
        let mut num = vec![0xFFu8; size];
        let mut start = 0;
        let mut chars = 0;
        while start < num.len() {
            Self::divmod(&mut num[start..], 62);
            chars += 1;
            start = Self::skip_zeros(&num, start);
        }
        chars
    }

    pub fn encode(data: &[u8]) -> String {
        let width = Self::length(data.len());
        let mut num = data.to_vec();
        let mut start = Self::skip_zeros(&num, 0);
        let mut out = vec![Self::ALPHABET[0]; width];
        for slot in out.iter_mut().rev() {
            if start >= num.len() {
                break;
            }
            *slot = Self::ALPHABET[Self::divmod(&mut num[start..], 62) as usize];
            start = Self::skip_zeros(&num, start);
        }
        out.into_iter().map(char::from).collect()
    }

    pub fn decode(text: &str) -> Result<Vec<u8>, Error> {
        let text = text.as_bytes();
        // log2(62) is irrational, so the estimate only seeds the search and
        // the exact length is always verified.
        let estimate = (text.len() as f64 * 5.954_196_310_386_876 / 8.0) as usize;
        let size = (estimate.saturating_sub(1)..=estimate + 1)
            .find(|&s| Self::length(s) == text.len())
            .ok_or(Error::Base62Length)?;
        let mut out = vec![0u8; size];
        for &c in text {
            let mut carry = Self::index(c).ok_or_else(|| {
                Error::Character(
                    String::from_utf8_lossy(text)
                        .chars()
                        .find(|&ch| !ch.is_ascii_alphanumeric())
                        .unwrap_or('\u{FFFD}'),
                )
            })?;
            for b in out.iter_mut().rev() {
                let cur = u32::from(*b) * 62 + carry;
                *b = cur as u8;
                carry = cur >> 8;
            }
            if carry != 0 {
                return Err(Error::Base62Range);
            }
        }
        Ok(out)
    }
}
