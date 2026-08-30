import fs from "node:fs";
import path from "node:path";
import { specsList } from "@/lib/db";

export const dynamic = "force-dynamic";

const REPO_ROOT = path.resolve(process.cwd(), "..");
const AGENTS_DIR = process.env.AGENT_OPS_DIR || path.join(REPO_ROOT, "agents");

export async function GET() {
  return Response.json({ specs: specsList() });
}

export async function PUT(req: Request) {
  // US-9.3：spec 编辑（直写 agents/functions/*.md，文件为真相源）
  const body = (await req.json()) as { name: string; content: string };
  const safeName = body.name.replace(/\.\./g, "").replace(/[\\/]/g, "");
  if (!safeName.endsWith(".md")) return Response.json({ error: "仅允许 .md spec 文件" }, { status: 400 });
  const target = path.join(AGENTS_DIR, "functions", safeName);
  if (!target.startsWith(path.join(AGENTS_DIR, "functions"))) {
    return Response.json({ error: "路径越界" }, { status: 400 });
  }
  fs.writeFileSync(target, body.content, "utf-8");
  return Response.json({ ok: true, path: target });
}
