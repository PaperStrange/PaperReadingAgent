import React, { useEffect, useRef, useState } from "react";

// Sprint-12（F2 阶段 B）：schema 驱动全字段交互表单——取代 ModelConfigPanel/DataSourcePanel/SchemaFieldList。
// 契约与旧面板一致：编辑写回同一份 params JSON（onChange(JSON.stringify(next, null, 2))）；JSON 编辑区仍为真相源。
// - US-12.1 类型控件/分组/中文标签/readonly 展示
// - US-12.2 字段级校验：防抖调 POST /api/config/validate，errors 逐字段标注、warnings/hints 顶部汇总
// - US-12.3 impacts 切换前可见（字段下方常驻）+ provider 下拉联动带出（与原面板行为一致）

const DEBOUNCE_MS = 600;

function toText(value) {
  if (Array.isArray(value)) return value.join("\n");
  if (typeof value === "string") return value;
  return "";
}

function linesToArr(text) {
  return (text || "")
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
}

export default function SchemaForm({ params, apiBase, onChange }) {
  const [schema, setSchema] = useState(null);
  const [providers, setProviders] = useState([]);
  const [loadError, setLoadError] = useState(null);
  const [validate, setValidate] = useState({ errors: [], warnings: [], hints: [] });
  const [validating, setValidating] = useState(false);
  const timerRef = useRef(null);

  useEffect(() => {
    let alive = true;
    fetch(`${apiBase}/api/config_schema`)
      .then((r) => {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then((d) => {
        if (alive) setSchema(d);
      })
      .catch((e) => {
        if (alive) setLoadError(String(e));
      });
    fetch(`${apiBase}/api/providers`)
      .then((r) => r.json())
      .then((d) => {
        if (alive && Array.isArray(d?.providers)) setProviders(d.providers);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [apiBase]);

  // 卸载清定时器
  useEffect(() => () => timerRef.current && clearTimeout(timerRef.current), []);

  // US-12.2：防抖校验（编辑后 600ms 调 validate 端点）；update 与 provider 联动共用
  const scheduleValidate = (snapshot) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(async () => {
      setValidating(true);
      try {
        const r = await fetch(`${apiBase}/api/config/validate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ params: snapshot }),
        });
        const d = await r.json();
        setValidate({
          errors: Array.isArray(d?.errors) ? d.errors : [],
          warnings: Array.isArray(d?.warnings) ? d.warnings : [],
          hints: Array.isArray(d?.hints) ? d.hints : [],
        });
      } catch {
        setValidate({ errors: [], warnings: [], hints: [] });
      } finally {
        setValidating(false);
      }
    }, DEBOUNCE_MS);
  };

  const update = (patch) => {
    const next = { ...(params || {}), ...patch };
    onChange(JSON.stringify(next, null, 2));
    scheduleValidate(next);
  };

  const onProviderChange = (name) => {
    // US-12.3：与原 ModelConfigPanel 完全一致的联动
    const info = providers.find((p) => p.name === name);
    const next = { ...(params || {}), provider: name };
    if (info) {
      next.api_base = info.api_base || "";
      next.model = info.model || "";
      next.vision_model = info.vision_model || "";
      if (info.has_embedding_api && info.embedding) {
        next.embedding_model = info.embedding;
      } else {
        delete next.embedding_model;
      }
    }
    onChange(JSON.stringify(next, null, 2));
    scheduleValidate(next);
  };

  if (loadError) {
    return (
      <div className="config-panel schema-form schema-error">
        配置 schema 拉取失败（{loadError}）——JSON 编辑区仍可用
      </div>
    );
  }
  if (!schema) return <div className="config-panel schema-form">配置 schema 加载中…</div>;

  const fieldError = (key) =>
    validate.errors.filter((e) => e.includes(`(${key})`) || e.includes(`${key}`)).join("；");

  const renderControl = (f) => {
    const key = f.key;
    const cur = params?.[key];
    const hasValue = cur !== undefined && cur !== null && cur !== "";
    const readonly = !!f.readonly;
    const ph = f.default === undefined || f.default === null ? f.hint || "" : `默认：${Array.isArray(f.default) ? "[]" : String(f.default)}`;
    const common = { disabled: readonly, className: "ds-input" };

    if (key === "provider") {
      // provider 下拉 + 联动（US-12.3）
      return (
        <select
          className="ds-select schema-field-provider"
          value={params?.provider || ""}
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
      );
    }
    switch (f.type) {
      case "password":
        return (
          <input
            type="password"
            className="ds-input"
            value={hasValue ? String(cur) : ""}
            placeholder={ph}
            autoComplete="off"
            onChange={(e) => update({ [key]: e.target.value })}
          />
        );
      case "boolean":
        return (
          <label className="ds-check">
            <input
              type="checkbox"
              checked={hasValue ? !!cur : !!f.default}
              disabled={readonly}
              onChange={(e) => update({ [key]: e.target.checked })}
            />
            <span>开启</span>
          </label>
        );
      case "enum":
        return (
          <select
            className={`ds-select ${key === "data_source" ? "schema-field-datasource" : ""}`}
            value={hasValue ? String(cur) : String(f.default ?? "")}
            disabled={readonly}
            onChange={(e) => {
              const v = e.target.value;
              // enum 选项为数字时（multimodal）保持数值类型
              const num = f.options.find((o) => String(o) === v);
              update({ [key]: typeof num === "number" ? num : v });
            }}
          >
            {f.options.map((o) => (
              <option key={String(o)} value={String(o)}>
                {String(o)}
              </option>
            ))}
          </select>
        );
      case "string_list":
        return (
          <textarea
            className="ds-textarea"
            value={toText(cur)}
            disabled={readonly}
            placeholder={ph}
            onChange={(e) => update({ [key]: linesToArr(e.target.value) })}
          />
        );
      case "number":
      case "integer":
        return (
          <input
            type="number"
            className="ds-input"
            value={hasValue ? String(cur) : ""}
            min={f.range?.[0]}
            max={f.range?.[1]}
            step={f.type === "integer" ? 1 : "any"}
            disabled={readonly}
            placeholder={ph}
            onChange={(e) => {
              const raw = e.target.value;
              if (raw === "") {
                const next = { ...(params || {}) };
                delete next[key];
                onChange(JSON.stringify(next, null, 2));
                return;
              }
              const n = Number(raw);
              if (!Number.isNaN(n)) update({ [key]: f.type === "integer" ? Math.trunc(n) : n });
            }}
          />
        );
      default: // string
        return (
          <input
            {...common}
            type="text"
            value={hasValue ? String(cur) : ""}
            placeholder={ph}
            onChange={(e) => update({ [key]: e.target.value })}
          />
        );
    }
  };

  return (
    <div className="config-panel schema-form">
      <div className="schema-form-title">
        配置唯一真源（schema v{schema.version} · 全字段表单）
        {validating ? " · 校验中…" : ""}
      </div>

      {/* US-12.2：warnings / hints 顶部汇总 */}
      {validate.warnings.length > 0 && (
        <div className="schema-msg schema-msg-warn">
          {validate.warnings.map((w, i) => (
            <div key={i}>⚠ {w}</div>
          ))}
        </div>
      )}
      {validate.hints.length > 0 && (
        <div className="schema-msg schema-msg-hint">
          {validate.hints.map((h, i) => (
            <div key={i}>💡 {h}</div>
          ))}
        </div>
      )}

      {schema.groups.map((g) => (
        <details key={g.key} className="schema-group" open={g.key === "llm" || g.key === "datasource"}>
          <summary>
            {g.label}（{g.fields.length} 项）
          </summary>
          <div className="schema-fields">
            {g.fields.map((f) => {
              const err = fieldError(f.key);
              return (
                <div key={f.key} className={`schema-field ${err ? "schema-field-error" : ""}`}>
                  <label className="ds-row">
                    <span className="ds-label">
                      {f.label}
                      {f.readonly ? " 🔒" : ""}
                    </span>
                    {renderControl(f)}
                  </label>
                  {/* US-12.3：impacts 切换前可见（常驻） */}
                  {f.impacts?.length > 0 && (
                    <div className="ds-hint schema-impact">
                      {f.impacts.map((im, i) => (
                        <div key={i}>⚠ {im}</div>
                      ))}
                    </div>
                  )}
                  {f.hint && !f.impacts?.length && (
                    <div className="ds-hint">{f.hint}</div>
                  )}
                  {err && <div className="schema-field-err">{err}</div>}
                </div>
              );
            })}
          </div>
        </details>
      ))}
    </div>
  );
}
