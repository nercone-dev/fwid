/// Crockford's Base32 without check symbols and without padding.
///
/// Encoding emits uppercase symbols. Decoding is case-insensitive and maps
/// the look-alike symbols `I` and `L` to `1` and `O` to `0`, as Crockford specifies.
public enum Base32Crockford {
    public static let alphabet = Array("0123456789ABCDEFGHJKMNPQRSTVWXYZ".utf8)

    /// Bytes carried by a block with this many characters.
    private static func bytes(fromChars chars: Int) -> Int? {
        switch chars {
        case 8: return 5
        case 7: return 4
        case 5: return 3
        case 4: return 2
        case 2: return 1
        default: return nil
        }
    }

    private static func index(_ c: UInt8) -> UInt64? {
        var c = c
        if c >= UInt8(ascii: "a") && c <= UInt8(ascii: "z") { c -= 32 }
        switch c {
        case UInt8(ascii: "I"), UInt8(ascii: "L"): c = UInt8(ascii: "1")
        case UInt8(ascii: "O"): c = UInt8(ascii: "0")
        default: break
        }
        return alphabet.firstIndex(of: c).map { UInt64($0) }
    }

    public static func encode(_ data: [UInt8]) -> String {
        var out = [UInt8]()
        out.reserveCapacity((data.count * 8 + 4) / 5)
        var i = 0
        while i < data.count {
            let n = min(5, data.count - i)
            var value: UInt64 = 0
            for b in data[i..<i + n] { value = value << 8 | UInt64(b) }
            value <<= UInt64(8 * (5 - n))
            let chars = (n * 8 + 4) / 5
            for j in 0..<chars { out.append(alphabet[Int((value >> UInt64(35 - 5 * j)) & 31)]) }
            i += 5
        }
        return String(decoding: out, as: UTF8.self)
    }

    public static func decode(_ text: String) throws -> [UInt8] {
        let text = Array(text.utf8)
        var out = [UInt8]()
        out.reserveCapacity(text.count / 8 * 5 + 4)
        for start in stride(from: 0, to: text.count, by: 8) {
            let block = text[start..<min(start + 8, text.count)]
            guard let n = bytes(fromChars: block.count) else { throw FWIDError.base32CrockfordLength }
            var value: UInt64 = 0
            for c in block {
                guard let i = index(c) else {
                    let offender = String(decoding: block, as: UTF8.self).first { ch in
                        !(ch.asciiValue.map { index($0) != nil } ?? false)
                    }
                    throw FWIDError.character(offender ?? "\u{FFFD}")
                }
                value = value << 5 | i
            }
            let extra = UInt64(block.count * 5 - n * 8)
            if value & ((1 << extra) - 1) != 0 { throw FWIDError.base32CrockfordTrailingBits }
            value >>= extra
            for i in 0..<n { out.append(UInt8(truncatingIfNeeded: value >> UInt64(8 * (n - 1 - i)))) }
        }
        return out
    }
}
