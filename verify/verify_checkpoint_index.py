"""F-AC16 v1：checkpoint 只读索引（`app/checkpoint_index.py`）的离线回归。

全部用**合成 fixture**（不碰真实 `~/.pqa`、不启用后端、零成本）：
  ① 扫描只认 `*.json`（`.json.tmp`/`notes.txt` 忽略），按 updated_at 倒序；
  ② 逐篇记录含**载荷路径/存在性/字节数**（ready 有载荷、deduped 无独立载荷、缺失载荷显式标 False）；
  ③ 坏 manifest → `readable=False` + `status=corrupt` + 记原因，**不拖垮整个视图**（fail-soft）；
  ④ `namespace_detail()` 命中/未命中/坏件三种情形；
  ⑤ `resolve_payload()` 供"用既有 checkpoint 复现"；
  ⑥ 白名单：返回字段**不含**任何密钥类字段（只读视图的暴露面钉死）；
  ⑦ 空目录/不存在目录 → 空列表（不抛）。

Run: .venv\\Scripts\\python.exe verify\\verify_checkpoint_index.py
"""
from __future__ import annotations
VERIFY_META = {'features': 'F-AC16 v1 checkpoint 只读索引：扫描/排序/逐篇载荷路径与存在性/坏件 fail-soft/detail 与 resolve_payload/字段白名单（离线合成 fixture）', 'tier': 'offline', 'providers': [], 'est_seconds': 5, 'est_cost_cny': 0, 'routes': ['/api/checkpoints'], 'requires': ['none']}

