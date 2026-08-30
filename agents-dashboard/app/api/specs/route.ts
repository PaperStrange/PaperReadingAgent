import fs from "node:fs";
import path from "node:path";
import { specsList } from "@/lib/db";

export const dynamic = "force-dynamic";

const REPO_ROOT = path.resolve(process.cwd(), "..");
const AGENTS_DIR = process.env.AGENT_OPS_DIR || path.join(REPO_ROOT, "agents");
const FUNC_DIR = path.join(AGENTS_DIR, "functions");

export async function GET() {
  return Response.json({ specs: specsList() });
}

export async function PUT(req: Request) {
  // US-9.3：spec 编辑（直写 agents/functions/*.md，文件为真相源）。
  // 仅绑定 127.0.0.1 回环的本机工具，无鉴权（与后端/前端同约定，见 README §5）。
  const body = (await req.json()) as { name: string; content: string };
  const raw = String(body.name ?? "");
  // review 修正（Sprint-9 三查 P1/P2）：白名单校验（拒绝而非剥离）；无扩展名时自动补 .md
  if (!/^[A-Za-z0-9._-]+$/.test(raw) || raw.includes("..")) {
    return Response.json({ error: "非法 spec 名称（仅允许字母数字 . _ -）" }, { status: 400 });
  }
  const fileName = raw.endsWith(".md") ? raw : `${raw}.md`;
  const target = path.join(FUNC_DIR, fileName);
  if (!target.startsWith(FUNC_DIR + path.sep)) {
    return Response.json({ error: "路径越界" }, { status: 400 });
  }
  fs.writeFileSync(target, body.content, "utf-8");
  return Response.json({ ok: true, path: target, name: fileName });
}
