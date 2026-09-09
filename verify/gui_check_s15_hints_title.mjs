// VERIFY_META: {"features": "Sprint-15 F-AC2：hints 限高滚动 + 分组标题影响聚合（N项，M项被改动，M 标红）", "tier": "gui", "providers": [], "est_seconds": 45, "est_cost_cny": 0, "routes": ["/api/config_schema", "/api/config/validate"], "requires": ["playwright", "servers"]}
// Sprint-15 F-AC2（验收①1.2）：提示行限高滚动 + 影响上浮标题聚合。
// 前提：后端 8787、前端 5173 已启动；playwright 取前端 node_modules。
// 断言：① 分组 summary 含"（N项，M项被改动）"形态；② 改动 M>0 时计数 span 为红色（rgb(220,38,38)）；
//       ③ hints/warnings 汇总容器 max-height + overflow-y auto。
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
  await page.waitForSelector(".schema-group summary", { timeout: 15000 });
  await page.waitForTimeout(1200);

  // ① summary 形态 + ② 标红：先把 temperature 改成非法值触发"被改动"（也触发校验 hints）
  await page.evaluate(() => {
    const inputs = Array.from(document.querySelectorAll(".schema-field input[type=number]"));
    const el = inputs.find((i) => {
      const row = i.closest(".schema-field");
      return row && row.querySelector(".ds-label")?.textContent?.includes("温度");
    });
    if (!el) return;
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
    setter.call(el, "5");
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  });
  await page.waitForTimeout(2500); // 防抖 600ms + validate 往返

  const summaries = await page.evaluate(() =>
    Array.from(document.querySelectorAll(".schema-group summary")).map((s) => s.textContent.replace(/\s+/g, ""))
  );
  ok(
    "F-AC2 summary 形态（N项，M项被改动）",
    summaries.some((t) => /（\d+项，\d+项被改动）/.test(t)),
    JSON.stringify(summaries.slice(0, 3))
  );
  const redInfo = await page.evaluate(() => {
    const spans = Array.from(document.querySelectorAll(".schema-group summary .schema-changed-count"));
    return spans.map((sp) => ({
      text: sp.textContent,
      color: window.getComputedStyle(sp).color,
    }));
  });
  ok(
    "F-AC2 改动数标红（M>0）",
    redInfo.some((x) => Number(x.text) > 0 && x.color === "rgb(220, 38, 38)"),
    JSON.stringify(redInfo)
  );
  const msgStyle = await page.evaluate(() => {
    const el = document.querySelector(".schema-msg");
    if (!el) return null;
    const cs = window.getComputedStyle(el);
    return { maxHeight: cs.maxHeight, overflowY: cs.overflowY };
  });
  ok(
    "F-AC2 hints 汇总限高滚动",
    msgStyle !== null && msgStyle.maxHeight === "96px" && msgStyle.overflowY === "auto",
    JSON.stringify(msgStyle)
  );

  await page.screenshot({ path: path.resolve(_here, "f2-hints-title.png"), fullPage: false });
  console.log("SHOT f2-hints-title.png");
} finally {
  await browser.close();
}
console.log(`\nALL PASS (${passed} assertions)`);
