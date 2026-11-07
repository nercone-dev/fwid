class Base62:
    """Base62 over a byte string of fixed length: the bytes are one big-endian integer, zero-padded to the exact length."""

    ALPHABET: str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

    @classmethod
    def length(cls, size: int) -> int:
        """The number of base-62 digits of 256**size - 1, the text length for size bytes."""
        limit = 256 ** size
        chars = 0
        capacity = 1
        while capacity < limit:
            capacity *= 62
            chars += 1
        return chars

    @classmethod
    def encode(cls, data: bytes) -> str:
        value = int.from_bytes(data, "big")
        out: list[str] = []
        for _ in range(cls.length(len(data))):
            rem = value % 62
            value = value // 62
            out.append(cls.ALPHABET[rem])
        out.reverse()
        return "".join(out)

    @classmethod
    def decode(cls, text: str) -> bytes:
        size = 0
        while cls.length(size) < len(text):
            size += 1
        if cls.length(size) != len(text):
            raise ValueError("Invalid Base62 length")
        value = 0
        for ch in text:
            index = cls.ALPHABET.find(ch)
            if index < 0:
                raise ValueError("Invalid character: " + repr(ch))
            value = value * 62 + index
        if value >= 256 ** size:
            raise ValueError("Value out of range")
        return value.to_bytes(size, "big")
