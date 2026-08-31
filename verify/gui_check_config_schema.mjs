// Sprint-11 US-11.3 截图：Config 节点的"配置唯一真源"分组字段清单（只读视图）。
// 前提：后端 8787 已启动（/api/config_schema 就绪）、前端 5173 已启动；playwright 取前端 node_modules。
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

await page.goto("http://127.0.0.1:5173/", { waitUntil: "networkidle" });
// 等待 schema 清单渲染（标题出现）
await page.waitForSelector(".schema-title", { timeout: 15000 });
await page.waitForTimeout(800);
await page.screenshot({ path: path.resolve(_here, "f2-config-schema.png"), fullPage: false });
console.log("SHOT f2-config-schema.png");

// 展开 Embedding 分组再截一张
await page.locator("details.schema-group summary", { hasText: "Embedding" }).first().click().catch(() => {});
await page.waitForTimeout(500);
await page.screenshot({ path: path.resolve(_here, "f2-config-schema-embedding.png"), fullPage: false });
console.log("SHOT f2-config-schema-embedding.png");

await browser.close();
