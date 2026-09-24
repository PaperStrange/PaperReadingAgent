"""TG-8：**离线开关**唯一实现（一个开关关掉全部外呼；不是靠网络超时）。

**为什么需要这个模块**（TG-8 正文 + 卡内追加证据）：此前的"离线能力"是**每处各自为战**的——
`agent-ops fetch-spec --offline` 只管自己那一条 URL、`refresh-providers --from-file` 只换掉
抓取函数、`fetch-prices` 干脆没有离线档。于是"离线跑一次"这个要求只能靠**断网碰运气**：
网络通就静默外呼（价格/配置/远程数据被悄悄刷新），网络不通就退化成**超时**（慢、且失败原因
指向超时而非"你开了离线开关"）。本模块把开关收敛成**一个判据 + 一处实现**：

    数据源（唯一真源）= `agents/policy.json::offline_switch`（`verify/agent_policy.py` 校验类型，
    字段名拼错/取值非法 → `PolicyError` fail-closed，不静默变"永远在线"）；取值优先级
    **env `<env_var>` > `policy.enabled`**（env 是显式操作者开关、能继承到子进程；policy 是默认值）。

    判据（可核，而非"看它有没有超时"）= 每个外呼入口在**发起请求之前**调 `refuse_if_offline(target)`
    → 开关开启即抛 `OfflineRefused`（`BaseException` 子类，不被各脚本 `except Exception` 吞掉），
    消息含 **来源**（env 名 / policy 键）与**目标**（URL / 模型名），退出码取
    `offline_switch.refuse_exit_code`。

**消费方（外呼入口全覆盖）**：`scripts/fetch-prices.py`（价格刷新，含三个固定来源）、
`scripts/refresh-providers.py`（provider 配置/官网刷新、远程文档抓取）、
`scripts/agent-ops.py fetch-spec`（远程 spec 抓取）、`verify/e2e_common.py`（自举后端时的
HF 离线变量注入）。**后端侧另有一份最小实现**：`paper-qa-script/app/offline_guard.py`
（模型 API 三处：LLM / vision / API 向量模型）——之所以不共用本模块：`app/**` 是原型运行时，
不能把"应用能不能起来"绑到 `agents/functions/*.md`+`fanout.json` 是否齐全（那是闸门数据）。
两侧读**同一份政策键**，并由 `verify/verify_agentops.py` 的 UC-19 断言"同一 env 取值同结论"。
**未覆盖**（如实标注）：GitHub API 直调、自定义 provider
（`PAPERQA_PROVIDERS_JSON`）指向的端点——它们的调用方不在本仓库脚本内。

**局限（如实标注，TG-8 卡内要求）**：本开关是**应用层**闸门，不是内核级/防火墙级阻断。
它能保证"被枚举的入口拒绝得又早又明确"，但**不能**保证"进程内所有 socket 都被拦"；
真正的内核级证据需要 `netsh advfirewall` / WFP 规则（需管理员权限，本卡不引入）。
故实测证据采用**代理级**断网（`HTTP(S)_PROXY=http://127.0.0.1:9`）做对照探针，并如实标注该口径。

**环境变量注入（开关开启时的附加动作）**：`hf_offline_env`（`HF_HUB_OFFLINE` /
`TRANSFORMERS_OFFLINE`）由 `apply_env()` 注入当前进程——用于消除本地向量模型解析时的
HF HEAD 重试阻塞（TG-8 正文 ③）。它**不参与**上面的拒绝判据（否则会把"本地模型解析"误判成外呼）。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from verify.agent_policy import PolicyError, load_policy  # noqa: E402


class OfflineRefused(BaseException):
    """离线开关拒绝一次外呼（**不是** `Exception`：入口的 `except Exception` 不得吞掉它）。

    继承 `BaseException` 的理由：脚本里"抓取失败就回退/降级"的兜底块普遍写 `except Exception`
    （这是对的——网络抖动确实该降级）。但"离线开关说这次外呼被禁止"不是抖动，**降级会把
    拒绝伪装成正常路径**（正是卡文要消灭的"静默"）。故它必须穿透兜底，直达顶层退出码。
    """


def switch_state() -> tuple[bool, str]:
    """返回 `(是否离线, 来源说明)`。取值优先级 env > policy；非法 env 取值 → `PolicyError`。

    `env` 为**空串/纯空白**时视为"未设置"（与 `run_suite.budget_from` 同口径），回落到
    policy 默认值——这样 `PAPERQA_OFFLINE=` 不会意外开启离线档。
    """
    policy = load_policy()
    data = policy.offline_switch
    name = str(data["env_var"])
    raw = (os.environ.get(name) or "").strip().lower()
    if raw:
        if raw in policy._offline_env_true_values(data):
            return True, f"env {name}={raw}"
        if raw in policy._offline_env_false_values(data):
            return False, f"env {name}={raw}"
        raise PolicyError(f"{name}={raw!r} 不是合法开关取值（合法：true/false/yes/no/1/0/on/off）"
                          f"——拼错不会静默当成『关闭』，请修正环境变量")
    enabled = data.get("enabled")
    if not isinstance(enabled, bool):
        raise PolicyError(f"offline_switch.enabled 必须是布尔值，实际 {enabled!r}"
                          f"（写错会让开关静默失效）")
    return enabled, "policy agents/policy.json::offline_switch.enabled"


def offline_enabled() -> bool:
    """只问"现在是否离线"（不关心的调用方用这个；原因文案走 `refusal_text`）。"""
    return switch_state()[0]


def refusal_text(target: str, source: str | None = None) -> str:
    """拒绝文案（模板来自政策 `offline_switch.refusal_reason`，本模块不写死第二份）。"""
    data = load_policy().offline_switch
    why = source if source is not None else switch_state()[1]
    return str(data["refusal_reason"]).replace("{source}", why).replace("{target}", str(target))


def refuse_if_offline(target: str) -> None:
    """**每个外呼入口在发请求之前**调本函数：开关开启 → 抛 `OfflineRefused`（点名来源与目标）。

    前置（在 DNS 解析/连接/超时之前）是关键：判据必须是"明确报错"而不是"网络超时"。
    """
    enabled, source = switch_state()
    if enabled:
        raise OfflineRefused(refusal_text(target, source))


def refuse_exit_code() -> int:
    """拒绝时的进程退出码（政策 `offline_switch.refuse_exit_code`；与"验出违规=1"区分开）。"""
    return int(load_policy().offline_switch["refuse_exit_code"])


def apply_env(environ: dict | None = None) -> dict:
    """把 `hf_offline_env` 注入环境（默认当前进程；传 dict 则只改该副本，测试用）。

    开关**关闭**时不注入（不改变既有行为）；开启时返回实际注入的键值（可核留痕）。
    """
    enabled, _ = switch_state()
    if not enabled:
        return {}
    pairs = {str(k): str(v) for k, v in (load_policy().offline_switch["hf_offline_env"] or {}).items()
             if not str(k).startswith("_")}
    target = os.environ if environ is None else environ
    target.update(pairs)
    return pairs


def refuse_or_exit(target: str) -> None:
    """CLI 便捷入口：被拒绝即打印原因并以政策退出码退出（`fetch-spec` 等单点入口用）。

    打印到 **stdout**：与各脚本既有的 `WARN:`/`ERR:` 输出同流，便于汇总与断言检索。
    """
    try:
        refuse_if_offline(target)
    except OfflineRefused as exc:
        print(f"OFFLINE-REFUSED: {exc}")
        raise SystemExit(refuse_exit_code()) from None
