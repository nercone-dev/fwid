[[Japanese/日本語](README.ja.md)]

# FWID (FourWord Identifier)
A novel random identifier generation method with time-series sortability.

## Overview
This is a novel method for generating random identifiers.
It is designed for use cases such as database primary keys.

To minimize the possibility of collisions while preventing overflows, the timestamp is not fixed, but instead occupies a quarter of the total bit length.
This means that simply increasing the total bit length increases the length of the timestamp, enabling continuous use over a longer period.

However, as a trade-off, increasing the bit length results in unnecessary leading zeros in the timestamp portion.

## Etymology
The name "Four" comes from the fact that the timestamp occupies 1/4 of the bit length.
It is also a wordplay on the word "Forward".

## Specification
FWID is represented as a byte array (big-endian) as follows:

```
[ (Total bits / 4) bits of timestamp (UTC, ms elapsed since the epoch 2001-01-01 00:00:00 UTC) ] + [ (Total bits / 4 * 3) bits of CSPRNG (Cryptographically Secure Pseudo-Random Number Generator) ]
```

For example, if the total bit length is 256 bits, the timestamp will be 64 bits and the random part will be 192 bits.

The ratio is fixed so that when extracting the timestamp from the ID, the exact length can be easily determined without the need for delimiters.

## Formats
Unlike other methods, FWID provides multiple formats.

### Standard Text

It uses a Base32 Hex variant for text conversion.

However, "Z" is used instead of "=" as the padding character. This allows it to be used in most places.

### Readable Text

Based on the Standard Text format, with the following modifications for human readability:

- Lowercase the character set (`0-9, A-V` → `0-9, a-v`)
- Insert hyphens (`-`) every 8 characters

### Compact Text

It uses Base62 (`0-9A-Za-z`) as the character set.
The byte array is interpreted as a big-endian multi-precision integer (arbitrary-precision integer) and converted to Base62.
It is zero-padded with leading `0`s so that it always produces a fixed-length output for the same bit length.

The length is approximately 76% of the text format.
For example, for 256 bits, the text format is 56 characters, whereas the compact text fits into 43 characters.

Note that since Base62 is not a power of 2, bitwise operations cannot be used, and decoding requires multi-precision integer arithmetic.
Also, it cannot be used in case-insensitive environments.

## Collision Probability
IDs with different timestamps will never collide. The following figures represent the worst-case scenario (where all IDs are generated within the same millisecond). Values are approximated with the birthday bound, n ≈ √(2·2^r·p) (50%: n ≈ 1.1774·√2^r), where r is the random part bit width.

| Bits | Random Part Bit Width | Number of IDs for Collision Probability 10⁻¹⁸ | Number of IDs for Collision Probability 10⁻⁹ | Number of IDs for Collision Probability 50% |
|---:|---:|:---|:---|:---|
| 128 | 96 | 4.0×10⁵ | 1.3×10¹⁰ | 3.3×10¹⁴ |
| 160 | 120 | 1.6×10⁹ | 5.2×10¹³ | 1.4×10¹⁸ |
| 192 | 144 | 6.7×10¹² | 2.1×10¹⁷ | 5.6×10²¹ |
| 256 | 192 | 1.1×10²⁰ | 3.5×10²⁴ | 9.3×10²⁸ |
| 384 | 288 | 3.2×10³⁴ | 1.0×10³⁹ | 2.6×10⁴³ |
| 512 | 384 | 8.9×10⁴⁸ | 2.8×10⁵³ | 7.4×10⁵⁷ |

## Overflow Timing
Each bit length overflows at the following times:

| Bits | Timestamp Bit Width | Maximum Seconds | Overflow Timing (Approximate) |
|---:|---:|:---|:---|
| 128 | 32 | 4,294,967 (≈49.7 days) | 2001-02-19 (already overflowed) |
| 160 | 40 | 1,099,511,627 (≈34.8 years) | 2035-11 |
| 192 | 48 | 281,474,976,710 (≈8,920 years) | Year ≈10920 |
| 256 | 64 | 1.8×10¹⁶ | ≈5.8×10⁸ years from the epoch |
| 384 | 96 | 7.9×10²⁵ | ≈2.5×10¹⁸ years from the epoch |
| 512 | 128 | 3.4×10³⁶ | ≈1.1×10²⁸ years from the epoch |

## License
The source code and libraries in this repository are freely available under the MIT License.

No attribution is required for software that utilizes the FWID specification itself or for data generated using FWID.
