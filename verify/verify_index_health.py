"""Sprint-7 M1 证据（可复现）：索引一致性三重探测（files.zip / index/meta.json / tantivy 段）。

覆盖：
  1) 合成状态探针（离线）：六种损坏形态 → _index_corrupt 判定
  2) 真实构建 + 段损坏自愈：config → load_index 建索引 → 篡改 meta.json →
     探针判损坏 → 再 load_index 整目录重建自愈（含 paper_dir_marker 指纹）
运行：
  .venv\\Scripts\\python.exe verify\\verify_index_health.py
前提：无需 API key、无需联网（无图 txt 语料 → 不触发视觉增强；tantivy 构建纯本地）。
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import tempfile
import types
import uuid
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "paper-qa-script"))

from app.orchestration import _index_corrupt  # noqa: E402
from app.orchestration import PipelineOrchestrator, StepRequest  # noqa: E402
from app.session_store import MemorySessionStore  # noqa: E402
from app.engine import ENGINE  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GOOD_META = '{"segments":[]}'


def _stub(index_directory: Path, name: str = "vh_stub") -> types.SimpleNamespace:
    return types.SimpleNamespace(
        agent=types.SimpleNamespace(
            index=types.SimpleNamespace(index_directory=str(index_directory), name=name)
        )
    )


def _setup(idx: Path, *, zip_bytes: bytes | None, meta_text: str | None) -> None:
    idx.mkdir(parents=True, exist_ok=True)
    if zip_bytes is not None:
        (idx / "files.zip").write_bytes(zip_bytes)
    if meta_text is not None:
        (idx / "index").mkdir(parents=True, exist_ok=True)
        (idx / "index" / "meta.json").write_text(meta_text, encoding="utf-8")


def synthetic_probes(tmp: Path) -> None:
    """六种损坏形态判定（全部离线）。"""
    good_zip = zlib.compress(b"payload")
    cases: list[tuple[str, Path, bool]] = []
    # 1) 空目录（半成品）
    d1 = tmp / "c1"
    _setup(d1, zip_bytes=None, meta_text=None)
    cases.append(("空目录（半成品）", d1, True))
    # 2) files.zip 损坏
    d2 = tmp / "c2"
    _setup(d2, zip_bytes=b"not-zlib", meta_text=GOOD_META)
    cases.append(("files.zip 损坏", d2, True))
    # 3) meta.json 缺失（files.zip 正常）
    d3 = tmp / "c3"
    _setup(d3, zip_bytes=good_zip, meta_text=None)
    cases.append(("index/meta.json 缺失", d3, True))
    # 4) meta.json 非法 JSON
    d4 = tmp / "c4"
    _setup(d4, zip_bytes=good_zip, meta_text="{broken")
    cases.append(("index/meta.json 非法 JSON", d4, True))
    # 5) meta.json 合法但非真 tantivy 段（Index.open 失败；已在 pin 的 tantivy 上实测成立）
    d5 = tmp / "c5"
    _setup(d5, zip_bytes=good_zip, meta_text=GOOD_META)
    cases.append(("meta.json 伪段（tantivy 打不开）", d5, True))
    # 6) files.zip 缺失 + meta 伪段 → 判损坏（注意：files.zip 缺失但真段完整时**不**判损坏，
    #    属已知边界——该状态可由 build=true 增量重建自愈，指纹不变不触发整目录删除）
    d6 = tmp / "c6"
    _setup(d6, zip_bytes=None, meta_text=GOOD_META)
    cases.append(("files.zip 缺失 + meta 伪段", d6, True))

    for name, d, expected in cases:
        got = _index_corrupt(_stub(d))
        assert got is expected, f"{name}: 期望 {expected}，实际 {got}"
        print(f"PASS: {name} -> corrupt={got}")


async def real_build_rebuild(tmp: Path) -> None:
    """真实构建 + 段损坏自愈（走编排层 load_index 完整路径，含指纹 marker）。"""
    old_home = os.environ.get("PQA_HOME")
    os.environ["PQA_HOME"] = str(tmp / "pqa_home")
    paper_dir = tmp / "papers"
    try:
        paper_dir.mkdir(parents=True, exist_ok=True)
        # 无图 txt 语料 + CSV manifest 提供 citation/title：
        # 使 aadd 跳过 LLM 引用推断（citation 已在 manifest）与结构化提取（use_doc_details=False），
        # 构建纯本地（tantivy 段/指纹/files.zip 逻辑与文件类型无关）
        (paper_dir / "fixture.txt").write_text(
            "PaperQA2 is an agent for scientific Q&A over papers.\n"
            "It uses RAG with evidence gathering and citation.\n"
            "Index consistency probes cover files.zip, meta.json, and tantivy segments.\n",
            encoding="utf-8",
        )
        manifest = tmp / "manifest.csv"
        manifest.write_text(
            "file_location,citation,title\n"
            'fixture.txt,"Fixture, 2026, Test Journal","Fixture title"\n',
            encoding="utf-8",
        )
        store = MemorySessionStore()
        orch = PipelineOrchestrator(engine=ENGINE, store=store)
        sid = f"vh-{uuid.uuid4().hex[:10]}"

        def ev(_: dict) -> None:
            return None

        r1 = await orch.run_step(
            StepRequest(
                session_id=sid,
                step="config",
                params={
                    "paper_directory": str(paper_dir),
                    "index_name": "vh_index",
                    "api_key": "dummy-not-used",
                    "embedding_model": "st-multi-qa-MiniLM-L6-cos-v1",  # 显式指定 → 跳过推荐器联网
                    "manifest_file": str(manifest),  # citation/title 由 manifest 提供 → 无 LLM 调用
                },
            ),
            on_event=ev,
        )
        assert r1.ok, f"config 失败：{r1.error}"
        settings = store.get_or_create(sid).settings

        # 构建前为空/半成品 → 判损坏（走整目录重建路径）
        assert _index_corrupt(settings) is True, "空索引应判损坏"

        r2 = await orch.run_step(
            StepRequest(session_id=sid, step="load_index", params={"build": True}),
            on_event=ev,
        )
        assert r2.ok, f"load_index 失败：{r2.error}"
        assert r2.output["indexed_files"] >= 1, f"索引文件数异常：{r2.output}"
        assert _index_corrupt(settings) is False, "健康索引被误判损坏"
        print(f"PASS: 真实构建 {r2.output['indexed_files']} 文件，健康探针 False")

        # 指纹 marker 已写入
        marker = Path(settings.agent.index.index_directory) / settings.agent.index.name / "paper_dir_marker.txt"
        assert marker.exists(), "paper_dir_marker.txt 未写入"
        print("PASS: paper_dir_marker.txt 指纹已写入")

        # 篡改 meta.json → 判损坏 → 再 load_index 整目录重建自愈
        meta = Path(settings.agent.index.index_directory) / settings.agent.index.name / "index" / "meta.json"
        meta.write_text("{corrupted-segments", encoding="utf-8")
        assert _index_corrupt(settings) is True, "篡改 meta.json 后应判损坏"
        r3 = await orch.run_step(
            StepRequest(session_id=sid, step="load_index", params={"build": True}),
            on_event=ev,
        )
        assert r3.ok, f"重建失败：{r3.error}"
        assert r3.output["indexed_files"] >= 1
        assert _index_corrupt(settings) is False, "重建后应健康"
        print("PASS: 篡改 meta.json → 整目录重建自愈 → 探针 False")
    finally:
        if old_home is not None:
            os.environ["PQA_HOME"] = old_home
        else:
            os.environ.pop("PQA_HOME", None)


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="verify_index_health_"))
    try:
        print("== 1) 合成状态探针（离线）==")
        synthetic_probes(tmp)
        print("\n== 2) 真实构建 + 段损坏自愈 ==")
        asyncio.run(real_build_rebuild(tmp))
        print("\nALL PASS")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
