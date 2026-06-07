// Render every html/<ep>/*.html to a 1920×1080 PNG in <ep>/assets/ using
// Chrome's built-in headless screenshot. No npm dependencies.
//
//   node html/render.mjs            # render all
//   node html/render.mjs ep1/B08    # render one block
//
import { execFileSync } from "node:child_process";
import { readdirSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join, basename, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const CHROME = [
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
].find(existsSync);
if (!CHROME) { console.error("No Chrome/Edge found"); process.exit(1); }

const filter = process.argv[2];                 // e.g. "ep1/B08" or "ep1"
const htmlRoot = join(ROOT, "html");
const eps = readdirSync(htmlRoot, { withFileTypes: true })
  .filter(d => d.isDirectory()).map(d => d.name);

let n = 0;
for (const ep of eps) {
  const dir = join(htmlRoot, ep);
  const outDir = join(ROOT, ep, "assets");
  for (const f of readdirSync(dir).filter(f => f.endsWith(".html"))) {
    const id = basename(f, ".html");           // "B08"
    if (filter && filter !== ep && filter !== `${ep}/${id}`) continue;
    if (!existsSync(outDir)) mkdirSync(outDir, { recursive: true });
    const out = join(outDir, `${id}.png`);
    execFileSync(CHROME, [
      "--headless=new", "--disable-gpu", "--hide-scrollbars",
      "--force-device-scale-factor=1", "--window-size=1920,1080",
      `--screenshot=${out}`, pathToFileURL(join(dir, f)).href,
    ], { stdio: "ignore" });
    console.log(`  ${ep}/${id}.png`);
    n++;
  }
}
console.log(`rendered ${n} image(s)`);
