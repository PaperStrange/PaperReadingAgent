"""One-off TG-2 migration helper: inject VERIFY_META headers into all verify scripts.
Run once, then delete (zero-residue)."""
import io
import json
import tokenize
from pathlib import Path

V = Path(__file__).resolve().parent.parent / "verify"

R_PIPE = [
    "/api/new_session", "/api/run_step", "/api/stream/{session_id}/{run_id}",
    "/api/session_records/{session_id}", "/api/reset_session",
]
R_ALL10 = R_PIPE + [
    "/api/health", "/api/providers", "/api/config_schema",
    "/api/config/validate", "/api/translate_preview",
]

PY_META = {
    "verify_smoke.py": {"features": "冒烟 8 项：paperqa 导入/后端 10 路由加载/runtime_trace 目标/PDF 解析等（离线）", "tier": "offline", "providers": [], "est_seconds": 10, "est_cost_cny": 0, "routes": R_ALL10, "requires": ["none"]},
    "verify_prune_callbacks.py": {"features": "litellm 回调裁剪：上限 env 可配 + 非法值回落 + 钳制（离线）", "tier": "offline", "providers": [], "est_seconds": 2, "est_cost_cny": 0, "routes": [], "requires": ["none"]},
    "verify_agentops.py": {"features": "AgentOps 账本 CLI 用例断言 UC-1~UC-10（离线）", "tier": "offline", "providers": [], "est_seconds": 5, "est_cost_cny": 0, "routes": [], "requires": ["none"]},
    "verify_config_schema.py": {"features": "配置 SSOT 一致性 + M7 前端零硬编码 + Settings 升级基线护栏（114 断言，离线）", "tier": "offline", "providers": [], "est_seconds": 5, "est_cost_cny": 0, "routes": ["/api/config_schema", "/api/config/validate"], "requires": ["none"]},
    "verify_index_health.py": {"features": "索引一致性三重探针 + 损坏自愈（合成六形态，离线）", "tier": "offline", "providers": [], "est_seconds": 20, "est_cost_cny": 0, "routes": [], "requires": ["none"]},
    "verify_e2e.py": {"features": "deepseek 全链路 6 步（LLM+vision + 本地 st- 向量）", "tier": "network", "providers": ["deepseek"], "est_seconds": 120, "est_cost_cny": 0.3, "routes": R_PIPE, "requires": ["keys", "network"]},
    "verify_e2e_openai.py": {"features": "OpenAI provider+embedding 全流程 + 同进程 deepseek→openai 切换隔离回归", "tier": "network", "providers": ["openai", "deepseek"], "est_seconds": 150, "est_cost_cny": 1.0, "routes": R_PIPE, "requires": ["keys", "network", "balance"]},
    "verify_e2e_dashscope.py": {"features": "dashscope 全链路 6 步 + 同进程 deepseek 切换隔离回归", "tier": "network", "providers": ["dashscope", "deepseek"], "est_seconds": 150, "est_cost_cny": 0.5, "routes": R_PIPE, "requires": ["keys", "network"]},
    "verify_remote_e2e.py": {"features": "remote 数据源全链路（arXiv 下载+索引+6 步）", "tier": "network", "providers": ["deepseek"], "est_seconds": 180, "est_cost_cny": 0.4, "routes": R_PIPE, "requires": ["keys", "network"]},
    "verify_agent.py": {"features": "Agent 流程（fake agent）+ 翻译接口", "tier": "network", "providers": ["deepseek"], "est_seconds": 60, "est_cost_cny": 0.3, "routes": ["/api/translate_preview", "/api/run_step"], "requires": ["keys", "network", "index"]},
    "verify_embed_load.py": {"features": "parse_chunk_embed 三种模式：run/load 同会话/load 新会话（embed 缓存）", "tier": "network", "providers": ["deepseek"], "est_seconds": 90, "est_cost_cny": 0.3, "routes": ["/api/run_step"], "requires": ["keys", "network"]},
    "verify_provider_switch.py": {"features": "provider 切换路由实证：内置 4 家 + 自定义（端点级拒绝断言）", "tier": "network", "providers": ["deepseek", "dashscope", "openai", "openrouter"], "est_seconds": 30, "est_cost_cny": 0.1, "routes": ["/api/providers"], "requires": ["keys", "network"]},
    "eval_retrieve.py": {"features": "检索质量小样本评测：双语料命中率 + hit@1 + 多语重试覆盖", "tier": "network", "providers": ["deepseek"], "est_seconds": 60, "est_cost_cny": 0.3, "routes": ["/api/run_step"], "requires": ["keys", "network"]},
}

