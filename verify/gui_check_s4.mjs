// VERIFY_META: {"features": "光标三断言（插入/位置/连续编辑）+ provider 联动四断言", "tier": "gui", "providers": [], "est_seconds": 30, "est_cost_cny": 0, "routes": [], "requires": ["playwright", "servers"]}
// Sprint-4 GUI 验证（US-4.1 光标 / US-4.5 provider 联动）
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

const SHOT =
  process.env.GUI_SHOT || path.resolve(_here, "gui_check_s4.png");

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1700, height: 1000 } });
await page.goto("http://127.0.0.1:5173", { waitUntil: "networkidle" });

// ---- US-4.1：光标不跳末尾（全程 evaluate，避开 ReactFlow 点击拦截） ----
const ta = page.locator(".node-textarea").first();
const original = await ta.inputValue();
const pos = Math.floor(original.length / 2);
await page.evaluate((p) => {
  const el = document.querySelector(".node-textarea");
  el.focus();
  el.setSelectionRange(p, p);
  document.execCommand("insertText", false, "X");
}, pos);
await page.waitForTimeout(300);
const afterTyping = await ta.inputValue();
const caret = await page.evaluate(() => document.querySelector(".node-textarea").selectionStart);
const expectMid = original.slice(0, pos) + "X" + original.slice(pos);
console.log("US-4.1 inserted-at-middle:", afterTyping === expectMid ? "PASS" : "FAIL");
console.log("US-4.1 caret after insert:", caret, "(expect", pos + 1 + ")",
  caret === pos + 1 ? "PASS" : "FAIL");
await page.evaluate(() => {
  const el = document.querySelector(".node-textarea");
  document.execCommand("insertText", false, "Y");
});
await page.waitForTimeout(300);
const afterSecond = await ta.inputValue();
console.log("US-4.1 continuous edit:", afterSecond.includes("XY") ? "PASS" : "FAIL");
// 结束编辑：blur 使草稿重新跟随 params，后续读取反映真实状态
await page.evaluate(() => document.querySelector(".node-textarea").blur());
await page.waitForTimeout(300);

// ---- US-4.5：provider 下拉联动（Sprint-12 起 selector 指向 SchemaForm，evaluate 派发 input+change 事件） ----
const options = await page.evaluate(() =>
  Array.from(document.querySelectorAll(".ds-select.schema-field-provider option")).map((o) => o.textContent)
);
console.log("US-4.5 select options:", options.join(","));
console.log("US-4.5 has openrouter:", options.some((o) => o.includes("openrouter")) ? "PASS" : "FAIL");

const setSelect = async (value) => {
  await page.evaluate((v) => {
    const el = document.querySelector(".ds-select.schema-field-provider");
    const setter = Object.getOwnPropertyDescriptor(
      window.HTMLSelectElement.prototype,
      "value"
    ).set;
    setter.call(el, v);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }, value);
  await page.waitForTimeout(2000); // 防抖校验 600ms + fetch
};

await setSelect("openrouter");
const json1 = JSON.parse(await ta.inputValue());
console.log(
  "US-4.5 openrouter autofill:",
  json1.provider === "openrouter" &&
    json1.api_base === "https://openrouter.ai/api/v1" &&
    json1.model === "openrouter/auto" &&
    !("embedding_model" in json1)
    ? "PASS"
    : `FAIL ${JSON.stringify(json1).slice(0, 200)}`
);

await setSelect("deepseek");
const json2 = JSON.parse(await ta.inputValue());
console.log(
  "US-4.5 deepseek autofill:",
  json2.provider === "deepseek" && !("embedding_model" in json2) ? "PASS" : "FAIL"
);
const hintText = await page.evaluate(() => {
  const el = document.querySelector(".schema-msg-hint");
  return el ? el.textContent : "";
});
console.log("US-4.5 auto hint:", (hintText || "").includes("多语言") ? "PASS" : "FAIL");

await page.screenshot({ path: SHOT, fullPage: true });
console.log("SHOT_SAVED " + SHOT);
await browser.close();
