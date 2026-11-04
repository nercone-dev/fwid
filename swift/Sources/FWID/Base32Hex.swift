/// Base32 Hex (RFC 4648 section 7) with `Z` as the padding character.
public enum Base32Hex {
    public static let alphabet = Array("0123456789ABCDEFGHIJKLMNOPQRSTUV".utf8)
    public static let pad = UInt8(ascii: "Z")

    /// Bytes carried by a block with this many non-padding characters.
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
        switch c {
        case UInt8(ascii: "0")...UInt8(ascii: "9"): return UInt64(c - UInt8(ascii: "0"))
        case UInt8(ascii: "A")...UInt8(ascii: "V"): return UInt64(c - UInt8(ascii: "A") + 10)
        default: return nil
        }
    }

    public static func encode(_ data: [UInt8]) -> String {
        var out = [UInt8]()
        out.reserveCapacity((data.count + 4) / 5 * 8)
        var i = 0
        while i < data.count {
            let n = min(5, data.count - i)
            var value: UInt64 = 0
            for b in data[i..<i + n] { value = value << 8 | UInt64(b) }
            value <<= UInt64(8 * (5 - n))
            let chars = (n * 8 + 4) / 5
            for j in 0..<chars { out.append(alphabet[Int((value >> UInt64(35 - 5 * j)) & 31)]) }
            out.append(contentsOf: repeatElement(pad, count: 8 - chars))
            i += 5
        }
        return String(decoding: out, as: UTF8.self)
    }

    public static func decode(_ text: String) throws -> [UInt8] {
        let text = Array(text.utf8)
        guard text.count % 8 == 0 else { throw FWIDError.base32HexLength }
        let blocks = text.count / 8
        var out = [UInt8]()
        out.reserveCapacity(blocks * 5)
        for b in 0..<blocks {
            let block = text[b * 8..<(b + 1) * 8]
            let bodyLength = (block.lastIndex { $0 != pad }.map { $0 - block.startIndex + 1 }) ?? 0
            if bodyLength != 8 && b != blocks - 1 { throw FWIDError.base32HexPaddingPosition }
            guard let n = bytes(fromChars: bodyLength) else { throw FWIDError.base32HexPaddingLength }
            var value: UInt64 = 0
            let body = block.prefix(bodyLength)
            for c in body {
                guard let i = index(c) else {
                    let offender = String(decoding: body, as: UTF8.self).first { ch in
                        !(ch.asciiValue.map { index($0) != nil } ?? false)
                    }
                    throw FWIDError.character(offender ?? "\u{FFFD}")
                }
                value = value << 5 | i
            }
            let extra = UInt64(bodyLength * 5 - n * 8)
            if value & ((1 << extra) - 1) != 0 { throw FWIDError.base32HexTrailingBits }
            value >>= extra
            for i in 0..<n { out.append(UInt8(truncatingIfNeeded: value >> UInt64(8 * (n - 1 - i)))) }
        }
        return out
    }
}
