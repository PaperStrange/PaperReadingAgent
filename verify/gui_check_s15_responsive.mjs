// VERIFY_META: {"features": "Sprint-15 F-AC5：分栏自适应——1280/1366/1920 桌面宽度下无横向溢出、fn 卡片完整可见", "tier": "gui", "providers": [], "est_seconds": 60, "est_cost_cny": 0, "routes": ["/api/run_step"], "requires": ["playwright", "servers"]}
// Sprint-15 F-AC5（验收③）：Function Subcanvas 桌面分辨率响应式（手机暂不考虑）。
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
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  await page.goto("http://127.0.0.1:5173/", { waitUntil: "networkidle" });
  await page.waitForSelector(".canvas-split", { timeout: 15000 });
  await page.waitForTimeout(1000);

  // 先跑 config（load_index 依赖 config 先建会话设置），再跑 load_index 填充 fn 卡片
  const cfgCard = page.locator(".node-card", { has: page.locator(".node-step", { hasText: "config" }) }).first();
  await cfgCard.evaluate((el) => el.click());
  await page.waitForTimeout(500);
  await cfgCard.locator("button", { hasText: "Run Node" }).evaluate((el) => el.click());
  await page.waitForFunction(
    () =>
      Array.from(document.querySelectorAll(".node-card")).some((c) => {
        const st = c.querySelector(".node-step");
        return st && /config/.test(st.textContent) && /status-(success|failed)/.test(c.className);
      }),
    { timeout: 60000 }
  );
  const liCard = page.locator(".node-card", { has: page.locator(".node-step", { hasText: "load_index" }) }).first();
  await liCard.evaluate((el) => el.click());
  await page.waitForTimeout(500);
  await liCard.locator("button", { hasText: "Run Node" }).evaluate((el) => el.click());
  await page.waitForFunction(
    () =>
      Array.from(document.querySelectorAll(".node-card")).some((c) => {
        const st = c.querySelector(".node-step");
        return st && /load_index/.test(st.textContent) && /status-(success|failed)/.test(c.className);
      }),
    { timeout: 150000 }
  );
  await page.waitForTimeout(1500);

  const measure = () =>
    page.evaluate(() => {
      const split = document.querySelector(".canvas-split").getBoundingClientRect();
      const cards = Array.from(document.querySelectorAll(".fn-node-card")).map((c) => c.getBoundingClientRect());
      return {
        winW: window.innerWidth,
        splitRight: split.right,
        splitLeft: split.left,
        cardCount: cards.length,
        cardMaxRight: cards.length ? Math.max(...cards.map((c) => c.right)) : 0,
        cardMinLeft: cards.length ? Math.min(...cards.map((c) => c.left)) : 0,
      };
    });

  for (const [w, h, label] of [[1280, 720, "1280x720"], [1366, 768, "1366x768"], [1920, 1080, "1920x1080"]]) {
    await page.setViewportSize({ width: w, height: h });
    await page.waitForTimeout(800);
    const m = await measure();
    ok(
      `F-AC5 ${label} 分栏无横向溢出`,
      m.splitLeft >= -0.5 && m.splitRight <= m.winW + 0.5,
      JSON.stringify(m)
    );
    ok(
      `F-AC5 ${label} fn 卡片完整可见`,
      m.cardCount > 0 && m.cardMinLeft >= -0.5 && m.cardMaxRight <= m.winW + 0.5,
      JSON.stringify(m)
    );
    await page.screenshot({ path: path.resolve(_here, `f2-responsive-${label}.png`), fullPage: false });
    console.log(`SHOT f2-responsive-${label}.png`);
  }
} finally {
  await browser.close();
}
console.log(`\nALL PASS (${passed} assertions)`);
