"""Sprint-16 F-AC8（验收⑥）：provider 一文件 + 加载校验 + 覆盖优先级 + 元数据可追溯。

离线断言（不联网、不起后端）：
  ① providers/<name>.json 四个内置文件齐备，name 与文件名一致，逐条可加载
  ② 切换 provider 只取对应文件的值（model/embedding/api_base/has_embedding_api 与文件逐项一致）
  ③ 生效来源标记为 file（provider_source）
  ④ 边界-非法文件：坏 JSON / 缺 model / name 与文件名不符 → 只跳过该文件并给出原因，不抛异常
  ⑤ 覆盖优先级：env PAPERQA_PROVIDERS_JSON 覆盖文件值（provider_source=env），随后还原
  ⑥ /api/providers 同源数据（list_providers_safe）含 source/fetched_at/source_urls，且**不含密钥字段**
  ⑦ 边界-未知 provider → ValueError 且消息列出可选值
  ⑧ 调研可追溯契约：每个内置文件 meta.source_urls 非空、meta.fetched_at 存在

Run: .venv\\Scripts\\python.exe verify\\verify_providers.py
"""
from __future__ import annotations
VERIFY_META = {'features': 'F-AC8 provider 一文件：文件加载/来源标记/覆盖优先级/非法文件跳过/无密钥泄漏/调研元数据契约', 'tier': 'offline', 'providers': [], 'est_seconds': 20, 'est_cost_cny': 0, 'routes': [], 'requires': []}

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "paper-qa-script"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import provider_config as pc  # noqa: E402

PASSED = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    assert cond, f"{name} FAIL: {detail}"
    PASSED += 1
    print(f"PASS: {name} {detail}")


