// Builds the module Home Assistant loads on every page (custom_components/virtuhome_pro/frontend):
// a tiny entry that registers the extension source with VirtuHome, and the Extras section and Check
// my setup lines as chunks fetched only when VirtuHome's editor asks for them. Commit the result.
import * as esbuild from "esbuild";
import { readFileSync, rmSync } from "node:fs";

const version = JSON.parse(readFileSync("../custom_components/virtuhome_pro/manifest.json", "utf8")).version;
const out = "../custom_components/virtuhome_pro/frontend/";
// old chunks would pile up next to the new ones
rmSync(out, { recursive: true, force: true });
await esbuild.build({
  entryPoints: { "virtuhome-pro": "src/index.ts" },
  outdir: out,
  bundle: true,
  format: "esm",
  splitting: true,
  chunkNames: "chunk-[hash]",
  minify: true,
  // the oldest browsers VirtuHome supports
  target: ["es2020", "chrome87", "safari15"],
  legalComments: "none",
  define: { __VERSION__: JSON.stringify(version) },
  logLevel: "info",
});
