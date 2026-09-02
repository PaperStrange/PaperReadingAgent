// VERIFY_META: {"features": "看板报告浏览页截图（run 详情+报告全文）", "tier": "gui", "providers": [], "est_seconds": 30, "est_cost_cny": 0, "routes": [], "requires": ["playwright", "dashboard"]}

// Sprint-9 US-9.5 截图：报告浏览页（打开一条真实 run）

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



const browser = await chromium.launch({ headless: true });

const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });



const list = await (await fetch("http://127.0.0.1:8600/api/runs?limit=1")).json();

const runId = list.rows[0]?.run_id;

if (runId) {

  await page.goto(`http://127.0.0.1:8600/runs/${encodeURIComponent(runId)}`, { waitUntil: "networkidle" });

  await page.waitForTimeout(1200);

  await page.screenshot({ path: path.resolve(_here, "dashboard-report.png"), fullPage: false });

  console.log("SHOT dashboard-report.png for", runId);

} else {

  console.log("no runs to browse");

}

await browser.close();

