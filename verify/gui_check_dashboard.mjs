// VERIFY_META: {"features": "看板概览页 + spec 编辑页截图", "tier": "gui", "providers": [], "est_seconds": 30, "est_cost_cny": 0, "routes": [], "requires": ["playwright", "dashboard"]}
// Sprint-9 看板界面截图（用户审阅用）：概览页 + spec 编辑页。
// 前提：agents-dashboard dev server 已在 8600 运行；playwright 取 reactflow frontend 的 node_modules。
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

// 概览页
await page.goto("http://127.0.0.1:8600/", { waitUntil: "networkidle" });
await page.waitForTimeout(1500);
await page.screenshot({ path: path.resolve(_here, "dashboard-overview.png"), fullPage: false });
console.log("SHOT dashboard-overview.png");

// 检索交互（填入 code-review 后截图）
await page.fill('input[placeholder*="全文检索"]', "code-review");
await page.waitForTimeout(800);
await page.screenshot({ path: path.resolve(_here, "dashboard-overview-search.png"), fullPage: false });
console.log("SHOT dashboard-overview-search.png");

// spec 编辑页
await page.goto("http://127.0.0.1:8600/specs", { waitUntil: "networkidle" });
await page.waitForTimeout(800);
await page.screenshot({ path: path.resolve(_here, "dashboard-specs.png"), fullPage: false });
console.log("SHOT dashboard-specs.png");

// 打开 impact-assessment spec（antd List.Item）
await page.locator(".ant-list-item", { hasText: "impact-assessment" }).first().click();
await page.waitForTimeout(800);
await page.screenshot({ path: path.resolve(_here, "dashboard-specs-editor.png"), fullPage: false });
console.log("SHOT dashboard-specs-editor.png");

await browser.close();