def main() -> int:
    builtin = ("deepseek", "dashscope", "openai", "openrouter")

    # ① 文件齐备且可加载
    registry, problems = pc.load_provider_files()
    ok("① providers/ 目录存在", pc.PROVIDERS_DIR.is_dir(), str(pc.PROVIDERS_DIR))
    ok("① 四个内置 provider 文件已加载（无解析问题）",
       all(n in registry for n in builtin) and not problems,
       json.dumps({"loaded": sorted(registry), "problems": problems}, ensure_ascii=False))

    # ② 切换 provider 只取对应文件的值
    for name in builtin:
        raw = json.loads((pc.PROVIDERS_DIR / f"{name}.json").read_text(encoding="utf-8"))
        cfg = pc.get_provider_config(name)
        same = all(cfg.get(k) == raw.get(k) for k in ("api_base", "model", "vision_model", "embedding", "has_embedding_api"))
        ok(f"② {name} 运行配置与 providers/{name}.json 逐项一致", same,
           json.dumps({k: (cfg.get(k), raw.get(k)) for k in ("model", "embedding") if cfg.get(k) != raw.get(k)}, ensure_ascii=False))

    # ③ 来源标记
    sources = {n: pc.provider_source(n) for n in builtin}
    ok("③ 四个内置 provider 生效来源 = file", all(v == "file" for v in sources.values()), json.dumps(sources, ensure_ascii=False))

    # ④ 边界：非法文件只跳过并给原因
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "good.json").write_text(json.dumps({"name": "good", "model": "openai/gpt-4o-mini"}), encoding="utf-8")
        (d / "broken_json.json").write_text("{not-json", encoding="utf-8")
        (d / "no_model.json").write_text(json.dumps({"name": "no_model"}), encoding="utf-8")
        (d / "mismatch.json").write_text(json.dumps({"name": "other", "model": "x"}), encoding="utf-8")
        reg2, probs2 = pc.load_provider_files(d)
        ok("④ 非法文件被跳过且不抛异常", list(reg2) == ["good"], json.dumps(sorted(reg2)))
        ok("④ 三类问题均有原因记录", len(probs2) == 3, json.dumps(probs2, ensure_ascii=False))

    # ⑤ 覆盖优先级（env 最高）
    env_backup = os.environ.get("PAPERQA_PROVIDERS_JSON")
    try:
        os.environ["PAPERQA_PROVIDERS_JSON"] = json.dumps({"dashscope": {"model": "openai/verify-override"}})
        cfg = pc.get_provider_config("dashscope")
        ok("⑤ env 覆盖文件值生效", cfg.get("model") == "openai/verify-override", str(cfg.get("model")))
        ok("⑤ 来源标记为 env", cfg.get("provider_source") == "env", str(cfg.get("provider_source")))
    finally:
        if env_backup is None:
            os.environ.pop("PAPERQA_PROVIDERS_JSON", None)
        else:
            os.environ["PAPERQA_PROVIDERS_JSON"] = env_backup
    ok("⑤ 还原后回到文件值", pc.get_provider_config("dashscope").get("model")
       == json.loads((pc.PROVIDERS_DIR / "dashscope.json").read_text(encoding="utf-8"))["model"],
       str(pc.get_provider_config("dashscope").get("model")))

    # ⑥ 列表接口同源数据 + 无密钥
    listed = pc.list_providers_safe()
    names = sorted(x["name"] for x in listed)
    ok("⑥ 列表含四个内置 provider", all(n in names for n in builtin), json.dumps(names, ensure_ascii=False))
    ok("⑥ 列表带 source/fetched_at/source_urls（未成功刷新者 fetched_at 可为 null）", all(
        x.get("source") and x.get("source_urls") for x in listed if x["name"] in builtin
    ) and all(
        (x.get("fetched_at") is not None)
        or (json.loads((pc.PROVIDERS_DIR / f"{x['name']}.json").read_text(encoding="utf-8")).get("meta") or {}).get("last_refresh_status") in ("error", "pending")
        for x in listed if x["name"] in builtin
    ), json.dumps([{k: v for k, v in x.items() if k in ("name", "source", "fetched_at")} for x in listed if x["name"] in builtin], ensure_ascii=False))
    ok("⑥ 列表不含密钥字段", all("api_key" not in x and "key_envs" not in x for x in listed),
       json.dumps(sorted({k for x in listed for k in x}), ensure_ascii=False))

    # ⑦ 边界：未知 provider
    try:
        pc.get_provider_config("no-such-provider")
        ok("⑦ 未知 provider 报错", False, "未抛异常")
    except ValueError as exc:
        ok("⑦ 未知 provider → ValueError 且列出可选值", "可选值" in str(exc) and "deepseek" in str(exc), str(exc)[:110])

    # ⑧ 调研可追溯契约（source_urls 必填；fetched_at 可为 null=从未成功刷新，须有 error/pending 状态解释）
    for name in builtin:
        meta = json.loads((pc.PROVIDERS_DIR / f"{name}.json").read_text(encoding="utf-8")).get("meta") or {}
        ok(f"⑧ {name} meta.source_urls 非空 + fetched_at 或失败状态齐备",
           bool(meta.get("source_urls"))
           and (bool(meta.get("fetched_at")) or meta.get("last_refresh_status") in ("error", "pending")),
           json.dumps(meta, ensure_ascii=False)[:120])

    # ⑧b SSOT 守护（code-review 050 major）：代码兜底表 PROVIDERS 与 providers/*.json 必须逐字段一致
    #     （providers/ 缺失/损坏时应用回落到兜底表；两者漂移 = 静默换模型/成本口径）
    fields = ("api_base", "model", "vision_model", "embedding", "embedding_local",
              "has_embedding_api", "key_envs", "thinking_disabled")
    for name in builtin:
        raw = json.loads((pc.PROVIDERS_DIR / f"{name}.json").read_text(encoding="utf-8"))
        # 两侧都先 normalize_entry（否则 key_envs 的 tuple/list 容器差异会假红）
        fb = pc.normalize_entry(name, pc.PROVIDERS[name])
        fl = pc.normalize_entry(name, raw)
        diff = {k: (fb.get(k), fl.get(k)) for k in fields if fb.get(k) != fl.get(k)}
        ok(f"⑧b {name} 代码兜底表与 providers/{name}.json 逐字段一致", not diff, json.dumps(diff, ensure_ascii=False))

    # ⑨~⑪ 刷新链路（离线快照，目录全部重定向到临时目录：绝不改动仓库文件）
    refresh_script = ROOT / "scripts" / "refresh-providers.py"
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        pdir = tdp / "providers"
        pdir.mkdir()
        for name in builtin:
            shutil.copy2(pc.PROVIDERS_DIR / f"{name}.json", pdir / f"{name}.json")
        runs_dir = tdp / "runs"
        state_dir = tdp / "state"
        snapshot = tdp / "snapshot.json"
        # dashscope/deepseek 快照有内容；openrouter 的 URL 故意缺失 → 模拟抓取失败
        snapshot.write_text(json.dumps({
            "https://help.aliyun.com/zh/model-studio/models": "模型列表 text-embedding-v1 text-embedding-v2 text-embedding-v3 text-embedding-v4 qwen3.5-omni-plus qwen3.8-max",
        }, ensure_ascii=False), encoding="utf-8")

        before = {n: (pdir / f"{n}.json").read_text(encoding="utf-8") for n in builtin}
        res = subprocess.run(
            [sys.executable, str(refresh_script), "--from-file", str(snapshot), "--apply",
             "--providers-dir", str(pdir), "--runs-dir", str(runs_dir), "--state-dir", str(state_dir)],
            cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
        )
        out = (res.stdout or "") + (res.stderr or "")
        ok("⑨ 离线刷新执行成功（退出 0）", res.returncode == 0, out.strip()[-160:])
        archives = sorted(runs_dir.glob("run-*-provider-refresh-*"))
        ok("⑨ 产出 M16 归档（report/context/reasoning/evidence 齐备）",
           bool(archives) and all((archives[-1] / f).exists() for f in
                                  ("tech-research.report.md", "context.md", "reasoning.md"))
           and bool(list((archives[-1] / "evidence").glob("*.md"))),
           str(archives[-1] if archives else "（无归档）"))
        ok("⑨ proposal 与 status 落盘", (state_dir / "provider_refresh_proposal.json").is_file()
           and (state_dir / "provider_refresh_status.json").is_file(),
           str(state_dir))
        ds_after = json.loads((pdir / "dashscope.json").read_text(encoding="utf-8"))
        ok("⑨ 成功 provider 的 meta.fetched_at 被刷新（含 last_evidence_run）",
           ds_after["meta"].get("last_evidence_run", "").startswith("run-")
           and ds_after["meta"].get("fetched_at") != json.loads(before["dashscope"])["meta"]["fetched_at"],
           json.dumps(ds_after["meta"], ensure_ascii=False)[:140])

        # ⑩ 抓取失败 → 文件逐字节未变（fail-closed）
        same = (pdir / "openai.json").read_text(encoding="utf-8") == before["openai"]
        st = json.loads((state_dir / "provider_refresh_status.json").read_text(encoding="utf-8"))
        ok("⑩ 抓取失败 provider 文件未被改动（fail-closed）", same, "byte-identical")
        ok("⑩ 失败状态被记录为 error", st["providers"]["openai"]["status"] == "error",
           json.dumps(st["providers"]["openai"], ensure_ascii=False)[:140])

        # ⑪ 到期判定可配置：已成功刷新者按 14 天为"未到期"；失败/从未刷新者恒 due（正确语义）
        due_run = subprocess.run([sys.executable, str(refresh_script), "--check", "--providers-dir", str(pdir)],
                                 cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        out11 = due_run.stdout or ""
        ds_line = next((ln for ln in out11.splitlines() if ln.strip().startswith("dashscope")), "")
        ok("⑪ 已成功刷新者按 14 天判定未到期", "due=False" in ds_line, ds_line.strip()[:120])
        oa_line = next((ln for ln in out11.splitlines() if ln.strip().startswith("openai")), "")
        ok("⑪ 从未成功刷新者（fetched_at=null）判为 due（应尽快重试）", "due=True" in oa_line, oa_line.strip()[:120])
        due_zero = subprocess.run([sys.executable, str(refresh_script), "--check", "--interval-days", "0", "--providers-dir", str(pdir)],
                                  cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        ok("⑪ 间隔改为 0 天即全判到期（退出 1，间隔可配置）", due_zero.returncode == 1,
           (due_zero.stdout or "").strip()[-140:])

    print(f"\nALL PASS ({PASSED} assertions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
