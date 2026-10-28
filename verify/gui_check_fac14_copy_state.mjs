// VERIFY_META: {"features": "F-AC14：三个复制按钮各自独立暂态（点『复制答案』只它变『已复制 ✓』，复制 output / 复制报错不串台；1.5s 后各自复位；跨节点互不影响）", "tier": "gui", "providers": [], "est_seconds": 45, "est_cost_cny": 0, "routes": ["/api/run_step"], "requires": ["playwright", "servers"]}
// F-AC14（用户走查 2026-09-20 新增问题②）：三个复制按钮共用同一个 `copied` state → 点 A 时 B/C 也显示"已复制 ✓"。
// 根因：FlowNode.jsx 的单一 `copied`（HEAD e1c6cdb 的 :42）被"复制 output"/"复制报错"/"复制答案"三处按钮共用。
//
// **反向对照（TG-6 ⑤「倒过来试试」）**：本检查在**修复前**必须 FAIL。
// 复现：保持 FlowNode.jsx 为 HEAD 原始形态（单一 copied state），跑本脚本 →
// 「点『复制答案』后『复制 output』文案不变」断言必须失败（实测修复前：两者同时变"已复制 ✓"）。
// 后端调用用 page.route 注入固定响应（answer 成功 / parse 失败），**不产生任何 LLM 成本**。
// 前提：后端 8787 + 前端 5173 已启动；playwright 取前端 node_modules。
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
const failed = [];
function ok(name, cond, detail = "") {
  if (cond) {
    passed += 1;
    console.log(`PASS: ${name} ${detail}`);
  } else {
    failed.push(name);
    console.log(`FAIL: ${name} ${detail}`);
  }
}

