#!/usr/bin/env python3
"""取**网络事件时间**并折算 UTC+8（规则 R2：`docs/1-WORKFLOW.MD:401/:403`）。

为什么不用本机时钟：本机时区会变（曾为 UTC+9、现为 UTC-7），直接取本地时间会与仓库
口径（UTC+8）差一天甚至差几天；而 HTTP `Date` 响应头是**服务器时间**，属"网络事件"。

用法：
    python scripts/now-network.py            # 打印 `YYYY-MM-DD HH:MM UTC+8`
    python scripts/now-network.py --date     # 只打印 `YYYY-MM-DD`
    python scripts/now-network.py --json     # 机器可读：来源/UTC/UTC+8/偏移

fail-closed：取不到网络时间 ⇒ **rc=1 并明确报错**，绝不回退到本机时钟
（回退会让"未核验"伪装成"已核验"，正是该规则要防的事）。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.request

# 2026-10-25 实测：本机无 token 直连 github.com/api.github.com 会被 TLS 拦
# （SSL UNEXPECTED_EOF），而 baidu/bing 可达且都返回 HTTP `Date` 头 ⇒ 用它们做时间源。
# 顺序即优先级；任一成功即用。取不到 ⇒ fail-closed（不回退本机时钟）。
SOURCES = [
    "https://www.baidu.com/",
    "https://www.bing.com/",
]
USER_AGENT = "dsh-now-network/1.0"


def fetch_server_time() -> tuple[dt.datetime, str]:
    """取第一个可用来源的 HTTP `Date` 头，返回 (UTC 时间, 来源 URL)。"""
    last = ""
    for url in SOURCES:
        try:
            req = urllib.request.Request(
                url, method="HEAD", headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.headers.get("Date")
                if not raw:
                    last = f"{url}: 响应里没有 Date 头"
                    continue
                stamp = dt.datetime.strptime(raw, "%a, %d %b %Y %H:%M:%S %Z")
                return stamp.replace(tzinfo=dt.timezone.utc), url
        except Exception as exc:  # noqa: BLE001 - 任何网络失败都归一为"取不到"
            last = f"{url}: {exc}"
    raise RuntimeError(f"取不到网络时间（{last}）⇒ 按 R2 fail-closed，不回退本机时钟")


def main() -> int:
    """命令行入口。"""
    ap = argparse.ArgumentParser(description="网络事件时间 → UTC+8")
    ap.add_argument("--date", action="store_true", help="只打印日期")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args()

    try:
        utc, src = fetch_server_time()
    except RuntimeError as exc:
        print(f"NOW-NETWORK FAIL：{exc}", file=sys.stderr)
        return 1
    cst = utc.astimezone(dt.timezone(dt.timedelta(hours=8)))
    if args.json:
        print(json.dumps({"source": src,
                          "utc": utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                          "utc8": cst.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
                          "date": cst.strftime("%Y-%m-%d")}, ensure_ascii=False))
    elif args.date:
        print(cst.strftime("%Y-%m-%d"))
    else:
        print(f"{cst.strftime('%Y-%m-%d %H:%M')} UTC+8（来源 {src} 的 HTTP Date 头）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
