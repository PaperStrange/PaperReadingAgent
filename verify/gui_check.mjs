// GUI 全链路回归脚本（US-2.6 证据）：Run All 全链路 + 截图
// 运行前提：后端 8787 / 前端 5173 已启动：
//   node verify\gui_check.mjs
// playwright 为前端 node_modules 的 --no-save 安装：经 createRequire 显式定位。
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

const SHOT = "D:/All-Downloads/PaperReading/PaperReading-Windows/docs/iteration/sprint/us2-06.png";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1700, height: 1000 } });
await page.goto("http://127.0.0.1:5173", { waitUntil: "networkidle" });
await page.getByText("Run All (Left-to-Right)").click();
console.log("clicked Run All");
await page.waitForFunction(
  () => document.body.innerText.includes("Skarlinski"),
  null,
  { timeout: 600000 }
);
console.log("answer contains Skarlinski -> pipeline done");
await page.screenshot({ path: SHOT, fullPage: true });
console.log("SHOT_SAVED " + SHOT);
await browser.close();
