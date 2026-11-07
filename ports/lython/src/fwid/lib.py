import time

from .helpers import Base32Crockford, Base32Hex, Base62, ISO8601


class FWIDFormat:
    """The formats of an FWID. The text formats are the values STANDARD_TEXT, READABLE_TEXT and COMPACT_TEXT."""

    UNFORMATTED: int = 0
    STANDARD_TEXT: int = 1
    READABLE_TEXT: int = 2
    COMPACT_TEXT: int = 3

    @staticmethod
    def name(fmt: int) -> str:
        if fmt == FWIDFormat.UNFORMATTED:
            return "Unformatted"
        if fmt == FWIDFormat.STANDARD_TEXT:
            return "Standard Text"
        if fmt == FWIDFormat.READABLE_TEXT:
            return "Readable Text"
        if fmt == FWIDFormat.COMPACT_TEXT:
            return "Compact Text"
        raise ValueError("Unknown Format")

    @staticmethod
    def detect(text: str) -> int:
        return FWID.parse(text)[0]


class FWID:
    """A FourWord Identifier: a timestamp followed by random bytes.

    Points in time are ints: milliseconds since 1970-01-01T00:00:00Z. A naive
    time cannot be passed, since an int has no time zone to leave out.
    """

    EPOCH_UNIX_MS: int = 978307200000  # 2001-01-01T00:00:00Z
    BITS_ALIGN: int = 32
    ENTROPY_SOURCE: str = "/dev/urandom"

    raw: bytes

    def __init__(self, raw: bytes) -> None:
        FWID.check_bits(len(raw) * 8)
        self.raw = raw

    @staticmethod
    def check_bits(bits: int) -> None:
        if bits < FWID.BITS_ALIGN or bits % FWID.BITS_ALIGN != 0:
            raise ValueError("Bits must be a positive multiple of 32")

    @staticmethod
    def now_unix_ms() -> int:
        return time.time_ns() // 1000000

    @staticmethod
    def epoch_ms(unix_ms: int) -> int:
        """Milliseconds from the FWID epoch to the given time. Raises ValueError for a time before the epoch."""
        ms = unix_ms - FWID.EPOCH_UNIX_MS
        if ms < 0:
            raise ValueError("datetime must not be before the FWID epoch (2001-01-01 00:00:00 UTC)")
        return ms

    @staticmethod
    def timestamp_bytes(ms: int) -> int:
        return max(1, (ms.bit_length() + 7) // 8)

    @staticmethod
    def min_bits(unix_ms: int) -> int:
        return FWID.timestamp_bytes(FWID.epoch_ms(unix_ms)) * FWID.BITS_ALIGN

    @staticmethod
    def random_bytes(size: int) -> bytes:
        """size bytes from the operating system's CSPRNG."""
        with open(FWID.ENTROPY_SOURCE, "rb") as source:
            data = source.read(size)
        if len(data) != size:
            raise ValueError("cannot read enough random bytes from " + FWID.ENTROPY_SOURCE)
        return data

    @staticmethod
    def generate(bits: int | None = None, unix_ms: int | None = None) -> "FWID":
        """Generate an FWID. bits=None chooses the smallest size that fits the timestamp; unix_ms=None means now."""
        ms = FWID.epoch_ms(FWID.now_unix_ms() if unix_ms is None else unix_ms)
        required = FWID.timestamp_bytes(ms) * FWID.BITS_ALIGN
        if bits is None:
            bits = required
        FWID.check_bits(bits)
        if ms.bit_length() > bits // 4:
            raise ValueError(str(bits) + " bits is too small for this timestamp (need at least " + str(required) + ")")
        return FWID(ms.to_bytes(bits // 32, "big") + FWID.random_bytes(bits // 32 * 3))

    @staticmethod
    def from_standard_text(text: str) -> "FWID":
        return FWID(Base32Hex.decode(text))

    @staticmethod
    def from_readable_text(text: str) -> "FWID":
        for ch in text:
            if "A" <= ch <= "Z":
                raise ValueError("Readable Text must be lowercase")
        groups = text.split("-")
        for i in range(len(groups) - 1):
            if len(groups[i]) != 8:
                raise ValueError("Readable Text must be split into groups of 8 characters (the last may be shorter)")
        if not 1 <= len(groups[len(groups) - 1]) <= 8:
            raise ValueError("Readable Text must be split into groups of 8 characters (the last may be shorter)")
        return FWID(Base32Crockford.decode("".join(groups)))

    @staticmethod
    def from_compact_text(text: str) -> "FWID":
        return FWID(Base62.decode(text))

    @staticmethod
    def parse(text: str) -> tuple[int, "FWID"]:
        """Parse any text format, trying Standard, Readable, then Compact Text. Returns the format and the FWID."""
        try:
            return (FWIDFormat.STANDARD_TEXT, FWID.from_standard_text(text))
        except ValueError:
            pass
        try:
            return (FWIDFormat.READABLE_TEXT, FWID.from_readable_text(text))
        except ValueError:
            pass
        try:
            return (FWIDFormat.COMPACT_TEXT, FWID.from_compact_text(text))
        except ValueError:
            pass
        raise ValueError("Unknown Format")

    @staticmethod
    def from_text(text: str) -> "FWID":
        return FWID.parse(text)[1]

    @property
    def bits(self) -> int:
        return len(self.raw) * 8

    @property
    def bits_timestamp(self) -> int:
        return self.bits // 4

    @property
    def bits_random(self) -> int:
        return (self.bits // 4) * 3

    @property
    def timestamp_ms(self) -> int:
        """Milliseconds since the FWID epoch."""
        return int.from_bytes(self.raw[:self.bits_timestamp // 8], "big")

    @property
    def timestamp(self) -> int:
        """The time, as milliseconds since 1970-01-01T00:00:00Z."""
        return FWID.EPOCH_UNIX_MS + self.timestamp_ms

    def text(self, fmt: int = FWIDFormat.STANDARD_TEXT) -> str:
        if fmt == FWIDFormat.STANDARD_TEXT:
            return self.standard_text
        if fmt == FWIDFormat.READABLE_TEXT:
            return self.readable_text
        if fmt == FWIDFormat.COMPACT_TEXT:
            return self.compact_text
        raise ValueError("Format '" + FWIDFormat.name(fmt) + "' is not Text-based Format")

    @property
    def standard_text(self) -> str:
        return Base32Hex.encode(self.raw)

    @property
    def readable_text(self) -> str:
        crockford = Base32Crockford.encode(self.raw).lower()
        groups: list[str] = []
        for i in range(0, len(crockford), 8):
            groups.append(crockford[i:i + 8])
        return "-".join(groups)

    @property
    def compact_text(self) -> str:
        return Base62.encode(self.raw)

    def __bytes__(self) -> bytes:
        return self.raw

    def __str__(self) -> str:
        return self.standard_text

    def __repr__(self) -> str:
        return "FWID(" + repr(self.standard_text) + ")"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FWID):
            return False
        return self.raw == other.raw

    def __hash__(self) -> int:
        return hash(self.raw)
