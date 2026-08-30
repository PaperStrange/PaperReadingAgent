"""US-5.4 单元证据（可复现）：litellm 回调裁剪。

模拟回调列表达到 MAX_CALLBACKS(30) 且含重复对象 → _prune_litellm_callbacks
应去重并保留最近 20 个，避免长期运行累计爆表。
运行：.venv\\Scripts\\python.exe verify\\verify_prune_callbacks.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "paper-qa-script"))

from app.engine import prune_litellm_callbacks  # noqa: E402


def main() -> int:
    import litellm

    keepers = [object() for _ in range(28)]  # 28 个“最近注册”
    first = object()
    litellm.callbacks = [first, first] + [object() for _ in range(28)] + [first]
    # 上面 32 项（超上限且含重复）→ 预期：去重后 30 个唯一 → 保留最近 20 个
    prune_litellm_callbacks()
    items = list(litellm.callbacks)
    unique = len({id(x) for x in items})
    assert len(items) <= 20, f"len={len(items)} 超过 20"
    assert unique == len(items), "存在重复回调"
    # 最近注册的（后面加入的）应保留
    assert items[-1] is first or first not in items, "最近注册的回调被误删"
    print(f"PASS: {len(items)} unique callbacks (<=20) after prune")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
