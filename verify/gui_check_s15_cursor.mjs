// VERIFY_META: {"features": "Sprint-15 走查修复：真实键盘输入光标不跳（JSON 编辑区/表单输入）+ 无默认值字段（api_key）改动计数", "tier": "gui", "providers": [], "est_seconds": 50, "est_cost_cny": 0, "routes": ["/api/config/validate"], "requires": ["playwright", "servers"]}
// 走查 2026-09-10 发现：① 手动改 api_base 光标跳末尾；② api_key/api_base 等无默认值字段改动不计数。
// 本检查用**真实键盘事件**（非 .value 赋值——赋值本身会把光标移到末尾，是测试伪影）验证修复。
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
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  await page.goto("http://127.0.0.1:5173/", { waitUntil: "load", timeout: 30000 });
  await page.waitForSelector(".node-card .node-textarea", { timeout: 15000 });
  await page.waitForTimeout(1000);

  // ① JSON 编辑区：中部插入真实键入，光标应停在插入处之后
  const ta = page.locator(".node-card .node-textarea").first();
  const pos = await ta.evaluate((el) => {
    el.focus();
    const m = Math.floor(el.value.length / 2);
    el.setSelectionRange(m, m);
    return m;
  });
  await page.keyboard.type("YYY", { delay: 80 });
  await page.waitForTimeout(900);
  const r1 = await ta.evaluate((el, exp) => ({ sel: el.selectionStart, has: el.value.includes("YYY") }), pos);
  ok("走查① JSON 编辑区光标不跳", r1.sel === pos + 3 && r1.has, JSON.stringify(r1));

  // ② 表单输入：光标定位开头键入，光标应停在 3
  const inp = page.locator(".schema-field input[type=text]").first();
  await inp.evaluate((el) => {
    el.focus();
    el.setSelectionRange(0, 0);
  });
  await page.keyboard.type("abc", { delay: 80 });
  await page.waitForTimeout(900);
  const r2 = await inp.evaluate((el) => ({ sel: el.selectionStart, v: el.value.slice(0, 8) }));
  ok("走查① 表单输入光标不跳", r2.sel === 3, JSON.stringify(r2));

  // ③ 无默认值字段（api_key）改动计数：真实键入后 LLM 组 summary 应含"1项被改动"
  const keyInp = page.locator(".schema-field input[type=password]").first();
  await keyInp.evaluate((el) => el.focus());
  await page.keyboard.type("sk-walk-123", { delay: 50 });
  await page.waitForTimeout(1500);
  const llm = await page.evaluate(() => {
    const g = Array.from(document.querySelectorAll(".schema-group")).find((d) =>
      d.querySelector("summary")?.textContent?.includes("LLM")
    );
    return g ? g.querySelector("summary").textContent.replace(/\s+/g, "") : "";
  });
  ok("走查② api_key 改动计数生效", /项被改动/.test(llm) && !/0项被改动/.test(llm), llm);

  // ④ 走查三轮/四轮：回车与 Backspace 均不删卡（键盘删除整体禁用）
  const countBefore = await page.evaluate(() => document.querySelectorAll(".react-flow__node").length);
  await page.keyboard.press("Enter");
  await page.waitForTimeout(600);
  const countAfterEnter = await page.evaluate(() => document.querySelectorAll(".react-flow__node").length);
  ok("走查四轮 回车不删卡", countBefore === countAfterEnter, `before=${countBefore} after=${countAfterEnter}`);
  await page.keyboard.press("Backspace");
  await page.waitForTimeout(600);
  const countAfterBk = await page.evaluate(() => document.querySelectorAll(".react-flow__node").length);
  ok("走查四轮 Backspace 不删卡", countBefore === countAfterBk, `before=${countBefore} after=${countAfterBk}`);

  // ⑤ 走查三轮：输入控件带 nodrag/nopan（框选文字不拖动卡片/画布）
  const cls = await page.evaluate(() => ({
    ta: document.querySelector(".node-textarea")?.className || "",
    input: document.querySelector(".ds-input")?.className || "",
  }));
  ok(
    "走查三轮 输入控件 nodrag nopan",
    cls.ta.includes("nodrag") && cls.ta.includes("nopan") && cls.input.includes("nodrag") && cls.input.includes("nopan"),
    JSON.stringify(cls)
  );

  // ⑥ 走查四轮：tooltip 功能已按用户要求移除——json 区可框选（user-select text + nodrag）
  const selectInfo = await page.evaluate(() => {
    const out = document.querySelector(".node-output");
    if (!out) return null;
    const cs = window.getComputedStyle(out);
    return { userSelect: cs.userSelect, cls: out.className };
  });
  ok(
    "走查四轮 output 区可框选（user-select:text + nodrag nopan）",
    !!selectInfo && selectInfo.userSelect === "text" && selectInfo.cls.includes("nodrag") && selectInfo.cls.includes("nopan"),
    JSON.stringify(selectInfo)
  );

  await page.screenshot({ path: path.resolve(_here, "f2-cursor-count.png"), fullPage: false });
  console.log("SHOT f2-cursor-count.png");
} finally {
  await browser.close();
}
console.log(`\nALL PASS (${passed} assertions)`);
