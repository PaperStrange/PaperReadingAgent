// AgentOps 看板数据层：SQLite（better-sqlite3）+ FTS5，文件为真相源、库为派生索引。
// 文件真相源：agents/runtime/registry.json + agents/runs/**/*.report.md
import Database from "better-sqlite3";
import fs from "node:fs";
import path from "node:path";

// 启动 cwd 约定：须在 agents-dashboard/ 下启动（start 脚本已 Push-Location）。
// AGENT_OPS_DIR 显式设置时优先；getDb() 会校验目录存在并给出明确报错。
const REPO_ROOT = path.resolve(process.cwd(), "..");
const AGENTS_DIR = process.env.AGENT_OPS_DIR || path.join(REPO_ROOT, "agents");
const REGISTRY_PATH = path.join(AGENTS_DIR, "runtime", "registry.json");
const RUNS_DIR = path.join(AGENTS_DIR, "runs");
const DATA_DIR = path.join(process.cwd(), "data");
const DB_PATH = path.join(DATA_DIR, "ledger.db");

export interface LedgerRun {
  run_id: string;
  task_id: string;
  role: string;
  spec_source: string;
  model: string;
  status: string;
  started_at: string | null;
  ended_at: string | null;
  input_chars: number;
  output_chars: number;
  usage: Record<string, number>;
  context: Record<string, number>;
  cost: Record<string, unknown>;
  result_files: string[];
  error: string | null;
  report_body: string;
}

declare global {
  // eslint-disable-next-line no-var
  var __agentopsDb: Database.Database | undefined;
}

function openDb(): Database.Database {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  const db = new Database(DB_PATH);
  db.pragma("journal_mode = WAL");
  db.exec(`
    CREATE TABLE IF NOT EXISTS runs (
      run_id TEXT PRIMARY KEY,
      task_id TEXT, role TEXT, spec_source TEXT, model TEXT, status TEXT,
      started_at TEXT, ended_at TEXT,
      input_chars INTEGER, output_chars INTEGER,
      usage TEXT, context TEXT, cost TEXT,
      result_files TEXT, error TEXT, updated_at TEXT
    );
    CREATE VIRTUAL TABLE IF NOT EXISTS runs_fts USING fts5(
      role, task_id, spec_source, error, report_body,
      content='runs', content_rowid='rowid'
    );
    CREATE TRIGGER IF NOT EXISTS runs_ai AFTER INSERT ON runs BEGIN
      INSERT INTO runs_fts(rowid, role, task_id, spec_source, error, report_body)
      VALUES (new.rowid, new.role, new.task_id, new.spec_source, new.error, '');
    END;
    CREATE TRIGGER IF NOT EXISTS runs_ad AFTER DELETE ON runs BEGIN
      INSERT INTO runs_fts(runs_fts, rowid, role, task_id, spec_source, error, report_body)
      VALUES ('delete', old.rowid, old.role, old.task_id, old.spec_source, old.error, '');
    END;
    CREATE TRIGGER IF NOT EXISTS runs_au AFTER UPDATE ON runs BEGIN
      INSERT INTO runs_fts(runs_fts, rowid, role, task_id, spec_source, error, report_body)
      VALUES ('delete', old.rowid, old.role, old.task_id, old.spec_source, old.error, '');
      INSERT INTO runs_fts(rowid, role, task_id, spec_source, error, report_body)
      VALUES (new.rowid, new.role, new.task_id, new.spec_source, new.error, '');
    END;
  `);
  return db;
}

function reportBody(runId: string): string {
  // 路径穿越防护（review 修正 Sprint-9 三查）：runId 必须是纯目录名
  if (!runId || path.basename(runId) !== runId || runId.includes("..")) return "";
  const dir = path.join(RUNS_DIR, runId);
  if (!fs.existsSync(dir)) return "";
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".md"))
    .map((f) => fs.readFileSync(path.join(dir, f), "utf-8"))
    .join("\n\n");
}

