// VERIFY_META: {"features": "GUI 远程数据源：remote+arXiv → Run All → 截图", "tier": "gui", "providers": [], "est_seconds": 180, "est_cost_cny": 0, "routes": ["/api/new_session", "/api/run_step", "/api/stream/{session_id}/{run_id}", "/api/session_records/{session_id}", "/api/reset_session"], "requires": ["playwright", "servers", "network"]}

// GUI 远程数据源检查（US-3.4/US-3.5 证据）：Config 面板切 remote + arXiv → Run All → 截图

// 前提：后端 8787 / 前端 5173 已启动：node verify\gui_check_remote.mjs

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



// 截图输出：默认 verify/（两分支都存在）；可用环境变量 GUI_SHOT 覆盖（如指向 docs/iteration/sprint/）

const SHOT =

  process.env.GUI_SHOT ||

  path.resolve(_here, "gui_check_remote.png");

const browser = await chromium.launch({ headless: true });

const page = await browser.newPage({ viewport: { width: 1700, height: 1000 } });

await page.goto("http://127.0.0.1:5173", { waitUntil: "networkidle" });



// 1) 面板切 remote（Sprint-12 起 selector 指向 SchemaForm 的数据源下拉）

await page.locator(".ds-select.schema-field-datasource").selectOption("remote");

// 2) 第二个列表（arXiv ID）填 2409.13740

await page.locator(".ds-textarea").nth(1).fill("2409.13740");

await page.waitForTimeout(300);

// 3) 把 index_name 改为 remote_gui_idx（避免与本地 debug_index 互串）

const ta = page.locator(".node-textarea").first();

const jsonText = await ta.inputValue();

const params = JSON.parse(jsonText);

params.index_name = "remote_gui_idx";

await ta.fill(JSON.stringify(params, null, 2));

await page.waitForTimeout(300);



console.log("params.data_source =", params.data_source, "index =", params.index_name);

await page.getByText("Run All (Left-to-Right)").click();

console.log("clicked Run All");

await page.waitForFunction(

  () => document.body.innerText.includes("PaperQA2"),

  null,

  { timeout: 900000 }

);

console.log("answer contains PaperQA2 -> remote pipeline done");

await page.screenshot({ path: SHOT, fullPage: true });

console.log("SHOT_SAVED " + SHOT);

await browser.close();

