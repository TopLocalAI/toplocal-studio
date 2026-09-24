// Lists t("…") keys in src/ that have no English translation: node scripts/check-i18n.mjs
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = fileURLToPath(new URL("../src/", import.meta.url));
const files = [];
const walk = (dir) => readdirSync(dir).forEach((f) => {
  const p = join(dir, f);
  if (statSync(p).isDirectory()) { if (!p.includes("i18n")) walk(p); } else if (/\.(jsx?|mjs)$/.test(f)) files.push(p);
});
walk(root);
const { default: EN } = await import(pathToFileURL(join(root, "i18n/en/index.js")).href);
const missing = new Map();
for (const f of files) {
  const src = readFileSync(f, "utf8");
  for (const m of src.matchAll(/\bt\(\s*(["'`])((?:\\.|(?!\1).)*)\1/g)) {
    const key = m[2].replace(/\\n/g, "\n").replace(/\\(["'`])/g, "$1");
    if (!(key in EN)) missing.set(key, f.replace(root, ""));
  }
}
for (const [k, f] of missing) console.log(`${f}: ${k}`);
console.log(`${missing.size} missing`);
process.exit(missing.size ? 1 : 0);
