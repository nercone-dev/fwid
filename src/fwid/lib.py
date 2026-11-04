from __future__ import annotations

import secrets
from enum import Enum
from typing import Optional, Union
from datetime import datetime, timedelta, timezone

from .helpers import Base32Hex, Base62

class FWIDFormat(Enum):
    UNFORMATTED = "Unformatted"
    # Text
    STANDARD_TEXT = "Standard Text"
    READABLE_TEXT = "Readable Text"
    COMPACT_TEXT  = "Compact Text"

    @staticmethod
    def detect(arg: Union[bytes, str]) -> FWIDFormat:
        if isinstance(arg, bytes):
            return FWIDFormat.UNFORMATTED
        elif isinstance(arg, str):
            parsers = (
                (FWIDFormat.STANDARD_TEXT, FWID.from_standard_text),
                (FWIDFormat.READABLE_TEXT, FWID.from_readable_text),
                (FWIDFormat.COMPACT_TEXT, FWID.from_compact_text),
            )
            for fmt, parse in parsers:
                try:
                    parse(arg)
                except ValueError:
                    continue
                return fmt
        raise ValueError("Unknown Format")

class FWID:
    EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)
    BITS_ALIGN = 32

    def __init__(self, arg: Optional[Union[bytes, str, int]] = None, dt: Optional[datetime] = None):
        if arg is None:
            self.raw = FWID.generate(dt=dt)
        elif isinstance(arg, bytes):
            FWID.check_bits(len(arg) * 8)
            self.raw = arg
        elif isinstance(arg, str):
            self.raw = FWID.from_text(arg).raw
        elif isinstance(arg, int):
            self.raw = FWID.generate(arg, dt)
        else:
            raise TypeError(f"Unsupported argument type: {type(arg).__name__}")

    @staticmethod
    def check_bits(bits: int) -> None:
        if bits < FWID.BITS_ALIGN or bits % FWID.BITS_ALIGN != 0:
            raise ValueError(f"Bits must be a positive multiple of {FWID.BITS_ALIGN}")

    @staticmethod
    def epoch_ms(dt: Optional[datetime] = None) -> int:
        if dt is None:
            dt = datetime.now(timezone.utc)
        elif dt.tzinfo is None or dt.utcoffset() is None:
            raise ValueError("datetime must be timezone-aware")
        ms = (dt - FWID.EPOCH) // timedelta(milliseconds=1)
        if ms < 0:
            raise ValueError("datetime must not be before the FWID epoch (2001-01-01 00:00:00 UTC)")
        return ms

    @staticmethod
    def from_text(text: str) -> "FWID":
        detected_format = FWIDFormat.detect(text)
        if detected_format == FWIDFormat.STANDARD_TEXT:
            return FWID.from_standard_text(text)
        elif detected_format == FWIDFormat.READABLE_TEXT:
            return FWID.from_readable_text(text)
        elif detected_format == FWIDFormat.COMPACT_TEXT:
            return FWID.from_compact_text(text)
        else:
            raise ValueError("Unknown Format")

    @staticmethod
    def from_standard_text(text: str) -> "FWID":
        return FWID(Base32Hex.decode(text))

    @staticmethod
    def from_readable_text(text: str) -> "FWID":
        if text != text.lower():
            raise ValueError("Readable Text must be lowercase")
        groups = text.split("-")
        if any(len(group) != 8 for group in groups):
            raise ValueError("Readable Text must be split into groups of 8 characters")
        return FWID(Base32Hex.decode("".join(groups).upper()))

    @staticmethod
    def from_compact_text(text: str) -> "FWID":
        return FWID(Base62.decode(text))

    @staticmethod
    def min_bits(dt: Optional[datetime] = None) -> int:
        timestamp_bytes = max(1, (FWID.epoch_ms(dt).bit_length() + 7) // 8)
        return timestamp_bytes * 8 * 4

    @staticmethod
    def generate(bits: Optional[int] = None, dt: Optional[datetime] = None) -> bytes:
        ms = FWID.epoch_ms(dt)
        required = max(1, (ms.bit_length() + 7) // 8) * 32
        if bits is None:
            bits = required
        FWID.check_bits(bits)
        if ms.bit_length() > bits // 4:
            raise ValueError(f"{bits} bits is too small for this timestamp (need at least {required})")
        return ms.to_bytes(bits // 32, "big") + secrets.token_bytes(bits // 32 * 3)

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
    def timestamp(self) -> datetime:
        ms = int.from_bytes(self.raw[:self.bits_timestamp // 8], "big")
        return FWID.EPOCH + timedelta(milliseconds=ms)

    def text(self, format: FWIDFormat = FWIDFormat.STANDARD_TEXT) -> str:
        if format == FWIDFormat.STANDARD_TEXT:
            return self.standard_text
        elif format == FWIDFormat.READABLE_TEXT:
            return self.readable_text
        elif format == FWIDFormat.COMPACT_TEXT:
            return self.compact_text
        else:
            raise ValueError(f"Format '{format.value}' is not Text-based Format")

    @property
    def standard_text(self) -> str:
        return Base32Hex.encode(self.raw)

    @property
    def readable_text(self) -> str:
        standard = self.standard_text.lower()
        return "-".join(standard[i:i + 8] for i in range(0, len(standard), 8))

    @property
    def compact_text(self) -> str:
        return Base62.encode(self.raw)

    def __bytes__(self) -> bytes:
        return self.raw

    def __str__(self) -> str:
        return self.text()

    def __repr__(self) -> str:
        return f"FWID({self.standard_text!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FWID):
            return NotImplemented
        return self.raw == other.raw

    def __hash__(self) -> int:
        return hash(self.raw)
