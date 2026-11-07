import unittest

from fwid.cli import CLI
from fwid.helpers import Base32Crockford, Base32Hex, Base62, ISO8601
from fwid.lib import FWID, FWIDFormat

# Run from ports/lython.
TESTDATA = "../../testdata/"
UNIX_2024 = 1704067200000
MS_2024 = 725760000000


def rows(name: str) -> list[list[str]]:
    out: list[list[str]] = []
    with open(TESTDATA + name, "r") as f:
        for line in f.read().split("\n"):
            if line != "" and not line.startswith("#"):
                out.append(line.split("\t"))
    return out


def rejects(parse_text: str) -> bool:
    try:
        FWID.from_text(parse_text)
    except ValueError:
        return True
    return False


def runs(argv: list[str], stdin: str) -> tuple[int, str, str]:
    out: list[str] = []
    err: list[str] = []
    status = CLI.run(argv, stdin, out, err)
    return (status, "\n".join(out), "\n".join(err))


class SharedVectors(unittest.TestCase):
    def test_vectors(self) -> None:
        vectors = rows("vectors.tsv")
        self.assertTrue(len(vectors) > 0)
        for f in vectors:
            raw = bytes.fromhex(f[0])
            fwid = FWID(raw)
            self.assertEqual(fwid.standard_text, f[1], f[0])
            self.assertEqual(fwid.readable_text, f[2], f[0])
            self.assertEqual(fwid.compact_text, f[3], f[0])
            if f[4] != "-":
                self.assertEqual(fwid.timestamp_ms, int(f[4]), f[0])
            formats = (FWIDFormat.STANDARD_TEXT, FWIDFormat.READABLE_TEXT, FWIDFormat.COMPACT_TEXT)
            for i in range(3):
                fmt, parsed = FWID.parse(f[1 + i])
                self.assertEqual(fmt, formats[i], f[1 + i])
                self.assertEqual(parsed.raw, raw, f[1 + i])

    def test_invalid_texts_are_rejected(self) -> None:
        texts = [""]
        for f in rows("invalid.tsv"):
            texts.append(f[0])
        for text in texts:
            self.assertTrue(rejects(text), repr(text))


class Base32HexTests(unittest.TestCase):
    def test_rfc4648_vectors_with_z_padding(self) -> None:
        cases = [
            ("", ""), ("f", "COZZZZZZ"), ("fo", "CPNGZZZZ"), ("foo", "CPNMUZZZ"),
            ("foob", "CPNMUOGZ"), ("fooba", "CPNMUOJ1"), ("foobar", "CPNMUOJ1E8ZZZZZZ"),
        ]
        for data, text in cases:
            self.assertEqual(Base32Hex.encode(data.encode()), text)
            self.assertEqual(Base32Hex.decode(text), data.encode())

    def test_rejects_malformed_input(self) -> None:
        for text in ["C", "COZZZZZ", "CZZZZZZZ", "COZZZZZZCOZZZZZZ", "COzzzzzz", "C1ZZZZZZ", "CPNMUOJé"]:
            with self.assertRaises(ValueError):
                Base32Hex.decode(text)


class Base32CrockfordTests(unittest.TestCase):
    def test_unpadded_with_aliases(self) -> None:
        self.assertEqual(Base32Crockford.encode(b"\xff\xff\xff\xff"), "ZZZZZZR")
        self.assertEqual(Base32Crockford.decode("zzzzzzr"), b"\xff\xff\xff\xff")
        self.assertEqual(Base32Crockford.decode("OILOILO"), Base32Crockford.decode("0110110"))

    def test_rejects_malformed_input(self) -> None:
        for text in ["U0000000", "000000", "ZZZZZZZ", "0000000ß"]:
            with self.assertRaises(ValueError):
                Base32Crockford.decode(text)


class Base62Tests(unittest.TestCase):
    def test_lengths(self) -> None:
        for size, want in [(0, 0), (1, 2), (4, 6), (16, 22), (32, 43)]:
            self.assertEqual(Base62.length(size), want)

    def test_round_trip(self) -> None:
        for size in range(0, 40):
            data = bytearray()
            for i in range(size):
                data.append((i * 37 + 11) % 256)
            text = Base62.encode(bytes(data))
            self.assertEqual(len(text), Base62.length(size))
            self.assertEqual(Base62.decode(text), bytes(data))

    def test_rejects_malformed_input(self) -> None:
        for text in ["0", "zzzzzz", "00000-", "00000é"]:
            with self.assertRaises(ValueError):
                Base62.decode(text)


