class Base62:
    ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

    @classmethod
    def length(cls, size: int) -> int:
        limit = 256 ** size
        chars, capacity = 0, 1
        while capacity < limit:
            capacity *= 62
            chars += 1
        return chars

    @classmethod
    def encode(cls, data: bytes) -> str:
        value = int.from_bytes(data, "big")
        out = []
        for _ in range(cls.length(len(data))):
            value, rem = divmod(value, 62)
            out.append(cls.ALPHABET[rem])
        return "".join(reversed(out))

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
                raise ValueError(f"Invalid character: {ch!r}")
            value = value * 62 + index
        if value >= 256 ** size:
            raise ValueError("Value out of range")
        return value.to_bytes(size, "big")
