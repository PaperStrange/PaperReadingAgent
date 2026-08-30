import fs from "node:fs";
import path from "node:path";
import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const REPO_ROOT = path.resolve(process.cwd(), "..");
const AGENTS_DIR = process.env.AGENT_OPS_DIR || path.join(REPO_ROOT, "agents");
const FUNC_DIR = path.join(AGENTS_DIR, "functions");

export async function GET(_req: NextRequest, ctx: { params: Promise<{ name: string }> }) {
  const { name } = await ctx.params;
  let safe: string;
  try {
    safe = decodeURIComponent(name);
  } catch {
    return Response.json({ error: "非法 spec 名称" }, { status: 400 });
  }
  // review 修正（Sprint-9 三查）：名称必须是纯文件名、仅 *.md；前端传 frontmatter name（无 .md）时自动补扩展名
  if (path.basename(safe) !== safe || !/^[A-Za-z0-9._-]+$/.test(safe)) {
    return Response.json({ error: "非法 spec 名称" }, { status: 400 });
  }
  const fileName = safe.endsWith(".md") ? safe : `${safe}.md`;
  const target = path.join(FUNC_DIR, fileName);
  if (!fs.existsSync(target)) {
    return Response.json({ error: "spec 不存在" }, { status: 404 });
  }
  return Response.json({ name: fileName, content: fs.readFileSync(target, "utf-8") });
}
