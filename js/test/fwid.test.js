import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { Base32Hex, Base62, FWID, FWIDError, FWIDFormat, ISO8601 } from "../src/index.js";
import { CLI } from "../src/cli.js";

const rows = (name) =>
  readFileSync(new URL(`../../testdata/${name}`, import.meta.url), "utf8")
    .split("\n")
    .filter((line) => line !== "" && !line.startsWith("#"))
    .map((line) => line.split("\t"));

const unhex = (hex) => Uint8Array.from(hex.match(/../g) ?? [], (h) => parseInt(h, 16));
const at = (unixMS) => new Date(unixMS);
const code = (c) => (e) => e instanceof FWIDError && e.code === c;

test("shared vectors", () => {
  const vectors = rows("vectors.tsv");
  assert.ok(vectors.length > 0);
  for (const [hex, standard, readable, compact, ms] of vectors) {
    const raw = unhex(hex);
    const id = new FWID(raw);
    assert.equal(id.standardText, standard);
    assert.equal(id.readableText, readable);
    assert.equal(id.compactText, compact);
    if (ms !== "-") assert.equal(String(id.timestampMS), ms);
    for (const [text, format] of [
      [standard, FWIDFormat.STANDARD_TEXT],
      [readable, FWIDFormat.READABLE_TEXT],
      [compact, FWIDFormat.COMPACT_TEXT],
    ]) {
      const parsed = FWID.parse(text);
      assert.equal(parsed.format, format, text);
      assert.deepEqual(parsed.id.raw, raw, text);
      assert.equal(FWIDFormat.detect(text), format);
    }
  }
});

test("invalid texts are rejected", () => {
  assert.throws(() => FWID.fromText(""), FWIDError);
  for (const [text] of rows("invalid.tsv")) {
    assert.throws(() => new FWID(text), FWIDError, text);
    assert.throws(() => FWIDFormat.detect(text), code("unknownFormat"), text);
  }
});

// RFC 4648 section 10, with '=' replaced by 'Z'.
test("Base32Hex RFC 4648 vectors", () => {
  for (const [plain, encoded] of [
    ["", ""], ["f", "COZZZZZZ"], ["fo", "CPNGZZZZ"], ["foo", "CPNMUZZZ"],
    ["foob", "CPNMUOGZ"], ["fooba", "CPNMUOJ1"], ["foobar", "CPNMUOJ1E8ZZZZZZ"],
  ]) {
    const bytes = new TextEncoder().encode(plain);
    assert.equal(Base32Hex.encode(bytes), encoded);
    assert.deepEqual(Base32Hex.decode(encoded), bytes);
  }
});

test("Base32Hex rejects malformed input", () => {
  for (const text of ["C", "COZZZZZ", "CZZZZZZZ", "COZZZZZZCOZZZZZZ", "COzzzzzz", "C1ZZZZZZ", "CPNMUOJé"]) {
    assert.throws(() => Base32Hex.decode(text), FWIDError, text);
  }
});

test("Base62 lengths and round trip", () => {
  assert.deepEqual([0, 1, 4, 16, 32].map(Base62.length), [0, 2, 6, 22, 43]);
  for (let size = 0; size < 40; size++) {
    const data = Uint8Array.from({ length: size }, (_, i) => (i * 37 + 11) & 255);
    const text = Base62.encode(data);
    assert.equal(text.length, Base62.length(size));
    assert.deepEqual(Base62.decode(text), data);
  }
});

test("Base62 rejects malformed input", () => {
  for (const text of ["0", "zzzzzz", "00000-", "00000é"]) {
    assert.throws(() => Base62.decode(text), FWIDError, text);
  }
});

test("generate layout", () => {
  const t = at(1_704_067_200_000);
  const ms = 725_760_000_000;
  assert.equal(FWID.epochMS(t), ms);
  assert.equal(FWID.minBits(t), 160);
  for (let bits = 160; bits <= 512; bits += 32) {
    const id = new FWID(bits, t);
    assert.equal(id.bits, bits);
    assert.equal(id.bitsTimestamp, bits / 4);
    assert.equal(id.bitsRandom, (bits / 4) * 3);
    assert.equal(id.timestampMS, ms);
    assert.equal(id.timestamp.getTime(), t.getTime());
    const field = id.raw.subarray(0, bits / 32);
    assert.deepEqual(field.subarray(field.length - 5), Uint8Array.of(0xa8, 0xfa, 0xaa, 0xc0, 0x00));
    assert.ok(field.subarray(0, field.length - 5).every((b) => b === 0));
  }
  assert.equal(new FWID(131072 * 8, t).bits, 131072 * 8); // random part larger than one getRandomValues call
});

