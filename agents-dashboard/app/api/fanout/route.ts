import fs from "node:fs";
import path from "node:path";

export const dynamic = "force-dynamic";

const REPO_ROOT = path.resolve(process.cwd(), "..");
const AGENTS_DIR = process.env.AGENT_OPS_DIR || path.join(REPO_ROOT, "agents");
const FANOUT_PATH = path.join(AGENTS_DIR, "fanout.json");

// fanout.json 最小结构校验：version + 两条流水线数组 + 每步必备字段（US-10.5）
function validateFanout(data: unknown): string | null {
  if (!data || typeof data !== "object") return "必须是 JSON 对象";
  const d = data as Record<string, unknown>;
  if (typeof d.version !== "number") return "缺少 version（数字）";
  const pipelines = ["planning_pipeline", "sprint_close_pipeline"];
  for (const key of pipelines) {
    const steps = d[key];
    if (!Array.isArray(steps)) return `缺少 ${key}（数组）`;
    for (let i = 0; i < steps.length; i++) {
      const s = steps[i] as Record<string, unknown>;
      for (const field of ["order", "step", "role", "spec", "condition", "executor"]) {
        if (typeof s?.[field] !== "string" && typeof s?.[field] !== "number")
          return `${key}[${i}].${field} 缺失或类型错误`;
      }
      const orders = steps.map((x) => (x as Record<string, number>).order);
      if (orders[i] !== i + 1) return `${key}[${i}].order 应为 ${i + 1}（保持连续顺序）`;
    }
  }
  return null;
}

export async function GET() {
  if (!fs.existsSync(FANOUT_PATH)) {
    return Response.json({ error: "agents/fanout.json 不存在" }, { status: 404 });
  }
  const text = fs.readFileSync(FANOUT_PATH, "utf-8");
  let parsed: unknown = null;
  let error: string | null = null;
  try {
    parsed = JSON.parse(text);
    error = validateFanout(parsed);
  } catch (e) {
    error = String(e);
  }
  return Response.json({ content: text, parsed, valid: error === null, error });
}

// 仅绑定 127.0.0.1 回环的本机工具，无鉴权（与 specs 写端点同约定，见 README §6）
export async function PUT(req: Request) {
  const body = (await req.json()) as { content: string };
  const text = String(body.content ?? "");
  let parsed: unknown = null;
  try {
    parsed = JSON.parse(text);
  } catch {
    return Response.json({ ok: false, error: "JSON 解析失败" }, { status: 400 });
  }
  const err = validateFanout(parsed);
  if (err) {
    return Response.json({ ok: false, error: err }, { status: 400 });
  }
  fs.writeFileSync(FANOUT_PATH, text, "utf-8");
  return Response.json({ ok: true, path: FANOUT_PATH });
}
