[[Japanese/日本語](SPEC.ja.md)]

# FWID Specification

This document defines the FWID (FourWord Identifier) binary layout, its text formats, and the rules for generating and parsing them. The key words "MUST", "MUST NOT", "SHOULD" and "MAY" are to be interpreted as described in RFC 2119 and RFC 8174.

## 1. Bit Length

The total bit length `B` of an FWID MUST be a positive multiple of 32: 32, 64, 96, 128, 160, 192, … Any such value is allowed; this specification sets no upper bound.

- The timestamp part is `B / 4` bits and the random part is `B / 4 × 3` bits.
- `B` is a multiple of 32 so that the timestamp part (`B / 4`) is a whole number of bytes, and therefore the whole identifier is a whole number of bytes (`B / 8`).
- An implementation MUST reject any bit length that is not a positive multiple of 32, both when generating and when parsing (for example, raw bytes whose length is not a multiple of 4, or text that decodes to such bytes).

As of 2026-11-04, the recommended bit length is 192.

## 2. Binary Layout

An FWID is a byte array of `B / 8` bytes:

```
+-----------------------------+------------------------------------+
| timestamp (B / 4 bits)      | random (B / 4 × 3 bits)            |
+-----------------------------+------------------------------------+
```

- **Timestamp**: an unsigned integer in big-endian byte order. Its value is the number of milliseconds elapsed since the FWID epoch, `2001-01-01T00:00:00.000Z` (UTC). Times are rounded down (floored) to the millisecond.
- **Random**: `B / 4 × 3` bits of output from a cryptographically secure pseudo-random number generator (CSPRNG).

Because the timestamp is at the front and big-endian, the raw bytes of identifiers with the **same** bit length sort in time order when compared byte by byte. Identifiers of different bit lengths cannot be ordered this way; decode them and compare the timestamps instead.

The ratio between the two parts is fixed so that the timestamp can be extracted from the bit length alone, without a delimiter.

## 3. Generation

To generate an FWID for time `t` and bit length `B`:

