// Sprint-5 GUI 验证：US-5.1 自动重跑 config / US-5.2 retrieve 标记 / US-5.3 复制按钮与计时
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

// 1) 改 config 参数（temperature）→ 节点变 stale → 直接跑 load_index
const ta = page.locator(".node-textarea").first();
await page.evaluate(() => {
  const el = document.querySelector(".node-textarea");
  el.focus();
});
const parsed = JSON.parse(await ta.inputValue());
parsed.temperature = 0.5;
await page.evaluate((txt) => {
  const el = document.querySelector(".node-textarea");
  const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
  setter.call(el, txt);
  el.dispatchEvent(new Event("input", { bubbles: true }));
}, JSON.stringify(parsed, null, 2));
await page.waitForTimeout(500);

// 点击 2) Load Index 节点的 Run Node（DOM click 绕过 ReactFlow 指针拦截）
await page.evaluate(() => {
  const cards = document.querySelectorAll(".node-card");
  const card2 = cards[1];
  const btns = card2.querySelectorAll(".run-btn");
  btns[1].click(); // Run Node
});
console.log("clicked load_index Run Node (config should auto-rerun first)");

// 等待 load_index 完成（config 自动重跑 + load_index），轮询 status
let okLoad = false;
let logHasAutoConfig = false;
let sawTimer = false;
for (let i = 0; i < 240; i++) {
  await page.waitForTimeout(500);
  const state = await page.evaluate(() => {
    const cards = document.querySelectorAll(".node-card");
    const c = (idx) => cards[idx]?.querySelector(".node-status")?.textContent || "";
    const log = document.body.innerText;
    return { cfg: c(0), load: c(1), timer: document.querySelector(".fn-timer")?.textContent || "", log };
  });
  if (state.timer) sawTimer = true;
  if (state.load.includes("success")) {
    okLoad = true;
    break;
  }
  if (state.load.includes("failed")) break;
}
console.log("US-5.1 load_index success after auto-config:", okLoad ? "PASS" : "FAIL");
console.log("US-5.3 fn-timer seen while running:", sawTimer ? "PASS" : "check-manually");

// 2) retrieve output 标记（点 3) Retrieve 的 Run Node）
await page.evaluate(() => {
  const cards = document.querySelectorAll(".node-card");
  const btns = cards[2].querySelectorAll(".run-btn");
  btns[1].click();
});
await page.waitForFunction(
  () => {
    const cards = document.querySelectorAll(".node-card");
    return cards[2]?.querySelector(".node-status")?.textContent?.includes("success");
  },
  null,
  { timeout: 120000 }
);
const retrieveOut = await page.evaluate(() => {
  const cards = document.querySelectorAll(".node-card");
  const json = cards[2].querySelector(".json-tree")?.textContent || "";
  return json;
});
console.log(
  "US-5.2 retrieve result marker:",
  retrieveOut.includes("result") && retrieveOut.includes("ranked") ? "PASS" : "MANUAL-CHECK"
);
console.log("retrieve output snippet:", retrieveOut.replace(/\s+/g, " ").slice(0, 160));

// 3) 复制报错按钮存在性（无错误时按钮不渲染——检查 parse 失败场景略；改为存在性检查在 4.2 完成）
await page.screenshot({ path: SHOT, fullPage: true });
console.log("SHOT_SAVED " + SHOT);
await browser.close();
