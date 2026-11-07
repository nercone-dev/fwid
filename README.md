[[Japanese/日本語](README.ja.md)]

# FWID (FourWord Identifier)
A novel random identifier generation method with time-series sortability.

## Overview
FWID is a random identifier designed for use cases such as database primary keys.

The length is variable: any multiple of 32 bits. As of 2026-11-04, the recommended length is 192 bits.

```
[ timestamp: total bits / 4 ] + [ CSPRNG output: total bits / 4 × 3 ]
```

The timestamp is the number of milliseconds since 2001-01-01 00:00:00 UTC. Because it occupies a quarter of the total length instead of a fixed width, a longer identifier also lasts longer before its timestamp overflows. The trade-off is more leading zeros in the timestamp.

## Formats

| Format | Encoding | Example (192 bits) |
|---|---|---|
| Standard Text | Base32 Hex, `Z` as padding | `00NNTHJS00TETRA0QEQOA000000000001LISHPGZ` |
| Readable Text | Crockford's Base32, lowercase, no padding, hyphen every 8 characters | `00qqxhkw-00xexva0-tetra000-00000000-1njwhsg` |
| Compact Text | Base62, fixed length | `007h3WQ0lRIoEEs6MANGd9PJQhKTtetra` |

See [SPEC.md](SPEC.md) for the full specification: bit lengths, layout, overflow rules, text formats and their parsing rules, collision probability and overflow times.

## Etymology
The name "Four" comes from the fact that the timestamp occupies 1/4 of the bit length.
It is also a wordplay on the word "Forward".

## Implementations
Implementations for Python (this package, in `src/fwid`), Rust, Go, Swift, JavaScript and Lython Compiler are included, each with the same command line tool. See [docs/implementations.md](docs/implementations.md).

## License
The source code and libraries in this repository are freely available under the MIT License.

No attribution is required for software that utilizes the FWID specification itself or for data generated using FWID.