1. Compute `ms`, the milliseconds from the epoch to `t`, rounded down.
2. If `t` is before the epoch (`ms < 0`), the implementation MUST reject the request.
3. If `ms ≥ 2^(B / 4)`, the timestamp overflows the timestamp part, and the implementation MUST reject the request (see [Section 4](#4-timestamp-overflow)).
4. Write `ms` as a big-endian unsigned integer of `B / 32` bytes, followed by `B / 32 × 3` bytes from a CSPRNG.

When the caller does not specify `B`, an implementation SHOULD choose the smallest multiple of 32 whose timestamp part can hold `ms` (but never less than 32).

A time without time zone information (a "naive" time) is ambiguous. A library MUST NOT accept one; an application such as a command line tool MAY interpret it as UTC if it documents this.

## 4. Timestamp Overflow

A timestamp part of `B / 4` bits can hold values from `0` to `2^(B / 4) − 1` milliseconds. When a time does not fit, the implementation MUST reject the operation with an error. It MUST NOT wrap around, truncate the high bits, saturate to the maximum value, or silently switch to another bit length that the caller did not ask for.

This applies to:

- **Encoding (generation)**: a time with `ms ≥ 2^(B / 4)` for the requested `B` MUST be rejected.
- **Decoding**: the timestamp part of a parsed identifier always fits in `B / 4` bits by construction. However, if an implementation converts it to a native integer or time type that cannot represent the value (for example a 64-bit integer, or a date type with a limited year range), the conversion MUST fail with an error instead of returning a wrong value. Parsing the identifier itself, formatting it as text, and comparing it MUST still work in that case, because they do not need the timestamp as a number.

Approximate overflow times for common bit lengths:

| Bits | Timestamp Bits | Maximum Seconds                | Overflow (Approximate)                               |
|-----:|---------------:|:-------------------------------|:-----------------------------------------------------|
|  128 |             32 | 4,294,967         (≈49.7 days) | `2001-02-19T17:02:47.296+00:00` (already overflowed) |
|  160 |             40 | 1,099,511,627    (≈34.8 years) | `2035-11-04T19:53:47.776+00:00`                      |
|  192 |             48 | 281,474,976,710 (≈8,920 years) | `10920-08-03T05:31:50.656+00:00`                     |
|  256 |             64 | 1.8×10¹⁶                       | ≈5.8×10⁸ years from the epoch                        |
|  384 |             96 | 7.9×10²⁵                       | ≈2.5×10¹⁸ years from the epoch                       |
|  512 |            128 | 3.4×10³⁶                       | ≈1.1×10²⁸ years from the epoch                       |

The epoch is fixed. Unlike TSID or Snowflake-style schemes, the lifetime cannot be extended by moving the epoch; use a larger bit length instead.

## 5. Text Formats

An FWID has three text formats. All of them encode the byte array from [Section 2](#2-binary-layout); none of them contains any extra data.

For every format, the parser MUST reject text that decodes to a bit length not allowed by [Section 1](#1-bit-length), and MUST reject any character outside the format's alphabet. An encoder MUST always produce the canonical form defined below.

### 5.1 Standard Text

Base32 with the "Extended Hex" alphabet of RFC 4648 Section 7, except that the padding character is `Z` instead of `=`, so the text can be used in URLs, file names and most identifiers.

- Alphabet: `0123456789ABCDEFGHIJKLMNOPQRSTUV` (uppercase only). `Z` is the padding character and is not a digit.
- Encoding: as RFC 4648. The bytes are split into 5-byte blocks; each block becomes 8 characters, and the last block is padded with `Z` to 8 characters.
- Length: always a multiple of 8, `8 × ceil(B / 40)` characters.

Parsing rules:

- The length MUST be a multiple of 8.
- Padding MUST appear only at the end of the last 8-character block. The number of padding characters in that block MUST be 0, 1, 3, 4 or 6 (that is, 8, 7, 5, 4 or 2 data characters, giving 5, 4, 3, 2 or 1 bytes).
- Lowercase letters MUST be rejected.
- The unused low-order bits of the last data character MUST be zero (see [Section 5.4](#54-trailing-bits)).

### 5.2 Readable Text

Crockford's Base32, lowercase, without padding, split into hyphen-separated groups for human readability.

- Alphabet: `0123456789abcdefghjkmnpqrstvwxyz` (the digits and lowercase letters except `i`, `l`, `o`, `u`), which avoids look-alike characters.
- Encoding: the bytes are split into 5-byte blocks; each full block becomes 8 characters. The last, partial block becomes only as many characters as are needed to hold its bits, with the unused bits set to zero. There is no padding.
- Grouping: a hyphen (`-`) is inserted after every 8 characters. There is no hyphen at the start or the end. The last group has 1 to 8 characters.
- Crockford's check symbol is not used.

#### Length

Let `L` be the number of characters excluding hyphens, and `N = B / 8` the number of bytes.

- Encoding: `L = ceil(8 × N / 5)`. The text has `ceil(L / 8) − 1` hyphens.
- Decoding: because there is no padding, the bit length is computed from `L`:
  1. `N = floor(5 × L / 8)`.
  2. If `ceil(8 × N / 5) ≠ L`, the text MUST be rejected. Equivalently, `L mod 8` MUST be 0, 2, 4, 5 or 7, which give `5 × floor(L / 8)` plus 0, 1, 2, 3 or 4 bytes respectively. A remainder of 1, 3 or 6 cannot be produced by any byte count.
  3. `B = 8 × N` MUST satisfy [Section 1](#1-bit-length).

| `L mod 8` | Bytes in last block | Unused bits in last character |
|----------:|--------------------:|------------------------------:|
|         0 |    0 (or 5 if full) |                             0 |
|         2 |                   1 |                             2 |
|         4 |                   2 |                             4 |
|         5 |                   3 |                             1 |
|         7 |                   4 |                             3 |
|  1, 3, 6  |   invalid (reject)  |                             — |

#### Parsing rules

- Every group except the last MUST be exactly 8 characters. The last group MUST have 1 to 8 characters. This rejects empty groups, leading or trailing hyphens, and consecutive hyphens.
- Uppercase letters MUST be rejected, so that Readable Text is never confused with Standard Text.
- `i` and `l` MUST be read as `1`, and `o` MUST be read as `0`, as Crockford's Base32 specifies. `u` MUST be rejected.
- The unused low-order bits of the last character MUST be zero (see [Section 5.4](#54-trailing-bits)).

Because of the aliases, more than one text can decode to the same identifier. The canonical form is the encoder's output, which never contains `i`, `l` or `o`.

### 5.3 Compact Text

Base62, for the shortest text.

- Alphabet: `0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz` (value 0 to 61 in this order).
- Encoding: the byte array is read as one big-endian unsigned integer and written in base 62, most significant digit first, zero-padded on the left with `0` to a fixed length.
- Length: the number of base-62 digits of `256^N − 1`, that is the smallest `L` with `62^L ≥ 256^N`. The length is strictly increasing in `N`, so each length belongs to at most one byte count.

Parsing rules:

- The length MUST be the Compact length of some byte count `N`; otherwise the text MUST be rejected. `N` is then determined by the length.
- The decoded value MUST be less than `256^N`. A value that does not fit in `N` bytes (for example `zzzzzz`, which is larger than `2^32 − 1`) MUST be rejected rather than truncated.
- The text is case-sensitive; it cannot be used where case is not preserved.

Since 62 is not a power of 2, Compact Text cannot be decoded with bit operations; it needs multi-precision arithmetic (or repeated division and multiplication over the byte array). At 256 bits it is 43 characters, about 76% of Standard Text's 56.

### 5.4 Trailing Bits

In Standard Text and Readable Text, the last data character can carry more bits than the remaining data. These unused low-order bits MUST be zero when encoding, and a parser MUST reject text in which they are not zero. Otherwise several texts would decode to the same identifier, and a text could not be compared or used as a key by its characters alone.

Example (32 bits, Readable Text, `L = 7`): 7 characters carry 35 bits for 32 bits of data, so the lowest 3 bits of the 7th character must be zero. `zzzzzzr` (`r` = 24 = `11000₂`) is valid; `zzzzzzs` (25) is not.

### 5.5 Format Detection

A parser that accepts any text format MUST try Standard Text, then Readable Text, then Compact Text, and use the first format that accepts the whole text. Readable Text is lowercase and Standard Text is uppercase, so those two never overlap. The order makes the result well-defined if a Compact Text happens to also be valid Standard or Readable Text.

## 6. Collision Probability

Identifiers with different timestamps never collide. The figures below are the worst case, where all identifiers are generated in the same millisecond, using the birthday bound `n ≈ √(2 · 2^r · p)` (50%: `n ≈ 1.1774 · √(2^r)`), where `r` is the random part's bit width.

| Bits | Random Bits | IDs for p = 10⁻¹⁸ | IDs for p = 10⁻⁹ | IDs for p = 50% |
|-----:|------------:|:------------------|:-----------------|:----------------|
|  128 |          96 | 4.0×10⁵           | 1.3×10¹⁰         | 3.3×10¹⁴        |
|  160 |         120 | 1.6×10⁹           | 5.2×10¹³         | 1.4×10¹⁸        |
|  192 |         144 | 6.7×10¹²          | 2.1×10¹⁷         | 5.6×10²¹        |
|  256 |         192 | 1.1×10²⁰          | 3.5×10²⁴         | 9.3×10²⁸        |
|  384 |         288 | 3.2×10³⁴          | 1.0×10³⁹         | 2.6×10⁴³        |
|  512 |         384 | 8.9×10⁴⁸          | 2.8×10⁵³         | 7.4×10⁵⁷        |

## 7. Ordering

- There is no ordering guarantee within the same millisecond: identifiers generated in the same millisecond are ordered randomly.
- An application that needs ordering within a millisecond may replace the leading part of the random part with a sequence number, but that scheme is outside this specification.

## 8. Test Vectors

`testdata/vectors.tsv` lists raw bytes with their expected Standard, Readable and Compact texts and timestamp. `testdata/invalid.tsv` lists texts that every parser must reject.
