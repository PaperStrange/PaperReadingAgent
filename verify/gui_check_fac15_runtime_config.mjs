// VERIFY_META: {"features": "F-AC15 v1：运行参数只读面（/api/config_schema.runtime 形状 + 前端面板 env/spec/schedule 只读展示、面板内无可编辑控件、密钥/内部指标不外泄）", "tier": "gui", "providers": [], "est_seconds": 40, "est_cost_cny": 0, "routes": ["/api/config_schema"], "requires": ["playwright", "servers"]}
// F-AC15 v1（用户走查 B-15）：把只在 CLI/env/spec 里的运行参数做成前端**只读**面；可编辑留待后续。
// 范围边界：只展示 `GET /api/config_schema.runtime`（env 生效值 / schedule.json / tech-research.md 阈值表），
// 不写回、不新增 API 路由、不展示密钥类与内部指标文件。
//
// 反向对照（TG-6 ⑤，适用于"新增可见面"）：修复前（HEAD e1c6cdb）没有 runtime 段与面板 →
// 本脚本「/api/config_schema.runtime 存在」与「面板出现」两条断言必 FAIL。
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

// ① 后端形状（node 侧直连）
const schema = await (await fetch("http://127.0.0.1:8787/api/config_schema")).json();
const rt = schema.runtime;
ok("① /api/config_schema 保持 version=1 + 7 分组（runtime 为附加段）",
  schema.version === 1 && Array.isArray(schema.groups) && schema.groups.length === 7,
  `version=${schema.version} groups=${schema.groups?.length}`);
ok("① 存在 runtime 只读段且 editable=false", !!rt && rt.v === 1 && rt.editable === false,
  rt ? `v=${rt.v} editable=${rt.editable}` : "missing runtime");
const env = rt?.env || [];
const spec = rt?.spec || [];
const sched = rt?.schedule || {};
const expectedEnv = [
  "PAPERQA_PROVIDER",
  "PAPERQA_PROVIDER_INTERVAL_DAYS",
  "PAPERQA_NIGHTLY_BUDGET_CNY",
  "PAPERQA_SCHEDULE_PRICES_DAYS",
  "PAPERQA_SCHEDULE_NIGHTLY_SUITE_DAYS",
  "PAPERQA_SCHEDULE_PROVIDERS_DAYS",
  "PAPERQA_SCHEDULE_STATE",
  "PAPERQA_LITELLM_CALLBACK_LIMIT",
  "PAPERQA_EMBED_RECOMMEND_LIVE",
];
const envNames = env.map((e) => e.name);
ok("① 9 个 env 全部有只读行（含默认值/读取点）",
  expectedEnv.every((n) => envNames.includes(n)) &&
    env.every((e) => e.default !== undefined && e.read_point && e.label),
  `env=${envNames.length} ${envNames.join(",")}`);
ok("① 密钥类 / 内部指标文件不入面",
  !JSON.stringify(rt || {}).includes("PAPERQA_PROVIDERS_JSON") &&
    !JSON.stringify(rt || {}).includes("PAPERQA_SUITE_METRICS"));
ok("① spec 阈值表解析出 ≥6 行且含 min_sources_per_claim/timebox",
  spec.length >= 6 &&
    spec.some((s) => s.parameter === "min_sources_per_claim") &&
    spec.some((s) => s.parameter === "timebox"),
  `rows=${spec.length} keys=${spec.map((s) => s.parameter).join(",")}`);
ok("① schedule 只读视图给出路径与预算字段",
  typeof sched.path === "string" && /schedule\.json/.test(sched.path) && "budget_cny" in sched,
  `path=${sched.path} budget=${sched.budget_cny} exists=${sched.exists}`);

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1700, height: 1000 } });
  await page.goto("http://127.0.0.1:5173/", { waitUntil: "networkidle" });
  await page.waitForSelector('[data-testid="runtime-config-toggle"]', { timeout: 15000 });

  // ② 开关 → 面板出现
  await page.locator('[data-testid="runtime-config-toggle"]').click();
  await page.waitForSelector('[data-testid="runtime-config-panel"]', { timeout: 15000 });
  ok("② 点击「运行参数（只读）」面板出现", true);

  // ③ 只读声明 + 三块内容
  const note = await page.locator('[data-testid="runtime-readonly-note"]').innerText();
  ok("③ 面板显式声明『只读』且不提可编辑控件", /只读/.test(note), note.trim());
  await page
    .waitForFunction(
      (n) => document.querySelectorAll('[data-testid="runtime-env-row"]').length === n,
      env.length,
      { timeout: 15000 }
    )
    .catch(() => {});
  const envRows = await page.locator('[data-testid="runtime-env-row"]').count();
  ok("③ env 行数与 API 一致", envRows === env.length, `ui=${envRows} api=${env.length}`);
  const specRows = await page.locator('[data-testid="runtime-spec-row"]').count();
  ok("③ spec 行数与 API 一致", specRows === spec.length, `ui=${specRows} api=${spec.length}`);
  const scheduleText = await page.locator('[data-testid="runtime-schedule"]').innerText();
  ok("③ 调度区展示 schedule.json 路径与预算",
    /schedule\.json/.test(scheduleText) && scheduleText.includes("预算上限"),
    scheduleText.replace(/\s+/g, " ").slice(0, 120));

  // ④ 只读：面板内没有任何 input/textarea/select/contenteditable
  const editable = await page.evaluate(() => {
    const p = document.querySelector('[data-testid="runtime-config-panel"]');
    return {
      controls: p.querySelectorAll("input, textarea, select").length,
      editable: p.querySelectorAll('[contenteditable="true"]').length,
    };
  });
  ok("④ 面板内无可编辑控件（v1 只读边界）",
    editable.controls === 0 && editable.editable === 0,
    `controls=${editable.controls} contenteditable=${editable.editable}`);

  // ⑤ 生效值展示：默认值行必须显式标「默认」
  const defaultRow = page.locator('[data-testid="runtime-env-row"]', { hasText: "PAPERQA_NIGHTLY_BUDGET_CNY" }).first();
  const defaultText = await defaultRow.innerText();
  ok("⑤ 未设置 env 的行展示默认值并标『默认』",
    /10（默认）/.test(defaultText), defaultText.replace(/\s+/g, " ").slice(0, 120));

  await page.screenshot({ path: path.resolve(_here, "fac15-runtime-config.png") });
  console.log("SHOT fac15-runtime-config.png");
} finally {
  await browser.close();
}

console.log(`\nFAC15 ${failed.length ? "FAIL" : "PASS"} (${passed} passed, ${failed.length} failed)`);
process.exitCode = failed.length ? 1 : 0;
