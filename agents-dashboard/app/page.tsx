"use client";

import { useCallback, useEffect, useState } from "react";

interface RunRow {
  run_id: string;
  task_id: string;
  role: string;
  spec_source: string;
  model: string;
  status: string;
  started_at: string | null;
  ended_at: string | null;
  output_chars: number;
  cost: { total?: number | null; estimated?: boolean; pending_price?: boolean; override?: boolean };
}

interface Agg {
  total: number;
  by_status: Record<string, number>;
  by_role: Record<string, number>;
  cost_total: number;
  pending_price: number;
}

const fmt = (iso: string | null) => (iso ? iso.replace("T", " ").slice(0, 19) : "—");
const cost = (c: RunRow["cost"]) =>
  typeof c?.total === "number"
    ? `$${c.total.toFixed(6)}${c.estimated ? "~" : ""}`
    : c?.pending_price
      ? "待价表"
      : "—";

export default function Home() {
  const [agg, setAgg] = useState<Agg | null>(null);
  const [rows, setRows] = useState<RunRow[]>([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (search = q, r = role, s = status) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (search) params.set("q", search);
      if (r) params.set("role", r);
      if (s) params.set("status", s);
      const [a, l] = await Promise.all([
        fetch("/api/aggregates").then((x) => x.json()),
        fetch(`/api/runs?${params.toString()}`).then((x) => x.json()),
      ]);
      setAgg(a);
      setRows(l.rows as RunRow[]);
      setTotal(l.total);
    } finally {
      setLoading(false);
    }
  }, [q, role, status]);

  useEffect(() => {
    const t = setTimeout(() => void load(), 200);
    return () => clearTimeout(t);
  }, [load]);

  return (
    <main className="mx-auto max-w-6xl px-6 py-8 space-y-6">
      <header className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">AgentOps 看板</h1>
        <button
          onClick={() => void load()}
          className="rounded-md border border-zinc-200 px-3 py-1 text-sm hover:bg-zinc-50"
        >
          {loading ? "刷新中…" : "刷新"}
        </button>
      </header>

      <section className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="总 Run 数" value={String(agg?.total ?? "—")} />
        <StatCard
          label="状态分布"
          value={agg ? Object.entries(agg.by_status).map(([k, v]) => `${k} ${v}`).join(" · ") : "—"}
        />
        <StatCard
          label="职能分布"
          value={agg ? Object.entries(agg.by_role).map(([k, v]) => `${k} ${v}`).join(" · ") : "—"}
        />
        <StatCard
          label="累计成本（自报+估算）"
          value={agg ? `$${agg.cost_total.toFixed(6)}${agg.pending_price ? ` · ${agg.pending_price} 条待价表` : ""}` : "—"}
          hint="精确账单以服务商后台为准"
        />
      </section>

      <section className="space-y-3">
        <div className="flex flex-wrap gap-2">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="全文检索（role/task/spec/报告内容）"
            className="flex-1 min-w-52 rounded-md border border-zinc-200 px-3 py-1.5 text-sm"
          />
          <select value={role} onChange={(e) => setRole(e.target.value)} className="rounded-md border border-zinc-200 px-2 py-1.5 text-sm">
            <option value="">全部职能</option>
            {agg && Object.keys(agg.by_role).map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <select value={status} onChange={(e) => setStatus(e.target.value)} className="rounded-md border border-zinc-200 px-2 py-1.5 text-sm">
            <option value="">全部状态</option>
            {agg && Object.keys(agg.by_status).map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>

        <div className="overflow-x-auto rounded-lg border border-zinc-200">
          <table className="w-full text-left text-sm">
            <thead className="bg-zinc-50 text-zinc-500">
              <tr>
                <th className="px-3 py-2">Run</th>
                <th className="px-3 py-2">任务</th>
                <th className="px-3 py-2">职能</th>
                <th className="px-3 py-2">spec</th>
                <th className="px-3 py-2">状态</th>
                <th className="px-3 py-2">开始</th>
                <th className="px-3 py-2">成本</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {rows.map((r) => (
                <tr key={r.run_id} className="hover:bg-zinc-50">
                  <td className="px-3 py-2 font-mono text-xs">{r.run_id}</td>
                  <td className="px-3 py-2">{r.task_id || "—"}</td>
                  <td className="px-3 py-2">{r.role}</td>
                  <td className="px-3 py-2 font-mono text-xs">{r.spec_source}</td>
                  <td className="px-3 py-2">
                    <span
                      className={`rounded px-1.5 py-0.5 text-xs ${
                        r.status === "succeeded"
                          ? "bg-emerald-50 text-emerald-700"
                          : r.status === "failed"
                            ? "bg-red-50 text-red-700"
                            : r.status === "running"
                              ? "bg-blue-50 text-blue-700"
                              : "bg-zinc-100 text-zinc-600"
                      }`}
                    >
                      {r.status}
                    </span>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">{fmt(r.started_at)}</td>
                  <td className="px-3 py-2 font-mono text-xs">{cost(r.cost)}</td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-3 py-6 text-center text-zinc-400">
                    无数据
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-zinc-400">共 {total} 条 · 数据源：agents/runtime/registry.json（文件真相源）+ SQLite 派生索引</p>
      </section>
    </main>
  );
}

function StatCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-zinc-200 p-4">
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="mt-1 truncate font-mono text-sm" title={value}>
        {value}
      </div>
      {hint && <div className="mt-1 text-[11px] text-zinc-400">{hint}</div>}
    </div>
  );
}
