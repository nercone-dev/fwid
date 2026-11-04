import Foundation

/// Extended-format ISO 8601 datetimes with millisecond precision.
///
/// Accepted input: `YYYY-MM-DD` optionally followed by `T`, `t` or a space and
/// `hh:mm[:ss[.fraction]]`, then optionally `Z` or an offset `+hh[:mm]` /
/// `+hhmm`. Values without an offset are UTC. Digits beyond milliseconds are
/// truncated.
public enum ISO8601 {
    private static let msPerDay: Int64 = 86_400_000

    private static func isLeap(_ year: Int64) -> Bool {
        year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)
    }

    private static func daysInMonth(_ year: Int64, _ month: Int64) -> Int64 {
        switch month {
        case 2: return isLeap(year) ? 29 : 28
        case 4, 6, 9, 11: return 30
        default: return 31
        }
    }

    private static func floorDiv(_ a: Int64, _ b: Int64) -> Int64 {
        let q = a / b
        return (a % b != 0 && (a < 0) != (b < 0)) ? q - 1 : q
    }

    /// Days since 1970-01-01 of a proleptic Gregorian date.
    private static func daysFromCivil(_ year: Int64, _ month: Int64, _ day: Int64) -> Int64 {
        let y = month <= 2 ? year - 1 : year
        let era = floorDiv(y, 400)
        let yoe = y - era * 400
        let doy = (153 * ((month + 9) % 12) + 2) / 5 + day - 1
        let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy
        return era * 146_097 + doe - 719_468
    }

    private static func civilFromDays(_ days: Int64) -> (year: Int64, month: Int64, day: Int64) {
        let z = days + 719_468
        let era = floorDiv(z, 146_097)
        let doe = z - era * 146_097
        let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365
        let doy = doe - (365 * yoe + yoe / 4 - yoe / 100)
        let mp = (5 * doy + 2) / 153
        let day = doy - (153 * mp + 2) / 5 + 1
        let month = mp < 10 ? mp + 3 : mp - 9
        return (yoe + era * 400 + (month <= 2 ? 1 : 0), month, day)
    }

    private static func digits(_ text: [UInt8], _ pos: inout Int, _ count: Int) -> Int64? {
        guard pos + count <= text.count else { return nil }
        var value: Int64 = 0
        for c in text[pos..<pos + count] {
            guard c >= UInt8(ascii: "0") && c <= UInt8(ascii: "9") else { return nil }
            value = value * 10 + Int64(c - UInt8(ascii: "0"))
        }
        pos += count
        return value
    }

    private static func expect(_ text: [UInt8], _ pos: inout Int, _ byte: Character) -> Bool {
        guard pos < text.count, text[pos] == byte.asciiValue else { return false }
        pos += 1
        return true
    }

    /// Returns Unix milliseconds.
    private static func parseMS(_ string: String) -> Int64? {
        let t = Array(string.utf8)
        var pos = 0
        guard let year = digits(t, &pos, 4), expect(t, &pos, "-"),
              let month = digits(t, &pos, 2), expect(t, &pos, "-"),
              let day = digits(t, &pos, 2),
              (1...12).contains(month), day >= 1, day <= daysInMonth(year, month)
        else { return nil }
        var hour: Int64 = 0, minute: Int64 = 0, second: Int64 = 0, millis: Int64 = 0, offset: Int64 = 0
        if pos < t.count {
            guard [UInt8(ascii: "T"), UInt8(ascii: "t"), UInt8(ascii: " ")].contains(t[pos]) else { return nil }
            pos += 1
            guard let h = digits(t, &pos, 2), expect(t, &pos, ":"), let m = digits(t, &pos, 2) else { return nil }
            hour = h
            minute = m
            if expect(t, &pos, ":") {
                guard let s = digits(t, &pos, 2) else { return nil }
                second = s
                if pos < t.count, t[pos] == UInt8(ascii: ".") || t[pos] == UInt8(ascii: ",") {
                    pos += 1
                    let start = pos
                    while pos < t.count, t[pos] >= UInt8(ascii: "0"), t[pos] <= UInt8(ascii: "9") { pos += 1 }
                    guard pos > start else { return nil }
                    for i in 0..<3 {
                        let d = start + i < pos ? Int64(t[start + i] - UInt8(ascii: "0")) : 0
                        millis = millis * 10 + d
                    }
                }
            }
            guard hour <= 23, minute <= 59, second <= 59 else { return nil }
            if pos < t.count {
                if t[pos] == UInt8(ascii: "Z") || t[pos] == UInt8(ascii: "z") {
                    pos += 1
                } else if t[pos] == UInt8(ascii: "+") || t[pos] == UInt8(ascii: "-") {
                    let sign: Int64 = t[pos] == UInt8(ascii: "-") ? -1 : 1
                    pos += 1
                    guard let oh = digits(t, &pos, 2) else { return nil }
                    _ = expect(t, &pos, ":")
                    var om: Int64 = 0
                    if pos < t.count {
                        guard let m = digits(t, &pos, 2) else { return nil }
                        om = m
                    }
                    guard oh <= 23, om <= 59 else { return nil }
                    offset = sign * (oh * 60 + om)
                } else {
                    return nil
                }
            }
        }
        guard pos == t.count else { return nil }
        let seconds = daysFromCivil(year, month, day) * 86_400 + hour * 3600 + minute * 60 + second - offset * 60
        return seconds * 1000 + millis
    }

    public static func parse(_ text: String) throws -> Date {
        guard let ms = parseMS(text) else { throw FWIDError.invalidDatetime }
        return Date(timeIntervalSince1970: Double(ms) / 1000)
    }

    /// Formats in UTC as `YYYY-MM-DDThh:mm:ss.mmm+00:00`.
    public static func format(_ date: Date) -> String {
        // Round to microseconds first so that a Double built from whole
        // milliseconds never floors to the millisecond before.
        let ms = Int64(((date.timeIntervalSince1970 * 1e6).rounded() / 1000).rounded(.down))
        let (year, month, day) = civilFromDays(floorDiv(ms, msPerDay))
        let rem = ms - floorDiv(ms, msPerDay) * msPerDay
        func pad(_ v: Int64, _ width: Int) -> String {
            let s = String(v)
            return String(repeating: "0", count: max(0, width - s.count)) + s
        }
        return "\(pad(year, 4))-\(pad(month, 2))-\(pad(day, 2))T\(pad(rem / 3_600_000, 2)):"
            + "\(pad(rem / 60_000 % 60, 2)):\(pad(rem / 1000 % 60, 2)).\(pad(rem % 1000, 3))+00:00"
    }
}
