import { getDb, reindex } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET() {
  const state = reindex(); // 每次健康检查前确保索引最新（文件真相源优先）
  const db = getDb();
  const count = (db.prepare("SELECT COUNT(*) AS c FROM runs").get() as { c: number }).c;
  return Response.json({ ok: true, runs: count, indexed_at: state.indexed_at });
}