import gzip
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "paper-qa-script") not in sys.path:
    sys.path.insert(0, str(ROOT / "paper-qa-script"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import checkpoint_index as CI  # noqa: E402

PASSED = 0
ALLOWED_KEYS = {
    "checkpoint_key", "manifest_path", "payload_dir", "status", "paper_dir", "index_name",
    "embedding_model", "chunk_chars", "chunk_overlap", "updated_at", "docs_total",
    "docs_by_status", "payload_bytes_total", "readable", "error", "docs",
}


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    assert cond, f"{name} FAIL: {detail}"
    PASSED += 1
    print(f"PASS: {name} {detail}")


def build_fixture(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    good = {
        "schema": 1,
        "checkpoint_key": "aaa111",
        "paper_dir": "D:/papers",
        "index_name": "idx-demo",
        "embedding_model": "st-demo",
        "chunk_chars": 5000,
        "chunk_overlap": 250,
        "status": "ready",
        "updated_at": 4_000_000_000.0,
        "docs": {
            "A.pdf": {"dockey": "dk1", "docname": "A", "texts_count": 3, "status": "ready", "reused": True},
            "B.pdf": {"dockey": "dk2", "docname": "B", "texts_count": 0, "status": "deduped"},
        },
    }
    (root / "aaa111.json").write_text(json.dumps(good, ensure_ascii=False), encoding="utf-8")
    # 真实 gzip 载荷（ready 篇）
    payload_dir = root / "aaa111"
    payload_dir.mkdir(parents=True, exist_ok=True)
    with gzip.open(payload_dir / "dk1.json.gz", "wt", encoding="utf-8") as fh:
        json.dump({"doc": {"dockey": "dk1"}, "texts": [{"text": "x"}]}, fh)

    partial = {
        "schema": 1, "checkpoint_key": "bbb222", "status": "partial", "updated_at": 3_999_999_000.0,
        "docs": {"C.pdf": {"dockey": "dk3", "docname": "C", "texts_count": 2, "status": "ready"}},
    }
    (root / "bbb222.json").write_text(json.dumps(partial, ensure_ascii=False), encoding="utf-8")  # 无载荷目录 → 缺失

    (root / "ccc333.json").write_text("{ not valid json", encoding="utf-8")
    (root / "notes.txt").write_text("hello", encoding="utf-8")
    (root / "ddd444.json.tmp").write_text("{}", encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "checkpoints"
        build_fixture(root)

        items = CI.scan(root)
        by_key = {r["checkpoint_key"]: r for r in items}
        ok("① 只认 *.json 且返回 3 条（.json.tmp/notes.txt 忽略）", len(items) == 3, f"keys={sorted(by_key)}")
        ok("① 按 updated_at 倒序（两件可读件在前）",
           [r["checkpoint_key"] for r in items][:2] == ["aaa111", "bbb222"],
           str([r["checkpoint_key"] for r in items]))
        ok("① 坏件（无 updated_at）回落到 manifest mtime 参与排序",
           items[-1]["checkpoint_key"] == "ccc333" and float(items[-1]["updated_at"] or 0) > 0,
           f"key={items[-1]['checkpoint_key']} updated_at={items[-1]['updated_at']}")

        aaa = by_key["aaa111"]
        ok("② ready 命名空间：status/docs 统计正确",
           aaa["status"] == "ready" and aaa["docs_total"] == 2
           and aaa["docs_by_status"] == {"ready": 1, "deduped": 1},
           json.dumps({k: aaa[k] for k in ("status", "docs_total", "docs_by_status")}, ensure_ascii=False))
        dk1 = next(d for d in aaa["docs"] if d["dockey"] == "dk1")
        ok("② 有载荷篇：路径存在、字节数 >0、reused 透传",
           dk1["payload_exists"] is True and int(dk1["payload_bytes"] or 0) > 0
           and dk1["payload_path"].endswith("dk1.json.gz") and dk1["reused"] is True,
           f"bytes={dk1['payload_bytes']} path={dk1['payload_path']}")
        ok("② 载荷字节合计 = 该篇字节", aaa["payload_bytes_total"] == dk1["payload_bytes"],
           f"total={aaa['payload_bytes_total']}")
        dk2 = next(d for d in aaa["docs"] if d["dockey"] == "dk2")
        ok("② deduped 篇：无载荷文件（显式 False，不谎报就绪）",
           dk2["status"] == "deduped" and dk2["payload_exists"] is False, json.dumps(dk2, ensure_ascii=False))

        dk3 = by_key["bbb222"]["docs"][0]
        ok("② 载荷缺失被显式标出（不静默）", dk3["payload_exists"] is False and dk3["payload_path"] != "",
           dk3["payload_path"])

        # ②b 复核 Round 5 minor：manifest 被改坏（dockey 带 `..`）时路径必须归一化，**不得探出命名空间**
        (root / "eee444.json").write_text(json.dumps({
            "checkpoint_key": "eee444", "status": "ready", "updated_at": 4_000_000_100.0,
            "docs": {"E.pdf": {"dockey": "..\\..\\outside", "docname": "E", "texts_count": 1, "status": "ready"}},
        }, ensure_ascii=False), encoding="utf-8")
        evil = {r["checkpoint_key"]: r for r in CI.scan(root)}["eee444"]["docs"][0]
        ok("②b manifest 的 dockey 带 `..` → 路径归一化到命名空间内（不探出根外）",
           ".." not in Path(evil["payload_path"]).name and Path(evil["payload_path"]).parent.name == "eee444",
           evil["payload_path"])

        ccc = by_key["ccc333"]
        ok("③ 坏 manifest：fail-soft（readable=False + status=corrupt + 记原因）",
           ccc["readable"] is False and ccc["status"] == "corrupt" and bool(ccc["error"]) and ccc["docs"] == [],
           f"error={ccc['error'][:48]}")

        detail = CI.namespace_detail("aaa111", root)
        ok("④ namespace_detail 命中且与扫描一致",
           bool(detail) and detail["docs_total"] == 2 and detail["embedding_model"] == "st-demo",
           json.dumps({k: (detail or {}).get(k) for k in ("docs_total", "embedding_model")}, ensure_ascii=False))
        ok("④ namespace_detail 合法但不存在 → None（非法格式由 ⑧ 断言）",
           CI.namespace_detail("deadbeefdeadbeef", root) is None)
        bad_detail = CI.namespace_detail("ccc333", root)
        ok("④ namespace_detail 坏件 → readable=False", bool(bad_detail) and bad_detail["readable"] is False,
           str((bad_detail or {}).get("error", ""))[:48])

        ok("⑤ resolve_payload 命中存在的载荷", CI.resolve_payload("aaa111", "dk1", root) is not None)
        ok("⑤ resolve_payload 缺失 → None", CI.resolve_payload("aaa111", "dk2", root) is None)

        leaked = set(aaa) - ALLOWED_KEYS
        ok("⑥ 字段白名单（无密钥类字段泄漏）", not leaked, str(sorted(leaked)))
        docs_keys = {k for d in aaa["docs"] for k in d}
        ok("⑥ 逐篇字段白名单", docs_keys <= {"name", "docname", "dockey", "status", "texts_count", "reused",
                                              "embedded_at", "error", "payload_path", "payload_exists", "payload_bytes"},
           str(sorted(docs_keys)))

        slim = CI.scan(root, include_docs=False)
        ok("⑥ include_docs=False 时省略 docs", all("docs" not in r for r in slim), str(len(slim)))

        ok("⑦ 不存在目录 → 空列表", CI.scan(Path(td) / "nope") == [])
        empty = Path(td) / "empty"
        empty.mkdir()
        ok("⑦ 空目录 → 空列表", CI.scan(empty) == [])

        # ⑧ 安全：`?key=` 来自 HTTP 查询串，必须防路径穿越（2026-09-21 自查发现并修复）
        for bad in ("../evil", "..\\evil", "aaa/bbb", "a" * 65, "", "not-hex!", "abc12"):
            raised = False
            try:
                CI.namespace_detail(bad, root)
            except ValueError:
                raised = True
            ok(f"⑧ 非法 key 被拒（路径穿越防护）：{bad[:12]!r}", raised, "expected ValueError")
        ok("⑧ 合法 key 大小写归一（大写 hex 也可用）+ 不存在的合法 key → None",
           bool(CI.namespace_detail("AAA111", root)) and CI.namespace_detail("deadbeefdeadbeef", root) is None,
           "AAA111 → aaa111；deadbeefdeadbeef → None")
        legit = CI.resolve_payload("aaa111", "dk1", root)
        ok("⑧ resolve_payload 的 dockey basename 收敛（`../../dk1` → 同一个合法载荷，未逃逸；`../nope` → None）",
           legit is not None and CI.resolve_payload("aaa111", "../../dk1", root) == legit
           and CI.resolve_payload("aaa111", "../nope", root) is None,
           f"legit={legit}")

    print(f"\nALL PASS ({PASSED} assertions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
