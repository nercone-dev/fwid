class Base32Hex:
    """Base32 with the "Extended Hex" alphabet of RFC 4648 Section 7, using Z as the padding character."""

    ALPHABET: str = "0123456789ABCDEFGHIJKLMNOPQRSTUV"
    PAD: str = "Z"

    @classmethod
    def bytes_from_chars(cls, chars: int) -> int:
        """The number of bytes carried by the given number of data characters in a block, or -1."""
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
    def encode(cls, data: bytes) -> str:
        out: list[str] = []
        for i in range(0, len(data), 5):
            chunk = data[i:i + 5]
            n = len(chunk)
            value = int.from_bytes(chunk, "big") << (8 * (5 - n))
            chars = (n * 8 + 4) // 5
            for j in range(chars):
                out.append(cls.ALPHABET[(value >> (35 - 5 * j)) & 31])
            out.append(cls.PAD * (8 - chars))
        return "".join(out)

    @classmethod
    def decode(cls, text: str) -> bytes:
        if len(text) % 8 != 0:
            raise ValueError("Base32Hex length must be a multiple of 8")
        out = bytearray()
        blocks = len(text) // 8
        for b in range(blocks):
            block = text[b * 8:(b + 1) * 8]
            body = block.rstrip(cls.PAD)
            if body != block and b != blocks - 1:
                raise ValueError("Padding is only allowed in the last block")
            n = cls.bytes_from_chars(len(body))
            if n < 0:
                raise ValueError("Invalid padding length")
            value = 0
            for ch in body:
                index = cls.ALPHABET.find(ch)
                if index < 0:
                    raise ValueError("Invalid character: " + repr(ch))
                value = (value << 5) | index
            extra = len(body) * 5 - n * 8
            if value & ((1 << extra) - 1) != 0:
                raise ValueError("Non-zero trailing bits")
            out += (value >> extra).to_bytes(n, "big")
        return bytes(out)
