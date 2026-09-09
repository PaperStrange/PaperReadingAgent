// VERIFY_META: {"features": "Sprint-15 F-AC4：节点运行完成后自动收起全部展开项，仅 output_snapshot 保持展开", "tier": "gui", "providers": [], "est_seconds": 50, "est_cost_cny": 0, "routes": ["/api/run_step"], "requires": ["playwright", "servers"]}
// Sprint-15 F-AC4（验收②）：完成即收起、仅留 output_snapshot（Q4 口径：全部收起含手动展开项）。
// 前提：后端 8787、前端 5173 已启动；playwright 取前端 node_modules。
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

let passed = 0;
function ok(name, cond, detail = "") {
  if (!cond) {
    console.log(`FAIL: ${name} ${detail}`);
    process.exitCode = 1;
    return;
  }
  passed += 1;
  console.log(`PASS: ${name} ${detail}`);
}

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto("http://127.0.0.1:5173/", { waitUntil: "networkidle" });
  await page.waitForSelector(".node-card", { timeout: 15000 });
  await page.waitForTimeout(1200);

  // 定位 config 节点卡片
  const configCard = page.locator(".node-card", { has: page.locator(".node-step", { hasText: "config" }) }).first();
  await configCard.waitFor({ state: "visible" });

  const openGroupsBefore = await configCard.locator(".schema-group[open]").count();
  ok("F-AC4 运行前分组默认展开（≥2）", openGroupsBefore >= 2, `open=${openGroupsBefore}`);

  await page.screenshot({ path: path.resolve(_here, "f2-collapse-before.png"), fullPage: false });
  console.log("SHOT f2-collapse-before.png");

  // 运行 config 节点（最快完成）；DOM 级 click——卡片较高时按钮在视口外，Playwright 滚动不可靠
  await configCard.locator("button", { hasText: "Run Node" }).evaluate((el) => el.click());
  await page.waitForFunction(
    () =>
      Array.from(document.querySelectorAll(".node-card")).some((c) => {
        const step = c.querySelector(".node-step");
        return step && /config/.test(step.textContent) && c.className.includes("status-success");
      }),
    { timeout: 30000 }
  );
  await page.waitForTimeout(500);

  const openGroupsAfter = await configCard.locator(".schema-group[open]").count();
  ok("F-AC4 完成后分组全部收起", openGroupsAfter === 0, `open=${openGroupsAfter}`);

  // output_snapshot = 第一个 .node-output；input_snapshot/function_trace 为后续块
  const outputBlocks = configCard.locator(".node-output");
  const outOpen = await outputBlocks.nth(0).locator(".json-details[open]").count();
  ok("F-AC4 output_snapshot 保持展开", outOpen >= 1, `outOpen=${outOpen}`);
  const inOpen = await outputBlocks.nth(1).locator(".json-details[open]").count();
  ok("F-AC4 input_snapshot 收起", inOpen === 0, `inOpen=${inOpen}`);

  await page.screenshot({ path: path.resolve(_here, "f2-collapse-after.png"), fullPage: false });
  console.log("SHOT f2-collapse-after.png");
} finally {
  await browser.close();
}
console.log(`\nALL PASS (${passed} assertions)`);
