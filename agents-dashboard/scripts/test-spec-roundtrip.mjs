// US-9.3 保存往返测试（编码安全：Node 全程 UTF-8）
const base = "http://127.0.0.1:8600";
const get = await fetch(`${base}/api/specs/impact-assessment.md`);
const spec = await get.json();
const put = await fetch(`${base}/api/specs`, {
  method: "PUT",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ name: "impact-assessment.md", content: spec.content }),
});
const putRes = await put.json();
const get2 = await fetch(`${base}/api/specs/impact-assessment.md`);
const spec2 = await get2.json();
console.log("PUT:", putRes.ok, "| round-trip identical:", spec.content === spec2.content);
