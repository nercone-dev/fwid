use std::time::{Duration, SystemTime, UNIX_EPOCH};

use fwid::{Base32Crockford, Base32Hex, Base62, Error, Format, FWID, ISO8601};

const VECTORS: &str = include_str!("../../../testdata/vectors.tsv");
const INVALID: &str = include_str!("../../../testdata/invalid.tsv");

fn rows(data: &str) -> impl Iterator<Item = &str> {
    data.lines().filter(|l| !l.is_empty() && !l.starts_with('#'))
}

fn unhex(hex: &str) -> Vec<u8> {
    (0..hex.len() / 2)
        .map(|i| u8::from_str_radix(&hex[i * 2..i * 2 + 2], 16).unwrap())
        .collect()
}

fn at(unix_ms: u64) -> SystemTime {
    UNIX_EPOCH + Duration::from_millis(unix_ms)
}

#[test]
fn shared_vectors() {
    let mut n = 0;
    for row in rows(VECTORS) {
        let f: Vec<&str> = row.split('\t').collect();
        let raw = unhex(f[0]);
        let id = FWID::from_bytes(raw.clone()).unwrap();
        assert_eq!(id.standard_text(), f[1]);
        assert_eq!(id.readable_text(), f[2]);
        assert_eq!(id.compact_text(), f[3]);
        if f[4] != "-" {
            assert_eq!(id.timestamp_ms().unwrap().to_string(), f[4]);
        }
        for (text, format) in [
            (f[1], Format::StandardText),
            (f[2], Format::ReadableText),
            (f[3], Format::CompactText),
        ] {
            let (detected, parsed) = FWID::parse(text).unwrap();
            assert_eq!(detected, format, "{text}");
            assert_eq!(parsed.as_bytes(), raw.as_slice(), "{text}");
        }
        n += 1;
    }
    assert!(n > 0);
}

#[test]
fn invalid_texts_are_rejected() {
    assert!(FWID::from_text("").is_err());
    for text in rows(INVALID) {
        assert!(FWID::from_text(text).is_err(), "{text:?}");
        assert_eq!(Format::detect(text), Err(Error::UnknownFormat), "{text:?}");
    }
}

// RFC 4648 section 10, with '=' replaced by 'Z'.
#[test]
fn base32_crockford_unpadded_with_aliases() {
    assert_eq!(Base32Crockford::encode(&[0xff; 4]), "ZZZZZZR");
    assert_eq!(Base32Crockford::decode("zzzzzzr").unwrap(), vec![0xff; 4]);
    assert_eq!(
        Base32Crockford::decode("OILOILO").unwrap(),
        Base32Crockford::decode("0110110").unwrap()
    );
    for text in ["U0000000", "000000", "ZZZZZZZ"] {
        assert!(Base32Crockford::decode(text).is_err(), "{text:?}");
    }
}

#[test]
fn base32hex_rfc4648_vectors() {
    for (plain, encoded) in [
        ("", ""),
        ("f", "COZZZZZZ"),
        ("fo", "CPNGZZZZ"),
        ("foo", "CPNMUZZZ"),
        ("foob", "CPNMUOGZ"),
        ("fooba", "CPNMUOJ1"),
        ("foobar", "CPNMUOJ1E8ZZZZZZ"),
    ] {
        assert_eq!(Base32Hex::encode(plain.as_bytes()), encoded);
        assert_eq!(Base32Hex::decode(encoded).unwrap(), plain.as_bytes());
    }
}

#[test]
fn base32hex_rejects_malformed_input() {
    for text in ["C", "COZZZZZ", "CZZZZZZZ", "COZZZZZZCOZZZZZZ", "COzzzzzz", "C1ZZZZZZ", "CPNMUOJ\u{e9}"] {
        assert!(Base32Hex::decode(text).is_err(), "{text:?}");
    }
}

#[test]
fn base62_lengths_and_roundtrip() {
    assert_eq!(Base62::length(0), 0);
    assert_eq!(Base62::length(1), 2);
    assert_eq!(Base62::length(4), 6);
    assert_eq!(Base62::length(16), 22);
    assert_eq!(Base62::length(32), 43);
    for size in 0..40usize {
        let data: Vec<u8> = (0..size).map(|i| (i * 37 + 11) as u8).collect();
        let text = Base62::encode(&data);
        assert_eq!(text.len(), Base62::length(size));
        assert_eq!(Base62::decode(&text).unwrap(), data);
    }
}

