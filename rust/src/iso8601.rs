use std::time::{Duration, SystemTime, UNIX_EPOCH};

use crate::error::Error;

const MS_PER_DAY: i64 = 86_400_000;

/// Extended-format ISO 8601 datetimes with millisecond precision.
///
/// Accepted input: `YYYY-MM-DD` optionally followed by `T`, `t` or a space and
/// `hh:mm[:ss[.fraction]]`, then optionally `Z` or an offset `+hh[:mm]` /
/// `+hhmm`. Values without an offset are UTC. Digits beyond milliseconds are
/// truncated.
pub struct ISO8601;

impl ISO8601 {
    fn is_leap(year: i64) -> bool {
        year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)
    }

    fn days_in_month(year: i64, month: i64) -> i64 {
        match month {
            2 if Self::is_leap(year) => 29,
            2 => 28,
            4 | 6 | 9 | 11 => 30,
            _ => 31,
        }
    }

    /// Days since 1970-01-01 of a proleptic Gregorian date.
    fn days_from_civil(year: i64, month: i64, day: i64) -> i64 {
        let y = if month <= 2 { year - 1 } else { year };
        let era = y.div_euclid(400);
        let yoe = y - era * 400;
        let doy = (153 * ((month + 9) % 12) + 2) / 5 + day - 1;
        let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
        era * 146_097 + doe - 719_468
    }

    fn civil_from_days(days: i64) -> (i64, i64, i64) {
        let z = days + 719_468;
        let era = z.div_euclid(146_097);
        let doe = z - era * 146_097;
        let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
        let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
        let mp = (5 * doy + 2) / 153;
        let day = doy - (153 * mp + 2) / 5 + 1;
        let month = if mp < 10 { mp + 3 } else { mp - 9 };
        let year = yoe + era * 400 + i64::from(month <= 2);
        (year, month, day)
    }

    fn digits(text: &[u8], pos: &mut usize, count: usize) -> Option<i64> {
        let slice = text.get(*pos..*pos + count)?;
        if !slice.iter().all(u8::is_ascii_digit) {
            return None;
        }
        *pos += count;
        Some(slice.iter().fold(0, |acc, &d| acc * 10 + i64::from(d - b'0')))
    }

    fn expect(text: &[u8], pos: &mut usize, byte: u8) -> Option<()> {
        if text.get(*pos) == Some(&byte) {
            *pos += 1;
            Some(())
        } else {
            None
        }
    }

    /// Returns Unix milliseconds.
    fn parse_ms(text: &str) -> Option<i64> {
        let t = text.as_bytes();
        let mut pos = 0;
        let year = Self::digits(t, &mut pos, 4)?;
        Self::expect(t, &mut pos, b'-')?;
        let month = Self::digits(t, &mut pos, 2)?;
        Self::expect(t, &mut pos, b'-')?;
        let day = Self::digits(t, &mut pos, 2)?;
        if !(1..=12).contains(&month) || day < 1 || day > Self::days_in_month(year, month) {
            return None;
        }
        let (mut hour, mut minute, mut second, mut millis, mut offset) = (0, 0, 0, 0, 0);
        if pos < t.len() {
            if !matches!(t[pos], b'T' | b't' | b' ') {
                return None;
            }
            pos += 1;
            hour = Self::digits(t, &mut pos, 2)?;
            Self::expect(t, &mut pos, b':')?;
            minute = Self::digits(t, &mut pos, 2)?;
            if Self::expect(t, &mut pos, b':').is_some() {
                second = Self::digits(t, &mut pos, 2)?;
                if matches!(t.get(pos), Some(b'.' | b',')) {
                    pos += 1;
                    let start = pos;
                    while pos < t.len() && t[pos].is_ascii_digit() {
                        pos += 1;
                    }
                    if pos == start {
                        return None;
                    }
                    millis = t[start..pos]
                        .iter()
                        .chain(std::iter::repeat(&b'0'))
                        .take(3)
                        .fold(0, |acc, &d| acc * 10 + i64::from(d - b'0'));
                }
            }
            if hour > 23 || minute > 59 || second > 59 {
                return None;
            }
            match t.get(pos) {
                None => {}
                Some(b'Z' | b'z') => pos += 1,
                Some(&sign @ (b'+' | b'-')) => {
                    pos += 1;
                    let oh = Self::digits(t, &mut pos, 2)?;
                    let _ = Self::expect(t, &mut pos, b':');
                    let om = if pos < t.len() { Self::digits(t, &mut pos, 2)? } else { 0 };
                    if oh > 23 || om > 59 {
                        return None;
                    }
                    offset = (oh * 60 + om) * if sign == b'-' { -1 } else { 1 };
                }
                Some(_) => return None,
            }
        }
        if pos != t.len() {
            return None;
        }
        let seconds = Self::days_from_civil(year, month, day) * 86_400
            + hour * 3600
            + minute * 60
            + second
            - offset * 60;
        Some(seconds * 1000 + millis)
    }

    pub fn parse(text: &str) -> Result<SystemTime, Error> {
        let ms = Self::parse_ms(text).ok_or(Error::InvalidDatetime)?;
        let magnitude = Duration::from_millis(ms.unsigned_abs());
        if ms >= 0 {
            UNIX_EPOCH.checked_add(magnitude)
        } else {
            UNIX_EPOCH.checked_sub(magnitude)
        }
        .ok_or(Error::TimeOutOfRange)
    }

    /// Formats in UTC as `YYYY-MM-DDThh:mm:ss.mmm+00:00`.
    pub fn format(time: SystemTime) -> String {
        let ms = match time.duration_since(UNIX_EPOCH) {
            Ok(d) => d.as_millis() as i64,
            Err(e) => -(e.duration().as_nanos().div_ceil(1_000_000) as i64),
        };
        let (year, month, day) = Self::civil_from_days(ms.div_euclid(MS_PER_DAY));
        let rem = ms.rem_euclid(MS_PER_DAY);
        format!(
            "{year:04}-{month:02}-{day:02}T{:02}:{:02}:{:02}.{:03}+00:00",
            rem / 3_600_000,
            rem / 60_000 % 60,
            rem / 1000 % 60,
            rem % 1000
        )
    }
}
