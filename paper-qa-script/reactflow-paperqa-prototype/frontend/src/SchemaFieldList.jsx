// Sprint-11 US-11.3（F2 阶段 A）：配置唯一真源的分组字段清单（只读视图）。
// 阶段 A 只展示：分组/字段/类型/默认值/影响提示 + 当前值高亮；字段交互替换在阶段 B（Sprint-12）。
import React, { useEffect, useState } from "react";

const TYPE_LABEL = {
  string: "字符串",
  password: "密码",
  number: "数值",
  integer: "整数",
  boolean: "开关",
  enum: "枚举",
  string_list: "多行文本",
};

function formatDefault(f, hasValue, cur) {
  if (hasValue) return `当前：${JSON.stringify(cur)}`;
  if (f.default === undefined || f.default === null) return "（无默认）";
  if (Array.isArray(f.default)) return f.default.length ? JSON.stringify(f.default) : "[]";
  return String(f.default);
}

export default function SchemaFieldList({ params, apiBase }) {
  const [schema, setSchema] = useState(null);
  const [error, setError] = useState(null);

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
        if (alive) setError(String(e));
      });
    return () => {
      alive = false;
    };
  }, [apiBase]);

  if (error) {
    return (
      <div className="schema-list schema-error">
        配置 schema 拉取失败（{error}）——现有配置面板不受影响
      </div>
    );
  }
  if (!schema) return <div className="schema-list">配置 schema 加载中…</div>;

  return (
    <div className="schema-list">
      <div className="schema-title">配置唯一真源（schema v{schema.version}，只读清单）</div>
      {schema.groups.map((g) => (
        <details key={g.key} className="schema-group" open={g.key === "llm"}>
          <summary>
            {g.label}（{g.fields.length} 项）
          </summary>
          <table className="schema-table">
            <tbody>
              {g.fields.map((f) => {
                const cur = params?.[f.key];
                const hasValue = cur !== undefined && cur !== null && cur !== "";
                return (
                  <tr key={f.key} className={hasValue ? "schema-row-current" : ""}>
                    <td className="schema-key">
                      <code>{f.key}</code>
                    </td>
                    <td className="schema-label">
                      {f.label}
                      {f.readonly ? " 🔒" : ""}
                    </td>
                    <td className="schema-type">{TYPE_LABEL[f.type] || f.type}</td>
                    <td className="schema-default">{formatDefault(f, hasValue, cur)}</td>
                    <td className="schema-hint">
                      {f.hint}
                      {f.impacts?.length ? ` ⚠ ${f.impacts.join("；")}` : ""}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </details>
      ))}
    </div>
  );
}
