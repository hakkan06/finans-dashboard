// esbuild ile üretim derlemesi: src/main.jsx → dist/ (hash'li dosya adları + index.html)
import { build } from "esbuild";
import { cpSync, mkdirSync, readFileSync, rmSync, writeFileSync, existsSync } from "node:fs";
import { basename } from "node:path";

rmSync("dist", { recursive: true, force: true });
mkdirSync("dist/assets", { recursive: true });

const result = await build({
  entryPoints: ["src/main.jsx"],
  bundle: true,
  minify: true,
  sourcemap: false,
  format: "esm",
  target: "es2022",
  jsx: "automatic",
  loader: { ".jsx": "jsx" },
  define: { "process.env.NODE_ENV": '"production"' },
  outdir: "dist/assets",
  entryNames: "[name]-[hash]",
  metafile: true,
  logLevel: "info",
});

const outputs = Object.keys(result.metafile.outputs).map((p) => basename(p));
const js = outputs.find((f) => f.endsWith(".js"));
const css = outputs.find((f) => f.endsWith(".css"));

let html = readFileSync("index.template.html", "utf8");
html = html
  .replace("<!--ASSETS_CSS-->", css ? `<link rel="stylesheet" href="/assets/${css}" />` : "")
  .replace("<!--ASSETS_JS-->", `<script type="module" src="/assets/${js}"></script>`);
writeFileSync("dist/index.html", html);

if (existsSync("public")) cpSync("public", "dist", { recursive: true });
console.log(`dist hazır → ${js}${css ? ", " + css : ""}`);
