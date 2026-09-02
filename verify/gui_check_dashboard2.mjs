// VERIFY_META: {"features": "看板 spec 编辑器打开态截图", "tier": "gui", "providers": [], "est_seconds": 20, "est_cost_cny": 0, "routes": [], "requires": ["playwright", "dashboard"]}
// 补拍：spec 编辑器打开状态截图
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
await page.goto("http://127.0.0.1:8600/specs", { waitUntil: "networkidle" });
await page.waitForSelector(".ant-list-item", { timeout: 60000 });
await page.waitForTimeout(1000);
await page.screenshot({ path: path.resolve(_here, "dashboard-specs.png"), fullPage: false });
const btns = await page.locator(".ant-list-item").allTextContents();
console.log("list items:", JSON.stringify(btns));
if (btns.length) {
  await page.locator(".ant-list-item").first().click();
  await page.waitForTimeout(1200);
  await page.screenshot({ path: path.resolve(_here, "dashboard-specs-editor.png"), fullPage: false });
  console.log("SHOT dashboard-specs-editor.png (first spec)");
}
await browser.close();
