#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# src/collect_acl.py

import json
import re
import argparse
from pathlib import Path
from typing import Iterable, Any, Dict, List, Optional

from tqdm import tqdm
from acl_anthology import Anthology


TARGET_COLLECTIONS = {"acl", "emnlp", "naacl"}
DEFAULT_YEARS = [2023, 2024, 2025]


def load_anthology(datadir: Path) -> Anthology:
    datadir = datadir.expanduser().resolve()
    if (datadir / "data" / "xml" / "schema.rnc").exists() and not (datadir / "xml" / "schema.rnc").exists():
        datadir = datadir / "data"
    schema = datadir / "xml" / "schema.rnc"
    if not schema.exists():
        raise FileNotFoundError(
            f"[acl-anthology] Cannot find schema.rnc. Tried: {schema}\n"
            f"Hint: pass --datadir <...>/acl-anthology/data (not repo root)."
        )
    return Anthology(datadir=str(datadir))


def iter_papers_compat(anthology: Anthology) -> Iterable[Any]:
    papers_attr = getattr(anthology, "papers", None)
    if isinstance(papers_attr, dict):
        return papers_attr.values()
    if callable(papers_attr):
        res = papers_attr()
        if isinstance(res, dict):
            return res.values()
        return res
    for name in ("get_papers", "iter_papers", "papers_iter"):
        fn = getattr(anthology, name, None)
        if callable(fn):
            res = fn()
            if isinstance(res, dict):
                return res.values()
            return res
    raise TypeError("Cannot iterate papers: unknown acl-anthology API (papers/papers()).")


def safe_str(x: Any) -> str:
    if x is None:
        return ""
    try:
        return str(x)
    except Exception:
        return ""


def paper_full_id(paper: Any) -> str:
    return safe_str(getattr(paper, "full_id", "")).strip()


def parse_full_id(full_id: str):
    m = re.match(r"^(?P<year>\d{4})\.(?P<rest>.+)$", full_id)
    if not m:
        return None, None, None
    year = int(m.group("year"))
    rest = m.group("rest")

    coll = re.split(r"[-.]", rest, maxsplit=1)[0].lower() if rest else ""

    track = "unknown"
    m2 = re.match(r"^(?P<coll>[a-z]+)-(?P<trk>[a-z]+)\.", rest)
    if m2:
        track = m2.group("trk").lower()
    else:
        m3 = re.match(r"^(?P<coll>[a-z]+)-(?P<trk>[a-z]+)-", rest)
        if m3:
            track = m3.group("trk").lower()

    return year, coll, track


def get_author_names(paper: Any) -> List[str]:
    out: List[str] = []
    authors_obj = getattr(paper, "authors", None) or []
    for a in authors_obj:
        # already string
        if isinstance(a, str):
            s = a.strip()
            if s:
                out.append(s)
            continue

        # Name-like object
        first = safe_str(getattr(a, "first", "")).strip()
        last = safe_str(getattr(a, "last", "")).strip()
        if first or last:
            out.append((first + " " + last).strip())
            continue

        # fallback to .name or str(a)
        name = safe_str(getattr(a, "name", "")).strip()
        if name:
            out.append(name)
        else:
            s = safe_str(a).strip()
            if s:
                out.append(s)
    return out


def normalize_pdf_url(fid: str, pdf_field: Any) -> str:
    """
    你这个包版本的 paper.pdf 可能是 PDFReference(...) 对象，不是 URL 字符串。
    最稳：直接用 ACL Anthology 的 canonical pdf URL。
    """
    s = safe_str(pdf_field).strip()
    if s.startswith("http://") or s.startswith("https://"):
        return s
    return f"https://aclanthology.org/{fid}.pdf"


def extract_abstract_from_bibtex(bib: str) -> str:
    m = re.search(r"\babstract\s*=\s*\{(.*?)\}\s*,\s*(?:\n|$)", bib, flags=re.S | re.I)
    return m.group(1).strip() if m else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out_path", type=str, required=True)
    ap.add_argument("--years", type=int, nargs="+", default=DEFAULT_YEARS)
    ap.add_argument("--datadir", type=str, required=True)
    args = ap.parse_args()

    out = Path(args.out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    anthology = load_anthology(Path(args.datadir))
    paper_iter = iter_papers_compat(anthology)

    years_set = set(args.years)
    papers: List[Dict[str, Any]] = []

    for paper in tqdm(paper_iter, desc="scan anthology"):
        fid = paper_full_id(paper)
        if not fid:
            continue

        year, coll, track = parse_full_id(fid)
        if year is None or coll is None:
            continue
        if year not in years_set:
            continue
        if coll not in TARGET_COLLECTIONS:
            continue

        title = safe_str(getattr(paper, "title", "")).strip()
        authors = get_author_names(paper)

        abstract = safe_str(getattr(paper, "abstract", "")).strip()
        if not abstract:
            try:
                bib = paper.to_bibtex(with_abstract=True)
                abstract = extract_abstract_from_bibtex(safe_str(bib)) or ""
            except Exception:
                pass

        pdf_url = normalize_pdf_url(fid, getattr(paper, "pdf", ""))

        papers.append(
            {
                "paper_id": f"acl:{fid}",
                "venue": coll.upper(),   # ACL / EMNLP / NAACL
                "track": track,
                "year": year,
                "title": title,
                "authors": authors,
                "keywords": [],
                "abstract": abstract,
                "pdf_url": pdf_url,
                "source_url": f"https://aclanthology.org/{fid}/",
                "intro_text": "",
            }
        )

    with out.open("w", encoding="utf-8") as f:
        for r in papers:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Wrote {len(papers)} ACL-family records -> {out}")


if __name__ == "__main__":
    main()
