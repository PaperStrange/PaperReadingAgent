// 调试 /api/specs 浏览器端状态
import { createRequire } from "module";
import path from "path";
import { fileURLToPath } from "url";

const _here = path.dirname(fileURLToPath(import.meta.url));
const _frontendNm = path.resolve(
  _here,
  "../paper-qa-script/reactflow-paperqa-prototype/frontend/node_modules"
);
const require = createRequire(path.join(_frontendNm, "noop.js"));
const { chromium } = require("playwright");

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
await page.goto("http://127.0.0.1:8600/", { waitUntil: "networkidle" });
const r = await page.evaluate(async () => {
  const res = await fetch("/api/specs");
  return { status: res.status, body: await res.text() };
});
console.log("[specs]", r.status, r.body.slice(0, 300));
await browser.close();
