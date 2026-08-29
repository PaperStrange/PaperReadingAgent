import React from "react";

function linesToArr(text) {
  return (text || "")
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
}

// Config 节点的「数据源」切换面板（Sprint-3 US-3.4）：
// 编辑同一份 params JSON（经 onChange 回写），不破坏原有 JSON 编辑区。
export default function DataSourcePanel({ params, onChange }) {
  const mode = params?.data_source || "local";
  const urls = (params?.source_urls || []).join("\n");
  const arxivIds = (params?.source_arxiv_ids || []).join("\n");
  const dois = (params?.source_dois || []).join("\n");
  const manifest = params?.manifest_file || "";

  const update = (patch) => {
    const next = { ...(params || {}), ...patch };
    onChange(JSON.stringify(next, null, 2));
  };

  return (
    <div className="data-source-panel">
      <div className="node-block-title">数据源</div>
      <label className="ds-row">
        <span className="ds-label">模式</span>
        <select
          className="ds-select"
          value={mode}
          onChange={(e) => update({ data_source: e.target.value })}
        >
          <option value="local">local（本地论文目录）</option>
          <option value="remote">remote（URL/arXiv/DOI 下载）</option>
        </select>
      </label>

      {mode === "remote" ? (
        <>
          <label className="ds-row">
            <span className="ds-label">URL 列表</span>
            <span className="ds-sub">每行一个（http/https 直链）</span>
          </label>
          <textarea
            className="ds-textarea"
            value={urls}
            placeholder="https://.../paper.pdf"
            onChange={(e) => update({ source_urls: linesToArr(e.target.value) })}
          />

          <label className="ds-row">
            <span className="ds-label">arXiv ID 列表</span>
            <span className="ds-sub">每行一个，如 2409.13740</span>
          </label>
          <textarea
            className="ds-textarea"
            value={arxivIds}
            placeholder="2409.13740"
            onChange={(e) => update({ source_arxiv_ids: linesToArr(e.target.value) })}
          />

          <label className="ds-row">
            <span className="ds-label">DOI 列表</span>
            <span className="ds-sub">每行一个；需环境变量 UNPAYWALL_EMAIL</span>
          </label>
          <textarea
            className="ds-textarea"
            value={dois}
            placeholder="10.xxxx/yyyy"
            onChange={(e) => update({ source_dois: linesToArr(e.target.value) })}
          />
        </>
      ) : null}

      <label className="ds-row">
        <span className="ds-label">Manifest 清单</span>
        <span className="ds-sub">可选：元数据 CSV/JSON</span>
      </label>
      <input
        className="ds-input"
        value={manifest}
        placeholder="meta.csv（相对论文目录或绝对路径）"
        onChange={(e) => update({ manifest_file: e.target.value })}
      />

      <div className="ds-hint">
        下载暂存 data/remote/&lt;index_name&gt;/；切换模式/数据源后需重建索引。
      </div>
    </div>
  );
}
