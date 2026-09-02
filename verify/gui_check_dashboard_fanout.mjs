// VERIFY_META: {"features": "看板 fan-out 配置页截图（两条流水线+JSON 编辑器）", "tier": "gui", "providers": [], "est_seconds": 30, "est_cost_cny": 0, "routes": [], "requires": ["playwright", "dashboard"]}
// Sprint-10 US-10.5 看板 fan-out 配置页截图（用户审阅用）。
// 前提：agents-dashboard 已在 8600 运行（生产模式）；playwright 取 reactflow frontend 的 node_modules。
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

// fan-out 配置页（两条流水线可视化 + JSON 编辑器）
await page.goto("http://127.0.0.1:8600/fanout", { waitUntil: "networkidle" });
await page.waitForTimeout(1200);
await page.screenshot({ path: path.resolve(_here, "dashboard-fanout.png"), fullPage: false });
console.log("SHOT dashboard-fanout.png");

await browser.close();
