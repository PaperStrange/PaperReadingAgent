// VERIFY_META: {"features": "Config schema 清单/全字段表单截图 + 字段级校验 + defaults-derived-from-schema 断言", "tier": "gui", "providers": [], "est_seconds": 60, "est_cost_cny": 0, "routes": ["/api/config_schema", "/api/config/validate"], "requires": ["playwright", "servers"]}

// Sprint-12（F2 阶段 B）Config 节点全字段表单截图 + 字段级校验证据。

// 前提：后端 8787（/api/config_schema + /api/config/validate 就绪）、前端 5173 已启动；playwright 取前端 node_modules。

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

try {

  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });



  await page.goto("http://127.0.0.1:5173/", { waitUntil: "networkidle" });

  await page.waitForSelector(".schema-form-title", { timeout: 15000 });

  await page.waitForTimeout(1200);

  // US-13.1：节点默认值由 schema 派生（无手写）——JSON 编辑区应含 schema 默认值

  const json0 = await page.locator(".node-textarea").first().inputValue();

  const derived = json0.includes("st-multi-qa-MiniLM-L6-cos-v1") && json0.includes('"chunk_chars": 5000');

  console.log("US-13.1 defaults-derived-from-schema:", derived ? "PASS" : "FAIL " + json0.slice(0, 120));

  await page.screenshot({ path: path.resolve(_here, "f2-schema-form.png"), fullPage: false });

  console.log("SHOT f2-schema-form.png");



  // 字段级校验证据：把 temperature 置为非法值（5），等防抖校验后截图错误态

  await page.evaluate(() => {

    const inputs = Array.from(document.querySelectorAll(".schema-field input[type=number]"));

    const el = inputs.find((i) => {

      const row = i.closest(".schema-field");

      return row && row.querySelector(".ds-label")?.textContent?.includes("温度");

    });

    if (!el) return;

    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;

    setter.call(el, "5");

    el.dispatchEvent(new Event("input", { bubbles: true }));

    el.dispatchEvent(new Event("change", { bubbles: true }));

  });

  await page.waitForTimeout(2500); // 防抖 600ms + 请求

  await page.screenshot({ path: path.resolve(_here, "f2-schema-form-validation.png"), fullPage: false });

  console.log("SHOT f2-schema-form-validation.png");

} finally {

  await browser.close();

}

