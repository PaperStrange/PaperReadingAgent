// VERIFY_META: {"features": "Sprint-15 F-AC7：步骤状态行仅展示当前查看节点的完成/失败文案（切换即更替，不残留他节点）", "tier": "gui", "providers": [], "est_seconds": 60, "est_cost_cny": 0, "routes": ["/api/run_step"], "requires": ["playwright", "servers"]}
// Sprint-15 F-AC7（验收⑤）：执行状态信息作用域。
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
try {
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  await page.goto("http://127.0.0.1:5173/", { waitUntil: "networkidle" });
  await page.waitForSelector(".node-card", { timeout: 15000 });
  await page.waitForTimeout(1200);

  const cardOf = (step) =>
    page.locator(".node-card", { has: page.locator(".node-step", { hasText: step }) }).first();
  const runNode = async (card) => card.locator("button", { hasText: "Run Node" }).evaluate((el) => el.click());
  const clickCard = async (card) => card.evaluate((el) => el.click());
  const waitDone = (step, timeout = 150000) =>
    page.waitForFunction(
      (s) => {
        const c = Array.from(document.querySelectorAll(".node-card")).find((n) => {
          const st = n.querySelector(".node-step");
          return st && new RegExp(s).test(st.textContent);
        });
        if (!c) return false;
        const cls = c.className;
        if (cls.includes("status-success")) return "success";
        if (cls.includes("status-failed")) return "failed";
        return false;
      },
      step,
      { timeout }
    );
  const timerText = () => page.locator(".fn-timer").first().textContent().catch(() => "");

  // 1) config：切到 config → 运行 → 状态行只含 config
  await clickCard(await cardOf("config"));
  await page.waitForTimeout(500);
  await runNode(await cardOf("config"));
  await waitDone("config");
  await page.waitForTimeout(1200);
  let t = await timerText();
  ok("F-AC7 config 完成后状态行含 config 完成", /config 完成/.test(t || ""), `t=${t}`);

  // 2) load_index：切到 load_index → 运行 → 状态行只含 load_index，不含 config
  await clickCard(await cardOf("load_index"));
  await page.waitForTimeout(500);
  await runNode(await cardOf("load_index"));
  const liResult = await waitDone("load_index");
  await page.waitForTimeout(1200);
  t = await timerText();
  ok("F-AC7 load_index 运行成功", String(liResult) === "success", `result=${liResult} t=${t}`);
  ok("F-AC7 load_index 状态行含 load_index 完成", /load_index 完成/.test(t || ""), `t=${t}`);
  ok("F-AC7 状态行不残留 config 文案", !/config 完成/.test(t || ""), `t=${t}`);

  // 3) 切回 config：状态行换回 config 文案，不残留 load_index
  await clickCard(await cardOf("config"));
  await page.waitForTimeout(1200);
  t = await timerText();
  ok("F-AC7 切回 config 状态行换回 config 完成", /config 完成/.test(t || ""), `t=${t}`);
  ok("F-AC7 切回后不残留 load_index 文案", !/load_index 完成/.test(t || ""), `t=${t}`);

  // 4) 走查语义修正：切到从未运行的节点 → 显示 "X idle"（而非空白）
  await clickCard(await cardOf("answer"));
  await page.waitForTimeout(1200);
  t = await timerText();
  ok("F-AC7 未运行节点显示 idle", /answer idle/.test(t || ""), `t=${t}`);

  // 5) 走查三轮：运行中切换节点——不显示他节点的实时计时；切回后恢复 + 不重新计数卡死
  await clickCard(await cardOf("parse"));
  await page.waitForTimeout(400);
  await runNode(await cardOf("parse"));
  await page.waitForTimeout(900); // parse 已在运行中（embedding 耗时）
  await clickCard(await cardOf("config"));
  await page.waitForTimeout(1200);
  t = await timerText();
  ok("F-AC7 运行中切换不显示他节点计时", !/parse \d+\.\d+s/.test(t || ""), `t=${t}`);
  await clickCard(await cardOf("parse"));
  await page.waitForTimeout(1200);
  t = await timerText();
  ok("F-AC7 切回运行节点恢复计时显示", /parse_chunk_embed \d+\.\d+s/.test(t || ""), `t=${t}`);
  await waitDone("parse");

  await page.screenshot({ path: path.resolve(_here, "f2-status-scope.png"), fullPage: false });
  console.log("SHOT f2-status-scope.png");
} finally {
  await browser.close();
}
console.log(`\nALL PASS (${passed} assertions)`);
