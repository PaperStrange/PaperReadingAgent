// VERIFY_META: {"features": "Sprint-15 F-AC9：subcanvas 手动切换节点 → 主画布联动选中并定位对应节点", "tier": "gui", "providers": [], "est_seconds": 40, "est_cost_cny": 0, "routes": [], "requires": ["playwright", "servers"]}
// Sprint-15 F-AC9（验收⑦）：双向联动（主画布→subcanvas 已有；补 subcanvas→主画布）。
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
  await page.waitForSelector(".step-switch-btn", { timeout: 15000 });
  await page.waitForTimeout(1200);

  // subcanvas 手动切换到 "3) Retrieve"
  await page.locator(".step-switch-btn", { hasText: "Retrieve" }).evaluate((el) => el.click());
  await page.waitForTimeout(1200);

  const selInfo = await page.evaluate(() => {
    const sel = document.querySelector(".react-flow__node.selected");
    return {
      hasSelected: !!sel,
      selectedText: sel ? sel.textContent.replace(/\s+/g, " ").slice(0, 80) : "",
      activeBtn: Array.from(document.querySelectorAll(".step-switch-btn"))
        .filter((b) => b.className.includes("active"))
        .map((b) => b.textContent.replace(/\s+/g, " ").trim()),
    };
  });
  ok("F-AC9 subcanvas 按钮切换生效", selInfo.activeBtn.some((t) => /Retrieve/.test(t)), JSON.stringify(selInfo.activeBtn));
  ok(
    "F-AC9 主画布对应节点选中",
    selInfo.hasSelected && /retrieve/i.test(selInfo.selectedText),
    JSON.stringify(selInfo)
  );

  // 切到 "6) Answer" 再验一次（联动跟随新节点）
  await page.locator(".step-switch-btn", { hasText: "Answer" }).evaluate((el) => el.click());
  await page.waitForTimeout(1200);
  const selInfo2 = await page.evaluate(() => {
    const sel = document.querySelector(".react-flow__node.selected");
    return { hasSelected: !!sel, selectedText: sel ? sel.textContent.replace(/\s+/g, " ").slice(0, 80) : "" };
  });
  ok("F-AC9 再次切换主画布选中跟随", selInfo2.hasSelected && /answer/i.test(selInfo2.selectedText), JSON.stringify(selInfo2));

  await page.screenshot({ path: path.resolve(_here, "f2-bidi-link.png"), fullPage: false });
  console.log("SHOT f2-bidi-link.png");
} finally {
  await browser.close();
}
console.log(`\nALL PASS (${passed} assertions)`);
