// VERIFY_META: {"features": "GUI 全链路：Run All 左到右 → 答案出现 → 截图", "tier": "gui", "providers": [], "est_seconds": 120, "est_cost_cny": 0, "routes": ["/api/new_session", "/api/run_step", "/api/stream/{session_id}/{run_id}", "/api/session_records/{session_id}", "/api/reset_session"], "requires": ["playwright", "servers"]}

// GUI 全链路回归脚本（US-2.6 证据）：Run All 全链路 + 截图

// 运行前提：后端 8787 / 前端 5173 已启动：

//   node verify\gui_check.mjs

// playwright 为前端 node_modules 的 --no-save 安装：经 createRequire 显式定位。

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

  path.resolve(_here, "gui_check.png");

const browser = await chromium.launch({ headless: true });

const page = await browser.newPage({ viewport: { width: 1700, height: 1000 } });

await page.goto("http://127.0.0.1:5173", { waitUntil: "networkidle" });

await page.getByText("Run All (Left-to-Right)").click();

console.log("clicked Run All");

await page.waitForFunction(

  () => document.body.innerText.includes("Skarlinski"),

  null,

  { timeout: 600000 }

);

console.log("answer contains Skarlinski -> pipeline done");

await page.screenshot({ path: SHOT, fullPage: true });

console.log("SHOT_SAVED " + SHOT);

await browser.close();

