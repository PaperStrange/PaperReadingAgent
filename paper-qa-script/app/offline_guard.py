"""TG-8：**模型 API 外呼的离线闸门**（app 包内的最小运行时只读实现）。

**为什么这个文件短**：`verify/outbound_guard.py` 是"脚本侧"的完整实现（含 CLI 退出码、
HF 离线变量注入、拒绝文案渲染），但 `app/**` 是**原型后端运行时**——它的 import 与仓库布局
解耦（`python main.py` 可能从任意 cwd 启动），若为了读一个开关去 import `verify.agent_policy`，
就会把"应用能不能起来"绑到"agents/functions/*.md 与 fanout.json 是否齐全"上（那是一套闸门数据，
不是应用依赖）。故此处只做**一件事**：读同一份政策键，回答"现在是否离线"。

**唯一真源仍是 `agents/policy.json::offline_switch`**（同一个键、同一个 env 名、同一套真值表）——
两处实现读的是同一份数据，不是两份政策。**类型/字段校验两侧各做一遍**（口径同键同真值表）：
脚本侧 `verify/agent_policy.py::Policy.offline_switch` 抛 `PolicyError`
（关掉整条命令），产品侧本模块**不抛在导入期**（后端进程要活着给前端一个可读错误），
而是把"政策不可读/字段非法"一律判成**离线**并写明原因
（`switch_state()` 的第一个返回值 + 来源说明），
**绝不静默回落成"永远在线"**。任何一侧改了语义都必须同步另一侧；为此
`verify/agentops` 用例直接断言"两侧对同一 env 取值给出一致结论"
（见 `verify/verify_agentops.py` 的 UC-19）。

**边界（如实标注）**：本模块拦三类外呼——① 要用 API 的模型
（LLM / vision / API 向量模型）、② 本地 embedding 推荐器对 `huggingface.co` 的在线查询
（`app/embedding_recommender.py`，缓存命中时不查网、故不拦）。`st-` 前缀的本地
SentenceTransformer 与本地索引/检索**不受影响**——离线档仍然可以跑
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


def load_policy_file() -> tuple[dict, str]:
    """读 `agents/policy.json` → `(数据, 问题说明)`；问题说明非空 = 政策**不可用**。

    与 `policy_file()` 的分别：这里把"为什么读不到"**带出来**。产品侧不因此让应用起不来
    （见模块头），但判定侧必须拿这个原因 fail-closed —— 之前把缺失/坏 JSON 折成 `{}`，
    于是 `bool({}.get("enabled"))` = `False` = **在线**：开关自己的数据一旦不可读，
    产品就静默回到"全部外呼放行"，正是政策明文要消灭的
    "静默变成永远在线"形态（M4，2026-09-25 三查）。
    """
    try:
        raw = POLICY.read_text(encoding="utf-8")
    except OSError as exc:
        return {}, f"agents/policy.json 不可读（{exc.__class__.__name__}）"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {}, f"agents/policy.json 不是合法 JSON（{exc.msg} @ 位置 {exc.pos}）"
    if not isinstance(data, dict):
        return {}, f"agents/policy.json 顶层必须是对象，实际 {type(data).__name__}"
    return data, ""


def policy_file() -> dict:
    """读政策文件（只要数据；"读不到"的原因见 `load_policy_file()`）。"""
    return load_policy_file()[0]


def switch_state() -> tuple[bool, str]:
    """返回 `(是否离线, 来源说明)`；取值优先级 env > `offline_switch.enabled`（与脚本侧同口径）。

    **政策不可读/非法 ⇒ 按离线处理**（M4）：文件缺失、不可读、坏 JSON、顶层不是对象、
    缺 `offline_switch`、`env_var`/真值表/`enabled` 类型非法 —— 六种形态全部返回 `True`
    并在来源说明里写清是哪一种（"按离线处理"不是"猜"，是可核的判据）。

    非法 env 取值（`flase` 之类）→ 按"**最保守**"处理：视为**开启**（宁可拒绝外呼，
    也不静默放行）。脚本侧同情形是 `PolicyError`（关掉整条命令）——两侧都不静默，
    只是失败形态不同：后端进程要活着给前端一个可读错误，所以这里不抛在导入期。
    """
    data, problem = load_policy_file()
    if problem:
        return True, f"{problem} → 按离线处理（政策不可读不得静默放行外呼）"
    switch = data.get("offline_switch")
    if not isinstance(switch, dict):
        return True, (f"agents/policy.json::offline_switch 缺失或不是对象（实际 "
                      f"{type(switch).__name__}）→ 按离线处理（开关不可知 = 不放行）")
    name = str(switch.get("env_var") or "").strip()
    if not name:
        return True, ("agents/policy.json::offline_switch.env_var 缺失 → 按离线处理"
                      "（开关名不可知 = 无法判定，不放行）")
    truthy = [str(v).lower() for v in (switch.get("env_true_values") or [])]
    falsy = [str(v).lower() for v in (switch.get("env_false_values") or [])]
    if not truthy or not falsy:
        return True, ("agents/policy.json::offline_switch 真值表缺失"
                      "（env_true_values / env_false_values）→ 按离线处理"
                      "（取值语义不可知）")
    raw = (os.environ.get(name) or "").strip().lower()
    if raw:
        if raw in truthy:
            return True, f"env {name}={raw}"
        if raw in falsy:
            return False, f"env {name}={raw}"
        return True, f"env {name}={raw}（非法取值 → 按离线处理，不静默放行）"
    enabled = switch.get("enabled")
    if not isinstance(enabled, bool):
        return True, (f"agents/policy.json::offline_switch.enabled 不是布尔值"
                      f"（实际 {enabled!r}）→ 按离线处理（写错不得静默失效）")
    return enabled, "policy agents/policy.json::offline_switch.enabled"


def _refusal_text(target: str, source: str) -> str:
    """按已取得的 `source` 渲染拒绝文案。

    **一次判定只读一遍政策**：来源与文案不得来自两版数据（同一次 `switch_state()`）。
    """
    data, problem = load_policy_file()
    template = ""
    if not problem:
        switch = data.get("offline_switch")
        if isinstance(switch, dict):
            template = str(switch.get("refusal_reason") or "").strip()
    if not template:
        return f"离线开关已开启（{source}）→ 拒绝外呼：{target}"
    return template.replace("{source}", source).replace("{target}", target)


def refusal_text(target: str) -> str:
    """拒绝文案（模板取自政策 `refusal_reason`；政策不可用或模板缺失 → 给最小文案）。
    """
    return _refusal_text(target, switch_state()[1])


def refuse_if_offline(target: str) -> None:
    """**在构造/发起模型调用之前**调用：离线即抛 `OfflineRefused`（点名来源与目标模型）。"""
    enabled, source = switch_state()
    if enabled:
        raise OfflineRefused(_refusal_text(target, source))
