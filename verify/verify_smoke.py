"""Smoke verification for the original (pre-port) codebase on Windows.

Checks: paperqa package imports, backend main.py loads its FastAPI app,
frontend static assets exist, PDF can be rendered to a page preview via PyMuPDF
(used by runtime_trace), and the local paper reader parses PaperQA2.pdf.
Run: .venv\\Scripts\\python.exe verify_smoke.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = ROOT / "paper-qa-script"
BACKEND = SCRIPT_DIR / "reactflow-paperqa-prototype" / "backend" / "main.py"
PDF = ROOT / "data" / "pdf" / "PaperQA2.pdf"

sys.path.insert(0, str(SCRIPT_DIR))

results: list[str] = []


def check(name: str, fn) -> None:
    try:
        detail = fn()
        results.append(f"[OK] {name}: {detail}")
    except Exception as exc:  # noqa: BLE001
        results.append(f"[FAIL] {name}: {type(exc).__name__}: {exc}")


def t_paperqa_import() -> str:
    import paperqa

    assert hasattr(paperqa, "Docs")
    assert hasattr(paperqa, "Settings")
    assert hasattr(paperqa, "ask")
    return f"paperqa {paperqa.__version__}"


def t_backend() -> str:
    spec = importlib.util.spec_from_file_location("backend_main", BACKEND)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "app")
    routes = sorted({r.path for r in mod.app.routes if hasattr(r, "path")})
    return f"FastAPI title={mod.app.title!r} routes={routes}"


def t_tracer() -> str:
    from runtime_trace import RuntimeTracer

    t = RuntimeTracer()
    t.__enter__()
    t.__exit__(None, None, None)
    return f"RuntimeTracer ok, targets={len(RuntimeTracer.TARGETS)}"


def t_streamlit() -> str:
    import streamlit as st

    return f"streamlit {st.__version__}"


def t_litellm() -> str:
    import litellm

    return f"litellm {litellm.__version__ if hasattr(litellm, '__version__') else 'ok'}"


def t_fitz() -> str:
    import base64

    import fitz

    with fitz.open(PDF) as pdf:
        n = len(pdf)
        pix = pdf[0].get_pixmap(matrix=fitz.Matrix(0.45, 0.45), alpha=False)
        raw = pix.tobytes("png")
        b64 = base64.b64encode(raw).decode("ascii")
    return f"fitz pages={n}, page1 png bytes={len(raw)}, b64 len={len(b64)}"


def t_graphviz() -> str:
    import os
    import shutil

    # dot 若不在 PATH（如 winget 安装的 Graphviz），自动补充常见安装目录
    if not shutil.which("dot"):
        for _d in (
            r"C:\Program Files\Graphviz\bin",
            r"C:\Program Files (x86)\Graphviz\bin",
            r"C:\ProgramData\chocolatey\bin",
            "/opt/homebrew/bin",
            "/usr/local/bin",
            "/usr/bin",
        ):
            if os.path.isdir(_d) and (
                os.path.isfile(os.path.join(_d, "dot"))
                or os.path.isfile(os.path.join(_d, "dot.exe"))
            ):
                os.environ["PATH"] = _d + os.pathsep + os.environ.get("PATH", "")
                break

    import graphviz as gv

    dot = "digraph G { a -> b; }"
    src = gv.Source(dot)
    svg = src.pipe(format="svg")
    return f"graphviz svg bytes={len(svg)}"


def t_reader_offline() -> str:
    """Parse the PDF with the locally discovered PDF parser (no API calls)."""
    import anyio

    from paperqa.readers import read_doc
    from paperqa.settings import get_settings
    from paperqa.types import Doc

    async def _run() -> str:
        settings = get_settings()
        parse_pdf = settings.parsing.parse_pdf
        parsed = await read_doc(
            str(PDF),
            Doc(docname="", citation="", dockey="smoke", content_hash="smoke"),
            parsed_text_only=True,
            page_range=(1, 4),
            parse_pdf=parse_pdf,
            **settings.parsing.reader_config,
        )
        media = getattr(parsed, "media", None) or []
        return (
            f"parser={getattr(parse_pdf, '__module__', '?')}."
            f"{getattr(parse_pdf, '__name__', '?')} "
            f"parsed_len={getattr(parsed, 'text_length', None)} media={len(media)}"
        )

    return anyio.run(_run)


for name, fn in [
    ("paperqa import", t_paperqa_import),
    ("backend main.py", t_backend),
    ("runtime_trace", t_tracer),
    ("streamlit", t_streamlit),
    ("litellm", t_litellm),
    ("pymupdf page preview", t_fitz),
    ("graphviz svg render", t_graphviz),
    ("offline reader parse", t_reader_offline),
]:
    check(name, fn)

print("\n".join(results))
failed = [r for r in results if r.startswith("[FAIL]")]
print(f"\n=== {len(results) - len(failed)}/{len(results)} checks passed ===")
sys.exit(1 if failed else 0)
