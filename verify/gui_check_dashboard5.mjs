// 记录 /specs 页面所有网络响应状态
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
const page = await browser.newPage();
page.on("response", (res) => {
  if (res.url().includes("/api/") || res.status() >= 400) {
    console.log("[resp]", res.status(), res.url());
  }
});
await page.goto("http://127.0.0.1:8600/specs", { waitUntil: "networkidle" });
await page.waitForTimeout(4000);
const btns = await page.locator("aside button").count();
console.log("[aside buttons]", btns);
const body = await page.evaluate(() => document.body.innerText.slice(0, 300));
console.log("[body]", body);
await browser.close();