function upsertRun(db: Database.Database, r: Record<string, unknown>): void {
  const stmt = db.prepare(`
    INSERT INTO runs (run_id, task_id, role, spec_source, model, status,
      started_at, ended_at, input_chars, output_chars, usage, context, cost,
      result_files, error, updated_at)
    VALUES (@run_id, @task_id, @role, @spec_source, @model, @status,
      @started_at, @ended_at, @input_chars, @output_chars, @usage, @context, @cost,
      @result_files, @error, @updated_at)
    ON CONFLICT(run_id) DO UPDATE SET
      status=excluded.status, ended_at=excluded.ended_at, output_chars=excluded.output_chars,
      usage=excluded.usage, context=excluded.context, cost=excluded.cost,
      result_files=excluded.result_files, error=excluded.error, updated_at=excluded.updated_at
  `);
  stmt.run({
    run_id: String(r.run_id ?? ""),
    task_id: String(r.task_id ?? ""),
    role: String(r.role ?? ""),
    spec_source: String(r.spec_source ?? ""),
    model: String(r.model ?? ""),
    status: String(r.status ?? ""),
    started_at: r.started_at ? String(r.started_at) : null,
    ended_at: r.ended_at ? String(r.ended_at) : null,
    input_chars: Number(r.input_chars ?? 0),
    output_chars: Number(r.output_chars ?? 0),
    usage: JSON.stringify(r.usage ?? {}),
    context: JSON.stringify(r.context_occupancy ?? {}),
    cost: JSON.stringify(r.cost_est ?? {}),
    result_files: JSON.stringify(r.result_files ?? []),
    error: r.error ? String(r.error) : null,
    updated_at: new Date().toISOString(),
  });
  // FTS5 虚拟表不支持 UPDATE：report_body 用 delete+reinsert 同步
  const row = db.prepare("SELECT rowid FROM runs WHERE run_id = ?").get(String(r.run_id ?? "")) as
    | { rowid: number }
    | undefined;
  if (row) {
    const body = reportBody(String(r.run_id ?? ""));
    db.prepare(
      "INSERT INTO runs_fts(runs_fts, rowid, role, task_id, spec_source, error, report_body) VALUES('delete', ?, '', '', '', '', '')"
    ).run(row.rowid);
    db.prepare(
      "INSERT INTO runs_fts(rowid, role, task_id, spec_source, error, report_body) VALUES(?, ?, ?, ?, ?, ?)"
    ).run(row.rowid, String(r.role ?? ""), String(r.task_id ?? ""), String(r.spec_source ?? ""),
      r.error ? String(r.error) : "", body);
  }
}

export function reindex(): { count: number; indexed_at: string } {
  const db = getDb();
  let count = 0;
  if (fs.existsSync(REGISTRY_PATH)) {
    const data = JSON.parse(fs.readFileSync(REGISTRY_PATH, "utf-8"));
    const runs: Record<string, unknown>[] = Array.isArray(data?.runs) ? data.runs : [];
    const upsertAll = db.transaction(() => {
      for (const r of runs) {
        upsertRun(db, r);
        count++;
      }
    });
    upsertAll();
  }
  return { count, indexed_at: new Date().toISOString() };
}

export function getDb(): Database.Database {
  if (!fs.existsSync(AGENTS_DIR)) {
    throw new Error(
      `AGENT_OPS_DIR 不存在：${AGENTS_DIR}。请在 agents-dashboard/ 目录下启动（start 脚本已处理），或显式设置 AGENT_OPS_DIR。`
    );
  }
  if (!global.__agentopsDb) {
    global.__agentopsDb = openDb();
    reindex();
    startWatcher();
  }
  return global.__agentopsDb;
}

let watcherStarted = false;
function startWatcher(): void {
  if (watcherStarted) return;
  watcherStarted = true;
  // 延迟加载 chokidar，避免在无文件变更时引入开销
  import("chokidar").then(({ default: chokidar }) => {
    // review 修正（Sprint-9 三查 P2）：监听 AGENTS_DIR 整目录（而非仅现存文件），
    // 新机首次启动时 runtime/、runs/ 尚不存在，后续落盘也能触发增量 reindex；排除 functions/（spec 编辑与账本无关）。
    const watcher = chokidar.watch(AGENTS_DIR, {
      ignoreInitial: true,
      ignored: (p: string) => p.split(path.sep).includes("functions"),
      awaitWriteFinish: { stabilityThreshold: 500 },
    });
    let t: NodeJS.Timeout | null = null;
    const kick = () => {
      if (t) clearTimeout(t);
      t = setTimeout(() => {
        try {
          reindex();
          console.log("[agent-ops] reindexed ledger after file change");
        } catch (e) {
          console.error("[agent-ops] reindex failed:", e);
        }
      }, 600);
    };
    watcher.on("add", kick).on("change", kick).on("unlink", kick);
  });
}

export function searchRuns(opts: {
  q?: string;
  role?: string;
  status?: string;
  limit?: number;
  offset?: number;
}): { rows: LedgerRun[]; total: number } {
  const db = getDb();
  const where: string[] = [];
  const params: Record<string, unknown> = {};
  if (opts.role) {
    where.push("r.role = @role");
    params.role = opts.role;
  }
  if (opts.status) {
    where.push("r.status = @status");
    params.status = opts.status;
  }
  let sql = `SELECT r.* FROM runs r`;
  if (opts.q) {
    sql += ` JOIN (SELECT rowid, bm25(runs_fts) AS rank FROM runs_fts WHERE runs_fts MATCH @q) f ON f.rowid = r.rowid`;
    // 短语查询：兼容含连字符的 role/task（如 doc-audit）
    params.q = `"${opts.q.replace(/"/g, '""')}"`;
    where.push("1=1");
  }
  if (where.length) sql += ` WHERE ${where.join(" AND ")}`;
  sql += opts.q ? " ORDER BY f.rank" : " ORDER BY r.updated_at DESC, r.rowid DESC";
  const total = db
    .prepare(`SELECT COUNT(*) AS c FROM runs r${opts.q ? ` JOIN (SELECT rowid FROM runs_fts WHERE runs_fts MATCH @q) f ON f.rowid = r.rowid` : ""}${where.length ? ` WHERE ${where.join(" AND ")}` : ""}`)
    .get(params) as { c: number };
  const rows = db
    .prepare(`${sql} LIMIT @limit OFFSET @offset`)
    .all({ ...params, limit: opts.limit ?? 50, offset: opts.offset ?? 0 }) as Record<string, unknown>[];
  return {
    total: total.c,
    rows: rows.map((r) => ({
      run_id: String(r.run_id),
      task_id: String(r.task_id),
      role: String(r.role),
      spec_source: String(r.spec_source),
      model: String(r.model),
      status: String(r.status),
      started_at: r.started_at ? String(r.started_at) : null,
      ended_at: r.ended_at ? String(r.ended_at) : null,
      input_chars: Number(r.input_chars),
      output_chars: Number(r.output_chars),
      usage: JSON.parse(String(r.usage || "{}")),
      context: JSON.parse(String(r.context || "{}")),
      cost: JSON.parse(String(r.cost || "{}")),
      result_files: JSON.parse(String(r.result_files || "[]")),
      error: r.error ? String(r.error) : null,
      report_body: "",
    })),
  };
}

