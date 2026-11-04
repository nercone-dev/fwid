class Base32Hex:
    ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUV"
    PAD = "Z"
    BYTES_FROM_CHARS = {8: 5, 7: 4, 5: 3, 4: 2, 2: 1}

    @classmethod
    def encode(cls, data: bytes) -> str:
        out = []
        for i in range(0, len(data), 5):
            chunk = data[i:i + 5]
            n = len(chunk)
            value = int.from_bytes(chunk, "big") << (8 * (5 - n))
            chars = (n * 8 + 4) // 5
            out.extend(cls.ALPHABET[(value >> (35 - 5 * j)) & 31] for j in range(chars))
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
            n = cls.BYTES_FROM_CHARS.get(len(body))
            if n is None:
                raise ValueError("Invalid padding length")
            value = 0
            for ch in body:
                index = cls.ALPHABET.find(ch)
                if index < 0:
                    raise ValueError(f"Invalid character: {ch!r}")
                value = (value << 5) | index
            extra = len(body) * 5 - n * 8
            if value & ((1 << extra) - 1):
                raise ValueError("Non-zero trailing bits")
            out += (value >> extra).to_bytes(n, "big")
        return bytes(out)
