import fs from "node:fs";
import path from "node:path";
import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const REPO_ROOT = path.resolve(process.cwd(), "..");
const AGENTS_DIR = process.env.AGENT_OPS_DIR || path.join(REPO_ROOT, "agents");

export async function GET(_req: NextRequest, ctx: { params: Promise<{ name: string }> }) {
  const { name } = await ctx.params;
  const safe = decodeURIComponent(name).replace(/\.\./g, "").replace(/[\\/]/g, "");
  const target = path.join(AGENTS_DIR, "functions", safe);
  if (!target.startsWith(path.join(AGENTS_DIR, "functions")) || !fs.existsSync(target)) {
    return Response.json({ error: "spec 不存在" }, { status: 404 });
  }
  return Response.json({ name: safe, content: fs.readFileSync(target, "utf-8") });
}
