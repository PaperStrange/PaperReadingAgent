#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# src/collect_iclr_openreview.py

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import openreview
from tqdm import tqdm


def safe_str(x: Any) -> str:
    if x is None:
        return ""
    try:
        return str(x)
    except Exception:
        return ""


def normalize_keywords(x: Any) -> List[str]:
    if x is None:
        return []
    if isinstance(x, str):
        s = x.strip()
        return [s] if s else []
    if isinstance(x, list):
        out = []
        for it in x:
            s = safe_str(it).strip()
            if s:
                out.append(s)
        return out
    return []


def note_to_record(year: int, note: Any) -> Dict[str, Any]:
    c = getattr(note, "content", {}) or {}
    title = safe_str(c.get("title") or c.get("paper_title") or "").strip()
    abstract = safe_str(c.get("abstract") or "").strip()

    keywords = normalize_keywords(
        c.get("keywords") or c.get("keyword") or c.get("KeyWords") or c.get("areas") or c.get("subject_areas")
    )

    authors = c.get("authors")
    if not isinstance(authors, list):
        authors = []
    authors = [safe_str(a).strip() for a in authors if safe_str(a).strip()]

    pdf_url = f"https://openreview.net/pdf?id={note.id}"
    source_url = f"https://openreview.net/forum?id={note.id}"

    return {
        "paper_id": f"iclr:{year}:{note.id}",
        "venue": "ICLR",
        "track": "main",
        "year": year,
        "title": title,
        "authors": authors,
        "keywords": keywords,
        "abstract": abstract,
        "pdf_url": pdf_url,
        "source_url": source_url,
        "intro_text": "",
    }


def invitation_candidates(year: int) -> List[str]:
    """
    ICLR 常见 submission invitation 命名（跨年份/阶段有差异）。
    这里列多一些，逐个尝试，哪个能拉到 notes 就用哪个。
    """
    return [
        f"ICLR.cc/{year}/Conference/-/Blind_Submission",
        f"ICLR.cc/{year}/Conference/-/Submission",
        f"ICLR.cc/{year}/Conference/-/Paper",
        f"ICLR.cc/{year}/Conference/-/Manuscript",
        f"ICLR.cc/{year}/Conference/Track/-/Blind_Submission",
        f"ICLR.cc/{year}/Conference/Track/-/Submission",
        f"ICLR.cc/{year}/Conference/Track/-/Paper",
    ]


def fetch_notes(client: Any, invitation: str) -> List[Any]:
    """
    兼容 v2 / v1 client：
    - v2: openreview.api.OpenReviewClient, 用 get_all_notes(invitation=...)
    - v1: openreview.Client, 用 get_all_notes(invitation=...)
    """
    return client.get_all_notes(invitation=invitation)


def try_collect_with_client(client: Any, year: int, debug: bool) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    for inv in invitation_candidates(year):
        try:
            notes = fetch_notes(client, inv)
            if notes:
                if debug:
                    print(f"[ICLR {year}] SUCCESS invitation={inv} notes={len(notes)}")
                return [note_to_record(year, n) for n in notes], inv
            else:
                if debug:
                    print(f"[ICLR {year}] invitation={inv} -> 0 notes")
        except Exception as e:
            if debug:
                print(f"[ICLR {year}] invitation={inv} FAILED: {repr(e)}")
            continue
    return None, None


def collect_year(year: int, debug: bool, baseurl_v2: str, baseurl_v1: str) -> Tuple[List[Dict[str, Any]], str]:
    # 先试 v2
    client_v2 = openreview.api.OpenReviewClient(baseurl=baseurl_v2)
    recs, inv = try_collect_with_client(client_v2, year, debug=debug)
    if recs is not None:
        return recs, inv  # type: ignore

    # 再试 v1（很多时候更稳）
    client_v1 = openreview.Client(baseurl=baseurl_v1)
    recs, inv = try_collect_with_client(client_v1, year, debug=debug)
    if recs is not None:
        return recs, inv  # type: ignore

    raise RuntimeError(
        f"Cannot find workable submission invitation for ICLR {year} using both v2 and v1 APIs.\n"
        f"Tried invitations:\n  " + "\n  ".join(invitation_candidates(year))
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out_path", type=str, required=True)
    ap.add_argument("--years", type=int, nargs="+", default=[2023, 2024, 2025])
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--baseurl_v2", type=str, default="https://api2.openreview.net")
    ap.add_argument("--baseurl_v1", type=str, default="https://api.openreview.net")
    args = ap.parse_args()

    out = Path(args.out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    all_recs: List[Dict[str, Any]] = []
    used: Dict[int, str] = {}

    for y in args.years:
        recs, inv = collect_year(y, debug=args.debug, baseurl_v2=args.baseurl_v2, baseurl_v1=args.baseurl_v1)
        used[y] = inv
        all_recs.extend(recs)

    with out.open("w", encoding="utf-8") as f:
        for r in all_recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Wrote {len(all_recs)} ICLR records -> {out}")
    for y in sorted(used):
        print(f"  ICLR {y}: {used[y]}")


if __name__ == "__main__":
    main()
