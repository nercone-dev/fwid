# Implementations

FWID is implemented in six languages and language implementations. All of them follow the same specification (see [SPEC.md](../SPEC.md)), accept the same text formats, and ship the same command line tool.

| Language / Implementation | Directory | Library | Command |
|---|---|---|---|
| Python | `src/fwid` | `from fwid import FWID` | `fwid` |
| Rust | `ports/rust` | `fwid` crate | `cargo run --release --` |
| Go | `ports/go` | `github.com/nercone-dev/fwid/ports/go` | `go run ./cmd/fwid` |
| Swift | `ports/swift` | `FWID` library product | `swift run fwid` |
| JavaScript | `ports/js` | `import { FWID } from "fwid"` | `node bin/fwid.js` |
| Lython Compiler | `ports/lython` | `from fwid.lib import FWID` | `lyc jit src/fwid_main.py` |

## Command line

```
fwid generate [-b BITS] [-f standard|readable|compact] [-n COUNT] [-t DATETIME]
fwid inspect  [FWID ...]        # reads standard input, one per line, if no FWID or "-" is given
```

`g` and `i` are short for `generate` and `inspect`. Exit status: 0 on success, 1 if any operation failed, 2 for a malformed command line.

`-t` takes an extended-format ISO 8601 datetime: `YYYY-MM-DD`, optionally followed by `T` (or `t`, or a space) and `hh:mm[:ss[.fraction]]`, then optionally `Z` or an offset (`+09:00`, `+0900`, `+09`). Values without an offset are UTC. Digits beyond milliseconds are truncated.

## Library

Every implementation offers the same operations; only the naming follows each language.

| Operation | Rust | Go | Swift | JavaScript | Lython |
|---|---|---|---|---|---|
| Generate (smallest size, now) | `FWID::new()` | `fwid.New()` | `FWID()` | `new FWID()` | `FWID.generate()` |
| Generate with size and time | `FWID::generate(Some(bits), Some(time))` | `fwid.Generate(bits, time)` | `FWID.generate(bits:date:)` | `new FWID(bits, date)` | `FWID.generate(bits, unix_ms)` |
| Parse any text format | `FWID::from_text` / `FWID::parse` | `fwid.FromText` / `fwid.Parse` | `FWID(text:)` / `FWID.parse` | `new FWID(text)` / `FWID.parse` | `FWID.from_text` / `FWID.parse` |
| From raw bytes | `FWID::from_bytes` | `fwid.FromBytes` | `FWID(bytes:)` | `new FWID(bytes)` | `FWID(raw)` |
| Texts | `standard_text()` `readable_text()` `compact_text()` | `StandardText()` `ReadableText()` `CompactText()` | `standardText` `readableText` `compactText` | `standardText` `readableText` `compactText` | `standard_text` `readable_text` `compact_text` |
| Timestamp | `timestamp()` `timestamp_ms()` | `Timestamp()` `TimestampMS()` | `timestamp` `timestampMS` | `timestamp` `timestampMS` | `timestamp` `timestamp_ms` |

Raw bytes sort in time order for identifiers of equal bit length. Each library exposes a comparison for this.

## Lython

`ports/lython` runs on [Lython](https://github.com/t3tra-dev/lython) and on NLython (the `merged` branch of [nercone-forks/lython](https://github.com/nercone-forks/lython)). The same source works on both. It also runs unchanged on CPython (checked with 3.14), which is how its tests are cross-checked: `PYTHONPATH=src python -m unittest discover -s src`.

```
cd ports/lython
lyc jit src/fwid_main.py generate -n 3          # Lython and NLython
lyc jit . generate -n 3                         # NLython only: runs the [project.scripts] entry
lyc jit -m fwid . inspect VVVVVVOZ              # NLython only
lyc jit src/test_fwid.py                        # tests; run from ports/lython
```

- A point in time is an `int`: milliseconds since 1970-01-01T00:00:00Z (Lython has no `datetime`). `FWID.generate(bits=None, unix_ms=None)` uses the smallest fitting size and the current time for `None`. `timestamp` returns Unix milliseconds, `timestamp_ms` milliseconds since the FWID epoch. `ISO8601.parse` and `ISO8601.format` convert from and to text.
- A format is an `int` constant of `FWIDFormat` (Lython has no `enum`). `FWIDFormat.name(fmt)` gives its name.
- Errors are `ValueError`, as in Python.
- Random bytes are read from `/dev/urandom`, since Lython has no `secrets` or `os.urandom`. Platforms without that device are not supported.
- Integers are unbounded, so the 64-bit timestamp limit of the other ports does not exist here. `inspect` prints any year with at least four digits.
- `inspect` and `generate` collect their output and print it at the end, so a failure message can appear before output of earlier entries when both go to one terminal.

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
cd ports/lython && lyc jit src/test_fwid.py
```
