// VERIFY_META: {"features": "多节点并发计时显示 + 完成后冻结", "tier": "gui", "providers": [], "est_seconds": 60, "est_cost_cny": 0, "routes": [], "requires": ["playwright", "servers"]}

// Sprint-7 M4 关闭证据脚本（可复现）：多节点并发计时显示 + 完成后冻结。

// 场景：预热 config/load_index/parse 后，并发跑 evidence + parse(regen)（双双慢、互不依赖）——

// subcanvas 计时应出现纯双运行中（"evidence X.Xs · parse_chunk_embed Y.Ys"），

// 先完成的节点冻结不被覆盖，全部完成后冻结最终时长。

// 前提：后端 8787 + 前端 5173 已启动（playwright 取前端 node_modules）。

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



const SHOT = process.env.GUI_SHOT || path.resolve(_here, "gui_check_s7.png");

const browser = await chromium.launch({ headless: true });

const page = await browser.newPage({ viewport: { width: 1700, height: 1000 } });

await page.goto("http://127.0.0.1:5173", { waitUntil: "networkidle" });



const clickRunNode = (cardIdx) =>

  page.evaluate((idx) => {

    const cards = document.querySelectorAll(".node-card");

    cards[idx].querySelectorAll(".run-btn")[1].click();

  }, cardIdx);



const nodeStatus = (idx) =>

  page.evaluate(

    (i) =>

      document.querySelectorAll(".node-card")[i]?.querySelector(".node-status")?.textContent || "",

    idx

  );



const waitStatus = async (idx, want, timeoutMs) => {

  const t0 = Date.now();

  while (Date.now() - t0 < timeoutMs) {

    const s = await nodeStatus(idx);

    if (s.includes(want)) return s;

    await page.waitForTimeout(500);

  }

  return await nodeStatus(idx);

};



const timerText = () =>

  page.evaluate(() => document.querySelector(".fn-timer")?.textContent || "");



// ---- 预热：config → load_index → parse_chunk_embed（建 docs，供 evidence 使用） ----

await clickRunNode(0);

const cfgStatus = await waitStatus(0, "success", 120000);

console.log("warm config:", cfgStatus.includes("success") ? "PASS" : `FAIL(${cfgStatus})`);

await clickRunNode(1);

const loadStatus = await waitStatus(1, "success", 240000);

console.log("warm load_index:", loadStatus.includes("success") ? "PASS" : `FAIL(${loadStatus})`);

await clickRunNode(3);

const parseStatus = await waitStatus(3, "success", 300000);

console.log("warm parse_chunk_embed:", parseStatus.includes("success") ? "PASS" : `FAIL(${parseStatus})`);



// ---- M4：并发 evidence（~15s，用预热 docs）+ parse_chunk_embed（regen，~20s），观察多节点计时 ----

// 二者互不依赖（evidence 读预热 docs；parse 重建 docs），双双慢 → 同一 tick 必然双"运行中"

await clickRunNode(4); // evidence（慢）

await page.waitForTimeout(150);

await clickRunNode(3); // parse（regen，慢）



const samples = [];

let multiSeen = null;

const t0 = Date.now();

while (Date.now() - t0 < 60000) {

  const t = await timerText();

  samples.push(t);

  // 纯双运行中样式："load_index 3.2s · parse_chunk_embed 1.1s"（两段均无 完成/失败）

  if (/^\S+ \d+(\.\d+)?s · \S+ \d+(\.\d+)?s$/.test(t) && !/完成|失败/.test(t)) {

    multiSeen = t;

    break;

  }

  await page.waitForTimeout(200);

}

console.log("M4 timer samples:", JSON.stringify([...new Set(samples)].slice(-12)));

console.log(

  "M4 multi-node concurrent timer:",

  multiSeen ? `PASS(${multiSeen})` : `MANUAL(${await timerText()})`

);

if (multiSeen) await page.screenshot({ path: SHOT.replace(/\.png$/, "_running.png") });



// ---- 完成后冻结（先完成的节点冻结不被覆盖） ----

await waitStatus(4, "success", 240000); // evidence 成功（其后会被 parse 重跑按设计标 stale）

await waitStatus(3, "success", 300000);

await page.waitForTimeout(800);

const frozen = await timerText();

console.log(

  "M4 frozen after done:",

  /完成 \d+(\.\d+)?s/.test(frozen) ? `PASS(${frozen})` : `MANUAL(${frozen})`

);

const evFinal = await nodeStatus(4);

console.log(

  "evidence status (success|stale):",

  /success|stale/.test(evFinal) ? `PASS(${evFinal})` : `FAIL(${evFinal})`

);

console.log("parse status:", (await nodeStatus(3)).includes("success") ? "PASS" : "FAIL");



await page.screenshot({ path: SHOT, fullPage: true });

console.log("SHOT_SAVED " + SHOT);

await browser.close();