const MOCK_ANSWER = "mock answer for F-AC14 (no LLM call)";
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({
  viewport: { width: 1700, height: 1000 },
  permissions: ["clipboard-read", "clipboard-write"],
});
try {
  const page = await ctx.newPage();
  // 固定响应：answer 成功（带 answer 字段 → 渲染"复制答案"）；其它步骤失败（渲染"复制报错"）
  await page.route("**/api/run_step", async (route) => {
    const body = route.request().postDataJSON();
    const base = {
      session_id: body.session_id || "mock-session",
      run_id: body.run_id || "run-mock-fac14",
      step: body.step,
      duration_s: 0.1,
      input_snapshot: {},
      function_trace: [],
    };
    const resp =
      body.step === "answer"
        ? {
            ...base,
            ok: true,
            output: { answer: MOCK_ANSWER, references: "[1] mock ref" },
            output_snapshot: { answer: MOCK_ANSWER },
            error: null,
            error_detail: null,
          }
        : {
            ...base,
            ok: false,
            output: {},
            output_snapshot: {},
            error: "mock error for F-AC14",
            error_detail: "Traceback (mock)\n  at facade",
          };
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(resp),
    });
  });

  await page.goto("http://127.0.0.1:5173/", { waitUntil: "networkidle" });
  await page.waitForSelector(".node-card", { timeout: 15000 });
  await page.waitForTimeout(600);

  const cardByStep = (s) =>
    page.locator(".node-card", { has: page.locator(".node-step", { hasText: s }) }).first();

  // ---- 场景 A：answer 节点同时有"复制 output"与"复制答案" ----
  const answerCard = cardByStep("answer");
  // 运行按钮用程序化 click：本检查考的是"复制状态是否串台"，不考鼠标输入（F-AC13 检查负责真实鼠标）；
  // 且 ReactFlow 画布内元素可能位于视口外，locator.click() 的自动滚动对 transform 画布无效。
  await answerCard.locator("button.run-btn", { hasText: "Run Node" }).evaluate((el) => el.click());
  await answerCard.locator(".node-answer").waitFor({ state: "visible", timeout: 15000 });
  const answerBtn = answerCard.locator(".node-answer button.copy-output-btn").first();
  const outputBtn = answerCard.locator(".node-output .node-block-title button.copy-output-btn").first();
  ok("A① answer 节点同时渲染『复制 output』与『复制答案』",
    (await outputBtn.count()) === 1 && (await answerBtn.count()) === 1);
  ok("A① 初始文案正确",
    (await outputBtn.innerText()).trim() === "复制 output" && (await answerBtn.innerText()).trim() === "复制答案",
    `output=${(await outputBtn.innerText()).trim()} answer=${(await answerBtn.innerText()).trim()}`);

  await answerBtn.click();
  await page
    .waitForFunction(
      () => {
        const c = Array.from(document.querySelectorAll(".node-card")).find((n) =>
          /answer/.test(n.querySelector(".node-step")?.textContent || "")
        );
        return c && /已复制/.test(c.querySelector(".node-answer button")?.textContent || "");
      },
      null,
      { timeout: 5000 }
    )
    .catch(() => {});
  const outputTextAfterAnswer = (await outputBtn.innerText()).trim();
  const answerTextAfterAnswer = (await answerBtn.innerText()).trim();
  ok("A② 点『复制答案』→ 它显示『已复制 ✓』", answerTextAfterAnswer.includes("已复制"), answerTextAfterAnswer);
  ok(
    "A② 点『复制答案』→『复制 output』文案不变（修复前 FAIL：两者同时变已复制）",
    outputTextAfterAnswer === "复制 output",
    `output=${outputTextAfterAnswer}`
  );

  await page.waitForTimeout(1700);
  ok("A③ 1.5s 后『复制答案』复位",
    (await answerBtn.innerText()).trim() === "复制答案", (await answerBtn.innerText()).trim());
  ok("A③ 1.5s 后『复制 output』仍为原文案（各自 timer 独立）",
    (await outputBtn.innerText()).trim() === "复制 output", (await outputBtn.innerText()).trim());

  // 反向覆盖：点 output 只 output 变
  await outputBtn.click();
  await page
    .waitForFunction(
      () => {
        const c = Array.from(document.querySelectorAll(".node-card")).find((n) =>
          /answer/.test(n.querySelector(".node-step")?.textContent || "")
        );
        const b = c?.querySelector(".node-output .node-block-title button");
        return b && /已复制/.test(b.textContent || "");
      },
      null,
      { timeout: 5000 }
    )
    .catch(() => {});
  ok("A④ 点『复制 output』→ 它显示『已复制 ✓』",
    (await outputBtn.innerText()).trim().includes("已复制"), (await outputBtn.innerText()).trim());
  ok("A④ 点『复制 output』→『复制答案』文案不变",
    (await answerBtn.innerText()).trim() === "复制答案", (await answerBtn.innerText()).trim());
  await page.waitForTimeout(1700);

  // ---- 场景 B：失败节点只有"复制报错"，且与 answer 节点互不影响 ----
  const parseCard = cardByStep("parse");
  await parseCard.locator("button.run-btn", { hasText: "Run Node" }).evaluate((el) => el.click());
  await parseCard.locator(".copy-err-btn").waitFor({ state: "visible", timeout: 15000 });
  // 运行 answer 时 App 会把视口居中到 answer 节点；先 fit view 让 parse 卡回到视口内再真实点击复制
  await page.locator(".react-flow__controls-fitview").first().click().catch(() => {});
  await page.waitForTimeout(500);
  const errBtn = parseCard.locator(".copy-err-btn").first();
  await errBtn.scrollIntoViewIfNeeded().catch(() => {});
  await errBtn.click();
  await page
    .waitForFunction(
      () => {
        const c = Array.from(document.querySelectorAll(".node-card")).find((n) =>
          /parse/.test(n.querySelector(".node-step")?.textContent || "")
        );
        return c && /已复制/.test(c.querySelector(".copy-err-btn")?.textContent || "");
      },
      null,
      { timeout: 5000 }
    )
    .catch(() => {});
  ok("B① 点『复制报错』→ 它自己显示『已复制 ✓』",
    (await errBtn.innerText()).trim().includes("已复制"), (await errBtn.innerText()).trim());
  ok("B② 另一个节点的『复制答案』不受影响（跨节点不串台）",
    (await answerBtn.innerText()).trim() === "复制答案", (await answerBtn.innerText()).trim());
  await page.waitForTimeout(1700);
  ok("B③ 『复制报错』1.5s 后复位", (await errBtn.innerText()).trim() === "复制报错",
    (await errBtn.innerText()).trim());

  await page.screenshot({ path: path.resolve(_here, "fac14-copy-state.png") });
  console.log("SHOT fac14-copy-state.png");
} finally {
  await browser.close();
}

console.log(`\nFAC14 ${failed.length ? "FAIL" : "PASS"} (${passed} passed, ${failed.length} failed)`);
process.exitCode = failed.length ? 1 : 0;
