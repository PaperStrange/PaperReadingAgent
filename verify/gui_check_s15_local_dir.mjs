// VERIFY_META: {"features": "Sprint-15 F-AC3：local 模式显示论文目录并隐藏远程源三字段、remote 模式恢复；Index 组不再含论文目录", "tier": "gui", "providers": [], "est_seconds": 45, "est_cost_cny": 0, "routes": ["/api/config_schema"], "requires": ["playwright", "servers"]}
// Sprint-15 F-AC3（验收①1.3）：数据源条件可见 + 本地路径入口。
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
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto("http://127.0.0.1:5173/", { waitUntil: "networkidle" });
  await page.waitForSelector(".schema-group summary", { timeout: 15000 });
  await page.waitForTimeout(1200);

  // 定位数据源组（summary 含"数据源"）
  const labelsOf = (groupText) =>
    page.evaluate((gt) => {
      const details = Array.from(document.querySelectorAll(".schema-group")).find((d) =>
        d.querySelector("summary")?.textContent?.includes(gt)
      );
      if (!details) return [];
      return Array.from(details.querySelectorAll(".ds-label")).map((l) => l.textContent.replace(" 🔒", ""));
    }, groupText);

  // ① local 模式（默认）：数据源组含"本地论文目录"，隐藏 URL/arXiv/DOI
  const localLabels = await labelsOf("数据源");
  ok(
    "F-AC3 local 显示本地论文目录",
    localLabels.includes("本地论文目录"),
    JSON.stringify(localLabels)
  );
  ok(
    "F-AC3 local 隐藏远程三字段",
    !localLabels.includes("URL 列表") && !localLabels.includes("arXiv ID 列表") && !localLabels.includes("DOI 列表"),
    JSON.stringify(localLabels)
  );

  // ② Index 组不再含论文目录字段
  const indexLabels = await labelsOf("Index");
  ok(
    "F-AC3 Index 组移除论文目录",
    !indexLabels.some((l) => l.includes("论文目录")),
    JSON.stringify(indexLabels)
  );

  // ③ 切 remote：三字段恢复可见
  await page.evaluate(() => {
    const sel = document.querySelector(".schema-field-datasource");
    if (!sel) return;
    const setter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, "value").set;
    setter.call(sel, "remote");
    sel.dispatchEvent(new Event("change", { bubbles: true }));
  });
  await page.waitForTimeout(1500);
  const remoteLabels = await labelsOf("数据源");
  ok(
    "F-AC3 remote 恢复远程三字段",
    remoteLabels.includes("URL 列表") && remoteLabels.includes("arXiv ID 列表") && remoteLabels.includes("DOI 列表"),
    JSON.stringify(remoteLabels)
  );

  // ④ 切回 local：再次隐藏（联动可逆）
  await page.evaluate(() => {
    const sel = document.querySelector(".schema-field-datasource");
    if (!sel) return;
    const setter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, "value").set;
    setter.call(sel, "local");
    sel.dispatchEvent(new Event("change", { bubbles: true }));
  });
  await page.waitForTimeout(1500);
  const backLabels = await labelsOf("数据源");
  ok(
    "F-AC3 切回 local 再次隐藏",
    !backLabels.includes("URL 列表"),
    JSON.stringify(backLabels)
  );

  await page.screenshot({ path: path.resolve(_here, "f2-local-dir.png"), fullPage: false });
  console.log("SHOT f2-local-dir.png");
} finally {
  await browser.close();
}
console.log(`\nALL PASS (${passed} assertions)`);