export function getRun(runId: string): LedgerRun & { report_body: string } {
  const db = getDb();
  const r = db.prepare("SELECT * FROM runs WHERE run_id = ?").get(runId) as Record<string, unknown> | undefined;
  if (!r) throw new Error(`run ${runId} not found`);
  return {
    run_id: String(r.run_id),
    task_id: String(r.task_id),
    role: String(r.role),
    spec_source: String(r.spec_source),
    model: String(r.model),
    status: String(r.status),
    started_at: r.started_at ? String(r.started_at) : null,
    ended_at: r.ended_at ? String(r.ended_at) : null,
    input_chars: Number(r.input_chars),
    output_chars: Number(r.output_chars),
    usage: JSON.parse(String(r.usage || "{}")),
    context: JSON.parse(String(r.context || "{}")),
    cost: JSON.parse(String(r.cost || "{}")),
    result_files: JSON.parse(String(r.result_files || "[]")),
    error: r.error ? String(r.error) : null,
    report_body: reportBody(String(r.run_id)),
  };
}

export function aggregates(): {
  total: number;
  by_status: Record<string, number>;
  by_role: Record<string, number>;
  by_model: { model: string; runs: number; cost: number; pending: number }[];
  cost_total: number;
  pending_price: number;
  estimated_count: number;
  fx_usd_cny: number;
} {
  const db = getDb();
  const rows = db.prepare("SELECT status, role, model, cost FROM runs").all() as {
    status: string;
    role: string;
    model: string;
    cost: string;
  }[];
  const by_status: Record<string, number> = {};
  const by_role: Record<string, number> = {};
  const by_model: Record<string, { runs: number; cost: number; pending: number }> = {};
  let cost_total = 0;
  let pending_price = 0;
  let estimated_count = 0;
  for (const r of rows) {
    by_status[r.status] = (by_status[r.status] ?? 0) + 1;
    by_role[r.role] = (by_role[r.role] ?? 0) + 1;
    const cost = JSON.parse(r.cost || "{}") as {
      total?: number | null;
      pending_price?: boolean;
      estimated?: boolean;
    };
    const m = by_model[r.model || "未知模型"] ?? { runs: 0, cost: 0, pending: 0 };
    m.runs += 1;
    if (typeof cost.total === "number") {
      cost_total += cost.total;
      m.cost += cost.total;
    }
    if (cost.pending_price) {
      pending_price++;
      m.pending += 1;
    }
    if (cost.estimated) estimated_count++;
    by_model[r.model || "未知模型"] = m;
  }
  // fallback 与 scripts/agent-ops.py 默认值一致；真相源 = agents/runtime/prices.json 的 meta.fx_usd_cny
  let fx_usd_cny = 7.2;
  const pricesPath = path.join(AGENTS_DIR, "runtime", "prices.json");
  if (fs.existsSync(pricesPath)) {
    try {
      const meta = (JSON.parse(fs.readFileSync(pricesPath, "utf-8")) as { meta?: { fx_usd_cny?: number } }).meta;
      if (meta?.fx_usd_cny) fx_usd_cny = meta.fx_usd_cny;
    } catch {
      /* ignore */
    }
  }
  return {
    total: rows.length,
    by_status,
    by_role,
    by_model: Object.entries(by_model).map(([model, v]) => ({ model, ...v })),
    cost_total,
    pending_price,
    estimated_count,
    fx_usd_cny,
  };
}

export function specsList(): { name: string; path: string; version: string }[] {
  const dir = path.join(AGENTS_DIR, "functions");
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".md"))
    .map((f) => {
      const text = fs.readFileSync(path.join(dir, f), "utf-8");
      const m = /^---\n([\s\S]*?)\n---/.exec(text);
      const fm = m ? m[1] : "";
      const version = /^version:\s*"?(.+?)"?\s*$/m.exec(fm)?.[1] ?? "";
      const name = /^name:\s*(.+)$/m.exec(fm)?.[1].trim() ?? f.replace(/\.md$/, "");
      return { name, path: path.join(dir, f), version };
    });
}