test("generate rejects bad sizes", () => {
  const t = at(1_704_067_200_000);
  for (const bits of [0, 31, 33, 161, -32, 1.5, NaN]) {
    assert.throws(() => new FWID(bits, t), code("bits"), String(bits));
  }
  assert.throws(() => new FWID(128, t), code("timestampTooLarge"));
  assert.throws(() => new FWID(null, at(978_307_199_999)), code("beforeEpoch"));
  assert.doesNotThrow(() => new FWID(null, at(978_307_200_000)));
  assert.throws(() => new FWID(new Uint8Array(3)), code("bits"));
  assert.throws(() => new FWID(new Uint8Array(0)), code("bits"));
  assert.throws(() => new FWID({}), code("type"));
});

test("ids sort by time", () => {
  const a = new FWID(256, at(1_000_000_000_000));
  const b = new FWID(256, at(1_000_000_000_001));
  assert.equal(FWID.compare(a, b), -1);
  assert.ok(a.standardText < b.standardText);
  assert.ok(!new FWID().equals(new FWID()));
  assert.ok(a.equals(new FWID(a.standardText)));
});

test("ISO 8601 parse and format", () => {
  for (const [text, unixMS] of [
    ["2024-01-01T00:00:00Z", 1_704_067_200_000],
    ["2024-01-01", 1_704_067_200_000],
    ["2024-01-01 00:00", 1_704_067_200_000],
    ["2024-01-01T09:00:00+09:00", 1_704_067_200_000],
    ["2024-01-01T09:00:00+0900", 1_704_067_200_000],
    ["2023-12-31T19:00:00-05", 1_704_067_200_000],
    ["2024-02-29T12:34:56.789123Z", 1_709_210_096_789],
    ["2024-02-29T12:34:56.5", 1_709_210_096_500],
    ["1970-01-01T00:00:00Z", 0],
  ]) {
    assert.equal(ISO8601.parse(text).getTime(), unixMS, text);
  }
  assert.equal(ISO8601.format(at(1_709_210_096_789)), "2024-02-29T12:34:56.789+00:00");
  for (const text of [
    "", "2024", "2024-13-01", "2023-02-29", "2024-04-31", "2024-01-01T24:00", "2024-01-01T00:60",
    "2024-01-01T00:00:60", "2024-01-01T00", "2024-01-01T00:00:00.", "2024-01-01T00:00:00+24:00",
    "2024-01-01T00:00:00Zx", "2024-01-01Z", "24-01-01", "2024-01-01T00:00:00 +09:00", "2024-01-01\n",
  ]) {
    assert.throws(() => ISO8601.parse(text), code("invalidDatetime"), JSON.stringify(text));
  }
});

test("text rejects Unformatted", () => {
  const id = new FWID();
  assert.throws(() => id.text(FWIDFormat.UNFORMATTED), code("notTextFormat"));
  assert.equal(id.text(FWIDFormat.STANDARD_TEXT), String(id));
});

const run = (args, stdin = "") => {
  let out = "";
  let err = "";
  const status = CLI.run(args, { readStdin: () => stdin, out: (s) => (out += s), err: (s) => (err += s) });
  return { status, out, err };
};

test("CLI generate and inspect", () => {
  const g = run(["g", "-t", "2024-01-01T00:00:00Z", "-b", "256", "-f", "compact", "-n", "3"]);
  assert.equal(g.status, 0);
  const lines = g.out.trim().split("\n");
  assert.equal(lines.length, 3);
  const i = run(["i", lines[0]]);
  assert.equal(i.status, 0);
  assert.match(i.out, /^Format:     Compact Text\n/);
  assert.ok(i.out.includes("Bits:       256 (timestamp 64, random 192)\n"));
  assert.ok(i.out.includes("Timestamp:  2024-01-01T00:00:00.000+00:00 (725760000000 ms)\n"));
  const s = run(["inspect"], `${lines[1]}  \n\nbogus\n${lines[2]}\n`);
  assert.equal(s.status, 1);
  assert.ok(s.err.startsWith("fwid: bogus: "));
  assert.equal(s.out.split("Format:").length, 3);
});

test("CLI usage errors", () => {
  for (const args of [[], ["x"], ["g", "-b", "0"], ["g", "-b", "x"], ["g", "-f", "nope"], ["g", "-t", "yesterday"], ["g", "-n"], ["g", "--zzz"]]) {
    assert.equal(run(args).status, 2, args.join(" "));
  }
  assert.equal(run(["g", "-b", "128"]).status, 1);
  assert.equal(run(["-h"]).status, 0);
});
