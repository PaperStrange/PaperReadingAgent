// 017 修复验收：POST dry-run 校验语义 + 畸形请求体 400 + 空管线 400（Node UTF-8 客户端）
import fs from "node:fs";

const c = fs.readFileSync(new URL("../../agents/fanout.json", import.meta.url), "utf-8");

const j = async (method, body) => {
  const r = await fetch("http://127.0.0.1:8600/api/fanout", {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : typeof body === "string" ? body : JSON.stringify(body),
  });
  return { status: r.status, body: await r.text() };
};

const g = await j("GET");
const gd = JSON.parse(g.body);
console.log("GET valid=" + gd.valid + " version=" + (gd.parsed && gd.parsed.version));

const p = await j("POST", { content: c });
console.log("POST dry-run status=" + p.status + " body=" + p.body);

const bad = await j("POST", "{not-json");
console.log("POST malformed-body status=" + bad.status + " (expect 400)");

const inv = await j("PUT", { content: '{"version":2,"planning_pipeline":[],"sprint_close_pipeline":[]}' });
console.log("PUT empty-pipelines status=" + inv.status + " (expect 400)");

const after = fs.readFileSync(new URL("../../agents/fanout.json", import.meta.url), "utf-8");
console.log("file unchanged after POST dry-run: " + (after === c));
