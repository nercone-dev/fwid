/// Base62 (`0-9A-Za-z`) over a big-endian arbitrary-precision integer,
/// zero-padded to a length that depends only on the byte length.
public enum Base62 {
    public static let alphabet = Array("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz".utf8)

    private static func index(_ c: UInt8) -> UInt32? {
        switch c {
        case UInt8(ascii: "0")...UInt8(ascii: "9"): return UInt32(c - UInt8(ascii: "0"))
        case UInt8(ascii: "A")...UInt8(ascii: "Z"): return UInt32(c - UInt8(ascii: "A")) + 10
        case UInt8(ascii: "a")...UInt8(ascii: "z"): return UInt32(c - UInt8(ascii: "a")) + 36
        default: return nil
        }
    }

    /// Divides the big-endian number `num[start...]` in place and returns the remainder.
    private static func divmod(_ num: inout [UInt8], from start: Int, by divisor: UInt32) -> UInt32 {
        var rem: UInt32 = 0
        for i in start..<num.count {
            let cur = rem << 8 | UInt32(num[i])
            num[i] = UInt8(cur / divisor)
            rem = cur % divisor
        }
        return rem
    }

    private static func skipZeros(_ num: [UInt8], from start: Int) -> Int {
        var start = start
        while start < num.count && num[start] == 0 { start += 1 }
        return start
    }

    /// Smallest `n` such that `62^n >= 256^size`, i.e. the number of base-62
    /// digits of the largest `size`-byte value.
    public static func length(_ size: Int) -> Int {
        var num = [UInt8](repeating: 0xFF, count: size)
        var start = 0
        var chars = 0
        while start < num.count {
            _ = divmod(&num, from: start, by: 62)
            chars += 1
            start = skipZeros(num, from: start)
        }
        return chars
    }

    public static func encode(_ data: [UInt8]) -> String {
        let width = length(data.count)
        var num = data
        var start = skipZeros(num, from: 0)
        var out = [UInt8](repeating: alphabet[0], count: width)
        var slot = width - 1
        while slot >= 0 && start < num.count {
            out[slot] = alphabet[Int(divmod(&num, from: start, by: 62))]
            start = skipZeros(num, from: start)
            slot -= 1
        }
        return String(decoding: out, as: UTF8.self)
    }

    public static func decode(_ text: String) throws -> [UInt8] {
        let text = Array(text.utf8)
        // log2(62) is irrational, so the estimate only seeds the search and
        // the exact length is always verified.
        let estimate = Int(Double(text.count) * 5.954196310386876 / 8.0)
        guard let size = (max(estimate - 1, 0)...estimate + 1).first(where: { length($0) == text.count }) else {
            throw FWIDError.base62Length
        }
        var out = [UInt8](repeating: 0, count: size)
        for c in text {
            guard var carry = index(c) else {
                let offender = String(decoding: text, as: UTF8.self).first { !($0.isASCII && ($0.isLetter || $0.isNumber)) }
                throw FWIDError.character(offender ?? "\u{FFFD}")
            }
            for i in stride(from: size - 1, through: 0, by: -1) {
                let cur = UInt32(out[i]) * 62 + carry
                out[i] = UInt8(truncatingIfNeeded: cur)
                carry = cur >> 8
            }
            if carry != 0 { throw FWIDError.base62Range }
        }
        return out
    }
}
