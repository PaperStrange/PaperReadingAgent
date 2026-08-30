"use client";

import { useEffect, useState } from "react";

interface Spec {
  name: string;
  version: string;
}

export default function SpecsPage() {
  const [specs, setSpecs] = useState<Spec[]>([]);
  const [current, setCurrent] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch("/api/specs")
      .then((r) => r.json())
      .then((d) => setSpecs(d.specs ?? []));
  }, []);

  const open = async (name: string) => {
    setCurrent(name);
    setMessage("");
    const d = await fetch(`/api/specs/${encodeURIComponent(name)}`).then((r) => r.json());
    setContent(d.content ?? "");
  };

  const save = async () => {
    if (!current) return;
    setBusy(true);
    setMessage("");
    try {
      const r = await fetch("/api/specs", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: current, content }),
      });
      const d = await r.json();
      setMessage(d.ok ? `已保存 ${current}` : `保存失败：${d.error}`);
    } finally {
      setBusy(false);
    }
  };

  const validate = async () => {
    if (!current) return;
    setBusy(true);
    setMessage("校验中…");
    try {
      const r = await fetch("/api/specs/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: current, content }),
      });
      const d = await r.json();
      setMessage(d.ok ? `✅ ${d.message}` : `❌ ${d.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto max-w-6xl px-6 py-8 space-y-6">
      <header className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">职能 spec 编辑（直写 agents/functions/）</h1>
        <a href="/" className="rounded-md border border-zinc-200 px-3 py-1 text-sm hover:bg-zinc-50">
          ← 看板
        </a>
      </header>

      <section className="grid gap-6 md:grid-cols-[220px_1fr]">
        <aside className="space-y-1">
          {specs.map((s) => (
            <button
              key={s.name}
              onClick={() => void open(s.name)}
              className={`block w-full rounded-md px-3 py-2 text-left text-sm ${
                current === s.name ? "bg-zinc-900 text-white" : "hover:bg-zinc-100"
              }`}
            >
              <div className="font-medium">{s.name}</div>
              <div className="text-xs opacity-70">v{s.version}</div>
            </button>
          ))}
        </aside>

        <section className="space-y-3">
          {current ? (
            <>
              <div className="flex gap-2">
                <button onClick={() => void save()} disabled={busy} className="rounded-md bg-zinc-900 px-3 py-1.5 text-sm text-white disabled:opacity-50">
                  保存（直写文件）
                </button>
                <button onClick={() => void validate()} disabled={busy} className="rounded-md border border-zinc-200 px-3 py-1.5 text-sm disabled:opacity-50">
                  validate-spec 校验
                </button>
                <span className="self-center text-xs text-zinc-400">
                  source 块（skill URL/ref/sha256/fallback）直接编辑下方 frontmatter 即可
                </span>
              </div>
              {message && (
                <div className={`rounded-md px-3 py-2 text-sm ${message.startsWith("❌") ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700"}`}>
                  {message}
                </div>
              )}
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                spellCheck={false}
                className="h-[70vh] w-full rounded-lg border border-zinc-200 p-4 font-mono text-xs leading-relaxed"
              />
            </>
          ) : (
            <div className="py-20 text-center text-zinc-400">从左侧选择要编辑的职能 spec</div>
          )}
        </section>
      </section>
    </main>
  );
}
