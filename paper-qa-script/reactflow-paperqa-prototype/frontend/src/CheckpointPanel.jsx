/* F-AC16 v1：checkpoint 只读索引的前端面板（用户在走查 CK-1 中要求"能看到载入了哪些 checkpoint 文件"）。
 *
 * 展示内容（全部只读，均来自 GET /api/checkpoints）：
 * - 本地命名空间列表：key 摘要、状态（ready/partial/corrupt）、论文目录、索引名、嵌入模型、切块口径、更新时间；
 * - 每个命名空间展开后的逐篇文献行：文件名、dockey、状态、texts 数、载荷路径（可一键复制，便于
 *   按路径定位 / 用既有 checkpoint 单独复现 / 人工核查是否幻觉）、载荷字节数（缺失会显式标红）。
 */
import React, { useEffect, useState } from "react";

const STATUS_TEXT = {
  ready: "就绪",
  partial: "部分完成",
  corrupt: "manifest 损坏",
  error: "失败",
  deduped: "内容去重",
  unknown: "未知",
};

function statusClass(status) {
  if (status === "ready" || status === "deduped") return "ck-status-ok";
  if (status === "partial") return "ck-status-warn";
  return "ck-status-bad";
}

export default function CheckpointPanel({ apiBase, onClose }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [copiedPath, setCopiedPath] = useState("");
  const [expanded, setExpanded] = useState({});

  const load = async () => {
    setErr("");
    try {
      const r = await fetch(`${apiBase}/api/checkpoints`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setData(await r.json());
    } catch (e) {
      setErr(String(e?.message || e));
    }
  };

  useEffect(() => {
    load();
  }, [apiBase]);

  const copy = async (text) => {
    try {
      if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(text || "");
      setCopiedPath(text);
      setTimeout(() => setCopiedPath(""), 1500);
    } catch {
      /* 降级：忽略 */
    }
  };

  const items = data?.checkpoints || [];

  return (
    <div className="ck-panel nodrag nopan" data-testid="checkpoint-panel">
      <div className="ck-panel-head">
        <strong>本地 Checkpoints</strong>
        <span className="ck-panel-root" title={data?.root || ""}>
          {data?.root || "…"}
        </span>
        <button className="run-btn" onClick={load}>刷新</button>
        <button className="run-btn" onClick={onClose}>关闭</button>
      </div>
      {err ? <div className="ck-error">读取失败：{err}</div> : null}
      {!err && data && items.length === 0 ? (
        <div className="ck-empty">本地暂无 checkpoint（首次运行 parse_chunk_embed 后生成）</div>
      ) : null}
      {items.map((ck) => (
        <div className="ck-item" key={ck.checkpoint_key} data-testid="checkpoint-item">
          <div className="ck-item-head">
            <code className="ck-key">{ck.checkpoint_key}</code>
            <span className={`ck-status ${statusClass(ck.status)}`}>{STATUS_TEXT[ck.status] || ck.status}</span>
            <span className="ck-meta">文献 {ck.docs_total}（{Object.entries(ck.docs_by_status || {}).map(([k, v]) => `${STATUS_TEXT[k] || k}:${v}`).join(" ")}）</span>
            <span className="ck-meta">载荷 {(ck.payload_bytes_total || 0)} B</span>
            <button
              className="run-btn"
              onClick={() => setExpanded((s) => ({ ...s, [ck.checkpoint_key]: !s[ck.checkpoint_key] }))}
            >
              {expanded[ck.checkpoint_key] ? "收起明细" : "展开明细"}
            </button>
            <button className="run-btn ck-copy-manifest" onClick={() => copy(ck.manifest_path)}>
              {copiedPath === ck.manifest_path ? "已复制 ✓" : "复制 manifest 路径"}
            </button>
          </div>
          <div className="ck-meta ck-sub">
            {ck.embedding_model || "—"} · chunk {ck.chunk_chars ?? "—"}/{ck.chunk_overlap ?? "—"} ·{" "}
            {ck.index_name || "—"} · {ck.paper_dir || "—"}
          </div>
          {ck.readable === false ? <div className="ck-error">该 manifest 无法解析：{ck.error}</div> : null}
          {expanded[ck.checkpoint_key] ? (
            <table className="ck-docs">
              <thead>
                <tr>
                  <th>文献</th>
                  <th>dockey</th>
                  <th>状态</th>
                  <th>texts</th>
                  <th>载荷路径</th>
                </tr>
              </thead>
              <tbody>
                {(ck.docs || []).map((d) => (
                  <tr key={`${d.name}-${d.dockey}`}>
                    <td title={d.name}>{d.docname || d.name}</td>
                    <td><code>{d.dockey || "—"}</code></td>
                    <td className={statusClass(d.status)}>{STATUS_TEXT[d.status] || d.status}</td>
                    <td>{d.texts_count}</td>
                    <td>
                      {d.payload_path ? (
                        <>
                          <button className="run-btn ck-copy-payload" onClick={() => copy(d.payload_path)}>
                            {copiedPath === d.payload_path ? "已复制 ✓" : "复制路径"}
                          </button>
                          <code className={d.payload_exists ? "ck-path" : "ck-path ck-path-missing"}>
                            {d.payload_exists ? d.payload_path : `${d.payload_path}（缺失）`}
                          </code>
                        </>
                      ) : (
                        <span className="ck-meta">无独立载荷（内容去重）</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </div>
      ))}
    </div>
  );
}
