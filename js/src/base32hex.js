import { FWIDError } from "./errors.js";

/** Base32 Hex (RFC 4648 section 7) with `Z` as the padding character. */
export class Base32Hex {
  static ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUV";
  static PAD = "Z";

  /** Bytes carried by a block with this many non-padding characters. */
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
      for (let j = 0; j < chars; j++) out += Base32Hex.ALPHABET[Math.floor(value / 2 ** (35 - 5 * j)) % 32];
      out += Base32Hex.PAD.repeat(8 - chars);
    }
    return out;
  }

  /** @param {string} text @returns {Uint8Array} */
  static decode(text) {
    if (text.length % 8 !== 0) throw FWIDError.base32HexLength();
    const blocks = text.length / 8;
    const out = new Uint8Array(blocks * 5);
    let length = 0;
    for (let b = 0; b < blocks; b++) {
      const block = text.slice(b * 8, (b + 1) * 8);
      let bodyLength = 8;
      while (bodyLength > 0 && block[bodyLength - 1] === Base32Hex.PAD) bodyLength--;
      if (bodyLength !== 8 && b !== blocks - 1) throw FWIDError.base32HexPaddingPosition();
      const n = Base32Hex.#bytesFromChars(bodyLength);
      if (n === undefined) throw FWIDError.base32HexPaddingLength();
      let value = 0;
      for (const ch of block.slice(0, bodyLength)) {
        const index = Base32Hex.ALPHABET.indexOf(ch);
        if (index < 0) throw FWIDError.character(ch);
        value = value * 32 + index;
      }
      const extra = bodyLength * 5 - n * 8;
      const unit = 2 ** extra;
      if (value % unit !== 0) throw FWIDError.base32HexTrailingBits();
      value /= unit;
      for (let i = n - 1; i >= 0; i--) {
        out[length + i] = value % 256;
        value = Math.floor(value / 256);
      }
      length += n;
    }
    return out.subarray(0, length);
  }
}
