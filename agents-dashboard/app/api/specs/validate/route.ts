import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

export const dynamic = "force-dynamic";

const REPO_ROOT = path.resolve(process.cwd(), "..");
const AGENTS_DIR = process.env.AGENT_OPS_DIR || path.join(REPO_ROOT, "agents");

export async function POST(req: Request) {
  // 调用 scripts/agent-ops.py validate-spec（先写临时内容再校验，保证所见即所验）
  const body = (await req.json()) as { name: string; content: string };
  const safe = body.name.replace(/\.\./g, "").replace(/[\\/]/g, "");
  const target = path.join(AGENTS_DIR, "functions", safe);
  if (!target.startsWith(path.join(AGENTS_DIR, "functions"))) {
    return Response.json({ ok: false, message: "路径越界" }, { status: 400 });
  }
  // 临时文件与 spec 同名（子目录隔离），使 validate-spec 的 name==文件名 校验生效
  const tmpDir = path.join(process.cwd(), "data", "validate");
  const tmp = path.join(tmpDir, safe);
  fs.mkdirSync(tmpDir, { recursive: true });
  fs.writeFileSync(tmp, body.content, "utf-8");
  try {
    const out = execFileSync(
      "python",
      [path.join(REPO_ROOT, "scripts", "agent-ops.py"), "validate-spec", tmp],
      { encoding: "utf-8", timeout: 30000, env: { ...process.env, PYTHONUTF8: "1" } },
    );
    return Response.json({ ok: true, message: out.trim() });
  } catch (e) {
    const err = e as { stdout?: string; stderr?: string; status?: number };
    return Response.json({
      ok: false,
      message: ((err.stdout || "") + (err.stderr || "")).trim() || "validate-spec 执行失败",
    });
  } finally {
    fs.rmSync(tmp, { force: true });
  }
}

export async function GET() {
  return Response.json({ ok: true, message: "POST {name, content} 校验 spec" });
}
