/* F-AC15 v1：运行参数**只读**面（用户走查 B-15：9 个 env + spec 阈值此前前端完全不可见）。
 *
 * 范围边界（v1）：
 * - 只展示、不写回：所有值来自后端 `GET /api/config_schema` 的 `runtime` 段
 *   （env 生效值 / agents/runtime/schedule.json / agents/functions/tech-research.md 阈值表）；
 * - 可编辑面留待后续（v2）；密钥类与内部指标文件**不**入面（后端已排除）。
 */
import React, { useEffect, useState } from "react";

function Value({ row }) {
  if (!row.is_set) {
    return (
      <span className="rt-default" title="未设置环境变量，展示默认值">
        {String(row.value)}（默认）
      </span>
    );
  }
  return <code>{String(row.value)}</code>;
}

export default function RuntimeParamsPanel({ apiBase, onClose }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");

  const load = async () => {
    setErr("");
    try {
      const r = await fetch(`${apiBase}/api/config_schema`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const schema = await r.json();
      if (!schema.runtime) throw new Error("后端未返回 runtime 只读面");
      setData(schema.runtime);
    } catch (e) {
      setErr(String(e?.message || e));
    }
  };

  useEffect(() => {
    load();
  }, [apiBase]);

  const env = data?.env || [];
  const spec = data?.spec || [];
  const sched = data?.schedule || {};
  const intervals = Object.entries(sched.interval_days || {});

  return (
    <div className="ck-panel rt-panel nodrag nopan" data-testid="runtime-config-panel">
      <div className="ck-panel-head">
        <strong>运行参数（只读 · v1）</strong>
        <span className="ck-panel-root">来源：env / schedule.json / tech-research.md</span>
        <button className="run-btn" onClick={load}>刷新</button>
        <button className="run-btn" onClick={onClose}>关闭</button>
      </div>
      {err ? <div className="ck-error">读取失败：{err}</div> : null}
      {!err && !data ? <div className="ck-empty">加载中…</div> : null}

      {data ? (
        <div className="rt-note" data-testid="runtime-readonly-note">
          v1 只读展示，不写回任何配置；可编辑面留待后续。
        </div>
      ) : null}

      {env.length ? (
        <section data-testid="runtime-env">
          <div className="rt-section-title">环境变量（{env.length}）</div>
          <table className="rt-table">
            <thead>
              <tr>
                <th>变量</th>
                <th>生效值</th>
                <th>默认</th>
                <th>说明</th>
                <th>读取点</th>
              </tr>
            </thead>
            <tbody>
              {env.map((row) => (
                <tr key={row.name} data-testid="runtime-env-row">
                  <td><code>{row.name}</code></td>
                  <td><Value row={row} /></td>
                  <td><code>{String(row.default)}</code></td>
                  <td>{row.label}</td>
                  <td className="rt-read-point">{row.read_point}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}

      {spec.length ? (
        <section data-testid="runtime-spec">
          <div className="rt-section-title">
            调研 spec 阈值（tech-research.md Configurable Parameters）
          </div>
          <table className="rt-table">
            <thead>
              <tr>
                <th>参数</th>
                <th>当前值</th>
                <th>含义</th>
              </tr>
            </thead>
            <tbody>
              {spec.map((row) => (
                <tr key={row.parameter} data-testid="runtime-spec-row">
                  <td><code>{row.parameter}</code></td>
                  <td>{row.value}</td>
                  <td>{row.meaning}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}

      <section data-testid="runtime-schedule">
        <div className="rt-section-title">调度状态（schedule.json）</div>
        <div className="rt-kv">
          <span>路径</span>
          <code>{sched.path || "—"}</code>
        </div>
        <div className="rt-kv">
          <span>预算上限</span>
          <b>{sched.budget_cny == null ? "未配置（回落默认）" : `${sched.budget_cny} CNY`}</b>
        </div>
        <div className="rt-kv">
          <span>任务间隔覆盖</span>
          <b>
            {intervals.length
              ? intervals.map(([k, v]) => `${k}=${v} 天`).join(" · ")
              : "无（回落任务默认）"}
          </b>
        </div>
        {sched.error ? <div className="ck-error">状态文件读取失败：{sched.error}</div> : null}
      </section>
    </div>
  );
}