#[test]
fn base62_rejects_malformed_input() {
    assert!(Base62::decode("0").is_err()); // no byte length has one character
    assert!(Base62::decode("zzzzzz").is_err()); // 62^6-1 > 2^32-1
    assert!(Base62::decode("00000-").is_err());
    assert!(Base62::decode("00000\u{e9}").is_err());
}

#[test]
fn generate_layout() {
    let t = at(1_704_067_200_000); // 2024-01-01T00:00:00Z
    let ms = 725_760_000_000u64;
    assert_eq!(FWID::epoch_ms(Some(t)).unwrap(), ms);
    assert_eq!(FWID::min_bits(Some(t)).unwrap(), 160);
    for bits in (160..=512).step_by(32) {
        let id = FWID::generate(Some(bits), Some(t)).unwrap();
        assert_eq!(id.bits(), bits);
        assert_eq!(id.bits_timestamp(), bits / 4);
        assert_eq!(id.bits_random(), bits / 4 * 3);
        assert_eq!(id.timestamp_ms().unwrap(), ms);
        assert_eq!(id.timestamp().unwrap(), t);
        let field = &id.as_bytes()[..bits / 32];
        assert!(field.ends_with(&ms.to_be_bytes()[3..]));
        assert!(field[..field.len() - 5].iter().all(|&b| b == 0));
    }
}

#[test]
fn generate_rejects_bad_sizes() {
    let t = at(1_704_067_200_000);
    for bits in [0, 31, 33, 161] {
        assert_eq!(FWID::generate(Some(bits), Some(t)), Err(Error::Bits));
    }
    assert_eq!(
        FWID::generate(Some(128), Some(t)),
        Err(Error::TimestampTooLarge { bits: 128, required: 160 })
    );
    assert_eq!(FWID::generate(None, Some(at(978_307_199_999))), Err(Error::BeforeEpoch));
    assert!(FWID::generate(None, Some(at(978_307_200_000))).is_ok());
    assert!(FWID::from_bytes(vec![0; 3]).is_err());
    assert!(FWID::from_bytes(vec![]).is_err());
}

#[test]
fn ids_sort_by_time() {
    let a = FWID::generate(Some(256), Some(at(1_000_000_000_000))).unwrap();
    let b = FWID::generate(Some(256), Some(at(1_000_000_000_001))).unwrap();
    assert!(a < b);
    assert!(a.standard_text() < b.standard_text());
}

#[test]
fn random_part_differs() {
    let a = FWID::new().unwrap();
    let b = FWID::new().unwrap();
    assert_ne!(a, b);
}

#[test]
fn iso8601_parse_and_format() {
    for (text, unix_ms) in [
        ("2024-01-01T00:00:00Z", 1_704_067_200_000i64),
        ("2024-01-01", 1_704_067_200_000),
        ("2024-01-01 00:00", 1_704_067_200_000),
        ("2024-01-01T09:00:00+09:00", 1_704_067_200_000),
        ("2024-01-01T09:00:00+0900", 1_704_067_200_000),
        ("2023-12-31T19:00:00-05", 1_704_067_200_000),
        ("2024-02-29T12:34:56.789123Z", 1_709_210_096_789),
        ("2024-02-29T12:34:56.5", 1_709_210_096_500),
        ("1970-01-01T00:00:00Z", 0),
    ] {
        let t = ISO8601::parse(text).unwrap();
        assert_eq!(t, at(unix_ms as u64), "{text}");
    }
    assert_eq!(
        ISO8601::format(at(1_709_210_096_789)),
        "2024-02-29T12:34:56.789+00:00"
    );
    for text in [
        "", "2024", "2024-13-01", "2023-02-29", "2024-04-31", "2024-01-01T24:00", "2024-01-01T00:60",
        "2024-01-01T00:00:60", "2024-01-01T00", "2024-01-01T00:00:00.", "2024-01-01T00:00:00+24:00",
        "2024-01-01T00:00:00Zx", "2024-01-01Z", "24-01-01", "2024-01-01T00:00:00 +09:00",
    ] {
        assert_eq!(ISO8601::parse(text), Err(Error::InvalidDatetime), "{text:?}");
    }
}

#[test]
fn text_rejects_unformatted() {
    let id = FWID::new().unwrap();
    assert_eq!(id.text(Format::Unformatted), Err(Error::NotTextFormat));
    assert_eq!(id.text(Format::StandardText).unwrap(), id.to_string());
}
