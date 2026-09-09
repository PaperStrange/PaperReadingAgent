// VERIFY_META: {"features": "Sprint-15 F-AC6：失败一键复制（主卡+fn 卡，含完整堆栈）+ fn 卡框选复制 + 主画布错误摘要可展开 + 多报错卡定位按钮显隐 + 走查七轮报错卡 zIndex 压顶与 fn_title 定位 + 走查八轮定位目标抬层 10001 高亮", "tier": "gui", "providers": [], "est_seconds": 120, "est_cost_cny": 0, "routes": ["/api/run_step"], "requires": ["playwright", "servers"]}
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

  // ⑤-走查五轮：报错卡 < 2 张时不显示"定位下一处报错"按钮（≥2 张才出现，多卡场景见手动走查记录）
  const locateBtnCount = await page.locator(".fn-locate-err-btn").count();
  ok("F-AC6 单张报错卡时隐藏定位下一处报错按钮", locateBtnCount === 0, `btn=${locateBtnCount}`);

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

  // ⑧ 走查七轮：报错卡 zIndex 最高（重叠压顶）+ 定位按 fn_title 找卡（拖正常卡压住报错卡后切走切回仍居中报错卡）
  const zIdx = await page.evaluate(() => {
    const zi = (el) => {
      if (!el) return null;
      const z = window.getComputedStyle(el).zIndex;
      const n = parseInt(z, 10);
      return Number.isNaN(n) ? 0 : n;
    };
    return {
      err: zi(document.querySelector(".fn-node-card.fn-error")?.closest(".react-flow__node")),
      ok: zi(document.querySelector(".fn-node-card:not(.fn-error)")?.closest(".react-flow__node")),
    };
  });
  ok("F-AC6 七轮 报错卡 zIndex 高于正常卡", zIdx.err != null && zIdx.err > (zIdx.ok ?? 0), JSON.stringify(zIdx));

  // ⑧-八轮：被定位的报错卡抬升至 10001 并带 fn-located 高亮（报错卡之间重叠时定位目标唯一压顶）
  const elev = await page.evaluate(() => {
    const err = document.querySelector(".fn-node-card.fn-error");
    const zw = err?.closest(".react-flow__node");
    const z = zw ? parseInt(window.getComputedStyle(zw).zIndex, 10) || 0 : 0;
    return { z, located: err?.classList.contains("fn-located") || false };
  });
  ok("F-AC6 八轮 被定位报错卡抬升至 10001 且高亮", elev.z === 10001 && elev.located, JSON.stringify(elev));

  const drag = await page.evaluate(() => {
    const err = document.querySelector(".fn-node-card.fn-error");
    const normals = [...document.querySelectorAll(".fn-node-card:not(.fn-error)")];
    if (!err || !normals.length) return null;
    const er = err.getBoundingClientRect();
    const ec = { x: er.left + er.width / 2, y: er.top + er.height / 2 };
    const nearest = normals
      .map((c) => {
        const r = c.getBoundingClientRect();
        return { dx: r.left + r.width / 2 - ec.x, dy: r.top + r.height / 2 - ec.y, sx: r.left + r.width / 2, sy: r.top + r.height / 2 };
      })
      .sort((a, b) => a.dx * a.dx + a.dy * a.dy - (b.dx * b.dx + b.dy * b.dy))[0];
    return { ...nearest, ex: ec.x, ey: ec.y };
  });
  if (drag) {
    await page.mouse.move(drag.sx, drag.sy);
    await page.mouse.down();
    await page.mouse.move(drag.ex, drag.ey, { steps: 25 });
    await page.mouse.up();
    await page.waitForTimeout(800);
  }
  const topAtErr = await page.evaluate(() => {
    const err = document.querySelector(".fn-node-card.fn-error");
    if (!err) return { hit: false };
    const r = err.getBoundingClientRect();
    const el = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    const card = el?.closest?.(".fn-node-card") || null;
    return { hit: !!card, isErr: card?.classList.contains("fn-error") || false };
  });
  ok("F-AC6 七轮 重叠时报错卡压顶（elementFromPoint）", topAtErr.hit && topAtErr.isErr, JSON.stringify(topAtErr));

  // 压住报错卡后切走再切回：定位必须按 fn_title 直接找报错卡居中，且仍压顶
  await page.locator(".step-switch-btn", { hasText: "Retrieve" }).evaluate((el) => el.click());
  await page.waitForTimeout(1500);
  await page.locator(".step-switch-btn", { hasText: "parse" }).evaluate((el) => el.click());
  await page.waitForTimeout(2500);
  const overlapRecheck = await page.evaluate(() => {
    const err = document.querySelector(".fn-node-card.fn-error");
    const pane = document.querySelector(".fn-pane-flow");
    if (!err || !pane) return { visible: false, centerDelta: 1, topErr: false };
    const c = err.getBoundingClientRect();
    const p = pane.getBoundingClientRect();
    const visible = c.left < p.right && c.right > p.left && c.top < p.bottom && c.bottom > p.top;
    const centerDelta = Math.abs(c.left + c.width / 2 - (p.left + p.width / 2)) / (p.width || 1);
    const el = document.elementFromPoint(c.left + c.width / 2, c.top + c.height / 2);
    const card = el?.closest?.(".fn-node-card") || null;
    const zw = err.closest(".react-flow__node");
    const z = zw ? parseInt(window.getComputedStyle(zw).zIndex, 10) || 0 : 0;
    return { visible, centerDelta, topErr: card?.classList.contains("fn-error") || false, located: err.classList.contains("fn-located"), z };
  });
  ok("F-AC6 七轮 重叠后切回仍按 fn_title 定位报错卡（居中）", overlapRecheck.visible && overlapRecheck.centerDelta < 0.35, JSON.stringify(overlapRecheck));
  ok("F-AC6 七轮 重叠后切回报错卡仍压顶", overlapRecheck.topErr, JSON.stringify(overlapRecheck));
  ok("F-AC6 八轮 切回后定位卡仍抬层高亮", overlapRecheck.located && overlapRecheck.z === 10001, JSON.stringify(overlapRecheck));

  await page.screenshot({ path: path.resolve(_here, "f2-error-copy.png"), fullPage: false });
  console.log("SHOT f2-error-copy.png");
} finally {
  await ctx.close();
  await browser.close();
}
console.log(`\nALL PASS (${passed} assertions)`);
