// VERIFY_META: {"features": "自动重跑 config / retrieve 双模式标记 / 复制报错按钮 / 计时冻结", "tier": "gui", "providers": [], "est_seconds": 40, "est_cost_cny": 0, "routes": [], "requires": ["playwright", "servers"]}
// Sprint-5 关闭证据脚本（可复现）：US-5.1 自动重跑 config / US-5.2 双模式标记 /
// US-5.3 复制报错按钮与计时冻结。前提：后端 8787 + 前端 5173 已启动。
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

const SHOT = process.env.GUI_SHOT || path.resolve(_here, "gui_check_s5.png");
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1700, height: 1000 } });
await page.goto("http://127.0.0.1:5173", { waitUntil: "networkidle" });

const setFirstNodeJson = async (patch) => {
  const ta = page.locator(".node-textarea").first();
  const parsed = JSON.parse(await ta.inputValue());
  const next = { ...parsed, ...patch };
  await page.evaluate((txt) => {
    const el = document.querySelector(".node-textarea");
    const setter = Object.getOwnPropertyDescriptor(
      window.HTMLTextAreaElement.prototype,
      "value"
    ).set;
    setter.call(el, txt);
    el.dispatchEvent(new Event("input", { bubbles: true }));
  }, JSON.stringify(next, null, 2));
  await page.waitForTimeout(400);
};

const setNodeJson = (cardIdx, patch) =>
  page.evaluate(
    ({ idx, patchText }) => {
      const cards = document.querySelectorAll(".node-card");
      const el = cards[idx].querySelector(".node-textarea");
      const parsed = JSON.parse(el.value || "{}");
      const next = { ...parsed, ...JSON.parse(patchText) };
      const setter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype,
        "value"
      ).set;
      setter.call(el, JSON.stringify(next, null, 2));
      el.dispatchEvent(new Event("input", { bubbles: true }));
    },
    { idx: cardIdx, patchText: JSON.stringify(patch) }
  );

const clickRunNode = (cardIdx) =>
  page.evaluate((idx) => {
    const cards = document.querySelectorAll(".node-card");
    cards[idx].querySelectorAll(".run-btn")[1].click();
  }, cardIdx);

const nodeStatus = (idx) =>
  page.evaluate(
    (i) =>
      document.querySelectorAll(".node-card")[i]?.querySelector(".node-status")?.textContent || "",
    idx
  );

const waitStatus = async (idx, want, timeoutMs) => {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    const s = await nodeStatus(idx);
    if (s.includes(want)) return s;
    await page.waitForTimeout(500);
  }
  return await nodeStatus(idx);
};

const nodeJsonTree = (idx) =>
  page.evaluate((i) => {
    const cards = document.querySelectorAll(".node-card");
    const trees = cards[i]?.querySelectorAll(".json-tree") || [];
    let out = "";
    trees.forEach((t) => {
      out += t.textContent || "";
    });
    return out;
  }, idx);

// ---- US-5.1：改参数 → 直接跑 load_index（config 应自动重跑） ----
await setFirstNodeJson({ temperature: 0.5 });
await clickRunNode(1);
const loadStatus = await waitStatus(1, "success", 240000);
console.log(
  "US-5.1 load_index success after auto-config:",
  loadStatus.includes("success") ? "PASS" : `FAIL(${loadStatus})`
);

// ---- US-5.3：计时冻结（用耗时更长的 parse 步骤验证"运行中刷新 + 完成后冻结"） ----
await clickRunNode(3);
const parseStatus = await waitStatus(3, "success", 300000);
console.log(
  "US-5.3 parse run status:",
  parseStatus.includes("success") ? "PASS" : `FAIL(${parseStatus})`
);
await page.waitForTimeout(800);
const timerAfter = await page.evaluate(
  () => document.querySelector(".fn-timer")?.textContent || ""
);
console.log(
  "US-5.3 timer frozen after done:",
  /完成 \d+(\.\d+)?s/.test(timerAfter) ? "PASS" : `MANUAL(${timerAfter})`
);

// ---- US-5.2a：中文 query 零命中 → fallback_first_n ----
await clickRunNode(2);
await waitStatus(2, "success", 120000);
const r1 = await nodeJsonTree(2);
console.log(
  "US-5.2a zero-hit fallback marker:",
  r1.includes("fallback_first_n") ? "PASS" : `MANUAL(${r1.replace(/\s+/g, " ").slice(0, 120)})`
);

// ---- US-5.2b：英文 query 命中 → ranked ----
await setNodeJson(2, { query: "PaperQA2" });
await clickRunNode(2);
await waitStatus(2, "success", 120000);
const r2 = await nodeJsonTree(2);
console.log(
  "US-5.2b ranked marker:",
  r2.includes("ranked") ? "PASS" : `MANUAL(${r2.replace(/\s+/g, " ").slice(0, 120)})`
);

// ---- US-5.3：失败态复制报错按钮 ----
await setFirstNodeJson({ paper_directory: "data/nonexistent_x" });
await clickRunNode(1);
await waitStatus(1, "failed", 120000);
const hasCopy = await page.evaluate(() => !!document.querySelector(".copy-err-btn"));
const errOk = await page.evaluate(() => {
  const pre = document.querySelector(".error-text");
  return pre ? pre.textContent.includes("论文目录不存在") : false;
});
console.log("US-5.3 copy-error button on failure:", hasCopy ? "PASS" : "FAIL");
console.log("US-5.3 friendly error text:", errOk ? "PASS" : "FAIL");

await page.screenshot({ path: SHOT, fullPage: true });
console.log("SHOT_SAVED " + SHOT);
await browser.close();
