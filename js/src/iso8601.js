import { FWIDError } from "./errors.js";

/**
 * Extended-format ISO 8601 datetimes with millisecond precision.
 *
 * Accepted input: `YYYY-MM-DD` optionally followed by `T`, `t` or a space and
 * `hh:mm[:ss[.fraction]]`, then optionally `Z` or an offset `+hh[:mm]` /
 * `+hhmm`. Values without an offset are UTC. Digits beyond milliseconds are
 * truncated.
 */
export class ISO8601 {
  static #isLeap(year) {
    return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  }

  static #daysInMonth(year, month) {
    if (month === 2) return ISO8601.#isLeap(year) ? 29 : 28;
    return [4, 6, 9, 11].includes(month) ? 30 : 31;
  }

  /** Days since 1970-01-01 of a proleptic Gregorian date. */
  static #daysFromCivil(year, month, day) {
    const y = month <= 2 ? year - 1 : year;
    const era = Math.floor(y / 400);
    const yoe = y - era * 400;
    const doy = Math.floor((153 * ((month + 9) % 12) + 2) / 5) + day - 1;
    const doe = yoe * 365 + Math.floor(yoe / 4) - Math.floor(yoe / 100) + doy;
    return era * 146097 + doe - 719468;
  }

  static #civilFromDays(days) {
    const z = days + 719468;
    const era = Math.floor(z / 146097);
    const doe = z - era * 146097;
    const yoe = Math.floor((doe - Math.floor(doe / 1460) + Math.floor(doe / 36524) - Math.floor(doe / 146096)) / 365);
    const doy = doe - (365 * yoe + Math.floor(yoe / 4) - Math.floor(yoe / 100));
    const mp = Math.floor((5 * doy + 2) / 153);
    const day = doy - Math.floor((153 * mp + 2) / 5) + 1;
    const month = mp < 10 ? mp + 3 : mp - 9;
    return { year: yoe + era * 400 + (month <= 2 ? 1 : 0), month, day };
  }

  /** Returns the Unix milliseconds of `text`, or null if it is malformed. */
  static #parseMS(text) {
    const m = /^(\d{4})-(\d{2})-(\d{2})(?:[Tt ](\d{2}):(\d{2})(?::(\d{2})(?:[.,](\d+))?)?(?:([Zz])|([+-])(\d{2})(?::?(\d{2}))?)?)?$/.exec(text);
    if (m === null) return null;
    const [year, month, day] = [m[1], m[2], m[3]].map(Number);
    const hour = Number(m[4] ?? 0);
    const minute = Number(m[5] ?? 0);
    const second = Number(m[6] ?? 0);
    const millis = Number((m[7] ?? "").slice(0, 3).padEnd(3, "0"));
    const offsetHour = Number(m[10] ?? 0);
    const offsetMinute = Number(m[11] ?? 0);
    if (month < 1 || month > 12 || day < 1 || day > ISO8601.#daysInMonth(year, month)) return null;
    if (hour > 23 || minute > 59 || second > 59 || offsetHour > 23 || offsetMinute > 59) return null;
    const offset = (m[9] === "-" ? -1 : 1) * (offsetHour * 60 + offsetMinute);
    const seconds = ISO8601.#daysFromCivil(year, month, day) * 86400 + hour * 3600 + minute * 60 + second - offset * 60;
    return seconds * 1000 + millis;
  }

  /** @param {string} text @returns {Date} */
  static parse(text) {
    if (typeof text !== "string") throw FWIDError.invalidDatetime();
    const ms = ISO8601.#parseMS(text);
    if (ms === null) throw FWIDError.invalidDatetime();
    const date = new Date(ms);
    if (Number.isNaN(date.getTime())) throw FWIDError.timeOutOfRange();
    return date;
  }

  /** Formats in UTC as `YYYY-MM-DDThh:mm:ss.mmm+00:00`. @param {Date} date */
  static format(date) {
    const ms = date.getTime();
    if (Number.isNaN(ms)) throw FWIDError.timeOutOfRange();
    const days = Math.floor(ms / 86400000);
    const rem = ms - days * 86400000;
    const { year, month, day } = ISO8601.#civilFromDays(days);
    const pad = (v, width) => String(v).padStart(width, "0");
    return (
      `${pad(year, 4)}-${pad(month, 2)}-${pad(day, 2)}T${pad(Math.floor(rem / 3600000), 2)}:` +
      `${pad(Math.floor(rem / 60000) % 60, 2)}:${pad(Math.floor(rem / 1000) % 60, 2)}.${pad(rem % 1000, 3)}+00:00`
    );
  }
}
