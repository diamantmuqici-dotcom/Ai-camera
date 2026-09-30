#!/usr/bin/env node
/**
 * Stages the PWA into ./www so Capacitor has a valid, self-contained webDir.
 *
 * Why this exists:
 *   Capacitor rejects "." / "./" / "" as webDir, so the repository root cannot be
 *   handed to `cap sync` directly. Staging also keeps native projects, tooling and
 *   docs out of the shipped Android assets.
 *
 * Usage:
 *   node scripts/build-web.mjs [--out www] [--quiet]
 */

import { cp, mkdir, readdir, readFile, rm, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

const args = process.argv.slice(2);
const flagValue = (name, fallback) => {
  const i = args.indexOf(`--${name}`);
  return i !== -1 && args[i + 1] ? args[i + 1] : fallback;
};
const OUT_NAME = flagValue("out", "www");
const QUIET = args.includes("--quiet");
const OUT_DIR = path.join(ROOT, OUT_NAME);

/** Never ship these to the device. */
const EXCLUDED = new Set([
  ".git",
  ".github",
  ".gitignore",
  ".gitattributes",
  ".gitmodules",
  ".vscode",
  ".idea",
  ".cache",
  ".DS_Store",
  "Thumbs.db",
  "node_modules",
  "android",
  "ios",
  "www",
  "dist",
  "build",
  "coverage",
  "scripts",
  "package-lock.json",
  "npm-debug.log",
]);

/** Docs and tooling stay in git but are not runtime assets. */
const EXCLUDED_EXT = new Set([".md", ".map", ".log", ".tmp"]);

const log = (...m) => {
  if (!QUIET) console.log("[build-web]", ...m);
};

async function isDirectory(p) {
  try {
    return (await stat(p)).isDirectory();
  } catch {
    return false;
  }
}

/** Files listed in the service worker cache must exist or offline mode breaks. */
async function serviceWorkerFiles() {
  const swPath = path.join(ROOT, "service-worker.js");
  let source;
  try {
    source = await readFile(swPath, "utf8");
  } catch {
    return null;
  }
  const match = source.match(/const\s+FILES\s*=\s*\[([\s\S]*?)\]/);
  if (!match) return null;
  return match[1]
    .split(",")
    .map((entry) => entry.trim().replace(/^["'`]|["'`]$/g, ""))
    .filter(Boolean);
}

async function verifyServiceWorkerAssets() {
  const entries = await serviceWorkerFiles();
  if (!entries) {
    log("service-worker.js has no FILES list; skipping asset verification");
    return;
  }
  const missing = [];
  for (const entry of entries) {
    const rel = entry.replace(/^\.\//, "");
    if (rel === "" || rel === ".") continue; // directory index
    const target = path.join(OUT_DIR, rel);
    try {
      await stat(target);
    } catch {
      missing.push(entry);
    }
  }
  if (missing.length) {
    console.error(
      `[build-web] service-worker.js caches ${
        missing.length
      } file(s) missing from ${OUT_NAME}/:\n  ${missing.join("\n  ")}`
    );
    process.exit(1);
  }
  log(`verified ${entries.length} service worker assets`);
}

async function main() {
  await rm(OUT_DIR, { recursive: true, force: true });
  await mkdir(OUT_DIR, { recursive: true });

  const entries = (await readdir(ROOT, { withFileTypes: true })).filter(
    (entry) =>
      !EXCLUDED.has(entry.name) && !EXCLUDED_EXT.has(path.extname(entry.name))
  );

  let copied = 0;
  for (const entry of entries) {
    const src = path.join(ROOT, entry.name);
    const dest = path.join(OUT_DIR, entry.name);
    await cp(src, dest, { recursive: entry.isDirectory() });
    copied += 1;
  }

  await verifyServiceWorkerAssets();

  const total = await countFiles(OUT_DIR);
  log(`staged ${total} file(s) from ${copied} top-level entr(y/ies) into ${OUT_NAME}/`);
  if (!(await isDirectory(path.join(OUT_DIR, ".")))) {
    console.error(`[build-web] output directory ${OUT_DIR} was not created`);
    process.exit(1);
  }
}

async function countFiles(dir) {
  let total = 0;
  const stack = [dir];
  while (stack.length) {
    const current = stack.pop();
    for (const entry of await readdir(current, { withFileTypes: true })) {
      if (entry.isDirectory()) stack.push(path.join(current, entry.name));
      else total += 1;
    }
  }
  return total;
}

main().catch((error) => {
  console.error("[build-web] failed:", error);
  process.exit(1);
});
