// Sprint-9 US-9.4/9.5 截图：成本/上下文页 + 报告浏览页
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
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

await page.goto("http://127.0.0.1:8600/costs", { waitUntil: "networkidle" });
await page.waitForTimeout(1500);
await page.screenshot({ path: path.resolve(_here, "dashboard-costs.png"), fullPage: false });
console.log("SHOT dashboard-costs.png");

await browser.close();
