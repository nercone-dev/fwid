# Ports

The reference implementation is the Python package in `src/fwid`. Rust, Go, Swift and JavaScript ports live in `ports/rust`, `ports/go`, `ports/swift` and `ports/js`. User-facing notes are in `docs/implementations.md`; this file records why the ports look the way they do.

## Structure

Each port has the same parts, mirroring Python's `helpers/base32hex.py`, `helpers/base32crockford.py`, `helpers/base62.py`, `lib.py` and `cli.py`:

- `Base32Hex`, `Base32Crockford`, `Base62`: independent, reusable codecs with no FWID-specific behaviour. Base32Hex and Base32Crockford are usable for any data, Base62 for any byte string whose length is fixed.
- `ISO8601`: parse and format of datetimes. Needed by the CLI's `-t` and by `inspect`, but implemented as a general component.
- `FWID` and a format type: the identifier.
- `CLI`: argument parsing and output, written against injected input and output streams so tests can drive it without a process.

Go uses one package per component (`base32hex`, `base32crockford`, `base62`, `iso8601`, `cli`) because package-level functions are its idiom for what Python and Java call static methods.

## Decisions

**No bignum in Base62.** The reference uses Python integers. Ports divide the big-endian byte array by 62 repeatedly (encode) and multiply-accumulate with carry (decode). This is quadratic but identifiers are tens of bytes. It avoids a dependency (Rust has no bigint in `std`) and keeps all ports identical.

**Exact Base62 length.** The text length for N bytes is the number of base-62 digits of `256^N - 1`. Ports compute it by dividing an array of `0xFF` bytes, which is exact. Decoding must invert it: a floating-point estimate of `N` (from `log2(62)`) picks three candidates, and each is verified with the exact computation. The estimate alone was rejected because it could be off by one near integer boundaries. The length is strictly increasing in N (each byte adds at least one digit), so the inverse is unique.

**Detection order.** `detect` and `from_text` try Standard, Readable, then Compact, as in Python, and the first parser that accepts wins. Ports parse once and return both the format and the value instead of parsing twice.

**Errors without allocation (Rust).** `detect` tries up to three parsers, and failures are the common case for two of them. Rust's `Error` is a `Copy` enum so failed attempts allocate nothing.

**Immutable values.** Go stores the bytes in a `string` so `FWID` is comparable and usable as a map key. JavaScript keeps bytes in a private field and returns copies.

**Time types.** Each port uses its platform's native time (`SystemTime`, `time.Time`, `Date`, `Date`). The library never accepts a naive time; the CLI treats an ISO 8601 datetime without an offset as UTC, matching Python.

**Timestamp width.** Python's integers are unbounded, so a 512-bit identifier has a 128-bit timestamp field. Ports read it as `u64` (53 bits in JavaScript) and report an error otherwise. A 64-bit millisecond count lasts about 584 million years, and `Date` / `SystemTime` cannot hold more anyway. Generation checks the same limit.

**CLI parsing.** Hand-written, to avoid dependencies and to give every port identical behaviour. It accepts `-b 256`, `-b256`, `--bits 256` and `--bits=256`. Unlike Python's argparse it does not accept abbreviated long options (`--bit`), because the abbreviation set would change whenever an option is added.

**`ISO8601` grammar.** Python 3.8's `fromisoformat` accepts only `isoformat()` output, while 3.11+ accepts much more. The ports accept a fixed documented subset (see `docs/implementations.md`) so results do not depend on a runtime version. Basic format (`20240101T000000Z`) and week dates are not supported.

**Python output differences.** `inspect` prints years with at least four digits; Python's `datetime` cannot represent years beyond 9999, the ports can (JavaScript and Swift within `Date` range).

**Readable Text uses Crockford Base32.** It was Base32 Hex lowercased. Crockford's alphabet avoids look-alike characters (`0/o`, `1/i/l`), which is what a text meant for humans needs. Crockford defines no padding, and `z` is a digit in it, so the old `z` padding cannot be kept; the last group is simply shorter, and the length still determines the byte count uniquely (2, 4, 5, 7 or 8 characters per final block). Uppercase stays rejected so Readable Text cannot be mistaken for Standard Text during detection. Check symbols were rejected: they add a mod-37 character that FWID's fixed lengths and `detect` do not need. Hyphens stay at every 8 characters, not Crockford's customary 4, to keep the existing grouping rule and to keep the 8-character block boundary visible.

## Things that are easy to get wrong

- Base32Hex padding is `Z`, not `=`. Readable Text has no padding at all (`z` is a real digit, 31, in Crockford's alphabet), so its last group may be shorter than 8.
- The Readable parser must reject any uppercase letter and any group other than the last that is not 8 characters, including a trailing hyphen. Its last group must have 1 to 8 characters.
- Crockford's alphabet skips `i`, `l`, `o`, `u`; the decoder maps `i`/`l` to `1` and `o` to `0` but rejects `u`.
- `inspect` prints a blank line between entries by input index, so a failed entry still counts toward separating the next one.
- `0` is not a valid Base62 length for any non-empty input; one-character Base62 text must be rejected.
