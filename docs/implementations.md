# Implementations

FWID is implemented in five languages. All of them follow the same specification (see [SPEC.md](../SPEC.md)), accept the same text formats, and ship the same command line tool.

| Language | Directory | Library | Command |
|---|---|---|---|
| Python | `src/fwid` | `from fwid import FWID` | `fwid` |
| Rust | `ports/rust` | `fwid` crate | `cargo run --release --` |
| Go | `ports/go` | `github.com/nercone-dev/fwid/ports/go` | `go run ./cmd/fwid` |
| Swift | `ports/swift` | `FWID` library product | `swift run fwid` |
| JavaScript | `ports/js` | `import { FWID } from "fwid"` | `node bin/fwid.js` |

## Command line

```
fwid generate [-b BITS] [-f standard|readable|compact] [-n COUNT] [-t DATETIME]
fwid inspect  [FWID ...]        # reads standard input, one per line, if no FWID or "-" is given
```

`g` and `i` are short for `generate` and `inspect`. Exit status: 0 on success, 1 if any operation failed, 2 for a malformed command line.

`-t` takes an extended-format ISO 8601 datetime: `YYYY-MM-DD`, optionally followed by `T` (or `t`, or a space) and `hh:mm[:ss[.fraction]]`, then optionally `Z` or an offset (`+09:00`, `+0900`, `+09`). Values without an offset are UTC. Digits beyond milliseconds are truncated.

## Library

Every implementation offers the same operations; only the naming follows each language.

| Operation | Rust | Go | Swift | JavaScript |
|---|---|---|---|---|
| Generate (smallest size, now) | `FWID::new()` | `fwid.New()` | `FWID()` | `new FWID()` |
| Generate with size and time | `FWID::generate(Some(bits), Some(time))` | `fwid.Generate(bits, time)` | `FWID.generate(bits:date:)` | `new FWID(bits, date)` |
| Parse any text format | `FWID::from_text` / `FWID::parse` | `fwid.FromText` / `fwid.Parse` | `FWID(text:)` / `FWID.parse` | `new FWID(text)` / `FWID.parse` |
| From raw bytes | `FWID::from_bytes` | `fwid.FromBytes` | `FWID(bytes:)` | `new FWID(bytes)` |
| Texts | `standard_text()` `readable_text()` `compact_text()` | `StandardText()` `ReadableText()` `CompactText()` | `standardText` `readableText` `compactText` | `standardText` `readableText` `compactText` |
| Timestamp | `timestamp()` `timestamp_ms()` | `Timestamp()` `TimestampMS()` | `timestamp` `timestampMS` | `timestamp` `timestampMS` |

Raw bytes sort in time order for identifiers of equal bit length. Each library exposes a comparison for this.

## Limits

- Timestamps are read as unsigned 64-bit millisecond counts (JavaScript: 53 bits, the range of a safe integer). A timestamp field that holds a larger value, which can only happen for hand-made bytes, is reported as an error by the timestamp accessors. Parsing, formatting and sorting still work for such identifiers.
- Times are rounded down to the millisecond.
- Swift uses `Date`, a floating-point type. Times are rounded to the microsecond before being floored to the millisecond, so a `Date` built from whole milliseconds is exact.
- Random bytes come from the operating system CSPRNG (`getrandom` crate, `crypto/rand`, `SystemRandomNumberGenerator`, `crypto.getRandomValues`).

## Tests

Shared test vectors live in `testdata/`. `vectors.tsv` holds raw bytes with their expected Standard, Readable and Compact texts and timestamp; `invalid.tsv` holds texts every parser must reject. The vectors were produced with plain integer arithmetic and the Python standard library's `base64.b32hexencode` (Standard) and an independent Crockford alphabet table (Readable), not with any FWID implementation.

```
cd ports/rust  && cargo test
cd ports/go    && go test ./...
cd ports/swift && swift test
cd ports/js    && node --test test/
```
