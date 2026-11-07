class Base32Crockford:
    """Crockford's Base32 without check symbols and without padding.

    Encoding emits uppercase symbols. Decoding is case-insensitive and maps
    the look-alike symbols I and L to 1 and O to 0, as Crockford specifies.
    """

    ALPHABET: str = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

    @classmethod
    def bytes_from_chars(cls, chars: int) -> int:
        """The number of bytes carried by the given number of characters in a block, or -1."""
        if chars == 8:
            return 5
        if chars == 7:
            return 4
        if chars == 5:
            return 3
        if chars == 4:
            return 2
        if chars == 2:
            return 1
        return -1

    @classmethod
    def symbol_value(cls, ch: str) -> int:
        """The value of one symbol, or -1 if it is not part of the alphabet or its aliases."""
        code = ord(ch)
        if 97 <= code <= 122:
            ch = chr(code - 32)
        if ch == "I" or ch == "L":
            ch = "1"
        elif ch == "O":
            ch = "0"
        return cls.ALPHABET.find(ch)

    @classmethod
    def encode(cls, data: bytes) -> str:
        out: list[str] = []
        for i in range(0, len(data), 5):
            chunk = data[i:i + 5]
            n = len(chunk)
            value = int.from_bytes(chunk, "big") << (8 * (5 - n))
            chars = (n * 8 + 4) // 5
            for j in range(chars):
                out.append(cls.ALPHABET[(value >> (35 - 5 * j)) & 31])
        return "".join(out)

    @classmethod
    def decode(cls, text: str) -> bytes:
        out = bytearray()
        for i in range(0, len(text), 8):
            block = text[i:i + 8]
            n = cls.bytes_from_chars(len(block))
            if n < 0:
                raise ValueError("Invalid Base32Crockford length")
            value = 0
            for ch in block:
                index = cls.symbol_value(ch)
                if index < 0:
                    raise ValueError("Invalid character: " + repr(ch))
                value = (value << 5) | index
            extra = len(block) * 5 - n * 8
            if value & ((1 << extra) - 1) != 0:
                raise ValueError("Non-zero trailing bits")
            out += (value >> extra).to_bytes(n, "big")
        return bytes(out)
