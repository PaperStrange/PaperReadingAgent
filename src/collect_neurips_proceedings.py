#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# src/collect_neurips_proceedings.py

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


BASE = "https://proceedings.neurips.cc"


def safe_str(x: Any) -> str:
    if x is None:
        return ""
    try:
        return str(x)
    except Exception:
        return ""


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def fetch_html(url: str, timeout: int = 30) -> str:
    r = requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; PaperReadingBot/1.0; +https://example.com)"
        },
    )
    r.raise_for_status()
    return r.text


def parse_listing(year: int, html: str) -> List[Tuple[str, str, str]]:
    """
    返回 (paper_page_url, title, track_guess)
    track_guess: "main" or "datasets_and_benchmarks" (best-effort)
    """
    soup = BeautifulSoup(html, "html.parser")

    # 页面结构：通常是很多 <a href="/paper_files/paper/2023/hash/...-Abstract-Conference.html">Title</a>
    links = soup.select('a[href*="/paper_files/paper/"]')
    out = []
    for a in links:
        href = a.get("href") or ""
        text = norm_ws(a.get_text(" ", strip=True) or "")
        if not href or not text:
            continue

        # 只要 abstract 页面（最稳）
        if "Abstract" not in href:
            continue

        full = urljoin(BASE, href)

        # track：listing 页面顶部可能有筛选，单条 paper 页也可能标注
        # 这里先置 unknown，后面在 paper page 再解析
        out.append((full, text, "unknown"))
    # 去重
    seen = set()
    dedup = []
    for u, t, tr in out:
        if u in seen:
            continue
        seen.add(u)
        dedup.append((u, t, tr))
    return dedup


def parse_paper_page(paper_url: str, html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")

    # 标题通常在 <h4> 或 <h2> 等位置；以最大概率抓到为主
    title = ""
    for sel in ["h4", "h2", "h3", "title"]:
        el = soup.select_one(sel)
        if el:
            t = norm_ws(el.get_text(" ", strip=True))
            if t and "Advances in Neural Information Processing Systems" not in t:
                title = t
                break

    # 作者：常见在 <i> 或某个 <p> 中
    authors = []
    # 1) 先找包含逗号分隔作者的块
    cand_texts = []
    for el in soup.find_all(["i", "p", "h5"]):
        tx = norm_ws(el.get_text(" ", strip=True))
        if tx and "," in tx and len(tx) < 400:
            cand_texts.append(tx)
    # heuristic：取最像作者的一条（通常第一个 i）
    if cand_texts:
        raw = cand_texts[0]
        # authors 多为 "A, B, C"
        authors = [norm_ws(x) for x in raw.split(",") if norm_ws(x)]

    # PDF 链接：页面里一般有 “Paper” 链接，指向 ...-Paper-Conference.pdf
    pdf_url = ""
    for a in soup.select('a[href$=".pdf"]'):
        href = a.get("href") or ""
        if "Paper" in href or href.endswith(".pdf"):
            pdf_url = urljoin(BASE, href)
            break

    # track：页面上可能出现 “All Main Conference Track Datasets and Benchmarks Track”
    # 或者 paper 所属 track 在某个导航/面包屑中。这里 best-effort：
    page_text = soup.get_text(" ", strip=True)
    track = "main"
    if re.search(r"Datasets\s+and\s+Benchmarks\s+Track", page_text, flags=re.I):
        track = "datasets_and_benchmarks"

    return {
        "title": title,
        "authors": authors,
        "pdf_url": pdf_url,
        "track": track,
    }


def collect_year(year: int, debug: bool = False) -> List[Dict[str, Any]]:
    list_url = f"{BASE}/paper_files/paper/{year}"
    listing_html = fetch_html(list_url)
    items = parse_listing(year, listing_html)

    if debug:
        print(f"[NeurIPS {year}] listing={list_url} papers_in_listing={len(items)}")

    recs: List[Dict[str, Any]] = []

    for paper_url, title_guess, _ in tqdm(items, desc=f"NeurIPS {year}", leave=False):
        try:
            html = fetch_html(paper_url)
            meta = parse_paper_page(paper_url, html)

            title = meta["title"] or title_guess
            authors = meta["authors"] or []
            pdf_url = meta["pdf_url"] or ""

            # fallback：有些页面可能没给 pdf link，但规律一般是把 Abstract 换成 Paper
            if not pdf_url and "Abstract" in paper_url:
                pdf_url = paper_url.replace("Abstract", "Paper").replace(".html", ".pdf")

            track = meta.get("track") or "main"

            recs.append(
                {
                    "paper_id": f"neurips:{year}:{paper_url.rsplit('/', 1)[-1]}",
                    "venue": "NeurIPS",
                    "track": track,
                    "year": year,
                    "title": title,
                    "authors": authors,
                    "keywords": [],
                    "abstract": "",  # proceedings 列表页不总有 abstract；后续需要再抓或下 PDF 解析
                    "pdf_url": pdf_url,
                    "source_url": paper_url,
                    "intro_text": "",
                }
            )
        except Exception as e:
            if debug:
                print(f"[NeurIPS {year}] FAIL {paper_url}: {repr(e)}")
            continue

    return recs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out_path", type=str, required=True)
    ap.add_argument("--years", type=int, nargs="+", default=[2023, 2024, 2025])
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    out = Path(args.out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    all_recs: List[Dict[str, Any]] = []
    for y in args.years:
        all_recs.extend(collect_year(y, debug=args.debug))

    with out.open("w", encoding="utf-8") as f:
        for r in all_recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Wrote {len(all_recs)} NeurIPS records -> {out}")


if __name__ == "__main__":
    main()