class ISO8601Tests(unittest.TestCase):
    def test_parse(self) -> None:
        cases = [
            ("2024-01-01", UNIX_2024),
            ("2024-01-01T00:00:00Z", UNIX_2024),
            ("2024-01-01t00:00:00z", UNIX_2024),
            ("2024-01-01 00:00", UNIX_2024),
            ("2024-01-01T09:00:00+09:00", UNIX_2024),
            ("2024-01-01T09:00:00+0900", UNIX_2024),
            ("2024-01-01T09:00+09", UNIX_2024),
            ("2023-12-31T19:00:00-05:00", UNIX_2024),
            ("2024-01-01T00:00:00.1234", UNIX_2024 + 123),
            ("2024-01-01T00:00:00,5Z", UNIX_2024 + 500),
            ("2024-01-01T00:00:01", UNIX_2024 + 1000),
            ("2024-02-29", UNIX_2024 + 59 * 86400000),
            ("1970-01-01", 0),
        ]
        for text, want in cases:
            self.assertEqual(ISO8601.parse(text), want, text)

    def test_rejects_invalid(self) -> None:
        for text in ["", "yesterday", "2024", "2024-1-1", "2024-13-01", "2023-02-29", "2024-04-31", "2024-01-00",
                     "2024-01-01T", "2024-01-01T24:00", "2024-01-01T00:60", "2024-01-01T00:00:60",
                     "2024-01-01T00:00:00.", "2024-01-01T00:00:00+", "2024-01-01T00:00:00Zx", "2024-01-01x"]:
            with self.assertRaises(ValueError):
                ISO8601.parse(text)

    def test_format(self) -> None:
        self.assertEqual(ISO8601.format(UNIX_2024 + 5), "2024-01-01T00:00:00.005+00:00")
        self.assertEqual(ISO8601.format(0), "1970-01-01T00:00:00.000+00:00")
        self.assertEqual(ISO8601.format(951782400000), "2000-02-29T00:00:00.000+00:00")

    def test_round_trip_over_many_days(self) -> None:
        for days in range(-800000, 800000, 997):
            unix_ms = days * ISO8601.MS_PER_DAY + 12345678
            if days >= 0:
                self.assertEqual(ISO8601.parse(ISO8601.format(unix_ms)), unix_ms)
            year, month, day = ISO8601.civil_from_days(days)
            self.assertEqual(ISO8601.days_from_civil(year, month, day), days)


