"""Scrape many Coursera data/analytics/AI courses from sitemap + pricing signals.

Output:
  outputs/semantic/coursera_courses_prices.csv
"""
from __future__ import annotations

from pathlib import Path
import os
import re
import time
from xml.etree import ElementTree as ET

import pandas as pd
import requests


BASE_DIR = Path(__file__).resolve().parents[1]
OUT_PATH = BASE_DIR / "outputs" / "semantic" / "coursera_courses_prices.csv"
SITEMAP_URL = "https://www.coursera.org/sitemap~www~courses.xml"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}

TOKENS = [
    "data", "analytics", "analysis", "analyst", "scientist", "science",
    "machine-learning", "deep-learning", "ai", "artificial-intelligence",
    "python", "sql", "statistics", "probability", "tableau", "power-bi",
    "nlp", "llm", "cloud", "spark", "big-data", "business-intelligence",
    "data-engineering", "data-visualization", "excel", "r-programming",
]


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


def fetch(url: str, timeout: int = 30) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        return r.text if r.status_code == 200 else ""
    except Exception:
        return ""


def extract_title(html: str) -> str:
    m = re.search(r"<title>(.*?)</title>", html, flags=re.I | re.S)
    if not m:
        return ""
    return re.sub(r"\s+", " ", m.group(1)).strip()


def extract_price_signals(html: str) -> tuple[str, float | None, str]:
    low = html.lower()
    if "free trial" in low:
        return ("Free trial", None, "trial")
    if "coursera plus" in low:
        return ("Included with Coursera Plus", None, "subscription_plus")

    m_month = re.search(r"([$€£]\s?\d+(?:[.,]\d{2})?)\s*(?:/|per)\s*month", html, flags=re.I)
    if m_month:
        txt = m_month.group(1).strip() + "/month"
        return (txt, parse_price_token(m_month.group(1)), "subscription_monthly")

    m_curr = re.search(r"([$€£]\s?\d+(?:[.,]\d{2})?)", html, flags=re.I)
    if m_curr:
        val = parse_price_token(m_curr.group(1))
        if val is not None and 5 <= val <= 50000:
            return (m_curr.group(1).strip(), val, "verified")

    if "subscribe" in low:
        return ("Subscription", None, "subscription")
    if "free" in low:
        return ("Free", 0.0, "free")
    return ("N/D", None, "unknown")


def load_sitemap_urls() -> list[str]:
    xml = fetch(SITEMAP_URL, timeout=45)
    if not xml:
        return []
    root = ET.fromstring(xml)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [n.text.strip() for n in root.findall(".//sm:url/sm:loc", ns) if n.text]
    return locs


def match_token(url: str) -> str:
    low = url.lower()
    for t in TOKENS:
        if t in low:
            return t
    return ""


def relevant_urls(all_urls: list[str], max_urls: int) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    seen = set()
    for u in all_urls:
        # keep core course-like routes
        if not any(x in u for x in ["/learn/", "/specializations/", "/professional-certificates/", "/projects/"]):
            continue
        tok = match_token(u)
        if not tok:
            continue
        if u in seen:
            continue
        seen.add(u)
        out.append((u, tok))
        if len(out) >= max_urls:
            break
    return out


def main() -> None:
    max_urls = int(os.getenv("COURSERA_MAX_URLS", "900") or "900")
    sleep_s = float(os.getenv("COURSERA_SLEEP_S", "0.2") or "0.2")
    save_every = int(os.getenv("COURSERA_SAVE_EVERY", "50") or "50")

    urls = load_sitemap_urls()
    picks = relevant_urls(urls, max_urls=max_urls)
    rows = []
    for i, (url, tok) in enumerate(picks, 1):
        html = fetch(url)
        if not html:
            continue
        title = extract_title(html)
        price_text, price_value, price_type = extract_price_signals(html)
        rows.append(
            {
                "keyword": tok.replace("-", " "),
                "course_url": url,
                "title": title,
                "price_text": price_text,
                "price_value": price_value,
                "price_type": price_type,
                "provider": "coursera",
            }
        )
        if i % 100 == 0:
            print(f"processed={i}/{len(picks)}")
        if i % save_every == 0 and rows:
            pd.DataFrame(rows).drop_duplicates(subset=["course_url"], keep="first").to_csv(OUT_PATH, index=False, encoding="utf-8")
            print(f"checkpoint_saved={i}")
        time.sleep(sleep_s)

    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(columns=["keyword", "course_url", "title", "price_text", "price_value", "price_type", "provider"])
    else:
        df = df.drop_duplicates(subset=["course_url"], keep="first")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False, encoding="utf-8")
    priced = int(df["price_text"].astype(str).ne("N/D").sum()) if not df.empty else 0
    print(f"saved={OUT_PATH}")
    print(f"rows={len(df)} priced_signal={priced} coverage={priced/max(1,len(df)):.2%}")


if __name__ == "__main__":
    main()
