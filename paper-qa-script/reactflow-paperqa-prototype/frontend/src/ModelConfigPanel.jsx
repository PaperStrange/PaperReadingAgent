import React, { useEffect, useState } from "react";

// Config 节点「模型配置」面板（Sprint-4 US-4.5）：
// provider 下拉（/api/providers 动态列表）→ 自动带出 api_base / model / vision_model / embedding_model；
// embedding 支持「自动（按 provider 判断）」与「手动」两种模式；全部写回同一 params JSON。
export default function ModelConfigPanel({ params, apiBase, onChange }) {
  const [providers, setProviders] = useState([]);

  useEffect(() => {
    if (!apiBase) return;
    let cancelled = false;
    fetch(`${apiBase}/api/providers`)
      .then((r) => r.json())
      .then((d) => {
        if (!cancelled && Array.isArray(d?.providers)) setProviders(d.providers);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [apiBase]);

  const currentProvider = params?.provider || "";
  const providerInfo = providers.find((p) => p.name === currentProvider) || null;
  // embedding 自动 = params 中没有 embedding_model（后端 recommender 按 provider 判断）
  const embedAuto = !params?.embedding_model;

  const update = (patch) => {
    const next = { ...(params || {}), ...patch };
    onChange(JSON.stringify(next, null, 2));
  };

  const onProviderChange = (name) => {
    const info = providers.find((p) => p.name === name);
    const patch = { provider: name };
    if (info) {
      patch.api_base = info.api_base || "";
      patch.model = info.model || "";
      patch.vision_model = info.vision_model || "";
      if (info.has_embedding_api && info.embedding) {
        patch.embedding_model = info.embedding; // 有 API → 服务商策展模型
      } else {
        delete patch.embedding_model; // 无 API → 交给后端自动选择 HF 多语言热门模型
        patch.embedding_model = null; // 显式删除（下方 delete）
      }
    }
    const next = { ...(params || {}), ...patch };
    if (patch.embedding_model === null) delete next.embedding_model;
    onChange(JSON.stringify(next, null, 2));
  };

  const embedModeText = providerInfo?.has_embedding_api
    ? `自动：服务商策展模型（${providerInfo.embedding}）`
    : "自动：HuggingFace 下载量最高的多语言（含中文）模型";

  return (
    <div className="config-panel">
      <div className="node-block-title">模型配置</div>

      <label className="ds-row">
        <span className="ds-label">Provider</span>
        <select
          className="ds-select"
          value={currentProvider}
          onChange={(e) => onProviderChange(e.target.value)}
        >
          <option value="">未选择</option>
          {providers.map((p) => (
            <option key={p.name} value={p.name}>
              {p.name}
              {p.builtin ? "" : "（自定义）"}
            </option>
          ))}
        </select>
      </label>

      <label className="ds-row">
        <span className="ds-label">API Base</span>
        <input
          className="ds-input"
          value={params?.api_base || ""}
          placeholder="留空使用服务商默认"
          onChange={(e) => update({ api_base: e.target.value })}
        />
      </label>

      <label className="ds-row">
        <span className="ds-label">Model</span>
        <input
          className="ds-input"
          value={params?.model || ""}
          placeholder="如 openrouter/anthropic/claude-sonnet-4"
          onChange={(e) => update({ model: e.target.value })}
        />
      </label>

      <label className="ds-row">
        <span className="ds-label">Vision</span>
        <input
          className="ds-input"
          value={params?.vision_model || ""}
          placeholder="留空随 provider（回落 model）"
          onChange={(e) => update({ vision_model: e.target.value })}
        />
      </label>

      <div className="ds-row">
        <span className="ds-label">Embedding</span>
        <select
          className="ds-select"
          value={embedAuto ? "auto" : "manual"}
          onChange={(e) => {
            if (e.target.value === "auto") {
              const next = { ...(params || {}) };
              delete next.embedding_model;
              onChange(JSON.stringify(next, null, 2));
            } else {
              update({
                embedding_model:
                  providerInfo?.embedding || "st-multi-qa-MiniLM-L6-cos-v1",
              });
            }
          }}
        >
          <option value="auto">自动（按 provider 判断）</option>
          <option value="manual">手动</option>
        </select>
      </div>

      {!embedAuto ? (
        <label className="ds-row">
          <span className="ds-label">Embedding 模型</span>
          <input
            className="ds-input"
            value={params?.embedding_model || ""}
            placeholder="st-<HF模型> 或 API 向量名"
            onChange={(e) => update({ embedding_model: e.target.value })}
          />
        </label>
      ) : (
        <div className="ds-hint">{embedModeText}（可选「手动」覆盖）</div>
      )}
    </div>
  );
}
