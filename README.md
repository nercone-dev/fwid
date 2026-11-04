[[Japanese/日本語](README.ja.md)]

# FWID (FourWord Identifier)
A novel random identifier generation method with time-series sortability.

## Overview
This is a novel method for generating random identifiers.
It is designed for use cases such as database primary keys.

The length is variable and can be changed as needed.
As of 2026-11-04, the recommended length is 192 bits.

To minimize the possibility of collisions while preventing overflows, the timestamp is not fixed, but instead occupies a quarter of the total bit length.
This means that simply increasing the total bit length increases the length of the timestamp, enabling continuous use over a longer period.

However, as a trade-off, increasing the bit length results in unnecessary leading zeros in the timestamp portion.

## Etymology
The name "Four" comes from the fact that the timestamp occupies 1/4 of the bit length.
It is also a wordplay on the word "Forward".

## Specification
FWID is represented as a byte array (big-endian) as follows:

```
[ (Total bits / 4) bits of timestamp ] + [ (Total bits / 4 * 3) bits of CSPRNG output ]
```

The timestamp is the time elapsed in milliseconds since 2001-01-01 00:00:00 UTC.

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

Compared to the standard text format, the length at 256 bits is approximately 76% (56 characters in the standard text format, 43 characters in the compact format).

Note that since Base62 is not a power of 2, bitwise operations cannot be used, and decoding requires multi-precision integer arithmetic.
Also, it cannot be used in case-insensitive environments.

## Usage Notes

- There is no ordering guarantee within the same timestamp. That is, if multiple IDs are generated within the same millisecond, their order is random. If ordering within the same millisecond is required, the leading part of the random portion would need to be replaced with a sequence number, but the specification for that is not included in the FWID specification itself.
- The epoch is fixed at 2001-01-01 00:00:00 UTC, and unlike TSID or Snowflake-style schemes, the lifetime cannot be extended by changing the epoch. Instead, the bit width must be increased.

## Collision Probability
IDs with different timestamps will never collide. The following figures represent the worst-case scenario (where all IDs are generated within the same millisecond). Values are approximated with the birthday bound, n ≈ √(2·2^r·p) (50%: n ≈ 1.1774·√2^r), where r is the random part bit width.

| Bits | Random Part Bit Width | Number of IDs for Collision Probability 10⁻¹⁸ | Number of IDs for Collision Probability 10⁻⁹ | Number of IDs for Collision Probability 50% |
|-----:|----------------------:|:----------------------------------------------|:---------------------------------------------|:--------------------------------------------|
|  128 |                    96 | 4.0×10⁵                                       | 1.3×10¹⁰                                     | 3.3×10¹⁴                                    |
|  160 |                   120 | 1.6×10⁹                                       | 5.2×10¹³                                     | 1.4×10¹⁸                                    |
|  192 |                   144 | 6.7×10¹²                                      | 2.1×10¹⁷                                     | 5.6×10²¹                                    |
|  256 |                   192 | 1.1×10²⁰                                      | 3.5×10²⁴                                     | 9.3×10²⁸                                    |
|  384 |                   288 | 3.2×10³⁴                                      | 1.0×10³⁹                                     | 2.6×10⁴³                                    |
|  512 |                   384 | 8.9×10⁴⁸                                      | 2.8×10⁵³                                     | 7.4×10⁵⁷                                    |

## Overflow Timing
Each bit length overflows at the following times:

| Bits | Timestamp Bit Width | Maximum Seconds                | Overflow Timing (Approximate)                        |
|-----:|--------------------:|:-------------------------------|:-----------------------------------------------------|
|  128 |                  32 | 4,294,967         (≈49.7 days) | `2001-02-19T17:02:47.296+00:00` (already overflowed) |
|  160 |                  40 | 1,099,511,627    (≈34.8 years) | `2035-11-04T19:53:47.776+00:00`                      |
|  192 |                  48 | 281,474,976,710 (≈8,920 years) | `10920-08-03T05:31:50.656+00:00`                     |
|  256 |                  64 | 1.8×10¹⁶                       | ≈5.8×10⁸ years from the epoch                        |
|  384 |                  96 | 7.9×10²⁵                       | ≈2.5×10¹⁸ years from the epoch                       |
|  512 |                 128 | 3.4×10³⁶                       | ≈1.1×10²⁸ years from the epoch                       |

## Implementations
Python (this package, in `src/fwid`), Rust, Go, Swift and JavaScript implementations are included, each with the same command line tool. See [docs/implementations.md](docs/implementations.md).

## License
The source code and libraries in this repository are freely available under the MIT License.

No attribution is required for software that utilizes the FWID specification itself or for data generated using FWID.
