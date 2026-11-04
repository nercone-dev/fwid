#!/usr/bin/env node
import { readFileSync, writeSync } from "node:fs";

import { CLI } from "../src/cli.js";

/** Writes all of `text` to a file descriptor, retrying on EAGAIN from non-blocking pipes. */
function write(fd, text) {
  const data = Buffer.from(text);
  let offset = 0;
  while (offset < data.length) {
    try {
      offset += writeSync(fd, data, offset);
    } catch (e) {
      if (e.code === "EAGAIN") continue;
      if (e.code === "EPIPE") process.exit(1);
      throw e;
    }
  }
}

process.exitCode = CLI.run(process.argv.slice(2), {
  readStdin: () => readFileSync(0, "utf8"),
  out: (text) => write(1, text),
  err: (text) => write(2, text),
});
