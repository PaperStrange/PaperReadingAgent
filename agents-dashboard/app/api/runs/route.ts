import { NextRequest } from "next/server";
import { searchRuns } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const sp = req.nextUrl.searchParams;
  const result = searchRuns({
    q: sp.get("q") || undefined,
    role: sp.get("role") || undefined,
    status: sp.get("status") || undefined,
    limit: Math.min(Number(sp.get("limit") || 50), 200),
    offset: Number(sp.get("offset") || 0),
  });
  return Response.json(result);
}
