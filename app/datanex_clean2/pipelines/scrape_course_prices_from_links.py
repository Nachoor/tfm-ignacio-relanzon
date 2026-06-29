"""Scrape course prices from course URLs and persist a reusable price cache.

Usage:
  python pipelines/scrape_course_prices_from_links.py
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import os
import re
import time

import pandas as pd
import requests

try:
    import cloudscraper  # type: ignore
except Exception:
    cloudscraper = None


BASE_DIR = Path(__file__).resolve().parents[1]
COURSES_PATH = BASE_DIR / "outputs" / "semantic" / "courses_features.csv"
OUT_PATH = BASE_DIR / "outputs" / "semantic" / "course_prices_scraped.csv"


def normalize_course_url(url: str) -> str:
    u = str(url or "").strip()
    if not u:
        return ""
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("/"):
        return "https://www.udemy.com" + u
    if not u.startswith("http"):
        return "https://www.udemy.com/" + u.lstrip("/")
    return u


def parse_price_token(token: str) -> float | None:
    t = str(token or "").strip()
    if not t:
        return None
    t = re.sub(r"[^\d,.\-]", "", t)
    if not t:
        return None
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", t):
        return float(re.sub(r"[.,]", "", t))
    if "," in t and "." in t:
        if t.rfind(".") > t.rfind(","):
            return float(t.replace(",", ""))
        return float(t.replace(".", "").replace(",", "."))
    if re.fullmatch(r"\d+[.,]\d{1,2}", t):
        return float(t.replace(",", "."))
    if re.fullmatch(r"\d+", t):
        return float(t)
    return None


def extract_price(html_text: str) -> str:
    def normalize_candidate(val: str) -> str:
        txt = str(val or "").strip()
        if not txt:
            return "N/D"
        n = parse_price_token(txt)
        if n is not None and (n < 5 or n > 50000):
            return "N/D"
        return txt

    patterns = [
        r'"discount_price"\s*:\s*"([^"]+)"',
        r'"price_string"\s*:\s*"([^"]+)"',
        r'"list_price"\s*:\s*"([^"]+)"',
        r'"price"\s*:\s*"([^"]+)"',
        r'product:price:amount"\s+content="([^"]+)"',
        r">\s*([€$£]\s?\d+(?:[.,]\d{2})?)\s*</span>",
        r">\s*([€$£]\s?\d+(?:[.,]\d{2})?)\s*</div>",
        r"([€$£]\s?\d+(?:[.,]\d{2})?)",
    ]
    for pat in patterns:
        m = re.search(pat, html_text, flags=re.IGNORECASE)
        if m:
            candidate = normalize_candidate(m.group(1))
            if candidate != "N/D":
                return candidate
    return "N/D"


def scrape_one(row: pd.Series, timeout: int = 25) -> dict:
    course_id = row.get("course_id")
    raw_url = row.get("url", "")
    url = normalize_course_url(raw_url)
    if not url:
        return {"course_id": course_id, "url": raw_url, "url_normalized": "", "price_text": "N/D", "price_value_eur": None, "http_status": 0}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    cookie_header = os.getenv("UDEMY_COOKIE", "").strip()
    if cookie_header:
        headers["Cookie"] = cookie_header
    try:
        if cloudscraper is not None:
            scraper = cloudscraper.create_scraper(browser={"browser": "chrome", "platform": "windows", "desktop": True})
            resp = scraper.get(url, headers=headers, timeout=timeout)
        else:
            resp = requests.get(url, headers=headers, timeout=timeout)
        body = resp.text or ""
        blocked = "Just a moment" in body or "cf-challenge" in body.lower() or "Attention Required" in body
        price_text = extract_price(body) if (resp.status_code == 200 and not blocked) else "N/D"
        return {
            "course_id": course_id,
            "url": raw_url,
            "url_normalized": url,
            "price_text": price_text,
            "price_value_eur": parse_price_token(price_text),
            "http_status": int(resp.status_code),
            "blocked_cf": bool(blocked),
        }
    except Exception:
        return {
            "course_id": course_id,
            "url": raw_url,
            "url_normalized": url,
            "price_text": "N/D",
            "price_value_eur": None,
            "http_status": -1,
            "blocked_cf": False,
        }


def main():
    df = pd.read_csv(COURSES_PATH)
    rows = df[["course_id", "url"]].drop_duplicates().reset_index(drop=True)
    max_rows = int(os.getenv("MAX_ROWS", "0") or "0")
    if max_rows > 0:
        rows = rows.head(max_rows).copy()
    out = []
    start = time.time()
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(scrape_one, row): idx for idx, row in rows.iterrows()}
        for i, fut in enumerate(as_completed(futures), 1):
            out.append(fut.result())
            if i % 100 == 0:
                print(f"processed={i}/{len(rows)}")
    out_df = pd.DataFrame(out)
    out_df = out_df.sort_values(["course_id", "price_value_eur"], ascending=[True, False]).drop_duplicates(subset=["course_id"], keep="first")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(OUT_PATH, index=False, encoding="utf-8")
    ok = int((out_df["price_text"] != "N/D").sum())
    print(f"saved={OUT_PATH}")
    print(f"rows={len(out_df)} priced={ok} coverage={ok/len(out_df):.2%} elapsed_s={time.time()-start:.1f}")


if __name__ == "__main__":
    main()
