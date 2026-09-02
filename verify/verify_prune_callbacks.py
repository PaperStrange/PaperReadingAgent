"""US-5.4 + Sprint-7 M2 单元证据（可复现）：litellm 回调裁剪（上限 env 可配 + 钳制）。

模拟回调列表达到 MAX_CALLBACKS(30) 且含重复对象 → prune_litellm_callbacks
应去重并保留最近 N 个（默认 20；PAPERQA_LITELLM_CALLBACK_LIMIT 覆盖；
非法值回落 20；>30 钳制到 30，防止自拆 litellm MAX_CALLBACKS 防护）。
运行：.venv\\Scripts\\python.exe verify\\verify_prune_callbacks.py
"""

from __future__ import annotations
VERIFY_META = {'features': 'litellm 回调裁剪：上限 env 可配 + 非法值回落 + 钳制（离线）', 'tier': 'offline', 'providers': [], 'est_seconds': 2, 'est_cost_cny': 0, 'routes': [], 'requires': ['none']}

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "paper-qa-script"))

from app.engine import prune_litellm_callbacks  # noqa: E402


def _fill(limit_expected: int, set_env: str | None) -> None:
    import litellm

    if set_env is None:
        os.environ.pop("PAPERQA_LITELLM_CALLBACK_LIMIT", None)
    else:
        os.environ["PAPERQA_LITELLM_CALLBACK_LIMIT"] = set_env
    # 构造 31 项、29 个唯一对象（28 个独立对象 + first 注册 3 次且**最后注册**）：
    # 超上限且含重复 → 去重后 29 唯一（first 位于末位）→ 保留最近 limit 个
    first = object()
    litellm.callbacks = [object() for _ in range(28)] + [first, first, first]
    prune_litellm_callbacks()
    items = list(litellm.callbacks)
    unique = len({id(x) for x in items})
    assert len(items) <= limit_expected, f"len={len(items)} 超过 {limit_expected}"
    assert unique == len(items), "存在重复回调"
    # 最近注册的（最后加入的 first）应保留
    assert items[-1] is first, "最近注册的回调被误删"
    print(f"PASS: env={set_env!r} -> {len(items)} unique callbacks (<= {limit_expected})")


def main() -> int:
    try:
        _fill(20, None)      # 默认 20
        _fill(5, "5")        # env 覆盖为 5
        _fill(20, "abc")     # 非法值回落 20
        _fill(20, "0")       # 非正值回落 20
        _fill(30, "40")      # 超上限钳制到 30（litellm MAX_CALLBACKS）
        return 0
    finally:
        os.environ.pop("PAPERQA_LITELLM_CALLBACK_LIMIT", None)


if __name__ == "__main__":
    raise SystemExit(main())
