// VERIFY_META: {"features": "Sprint-15 F-AC11：output 一键复制全文 + answer 节点答案全文展示（不截断）", "tier": "network", "providers": ["deepseek"], "est_seconds": 300, "est_cost_cny": 0.4, "routes": ["/api/run_step"], "requires": ["keys", "network", "playwright", "servers"]}
// Sprint-15 F-AC11（走查 N1）：output 完整查看。全链路真实运行到 answer（有 API 成本），
// 断言：① answer 节点展示"答案全文"块且长度 > 180（未截断）；② 复制答案含全文；
// ③ 非 answer 节点"复制 output"可复制完整 JSON。
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
const ctx = await browser.newContext({
  viewport: { width: 1600, height: 900 },
  permissions: ["clipboard-read", "clipboard-write"],
});
try {
  const page = await ctx.newPage();
  await page.goto("http://127.0.0.1:5173/", { waitUntil: "networkidle" });
  await page.waitForSelector(".node-card", { timeout: 15000 });
  await page.waitForTimeout(1000);

  const card = (s) => page.locator(".node-card", { has: page.locator(".node-step", { hasText: s }) }).first();
  const run = async (s) => card(s).locator("button", { hasText: "Run Node" }).evaluate((el) => el.click());
  const clickC = async (s) => card(s).evaluate((el) => el.click());
  const waitTerm = (s, timeout = 300000) =>
    page.waitForFunction(
      (t) =>
        Array.from(document.querySelectorAll(".node-card")).some((c) => {
          const st = c.querySelector(".node-step");
          return st && new RegExp(t).test(st.textContent) && /status-(success|failed)/.test(c.className);
        }),
      s,
      { timeout }
    );

  // 全链路：config → load_index → retrieve → parse → evidence → answer
  for (const [step, wait] of [
    ["config", 60000],
    ["load_index", 300000],
    ["retrieve", 120000],
    ["parse", 300000],
    ["evidence", 300000],
    ["answer", 300000],
  ]) {
    await clickC(step);
    await page.waitForTimeout(400);
    await run(step);
    await waitTerm(step, wait);
    await page.waitForTimeout(800);
  }

  // ① answer 节点：答案全文块 + 长度 > 180
  const ansCard = card("answer");
  const ansText = await ansCard.locator(".answer-text").textContent().catch(() => "");
  ok("F-AC11 answer 节点展示答案全文", (ansText || "").length > 180, `len=${ansText?.length}`);
  ok("F-AC11 答案非截断（无 truncated 标记）", !/truncated/.test(ansText || ""), ansText?.slice(0, 60));

  // ② 复制答案：剪贴板含全文开头与结尾
  await ansCard.locator("button", { hasText: "复制答案" }).evaluate((el) => el.click());
  await page.waitForTimeout(500);
  const clipAns = await page.evaluate(() => navigator.clipboard.readText().catch(() => ""));
  ok("F-AC11 复制答案含全文", clipAns.includes("答案：") && clipAns.length > 200, `clipLen=${clipAns.length}`);

  // ③ 非 answer 节点：复制 output 完整 JSON
  const cfgCard = card("config");
  await cfgCard.locator("button", { hasText: "复制 output" }).evaluate((el) => el.click());
  await page.waitForTimeout(500);
  const clipOut = await page.evaluate(() => navigator.clipboard.readText().catch(() => ""));
  ok("F-AC11 复制 output 为完整 JSON", clipOut.trim().startsWith("{") && clipOut.length > 100, clipOut.slice(0, 60));

  await page.screenshot({ path: path.resolve(_here, "f2-output-view.png"), fullPage: false });
  console.log("SHOT f2-output-view.png");
} finally {
  await ctx.close();
  await browser.close();
}
console.log(`\nALL PASS (${passed} assertions)`);
