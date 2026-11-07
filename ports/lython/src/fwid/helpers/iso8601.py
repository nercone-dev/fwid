class ISO8601:
    """Extended-format ISO 8601 datetimes with millisecond precision.

    A point in time is an int: milliseconds since 1970-01-01T00:00:00Z (UTC).

    Accepted input: YYYY-MM-DD optionally followed by 'T', 't' or a space and
    hh:mm[:ss[.fraction]], then optionally 'Z' or an offset +hh[:mm] / +hhmm.
    Values without an offset are UTC. Digits beyond milliseconds are truncated.
    """

    MS_PER_DAY: int = 86400000

    @staticmethod
    def is_leap_year(year: int) -> bool:
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

    @staticmethod
    def days_in_month(year: int, month: int) -> int:
        if month == 2:
            return 29 if ISO8601.is_leap_year(year) else 28
        if month == 4 or month == 6 or month == 9 or month == 11:
            return 30
        return 31

    @staticmethod
    def days_from_civil(year: int, month: int, day: int) -> int:
        """Days from 1970-01-01 to the given proleptic Gregorian date."""
        if month <= 2:
            year -= 1
        era = year // 400
        yoe = year - era * 400
        shifted = month - 3 if month > 2 else month + 9
        doy = (153 * shifted + 2) // 5 + day - 1
        doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
        return era * 146097 + doe - 719468

    @staticmethod
    def civil_from_days(days: int) -> tuple[int, int, int]:
        """The proleptic Gregorian (year, month, day) that is the given number of days after 1970-01-01."""
        z = days + 719468
        era = z // 146097
        doe = z - era * 146097
        yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
        year = yoe + era * 400
        doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
        mp = (5 * doy + 2) // 153
        day = doy - (153 * mp + 2) // 5 + 1
        month = mp + 3 if mp < 10 else mp - 9
        if month <= 2:
            year += 1
        return (year, month, day)

    @staticmethod
    def invalid(text: str) -> ValueError:
        return ValueError("invalid ISO 8601 datetime: " + repr(text))

    @staticmethod
    def digits(text: str, pos: int, count: int) -> int:
        """The value of exactly count ASCII digits at pos, or -1."""
        if pos + count > len(text):
            return -1
        value = 0
        for i in range(pos, pos + count):
            code = ord(text[i])
            if code < 48 or code > 57:
                return -1
            value = value * 10 + (code - 48)
        return value

    @staticmethod
    def parse(text: str) -> int:
        """Parse text into milliseconds since 1970-01-01T00:00:00Z. Raises ValueError."""
        n = len(text)
        year = ISO8601.digits(text, 0, 4)
        month = ISO8601.digits(text, 5, 2)
        day = ISO8601.digits(text, 8, 2)
        if year < 0 or month < 1 or month > 12 or day < 1 or n < 10 or text[4] != "-" or text[7] != "-":
            raise ISO8601.invalid(text)
        if day > ISO8601.days_in_month(year, month):
            raise ISO8601.invalid(text)
        pos = 10
        hour = 0
        minute = 0
        second = 0
        millis = 0
        offset = 0
        if pos < n:
            if text[pos] != "T" and text[pos] != "t" and text[pos] != " ":
                raise ISO8601.invalid(text)
            pos += 1
            hour = ISO8601.digits(text, pos, 2)
            minute = ISO8601.digits(text, pos + 3, 2)
            if hour < 0 or minute < 0 or pos + 2 >= n or text[pos + 2] != ":":
                raise ISO8601.invalid(text)
            pos += 5
            if pos < n and text[pos] == ":":
                second = ISO8601.digits(text, pos + 1, 2)
                if second < 0:
                    raise ISO8601.invalid(text)
                pos += 3
                if pos < n and (text[pos] == "." or text[pos] == ","):
                    pos += 1
                    start = pos
                    while pos < n and 48 <= ord(text[pos]) <= 57:
                        pos += 1
                    if pos == start:
                        raise ISO8601.invalid(text)
                    for i in range(3):
                        d = ord(text[start + i]) - 48 if start + i < pos else 0
                        millis = millis * 10 + d
            if hour > 23 or minute > 59 or second > 59:
                raise ISO8601.invalid(text)
            if pos == n:
                pass
            elif text[pos] == "Z" or text[pos] == "z":
                pos += 1
            elif text[pos] == "+" or text[pos] == "-":
                sign = -1 if text[pos] == "-" else 1
                pos += 1
                oh = ISO8601.digits(text, pos, 2)
                if oh < 0:
                    raise ISO8601.invalid(text)
                pos += 2
                if pos < n and text[pos] == ":":
                    pos += 1
                om = 0
                if pos < n:
                    om = ISO8601.digits(text, pos, 2)
                    if om < 0:
                        raise ISO8601.invalid(text)
                    pos += 2
                if oh > 23 or om > 59:
                    raise ISO8601.invalid(text)
                offset = sign * (oh * 60 + om)
            else:
                raise ISO8601.invalid(text)
        if pos != n:
            raise ISO8601.invalid(text)
        days = ISO8601.days_from_civil(year, month, day)
        return days * ISO8601.MS_PER_DAY + ((hour * 60 + minute - offset) * 60 + second) * 1000 + millis

    @staticmethod
    def format(unix_ms: int) -> str:
        """Format milliseconds since 1970-01-01T00:00:00Z as YYYY-MM-DDThh:mm:ss.mmm+00:00."""
        days = unix_ms // ISO8601.MS_PER_DAY
        rest = unix_ms - days * ISO8601.MS_PER_DAY
        year, month, day = ISO8601.civil_from_days(days)
        sign = "-" if year < 0 else ""
        return (
            sign + str(abs(year)).zfill(4) + "-" + str(month).zfill(2) + "-" + str(day).zfill(2)
            + "T" + str(rest // 3600000).zfill(2) + ":" + str(rest // 60000 % 60).zfill(2)
            + ":" + str(rest // 1000 % 60).zfill(2) + "." + str(rest % 1000).zfill(3) + "+00:00"
        )
