"""TG-8：**模型 API 外呼的离线闸门**（app 包内的最小运行时只读实现）。

**为什么这个文件短**：`verify/outbound_guard.py` 是"脚本侧"的完整实现（含 CLI 退出码、
HF 离线变量注入、拒绝文案渲染），但 `app/**` 是**原型后端运行时**——它的 import 与仓库布局
解耦（`python main.py` 可能从任意 cwd 启动），若为了读一个开关去 import `verify.agent_policy`，
就会把"应用能不能起来"绑到"agents/functions/*.md 与 fanout.json 是否齐全"上（那是一套闸门数据，
不是应用依赖）。故此处只做**一件事**：读同一份政策键，回答"现在是否离线"。

**唯一真源仍是 `agents/policy.json::offline_switch`**（同一个键、同一个 env 名、同一套真值表）——
两处实现读的是同一份数据，不是两份政策：字段名/取值语义都由
`verify/agent_policy.py::Policy.offline_switch` 做类型校验（拼错即 fail-closed）。
任何一侧改了语义都必须同步另一侧；为此 `verify/agentops` 用例直接断言"两侧对同一 env 取值
给出一致结论"（见 `verify/verify_agentops.py` 的 UC-19）。

**边界（如实标注）**：本模块只拦"要用 API 的模型"（LLM / vision / API 向量模型）；
`st-` 前缀的本地 SentenceTransformer 与本地索引/检索**不受影响**——离线档仍然可以跑
"本地 PDF → 本地向量 → 检索"这条零外呼链路（`verify/verify_local_dir.py` 正是该链路）。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

# 仓库根：.../paper-qa-script/app/offline_guard.py → parents[2]
ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "agents" / "policy.json"


class OfflineRefused(RuntimeError):
    """当前处于离线档，本次模型 API 外呼被拒绝（消息含来源与目标模型）。"""


def policy_file() -> dict:
    """读政策文件（缺失/坏 JSON → 空 dict：**不因此让应用起不来**，见模块头说明）。"""
    try:
        data = json.loads(POLICY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def switch_state() -> tuple[bool, str]:
    """返回 `(是否离线, 来源说明)`；取值优先级 env > `offline_switch.enabled`（与脚本侧同口径）。

    非法 env 取值（`flase` 之类）→ 按"**最保守**"处理：视为**开启**（宁可拒绝外呼，也不静默放行）。
    脚本侧同情形是 `PolicyError`（关掉整条命令）——两侧都不静默，只是失败形态不同：
    后端进程要活着给前端一个可读错误，所以这里不抛在导入期。
    """
    data = (policy_file().get("offline_switch") or {})
    if not isinstance(data, dict):
        return False, "agents/policy.json::offline_switch 非法（按在线处理并留痕）"
    name = str(data.get("env_var") or "").strip()
    raw = (os.environ.get(name) or "").strip().lower() if name else ""
    if raw:
        truthy = [str(v).lower() for v in (data.get("env_true_values") or [])]
        falsy = [str(v).lower() for v in (data.get("env_false_values") or [])]
        if raw in truthy:
            return True, f"env {name}={raw}"
        if raw in falsy:
            return False, f"env {name}={raw}"
        return True, f"env {name}={raw}（非法取值 → 按离线处理，不静默放行）"
    return bool(data.get("enabled")), "policy agents/policy.json::offline_switch.enabled"


def refusal_text(target: str) -> str:
    """拒绝文案（模板取自政策 `refusal_reason`；缺失时给等价的最小文案）。"""
    data = (policy_file().get("offline_switch") or {})
    template = str((data or {}).get("refusal_reason") or "").strip()
    enabled, source = switch_state()
    if not template:
        return f"离线开关已开启（{source}）→ 拒绝外呼：{target}"
    return template.replace("{source}", source).replace("{target}", target)


def refuse_if_offline(target: str) -> None:
    """**在构造/发起模型调用之前**调用：离线即抛 `OfflineRefused`（点名来源与目标模型）。"""
    if switch_state()[0]:
        raise OfflineRefused(refusal_text(target))
