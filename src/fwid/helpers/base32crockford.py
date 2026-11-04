class Base32Crockford:
    """Crockford's Base32 without check symbols and without padding.

    Encoding emits uppercase symbols. Decoding is case-insensitive and maps
    the look-alike symbols I and L to 1 and O to 0, as Crockford specifies.
    """

    ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    ALIASES = {"I": "1", "L": "1", "O": "0"}
    BYTES_FROM_CHARS = {8: 5, 7: 4, 5: 3, 4: 2, 2: 1, 0: 0}

    @classmethod
    def encode(cls, data: bytes) -> str:
        out = []
        for i in range(0, len(data), 5):
            chunk = data[i:i + 5]
            n = len(chunk)
            value = int.from_bytes(chunk, "big") << (8 * (5 - n))
            chars = (n * 8 + 4) // 5
            out.extend(cls.ALPHABET[(value >> (35 - 5 * j)) & 31] for j in range(chars))
        return "".join(out)

    @classmethod
    def decode(cls, text: str) -> bytes:
        text = text.upper()
        out = bytearray()
        for i in range(0, len(text), 8):
            block = text[i:i + 8]
            n = cls.BYTES_FROM_CHARS.get(len(block))
            if n is None:
                raise ValueError("Invalid Base32Crockford length")
            value = 0
            for ch in block:
                index = cls.ALPHABET.find(cls.ALIASES.get(ch, ch))
                if index < 0:
                    raise ValueError(f"Invalid character: {ch!r}")
                value = (value << 5) | index
            extra = len(block) * 5 - n * 8
            if value & ((1 << extra) - 1):
                raise ValueError("Non-zero trailing bits")
            out += (value >> extra).to_bytes(n, "big")
        return bytes(out)
