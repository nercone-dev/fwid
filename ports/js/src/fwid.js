import { Base32Crockford } from "./base32crockford.js";
import { Base32Hex } from "./base32hex.js";
import { Base62 } from "./base62.js";
import { FWIDError } from "./errors.js";

export class FWIDFormat {
  static UNFORMATTED = "Unformatted";
  static STANDARD_TEXT = "Standard Text";
  static READABLE_TEXT = "Readable Text";
  static COMPACT_TEXT = "Compact Text";

  /**
   * Detects the text format of `text`; the first format that parses wins,
   * in the order Standard, Readable, Compact.
   * @param {Uint8Array | string} arg
   */
  static detect(arg) {
    if (arg instanceof Uint8Array) return FWIDFormat.UNFORMATTED;
    if (typeof arg === "string") return FWID.parse(arg).format;
    throw FWIDError.unknownFormat();
  }
}

/**
 * A FourWord Identifier: a quarter timestamp (milliseconds since
 * 2001-01-01 00:00:00 UTC) followed by three quarters of CSPRNG output.
 */
export class FWID {
  /** The FWID epoch, 2001-01-01 00:00:00 UTC, in Unix milliseconds. */
  static EPOCH_UNIX_MS = 978307200000;
  static BITS_ALIGN = 32;

  #raw;

  /**
   * @param {Uint8Array | string | number | null} [arg] bytes, text in any
   *   format, or a bit length to generate; omitted to generate the smallest
   *   size that fits the timestamp.
   * @param {Date | null} [date] timestamp to embed when generating (default: now)
   */
  constructor(arg = null, date = null) {
    if (arg === null || arg === undefined) {
      this.#raw = FWID.generate(null, date);
    } else if (arg instanceof Uint8Array) {
      FWID.checkBits(arg.length * 8);
      this.#raw = Uint8Array.from(arg);
    } else if (typeof arg === "string") {
      this.#raw = FWID.fromText(arg).#raw;
    } else if (typeof arg === "number") {
      this.#raw = FWID.generate(arg, date);
    } else {
      throw FWIDError.type(`Unsupported argument type: ${typeof arg}`);
    }
  }

  static fromStandardText(text) {
    return new FWID(Base32Hex.decode(text));
  }

  static fromReadableText(text) {
    if (text !== text.toLowerCase()) throw FWIDError.readableCase();
    const groups = text.split("-");
    const last = groups[groups.length - 1].length;
    if (groups.slice(0, -1).some((group) => group.length !== 8) || last < 1 || last > 8) {
      throw FWIDError.readableGroups();
    }
    return new FWID(Base32Crockford.decode(groups.join("")));
  }

  static fromCompactText(text) {
    return new FWID(Base62.decode(text));
  }

  /** Parses `text` in any text format and reports which one matched. */
  static parse(text) {
    const parsers = [
      [FWIDFormat.STANDARD_TEXT, FWID.fromStandardText],
      [FWIDFormat.READABLE_TEXT, FWID.fromReadableText],
      [FWIDFormat.COMPACT_TEXT, FWID.fromCompactText],
    ];
    for (const [format, parse] of parsers) {
      try {
        return { format, id: parse(text) };
      } catch (e) {
        if (!(e instanceof FWIDError)) throw e;
      }
    }
    throw FWIDError.unknownFormat();
  }

  static fromText(text) {
    return FWID.parse(text).id;
  }

  static checkBits(bits) {
    if (!Number.isSafeInteger(bits) || bits < FWID.BITS_ALIGN || bits % FWID.BITS_ALIGN !== 0) {
      throw FWIDError.bits();
    }
  }

  /** Milliseconds from the FWID epoch to `date` (default: now). */
  static epochMS(date = null) {
    const unixMS = (date ?? new Date()).getTime();
    if (Number.isNaN(unixMS)) throw FWIDError.timeOutOfRange();
    const ms = unixMS - FWID.EPOCH_UNIX_MS;
    if (ms < 0) throw FWIDError.beforeEpoch();
    return ms;
  }

  static #bytesFor(ms) {
    return Math.max(1, Math.ceil(ms.toString(2).length / 8));
  }

  /** Smallest bit length that fits the timestamp of `date` (default: now). */
  static minBits(date = null) {
    return FWID.#bytesFor(FWID.epochMS(date)) * FWID.BITS_ALIGN;
  }

  /**
   * Generates the bytes of an FWID of `bits` bits (default: the smallest that fits).
   * @returns {Uint8Array}
   */
  static generate(bits = null, date = null) {
    const ms = FWID.epochMS(date);
    const required = FWID.#bytesFor(ms) * FWID.BITS_ALIGN;
    bits ??= required;
    FWID.checkBits(bits);
    if (bits < required) throw FWIDError.timestampTooLarge(bits, required);
    const raw = new Uint8Array(bits / 8);
    const timestampLength = raw.length / 4;
    for (let i = timestampLength - 1, value = ms; i >= 0 && value > 0; i--) {
      raw[i] = value % 256;
      value = Math.floor(value / 256);
    }
    // getRandomValues accepts at most 65536 bytes per call.
    for (let i = timestampLength; i < raw.length; i += 65536) {
      globalThis.crypto.getRandomValues(raw.subarray(i, Math.min(i + 65536, raw.length)));
    }
    return raw;
  }

  /** A copy of the bytes. */
  get raw() {
    return Uint8Array.from(this.#raw);
  }

  get bits() {
    return this.#raw.length * 8;
  }

  get bitsTimestamp() {
    return this.bits / 4;
  }

  get bitsRandom() {
    return (this.bits / 4) * 3;
  }

  /** Milliseconds from the FWID epoch stored in the timestamp field. */
  get timestampMS() {
    let value = 0n;
    for (const byte of this.#raw.subarray(0, this.#raw.length / 4)) value = (value << 8n) | BigInt(byte);
    if (value > BigInt(Number.MAX_SAFE_INTEGER)) throw FWIDError.timestampOverflow();
    return Number(value);
  }

  /** @returns {Date} */
  get timestamp() {
    const date = new Date(FWID.EPOCH_UNIX_MS + this.timestampMS);
    if (Number.isNaN(date.getTime())) throw FWIDError.timeOutOfRange();
    return date;
  }

  text(format = FWIDFormat.STANDARD_TEXT) {
    switch (format) {
      case FWIDFormat.STANDARD_TEXT:
        return this.standardText;
      case FWIDFormat.READABLE_TEXT:
        return this.readableText;
      case FWIDFormat.COMPACT_TEXT:
        return this.compactText;
      default:
        throw FWIDError.notTextFormat(String(format));
    }
  }

  get standardText() {
    return Base32Hex.encode(this.#raw);
  }

  get readableText() {
    return Base32Crockford.encode(this.#raw).toLowerCase().match(/.{1,8}/g).join("-");
  }

  get compactText() {
    return Base62.encode(this.#raw);
  }

  /** Orders by the raw bytes, which is time order for equal bit lengths. */
  static compare(a, b) {
    const [x, y] = [a.#raw, b.#raw];
    for (let i = 0; i < Math.min(x.length, y.length); i++) {
      if (x[i] !== y[i]) return x[i] < y[i] ? -1 : 1;
    }
    return Math.sign(x.length - y.length);
  }

  equals(other) {
    return other instanceof FWID && FWID.compare(this, other) === 0;
  }

  toString() {
    return this.text();
  }

  toJSON() {
    return this.text();
  }

  [Symbol.for("nodejs.util.inspect.custom")]() {
    return `FWID(${JSON.stringify(this.standardText)})`;
  }
}
