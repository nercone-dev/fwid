import { FWIDError } from "./errors.js";

/**
 * Crockford's Base32 without check symbols and without padding.
 * Encoding emits uppercase symbols. Decoding is case-insensitive and maps
 * the look-alike symbols I and L to 1 and O to 0, as Crockford specifies.
 */
export class Base32Crockford {
  static ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";
  static ALIASES = { I: "1", L: "1", O: "0" };

  /** Bytes carried by a block with this many characters. */
  static #bytesFromChars(chars) {
    return { 8: 5, 7: 4, 5: 3, 4: 2, 2: 1 }[chars];
  }

  /** @param {Uint8Array} data @returns {string} */
  static encode(data) {
    let out = "";
    for (let i = 0; i < data.length; i += 5) {
      const n = Math.min(5, data.length - i);
      let value = 0; // at most 40 bits, exact in a double
      for (let j = 0; j < 5; j++) value = value * 256 + (j < n ? data[i + j] : 0);
      const chars = Math.ceil((n * 8) / 5);
      for (let j = 0; j < chars; j++) out += Base32Crockford.ALPHABET[Math.floor(value / 2 ** (35 - 5 * j)) % 32];
    }
    return out;
  }

  /** @param {string} text @returns {Uint8Array} */
  static decode(text) {
    text = text.toUpperCase();
    const out = new Uint8Array(Math.ceil(text.length / 8) * 5);
    let length = 0;
    for (let i = 0; i < text.length; i += 8) {
      const block = text.slice(i, i + 8);
      const n = Base32Crockford.#bytesFromChars(block.length);
      if (n === undefined) throw FWIDError.base32CrockfordLength();
      let value = 0;
      for (const ch of block) {
        const index = Base32Crockford.ALPHABET.indexOf(Base32Crockford.ALIASES[ch] ?? ch);
        if (index < 0) throw FWIDError.character(ch);
        value = value * 32 + index;
      }
      const extra = block.length * 5 - n * 8;
      const unit = 2 ** extra;
      if (value % unit !== 0) throw FWIDError.base32CrockfordTrailingBits();
      value /= unit;
      for (let j = n - 1; j >= 0; j--) {
        out[length + j] = value % 256;
        value = Math.floor(value / 256);
      }
      length += n;
    }
    return out.subarray(0, length);
  }
}
