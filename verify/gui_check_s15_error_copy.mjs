// VERIFY_META: {"features": "Sprint-15 F-AC6：失败一键复制（主卡+fn 卡，含完整堆栈）+ fn 卡框选复制 + 主画布错误摘要可展开", "tier": "gui", "providers": [], "est_seconds": 90, "est_cost_cny": 0, "routes": ["/api/run_step"], "requires": ["playwright", "servers"]}
// Sprint-15 F-AC6（验收④）：复制与报错详情（Q5 口径：摘要 + 可展开完整堆栈）。
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
  const waitTerm = (s, timeout = 150000) =>
    page.waitForFunction(
      (t) =>
        Array.from(document.querySelectorAll(".node-card")).some((c) => {
          const st = c.querySelector(".node-step");
          return st && new RegExp(t).test(st.textContent) && /status-(success|failed)/.test(c.className);
        }),
      s,
      { timeout }
    );

  // config → load_index → retrieve 成功后，给 parse 注入坏候选路径制造失败
  await clickC("config"); await page.waitForTimeout(400); await run("config"); await waitTerm("config");
  await clickC("load_index"); await page.waitForTimeout(400); await run("load_index"); await waitTerm("load_index");
  await clickC("retrieve"); await page.waitForTimeout(400); await run("retrieve"); await waitTerm("retrieve");
  const parseCard = card("parse");
  await clickC("parse"); await page.waitForTimeout(400);
  await parseCard.locator(".node-textarea").evaluate((ta) => {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
    setter.call(ta, JSON.stringify({ candidate_paths: ["does-not-exist.pdf"] }, null, 2));
    ta.dispatchEvent(new Event("input", { bubbles: true }));
    ta.dispatchEvent(new Event("change", { bubbles: true }));
    ta.blur();
  });
  await page.waitForTimeout(600);
  await run("parse"); await waitTerm("parse");
  await page.waitForTimeout(2500);

  // ① 主画布：复制按钮 + 摘要 + 可展开完整堆栈
  const mainCopy = parseCard.locator(".copy-err-btn");
  ok("F-AC6 主卡复制按钮存在", (await mainCopy.count()) === 1, "copy-err-btn");
  const summaryText = await parseCard.locator(".error-text").first().textContent();
  ok("F-AC6 主卡错误摘要非空", (summaryText || "").length > 0, summaryText?.slice(0, 80));
  const detailOpen = await parseCard.locator(".error-detail").count();
  ok("F-AC6 主卡可展开完整堆栈存在", detailOpen === 1, `detail=${detailOpen}`);
  const detailText = await parseCard.locator(".error-detail .error-text").textContent().catch(() => "");
  ok("F-AC6 堆栈含 Traceback", /Traceback/.test(detailText || ""), detailText?.slice(0, 80));

  await mainCopy.evaluate((el) => el.click());
  await page.waitForTimeout(500);
  const clipMain = await page.evaluate(() => navigator.clipboard.readText().catch(() => ""));
  ok("F-AC6 主卡复制含摘要与堆栈", /解析文件失败/.test(clipMain) && /Traceback/.test(clipMain), clipMain.slice(0, 80));

  // ① fn 卡：错误全文不截断 + 复制按钮
  const fnErr = page.locator(".fn-node-card.fn-error").first();
  ok("F-AC6 fn 卡错误卡存在", (await fnErr.count()) === 1, `fnErr=${await fnErr.count()}`);
  const fnErrText = await fnErr.locator(".fn-error-text").textContent().catch(() => "");
  ok("F-AC6 fn 卡错误全文不截断", !/truncated/.test(fnErrText) && /FileNotFoundError/.test(fnErrText), fnErrText.slice(0, 120));
  await fnErr.locator(".fn-copy-err-btn").evaluate((el) => el.click());
  await page.waitForTimeout(500);
  const clipFn = await page.evaluate(() => navigator.clipboard.readText().catch(() => ""));
  ok("F-AC6 fn 卡复制含完整错误", /FileNotFoundError/.test(clipFn) && !/truncated/.test(clipFn), clipFn.slice(0, 120));

  // ② 框选复制：fn 卡 user-select = text
  const us = await page.evaluate(() => window.getComputedStyle(document.querySelector(".fn-node-card")).userSelect);
  ok("F-AC6 fn 卡可框选复制（user-select:text）", us === "text", `userSelect=${us}`);

  // ⑤ 走查追加：报错后 fn 画布自动定位到报错卡（报错卡与 fn 面板视口相交 + 中心贴近面板中心）
  const errInView = await page.evaluate(() => {
    const errCard = document.querySelector(".fn-node-card.fn-error");
    const pane = document.querySelector(".fn-pane-flow");
    if (!errCard || !pane) return { visible: false, centerDelta: 1 };
    const c = errCard.getBoundingClientRect();
    const p = pane.getBoundingClientRect();
    const visible = c.left < p.right && c.right > p.left && c.top < p.bottom && c.bottom > p.top;
    const centerDelta = Math.abs(c.left + c.width / 2 - (p.left + p.width / 2)) / (p.width || 1);
    return { visible, centerDelta };
  });
  ok("F-AC6 报错后 fn 画布定位到报错卡", errInView.visible, JSON.stringify(errInView));
  ok("F-AC6 定位精度（报错卡中心贴近面板中心）", errInView.centerDelta < 0.35, JSON.stringify(errInView));

  // ⑦ 走查追加：切走再切回报错节点，仍定位到报错卡（正常节点则正常视图）
  await page.locator(".step-switch-btn", { hasText: "Retrieve" }).evaluate((el) => el.click());
  await page.waitForTimeout(1500);
  await page.locator(".step-switch-btn", { hasText: "parse" }).evaluate((el) => el.click());
  await page.waitForTimeout(2500);
  const errAgain = await page.evaluate(() => {
    const errCard = document.querySelector(".fn-node-card.fn-error");
    const pane = document.querySelector(".fn-pane-flow");
    if (!errCard || !pane) return false;
    const c = errCard.getBoundingClientRect();
    const p = pane.getBoundingClientRect();
    return c.left < p.right && c.right > p.left && c.top < p.bottom && c.bottom > p.top;
  });
  ok("F-AC7 切回报错节点再次定位到报错卡", errAgain, `errAgain=${errAgain}`);

  await page.screenshot({ path: path.resolve(_here, "f2-error-copy.png"), fullPage: false });
  console.log("SHOT f2-error-copy.png");
} finally {
  await ctx.close();
  await browser.close();
}
console.log(`\nALL PASS (${passed} assertions)`);
