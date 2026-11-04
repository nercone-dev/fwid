import { FWIDError } from "./errors.js";

/**
 * Base62 (`0-9A-Za-z`) over a big-endian arbitrary-precision integer,
 * zero-padded to a length that depends only on the byte length.
 */
export class Base62 {
  static ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";

  /** Divides the big-endian number `num[start..]` in place and returns the remainder. */
  static #divmod(num, start, divisor) {
    let rem = 0;
    for (let i = start; i < num.length; i++) {
      const cur = rem * 256 + num[i];
      num[i] = Math.floor(cur / divisor);
      rem = cur % divisor;
    }
    return rem;
  }

  static #skipZeros(num, start) {
    while (start < num.length && num[start] === 0) start++;
    return start;
  }

  /** Smallest `n` such that `62^n >= 256^size`, i.e. the digit count of the largest `size`-byte value. */
  static length(size) {
    const num = new Uint8Array(size).fill(0xff);
    let start = 0;
    let chars = 0;
    while (start < num.length) {
      Base62.#divmod(num, start, 62);
      chars++;
      start = Base62.#skipZeros(num, start);
    }
    return chars;
  }

  /** @param {Uint8Array} data @returns {string} */
  static encode(data) {
    const width = Base62.length(data.length);
    const num = Uint8Array.from(data);
    const out = new Array(width).fill(Base62.ALPHABET[0]);
    let start = Base62.#skipZeros(num, 0);
    for (let slot = width - 1; slot >= 0 && start < num.length; slot--) {
      out[slot] = Base62.ALPHABET[Base62.#divmod(num, start, 62)];
      start = Base62.#skipZeros(num, start);
    }
    return out.join("");
  }

  /** @param {string} text @returns {Uint8Array} */
  static decode(text) {
    // log2(62) is irrational, so the estimate only seeds the search and the exact length is always verified.
    const estimate = Math.floor((text.length * 5.954196310386876) / 8);
    let size = -1;
    for (let s = Math.max(estimate - 1, 0); s <= estimate + 1; s++) {
      if (Base62.length(s) === text.length) {
        size = s;
        break;
      }
    }
    if (size < 0) throw FWIDError.base62Length();
    const out = new Uint8Array(size);
    for (const ch of text) {
      const index = Base62.ALPHABET.indexOf(ch);
      if (index < 0) throw FWIDError.character(ch);
      let carry = index;
      for (let i = size - 1; i >= 0; i--) {
        const cur = out[i] * 62 + carry;
        out[i] = cur & 0xff;
        carry = cur >> 8;
      }
      if (carry !== 0) throw FWIDError.base62Range();
    }
    return out;
  }
}
