import { getRun } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  try {
    return Response.json(getRun(decodeURIComponent(id)));
  } catch (e) {
    return Response.json({ error: String(e instanceof Error ? e.message : e) }, { status: 404 });
  }
}