JS_META = {
    "gui_check.mjs": {"features": "GUI 全链路：Run All 左到右 → 答案出现 → 截图", "tier": "gui", "providers": [], "est_seconds": 120, "est_cost_cny": 0, "routes": R_PIPE, "requires": ["playwright", "servers"]},
    "gui_check_remote.mjs": {"features": "GUI 远程数据源：remote+arXiv → Run All → 截图", "tier": "gui", "providers": [], "est_seconds": 180, "est_cost_cny": 0, "routes": R_PIPE, "requires": ["playwright", "servers", "network"]},
    "gui_check_s4.mjs": {"features": "光标三断言（插入/位置/连续编辑）+ provider 联动四断言", "tier": "gui", "providers": [], "est_seconds": 30, "est_cost_cny": 0, "routes": [], "requires": ["playwright", "servers"]},
    "gui_check_s5.mjs": {"features": "自动重跑 config / retrieve 双模式标记 / 复制报错按钮 / 计时冻结", "tier": "gui", "providers": [], "est_seconds": 40, "est_cost_cny": 0, "routes": [], "requires": ["playwright", "servers"]},
    "gui_check_s7.mjs": {"features": "多节点并发计时显示 + 完成后冻结", "tier": "gui", "providers": [], "est_seconds": 60, "est_cost_cny": 0, "routes": [], "requires": ["playwright", "servers"]},
    "gui_check_dashboard.mjs": {"features": "看板概览页 + spec 编辑页截图", "tier": "gui", "providers": [], "est_seconds": 30, "est_cost_cny": 0, "routes": [], "requires": ["playwright", "dashboard"]},
    "gui_check_dashboard2.mjs": {"features": "看板 spec 编辑器打开态截图", "tier": "gui", "providers": [], "est_seconds": 20, "est_cost_cny": 0, "routes": [], "requires": ["playwright", "dashboard"]},
    "gui_check_dashboard_costs.mjs": {"features": "看板成本/上下文页截图（CNY 合计/pending 标注）", "tier": "gui", "providers": [], "est_seconds": 30, "est_cost_cny": 0, "routes": [], "requires": ["playwright", "dashboard"]},
    "gui_check_dashboard_report.mjs": {"features": "看板报告浏览页截图（run 详情+报告全文）", "tier": "gui", "providers": [], "est_seconds": 30, "est_cost_cny": 0, "routes": [], "requires": ["playwright", "dashboard"]},
    "gui_check_dashboard_fanout.mjs": {"features": "看板 fan-out 配置页截图（两条流水线+JSON 编辑器）", "tier": "gui", "providers": [], "est_seconds": 30, "est_cost_cny": 0, "routes": [], "requires": ["playwright", "dashboard"]},
    "gui_check_config_schema.mjs": {"features": "Config schema 清单/全字段表单截图 + 字段级校验 + defaults-derived-from-schema 断言", "tier": "gui", "providers": [], "est_seconds": 60, "est_cost_cny": 0, "routes": ["/api/config_schema", "/api/config/validate"], "requires": ["playwright", "servers"]},
}


def inject_py(path: Path, meta: dict) -> None:
    text = path.read_text(encoding="utf-8")
    end_line = 0
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(text).readline))
        doc = next((t for t in toks if t.type == tokenize.STRING), None)
        if doc is not None and doc.start[0] <= 2:
            end_line = doc.end[0]
    except tokenize.TokenError:
        end_line = 0
    lines = text.splitlines(keepends=True)
    block = "VERIFY_META = " + repr(meta) + "\n\n"
    lines.insert(end_line, block)
    path.write_text("".join(lines), encoding="utf-8")


def inject_js(path: Path, meta: dict) -> None:
    text = path.read_text(encoding="utf-8")
    block = "// VERIFY_META: " + json.dumps(meta, ensure_ascii=False) + "\n"
    path.write_text(block + text, encoding="utf-8")


for name, meta in PY_META.items():
    inject_py(V / name, meta)
for name, meta in JS_META.items():
    inject_js(V / name, meta)
print(f"injected: {len(PY_META)} py + {len(JS_META)} mjs")