class FWIDTests(unittest.TestCase):
    def test_generate_layout(self) -> None:
        self.assertEqual(FWID.epoch_ms(UNIX_2024), MS_2024)
        self.assertEqual(FWID.min_bits(UNIX_2024), 160)
        for bits in range(160, 513, 32):
            fwid = FWID.generate(bits, UNIX_2024)
            self.assertEqual(fwid.bits, bits)
            self.assertEqual(fwid.bits_timestamp, bits // 4)
            self.assertEqual(fwid.bits_random, bits // 4 * 3)
            self.assertEqual(fwid.timestamp_ms, MS_2024)
            self.assertEqual(fwid.timestamp, UNIX_2024)
            self.assertEqual(fwid.raw[:bits // 32], MS_2024.to_bytes(bits // 32, "big"))

    def test_generate_default_size_is_smallest_that_fits(self) -> None:
        self.assertEqual(FWID.generate(None, UNIX_2024).bits, 160)
        self.assertEqual(FWID.generate(None, FWID.EPOCH_UNIX_MS).bits, 32)
        self.assertEqual(FWID.generate(None, FWID.EPOCH_UNIX_MS + 256).bits, 64)

    def test_generate_rejects_bad_requests(self) -> None:
        for bits in [-32, 0, 31, 33, 161]:
            with self.assertRaises(ValueError):
                FWID.generate(bits, UNIX_2024)
        with self.assertRaises(ValueError):
            FWID.generate(128, UNIX_2024)
        with self.assertRaises(ValueError):
            FWID.generate(None, FWID.EPOCH_UNIX_MS - 1)
        with self.assertRaises(ValueError):
            FWID.generate(None, -1)
        self.assertEqual(FWID.generate(32, FWID.EPOCH_UNIX_MS).timestamp_ms, 0)
        self.assertEqual(FWID.generate(32, FWID.EPOCH_UNIX_MS + 255).timestamp_ms, 255)
        with self.assertRaises(ValueError):
            FWID.generate(32, FWID.EPOCH_UNIX_MS + 256)

    def test_random_part_differs(self) -> None:
        a = FWID.generate(256, UNIX_2024)
        b = FWID.generate(256, UNIX_2024)
        self.assertNotEqual(a.raw[8:], b.raw[8:])

    def test_rejects_bad_raw_sizes(self) -> None:
        for size in [0, 1, 3, 5, 31, 33]:
            with self.assertRaises(ValueError):
                FWID(bytes(size))

    def test_text_formats(self) -> None:
        fwid = FWID(bytes.fromhex("ffffffff"))
        self.assertEqual(fwid.text(FWIDFormat.STANDARD_TEXT), "VVVVVVOZ")
        self.assertEqual(fwid.text(FWIDFormat.READABLE_TEXT), "zzzzzzr")
        self.assertEqual(fwid.text(FWIDFormat.COMPACT_TEXT), "4gfFC3")
        with self.assertRaises(ValueError):
            fwid.text(FWIDFormat.UNFORMATTED)

    def test_readable_text_grouping_and_case(self) -> None:
        for text in ["zzzzzzr-", "-zzzzzzr", "zzzzzzzz--zzzzzzr", "zzzzzzzzzzzzzzzz", "ZZZZZZR", "zzzzzzz-zzzzzzzr"]:
            self.assertTrue(rejects(text), text)
        self.assertEqual(FWID.from_text("zzzzzzr").raw, b"\xff\xff\xff\xff")

    def test_trailing_bits_are_rejected(self) -> None:
        self.assertTrue(rejects("zzzzzzs"))
        self.assertTrue(rejects("VVVVVVPZ"))

    def test_detect(self) -> None:
        self.assertEqual(FWIDFormat.detect("VVVVVVOZ"), FWIDFormat.STANDARD_TEXT)
        self.assertEqual(FWIDFormat.detect("zzzzzzr"), FWIDFormat.READABLE_TEXT)
        self.assertEqual(FWIDFormat.detect("4gfFC3"), FWIDFormat.COMPACT_TEXT)
        with self.assertRaises(ValueError):
            FWIDFormat.detect("not an fwid")

    def test_equality_and_hash(self) -> None:
        a = FWID(bytes.fromhex("01000000"))
        b = FWID.from_text("0400000Z")
        self.assertEqual(a, b)
        self.assertEqual(hash(a), hash(b))
        self.assertNotEqual(a, FWID(bytes.fromhex("02000000")))

    def test_oversized_timestamp_is_not_an_error(self) -> None:
        fwid = FWID(b"\xff" * 32)
        self.assertEqual(fwid.timestamp_ms, 2 ** 64 - 1)
        self.assertEqual(FWID.from_text(fwid.compact_text), fwid)


class CLITests(unittest.TestCase):
    def test_generate_and_inspect(self) -> None:
        status, out, err = runs(["g", "-t", "2024-01-01T00:00:00Z", "-b", "256", "-f", "compact", "-n", "3"], "")
        lines = out.split("\n")
        self.assertEqual(status, 0)
        self.assertEqual(len(lines), 3)
        status, out, err = runs(["i", lines[0]], "")
        self.assertEqual(status, 0)
        self.assertIn("Format:     Compact Text\n", out + "\n")
        self.assertIn("Bits:       256 (timestamp 64, random 192)\n", out + "\n")
        self.assertIn("Timestamp:  2024-01-01T00:00:00.000+00:00 (725760000000 ms)\n", out + "\n")

    def test_inspect_reads_stdin_and_reports_failures(self) -> None:
        status, out, err = runs(["g", "-t", "2024-01-01", "-n", "2"], "")
        ids = out.split("\n")
        status, out, err = runs(["inspect"], ids[0] + "  \n\nbogus\n" + ids[1] + "\n")
        self.assertEqual(status, 1)
        self.assertTrue(err.startswith("fwid: bogus: "))
        self.assertEqual(out.count("Format:"), 2)
        self.assertIn("\n\n\nFormat:", out)

    def test_usage_errors(self) -> None:
        for argv in [[], ["x"], ["g", "-b", "0"], ["g", "-b", "x"], ["g", "-f", "nope"], ["g", "-t", "yesterday"],
                     ["g", "-n"], ["g", "--zzz"], ["i", "-x"]]:
            self.assertEqual(runs(argv, "")[0], 2, str(argv))

    def test_option_forms(self) -> None:
        for argv in [["g", "-b256"], ["g", "-b", "256"], ["g", "--bits", "256"], ["g", "--bits=256"]]:
            status, out, err = runs(argv, "")
            self.assertEqual(status, 0, str(argv))
            self.assertEqual(len(out), 56)

    def test_failures_exit_with_one(self) -> None:
        self.assertEqual(runs(["g", "-b", "128"], "")[0], 1)
        self.assertEqual(runs(["g", "-t", "2000-12-31"], "")[0], 1)

    def test_help(self) -> None:
        status, out, err = runs(["-h"], "")
        self.assertEqual(status, 0)
        self.assertTrue(out.startswith("usage: fwid [-h] COMMAND ..."))


if __name__ == "__main__":
    unittest.main()
