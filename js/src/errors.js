/** Every failure the FWID library reports. `code` is a stable machine-readable name. */
export class FWIDError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "FWIDError";
    this.code = code;
  }

  static bits() {
    return new FWIDError("bits", "Bits must be a positive multiple of 32");
  }
  static timestampTooLarge(bits, required) {
    return new FWIDError("timestampTooLarge", `${bits} bits is too small for this timestamp (need at least ${required})`);
  }
  static beforeEpoch() {
    return new FWIDError("beforeEpoch", "datetime must not be before the FWID epoch (2001-01-01 00:00:00 UTC)");
  }
  static timestampOverflow() {
    return new FWIDError("timestampOverflow", "timestamp does not fit in 53 bits");
  }
  static timeOutOfRange() {
    return new FWIDError("timeOutOfRange", "datetime is out of range");
  }
  static invalidDatetime() {
    return new FWIDError("invalidDatetime", "invalid ISO 8601 datetime");
  }
  static unknownFormat() {
    return new FWIDError("unknownFormat", "Unknown Format");
  }
  static notTextFormat(name) {
    return new FWIDError("notTextFormat", `Format '${name}' is not Text-based Format`);
  }
  static base32HexLength() {
    return new FWIDError("base32HexLength", "Base32Hex length must be a multiple of 8");
  }
  static base32HexPaddingPosition() {
    return new FWIDError("base32HexPaddingPosition", "Padding is only allowed in the last block");
  }
  static base32HexPaddingLength() {
    return new FWIDError("base32HexPaddingLength", "Invalid padding length");
  }
  static base32HexTrailingBits() {
    return new FWIDError("base32HexTrailingBits", "Non-zero trailing bits");
  }
  static base62Length() {
    return new FWIDError("base62Length", "Invalid Base62 length");
  }
  static base62Range() {
    return new FWIDError("base62Range", "Value out of range");
  }
  static character(char) {
    return new FWIDError("character", `Invalid character: ${JSON.stringify(char)}`);
  }
  static readableCase() {
    return new FWIDError("readableCase", "Readable Text must be lowercase");
  }
  static readableGroups() {
    return new FWIDError("readableGroups", "Readable Text must be split into groups of 8 characters");
  }
  static type(message) {
    return new FWIDError("type", message);
  }
}
