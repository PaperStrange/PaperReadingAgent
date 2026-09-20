// VERIFY_META: {"features": "F-AC16 v1：Checkpoints 只读面板（开关/命名空间/逐篇载荷路径/复制按钮）+ /api/checkpoints 形状", "tier": "gui", "providers": [], "est_seconds": 40, "est_cost_cny": 0, "routes": ["/api/checkpoints"], "requires": ["playwright", "servers"]}
// F-AC16 v1（用户走查 CK-1）：让 pro 用户**直接看到**本地已有哪些 checkpoint、逐篇载荷路径在哪，
// 以便按路径定位、用既有 checkpoint 单独复现、人工核查是否幻觉。
// 零成本：只读面板 + API 形状断言，**不触发任何 LLM 调用**（不点运行按钮）。
// 前提：后端 8787 + 前端 5173 已启动；playwright 取前端 node_modules。
import { createRequire } from "module";
import path from "path";
import { fileURLToPath } from "url";

const _here = path.dirname(fileURLToPath(import.meta.url));
const _frontendNm = path.resolve(_here, "../paper-qa-script/reactflow-paperqa-prototype/frontend/node_modules");
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

// ① API 形状（node 侧直连，不经过浏览器）
const api = await (await fetch("http://127.0.0.1:8787/api/checkpoints")).json();
const list = api.checkpoints || [];
ok("① /api/checkpoints 返回 root 与列表", typeof api.root === "string" && api.root.length > 0 && Array.isArray(list),
  `root=${api.root} count=${list.length}`);
if (list.length) {
  const c = list[0];
  ok("① 命名空间字段齐备（key/manifest/status/docs）",
    !!c.checkpoint_key && !!c.manifest_path && !!c.status && typeof c.docs_total === "number",
    JSON.stringify({ key: c.checkpoint_key, status: c.status, docs: c.docs_total }));
  const withPayload = (c.docs || []).find((d) => d.payload_exists);
  ok("① 至少一篇带存在的载荷路径（可定位/可复现）",
    !!withPayload && withPayload.payload_path.endsWith(".json.gz") && withPayload.payload_bytes > 0,
    withPayload ? `bytes=${withPayload.payload_bytes}` : "no payload doc in first namespace");
}

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto("http://127.0.0.1:5173/", { waitUntil: "networkidle" });

  // ② 面板开关
  await page.waitForSelector('[data-testid="checkpoint-toggle"]', { timeout: 15000 });
  await page.locator('[data-testid="checkpoint-toggle"]').click();
  await page.waitForSelector('[data-testid="checkpoint-panel"]', { timeout: 15000 });
  ok("② 点击工具按钮后面板出现", true);

  // ③ 面板内容：根路径 + 真实命名空间行
  const rootText = await page.locator(".ck-panel-root").first().innerText();
  ok("③ 面板展示 checkpoint 根路径", rootText.includes(".pqa"), rootText);
  const itemCount = await page.locator('[data-testid="checkpoint-item"]').count();
  ok("③ 渲染出真实命名空间行（>0）", itemCount > 0, `items=${itemCount}`);
  ok("③ 行数与 API 一致", itemCount === list.length, `ui=${itemCount} api=${list.length}`);

  // ④ 展开明细 → 逐篇载荷路径 + 复制按钮
  await page.locator('[data-testid="checkpoint-item"]').first().locator("button", { hasText: "展开明细" }).click();
  await page.waitForTimeout(400);
  const pathCount = await page.locator(".ck-path").count();
  ok("④ 展开后出现逐篇载荷路径", pathCount > 0, `paths=${pathCount}`);
  const firstPath = pathCount ? await page.locator(".ck-path").first().innerText() : "";
  ok("④ 路径形如 <key>/<dockey>.json.gz（可定位/可复现）", /\.json\.gz/.test(firstPath), firstPath.slice(-60));
  const copyBtn = await page.locator("button.ck-copy-payload").count();
  ok("④ 提供『复制路径』按钮（pro 用户据此复现）", copyBtn > 0, `buttons=${copyBtn}`);

  await page.screenshot({ path: path.resolve(_here, "fac16-checkpoint-panel.png"), fullPage: false });
  console.log("SHOT fac16-checkpoint-panel.png");
} finally {
  await browser.close();
}

console.log(`\n${failed.length ? "FAILED" : "ALL PASS"} (${passed} assertions)${failed.length ? "：" + failed.join(", ") : ""}`);
process.exitCode = failed.length ? 1 : 0;
