"""Sprint-15 F-AC12（走查 N2）：论文页面预览清晰度实证。

直接调 runtime_trace._render_pdf_page_preview 渲染 PaperQA2.pdf 第 1 页，
解析 PNG 头获取像素尺寸：1.0 缩放下 A4 页宽应 ≥ 500px（0.45 缩放时 ~268px）。
Run: .venv\\Scripts\\python.exe verify\\verify_f12_preview_res.py
"""
from __future__ import annotations
VERIFY_META = {'features': 'F-AC12 预览清晰度实证：1.0 缩放渲染，PNG 宽度 ≥500px（旧 0.45 为 ~268px）', 'tier': 'offline', 'providers': [], 'est_seconds': 10, 'est_cost_cny': 0, 'routes': [], 'requires': ['none']}

import base64
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "paper-qa-script"))

from runtime_trace import _render_pdf_page_preview  # noqa: E402

PASSED = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    assert cond, f"{name} FAIL: {detail}"
    PASSED += 1
    print(f"PASS: {name} {detail}")


def png_size(data_url: str) -> tuple[int, int]:
    b64 = data_url.split(",", 1)[1]
    raw = base64.b64decode(b64)
    assert raw[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    w, h = struct.unpack(">II", raw[16:24])
    return w, h


def main() -> int:
    pdf = ROOT / "data" / "pdf" / "PaperQA2.pdf"
    url, reason = _render_pdf_page_preview(str(pdf), 1)
    ok("F-AC12 预览渲染成功", url is not None and reason == "ok", f"reason={reason}")
    assert url is not None
    w, h = png_size(url)
    ok("F-AC12 分辨率提升（宽 ≥ 500px）", w >= 500, f"png={w}x{h}")
    print(f"\nALL PASS ({PASSED} assertions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
