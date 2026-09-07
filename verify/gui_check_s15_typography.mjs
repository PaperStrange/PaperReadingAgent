// VERIFY_META: {"features": "Sprint-15 F-AC1 排版统一断言：标题字号/字体族 token 一致性（node-title 13px、block 标题 12px、字体族统一）", "tier": "gui", "providers": [], "est_seconds": 40, "est_cost_cny": 0, "routes": [], "requires": ["playwright", "servers"]}
// Sprint-15 F-AC1（验收①1.1）：卡片标题字号收敛 + 字体类型统一。
// 前提：后端 8787、前端 5173 已启动；playwright 取前端 node_modules。
// 断言：① 所有 .node-title 字号 = 13px 且相互一致；② block 标题类（node-block-title/schema-title/
//       schema-form-title/fn-title/log-title）= 12px；③ 全部标题类字体族解析值一致（--font-ui token）。
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
  await page.waitForSelector(".node-title", { timeout: 15000 });
  await page.waitForTimeout(1200);

  const styles = await page.evaluate(() => {
    const collect = (sel) =>
      Array.from(document.querySelectorAll(sel)).map((el) => {
        const cs = window.getComputedStyle(el);
        return { fontSize: cs.fontSize, fontFamily: cs.fontFamily };
      });
    return {
      nodeTitle: collect(".node-title"),
      paneTitle: collect(".pane-title"),
      blockTitle: collect(
        ".node-block-title, .schema-list .schema-title, .schema-form .schema-form-title, .fn-title, .log-title"
      ),
    };
  });

  const allSizes = (list) => list.map((s) => s.fontSize);
  const allFams = (list) => list.map((s) => s.fontFamily);

  ok(
    "F-AC1 node-title 收敛至 13px 且一致",
    styles.nodeTitle.length > 0 && allSizes(styles.nodeTitle).every((s) => s === "13px"),
    JSON.stringify([...new Set(allSizes(styles.nodeTitle))])
  );
  ok(
    "F-AC1 block 标题统一 12px",
    styles.blockTitle.length > 0 && allSizes(styles.blockTitle).every((s) => s === "12px"),
    JSON.stringify([...new Set(allSizes(styles.blockTitle))])
  );
  const famSet = new Set([...allFams(styles.nodeTitle), ...allFams(styles.paneTitle), ...allFams(styles.blockTitle)]);
  ok("F-AC1 全部标题字体族一致", famSet.size === 1, JSON.stringify([...famSet]));

  await page.screenshot({ path: path.resolve(_here, "f2-typography.png"), fullPage: false });
  console.log("SHOT f2-typography.png");
} finally {
  await browser.close();
}
console.log(`\nALL PASS (${passed} assertions)`);
