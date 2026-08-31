import fs from "node:fs";
import path from "node:path";

export const dynamic = "force-dynamic";

const REPO_ROOT = path.resolve(process.cwd(), "..");
const AGENTS_DIR = process.env.AGENT_OPS_DIR || path.join(REPO_ROOT, "agents");
const FANOUT_PATH = path.join(AGENTS_DIR, "fanout.json");

// fanout.json 最小结构校验：version + 两条非空流水线数组 + 每步必备字段 + order 连续（US-10.5；017 修正：非空 + version 范围）
function validateFanout(data: unknown): string | null {
  if (!data || typeof data !== "object") return "必须是 JSON 对象";
  const d = data as Record<string, unknown>;
  if (typeof d.version !== "number" || !Number.isInteger(d.version) || d.version < 1 || d.version > 100)
    return "version 必须是 1~100 的整数";
  const pipelines = ["planning_pipeline", "sprint_close_pipeline"];
  for (const key of pipelines) {
    const steps = d[key];
    if (!Array.isArray(steps) || steps.length === 0) return `${key} 必须是非空数组`;
    const orders = steps.map((x) => (x as Record<string, number>).order);
    for (let i = 0; i < steps.length; i++) {
      const s = steps[i] as Record<string, unknown>;
      if (typeof s?.order !== "number") return `${key}[${i}].order 必须是数字`;
      for (const field of ["step", "role", "spec", "condition", "executor"]) {
        if (typeof s?.[field] !== "string")
          return `${key}[${i}].${field} 缺失或类型错误`;
      }
      if (orders[i] !== i + 1) return `${key}[${i}].order 应为 ${i + 1}（保持连续顺序）`;
    }
  }
  return null;
}

function parseJsonBody(text: string): { parsed: unknown; error: string | null } {
  try {
    return { parsed: JSON.parse(text), error: null };
  } catch {
    return { parsed: null, error: "JSON 解析失败" };
  }
}

export async function GET() {
  if (!fs.existsSync(FANOUT_PATH)) {
    return Response.json({ error: "agents/fanout.json 不存在" }, { status: 404 });
  }
  const text = fs.readFileSync(FANOUT_PATH, "utf-8");
  const { parsed, error: parseError } = parseJsonBody(text);
  const error = parseError ?? validateFanout(parsed);
  return Response.json({ content: text, parsed, valid: error === null, error });
}

// 校验（dry-run，不写入）——"校验"按钮专用（017 major 修复：与 PUT 写语义分离）
export async function POST(req: Request) {
  let body: { content?: string } | null = null;
  try {
    body = (await req.json()) as { content?: string };
  } catch {
    return Response.json({ ok: false, error: "请求体不是合法 JSON" }, { status: 400 });
  }
  const { parsed, error: parseError } = parseJsonBody(String(body?.content ?? ""));
  const err = parseError ?? validateFanout(parsed);
  return Response.json({ ok: err === null, error: err, dry_run: true });
}

// 仅绑定 127.0.0.1 回环的本机工具，无鉴权（与 specs 写端点同约定，见 README §6）
export async function PUT(req: Request) {
  let body: { content?: string } | null = null;
  try {
    body = (await req.json()) as { content?: string };
  } catch {
    return Response.json({ ok: false, error: "请求体不是合法 JSON" }, { status: 400 });
  }
  const { parsed, error: parseError } = parseJsonBody(String(body?.content ?? ""));
  const err = parseError ?? validateFanout(parsed);
  if (err) {
    return Response.json({ ok: false, error: err }, { status: 400 });
  }
  fs.writeFileSync(FANOUT_PATH, String(body?.content ?? ""), "utf-8");
  return Response.json({ ok: true, path: FANOUT_PATH });
}
