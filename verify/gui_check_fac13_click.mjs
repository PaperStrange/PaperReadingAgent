// VERIFY_META: {"features": "F-AC13：节点运行按钮首次真实鼠标点击即生效（mousedown→mouseup 序列，非程序化 .click()）+ 两处 .node-actions 均带 nodrag nopan", "tier": "gui", "providers": [], "est_seconds": 40, "est_cost_cny": 0, "routes": ["/api/run_step"], "requires": ["playwright", "servers"]}
// F-AC13（用户走查 2026-09-20 新增问题①）：运行按钮要点 1~2 次才生效。
// 根因（2026-09-20 全量按钮审计）：FlowNode.jsx 的 5 个运行按钮所在的两个 `.node-actions`
// 没有 `nodrag nopan`；ReactFlow v11 的 useDrag 用 `hasSelector(target, ".nodrag", nodeRef)`
// 判定是否禁用节点拖拽（node_modules/@reactflow/core/dist/esm/index.js:2836），
// 没有该 class 时 mousedown 会被画布当作拖拽起点，首次 click 被吃掉。
//
// **反向对照（TG-6 ⑤「倒过来试试」）**：本检查在**修复前**必须 FAIL。复现方法：
//   git stash / 回退 FlowNode.jsx 中两处 `.node-actions` 的 `nodrag nopan`
//   （HEAD e1c6cdb 的原始形态），重启前端后跑本脚本 → 「真实鼠标点击触发 /api/run_step」
//   断言必须失败（不是靠程序化 click，程序化 click 在修复前也会 PASS）。
// 本检查刻意用 page.mouse.move/down/up（真实输入事件），不用 locator.click()。
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

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1700, height: 1000 } });
  // F-AC13 只考"真实鼠标点击是否被拖拽吃掉"：/api/run_step 用固定成功响应，
  // 不触发任何 LLM/索引成本（点击是否被吃掉由"有没有发出这个 POST"判定）。
  await page.route("**/api/run_step", async (route) => {
    const body = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        session_id: body.session_id || "mock-session",
        run_id: body.run_id || "run-mock-fac13",
        step: body.step,
        ok: true,
        duration_s: 0.1,
        output: { mock: true },
        output_snapshot: { mock: true },
        error: null,
        error_detail: null,
        input_snapshot: {},
        function_trace: [],
      }),
    });
  });
  await page.goto("http://127.0.0.1:5173/", { waitUntil: "networkidle" });
  await page.waitForSelector(".node-card", { timeout: 15000 });
  await page.waitForTimeout(800);
  // 主画布初始 transform 为 scale(1)，6 张卡横向排到视口外（config 卡含完整 SchemaForm 更高）。
  // 先点 Controls 的 fit view（真实用户也会这么做），让短卡（load_index）的运行按钮进入视口。
  await page.locator(".canvas-pane").first().locator(".react-flow__controls-fitview").click();
  await page.waitForTimeout(700);

  // ① 静态结构：所有含运行按钮的 .node-actions 必须带 nodrag nopan（与 textarea/output 一致）
  const actions = await page.evaluate(() =>
    Array.from(document.querySelectorAll(".node-actions"))
      .filter((el) => el.querySelector(".run-btn"))
      .map((el) => ({
        cls: el.className,
        buttons: Array.from(el.querySelectorAll(".run-btn")).map((b) => b.textContent.trim()),
      }))
  );
  ok("① 找到含运行按钮的 .node-actions 容器", actions.length >= 2, `count=${actions.length}`);
  const missing = actions.filter((a) => !/\bnodrag\b/.test(a.cls) || !/\bnopan\b/.test(a.cls));
  ok(
    "① 每个运行按钮行都带 nodrag nopan（修复前此断言 FAIL）",
    missing.length === 0,
    missing.length ? `缺 class 的行：${JSON.stringify(missing)}` : actions.map((a) => a.buttons.join("/")).join(" | ")
  );

  // ② 真实鼠标序列：load_index 节点的 Run Node（/api/run_step 已被上面 mock，零成本）
  const card = page
    .locator(".node-card", { has: page.locator(".node-step", { hasText: "load_index" }) })
    .first();
  const btn = card.locator("button.run-btn", { hasText: "Run Node" }).first();
  ok("② 定位到 load_index 节点的 Run Node 按钮", (await btn.count()) === 1);
  const box = await btn.boundingBox();
  const paneBox = await page.locator(".canvas-pane").first().locator(".pane-flow").boundingBox();
  const inView =
    !!box && !!paneBox &&
    box.y >= paneBox.y && box.y + box.height <= paneBox.y + paneBox.height &&
    box.x >= paneBox.x && box.x + box.width <= paneBox.x + paneBox.width;
  ok("② 按钮在画布可视区内（真实鼠标可达）", inView, box ? JSON.stringify(box) : "null");

  const statusBefore = await card.getAttribute("class");
  const reqPromise = page
    .waitForRequest(
      (r) => r.url().includes("/api/run_step") && r.method() === "POST",
      { timeout: 10000 }
    )
    .catch(() => null);

  if (box) {
    const cx = box.x + box.width / 2;
    const cy = box.y + box.height / 2;
    await page.mouse.move(cx, cy, { steps: 3 });
    await page.mouse.down();
    // 真实用户点击不是"零位移"：按下与抬起之间通常有 1~3px 手抖。
    // 修复前（.node-actions 无 nodrag）：这 3px 会被 d3-drag 当成拖拽，click 被吞（实测 dx=2/4/8 均 0 次请求，
    // 且节点被拖动 2~4px；dx=0 才碰巧成功）——这正是用户"点 1~2 次无响应、第 3 次才 run"的形态。
    await page.mouse.move(cx + 3, cy, { steps: 2 });
    await page.mouse.up();
  }
  const req = await reqPromise;
  ok(
    "② 第一次真实鼠标点击（含 3px 手抖位移）就发出 /api/run_step（修复前此断言 FAIL：点击被判为拖拽吞掉）",
    !!req,
    req ? `POST ${req.url().replace("http://127.0.0.1:8787", "")}` : "10s 内未发出请求"
  );

  // ③ 状态机确实离开 idle/stale（click 被吃掉时 status 不变）
  const leftIdle = await page
    .waitForFunction(
      () => {
        const c = Array.from(document.querySelectorAll(".node-card")).find((n) =>
          /load_index/.test(n.querySelector(".node-step")?.textContent || "")
        );
        return c && /status-(running|success|failed)/.test(c.className);
      },
      null,
      { timeout: 15000 }
    )
    .then(() => true)
    .catch(() => false);
  const statusAfter = await card.getAttribute("class");
  ok("③ 点击后节点状态进入 running/success/failed", leftIdle, `${statusBefore} -> ${statusAfter}`);

  await page.screenshot({ path: path.resolve(_here, "fac13-click.png") });
  console.log("SHOT fac13-click.png");
} finally {
  await browser.close();
}

console.log(`\nFAC13 ${failed.length ? "FAIL" : "PASS"} (${passed} passed, ${failed.length} failed)`);
process.exitCode = failed.length ? 1 : 0;
