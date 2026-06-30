from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json
import os
import re
import time

import pandas as pd
from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright


BASE_DIR = Path(__file__).resolve().parents[1]
COURSES_PATH = BASE_DIR / "outputs" / "semantic" / "courses_features.csv"
SCRAPED_PATH = BASE_DIR / "outputs" / "semantic" / "course_prices_scraped.csv"

EURO = "\u20AC"
POUND = "\u00A3"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    t = re.sub(r"[^\d,.-]", "", t)
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


def is_valid_price_value(v: float | None) -> bool:
    return v is not None and 5 <= float(v) <= 50000


def normalize_candidate_price(text: str) -> tuple[str, float] | None:
    txt = str(text or "").strip()
    if not txt:
        return None
    val = parse_price_token(txt)
    if not is_valid_price_value(val):
        return None
    return txt, float(val)


def looks_blocked(title: str, html_text: str) -> bool:
    low = (title + "\n" + html_text).lower()
    markers = ["just a moment", "un momento", "cf-challenge", "attention required", "captcha"]
    return any(m in low for m in markers)


def click_cookie_buttons(page) -> None:
    for txt in ["Aceptar", "Accept", "Aceptar todo", "Allow all", "Rechazar todas", "Reject all"]:
        try:
            btn = page.get_by_role("button", name=txt)
            if btn.count() > 0:
                btn.first.click(timeout=1200)
                page.wait_for_timeout(600)
                return
        except Exception:
            continue


def extract_from_dom(page) -> tuple[str, str, float]:
    # 0) Exact Udemy selectors from buy-box.
    exact_selectors = [
        '[data-purpose="course-price-text"]',
        '[data-purpose="price-text-container"] [data-purpose="course-price-text"]',
        '.buy-box-module-scss-module__Au7YHG__discount-price',
    ]
    price_re_exact = re.compile(r'([€$£]\s?\d+(?:[.,]\d{2})?)')
    for sel in exact_selectors:
        try:
            loc = page.locator(sel)
            n = min(loc.count(), 4)
            for i in range(n):
                txt = (loc.nth(i).inner_text(timeout=600) or "").strip()
                if not txt:
                    continue
                m = price_re_exact.search(txt)
                if not m:
                    continue
                cand = normalize_candidate_price(m.group(1))
                if cand:
                    return cand[0], "dom_udemy_price_text", 0.98
        except Exception:
            continue

    # 1) High-confidence candidate from common CTA/price containers.
    selectors = [
        "[data-purpose*='buy']",
        "[data-purpose*='price']",
        "[class*='price']",
        "[class*='sidebar']",
        "[class*='purchase']",
        "button",
        "aside",
    ]
    symbol_class = rf"[{re.escape('$' + EURO + POUND)}]"
    price_re = re.compile(rf"({symbol_class}\s?\d+(?:[.,]\d{{2}})?)")

    for sel in selectors:
        try:
            loc = page.locator(sel)
            n = min(loc.count(), 20)
            for i in range(n):
                try:
                    t = (loc.nth(i).inner_text(timeout=500) or "").strip()
                except Exception:
                    continue
                if not t:
                    continue
                m = price_re.search(t)
                if not m:
                    continue
                cand = normalize_candidate_price(m.group(1))
                if cand:
                    return cand[0], "dom_selector", 0.92
        except Exception:
            continue

    # 2) Visible page text scan (medium confidence).
    try:
        body_text = page.inner_text("body", timeout=1500)
        m = price_re.search(body_text or "")
        if m:
            cand = normalize_candidate_price(m.group(1))
            if cand:
                return cand[0], "dom_body", 0.80
    except Exception:
        pass

    return "N/D", "none", 0.0


def extract_from_html(html_text: str) -> tuple[str, str, float]:
    # JSON-LD (can be 0.00 for subscription; reject by validator)
    for m in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html_text, flags=re.I | re.S):
        raw = m.group(1).strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        offers = obj.get("offers")
        if not (isinstance(offers, list) and offers):
            continue
        offer = offers[0] if isinstance(offers[0], dict) else {}
        price = offer.get("price")
        currency = str(offer.get("priceCurrency") or "").strip()
        if price is None:
            continue
        try:
            pval = float(price)
        except Exception:
            continue
        if not is_valid_price_value(pval):
            continue
        txt = f"{pval:.2f} {currency}".strip()
        return txt, "jsonld", 0.65

    # HTML token fallback
    symbol_class = rf"[{re.escape('$' + EURO + POUND)}]"
    pats = [
        r'"discount_price"\s*:\s*"([^"]+)"',
        r'"price_string"\s*:\s*"([^"]+)"',
        r'"list_price"\s*:\s*"([^"]+)"',
        rf">\s*({symbol_class}\s?\d+(?:[.,]\d{{2}})?)\s*</span>",
        rf">\s*({symbol_class}\s?\d+(?:[.,]\d{{2}})?)\s*</div>",
        rf"({symbol_class}\s?\d+(?:[.,]\d{{2}})?)",
    ]
    for pat in pats:
        m = re.search(pat, html_text, flags=re.I)
        if not m:
            continue
        cand = normalize_candidate_price(m.group(1))
        if cand:
            return cand[0], "html", 0.55

    return "N/D", "none", 0.0


def save_progress(records: list[dict]) -> None:
    if not records:
        return
    df = pd.DataFrame(records)
    # Prefer higher confidence and valid numeric price.
    df["_valid"] = df["price_value_eur"].notna().astype(int)
    df = df.sort_values(["course_id", "_valid", "price_confidence", "price_value_eur"], ascending=[True, False, False, False])
    df = df.drop_duplicates(subset=["course_id"], keep="first").drop(columns=["_valid"])
    SCRAPED_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SCRAPED_PATH, index=False, encoding="utf-8")


def main() -> None:
    max_rows = int(os.getenv("MAX_ROWS", "0") or "0")
    start_index = int(os.getenv("START_INDEX", "0") or "0")
    save_every = int(os.getenv("SAVE_EVERY", "25") or "25")
    headless = bool(int(os.getenv("HEADLESS", "0") or "0"))
    force_rescrape = bool(int(os.getenv("FORCE_RESCRAPE", "0") or "0"))
    challenge_wait_ms = int(os.getenv("CHALLENGE_WAIT_MS", "9000") or "9000")
    cf_max_wait_ms = int(os.getenv("CF_MAX_WAIT_MS", "180000") or "180000")

    user_data_dir = Path(
        os.getenv(
            "CHROME_USER_DATA_DIR",
            None,
        )
    )
    profile_dir = os.getenv("CHROME_PROFILE_DIR", "Default")

    courses = pd.read_csv(COURSES_PATH)
    rows = courses[["course_id", "url"]].drop_duplicates().copy()
    rows["url_norm"] = rows["url"].map(normalize_course_url)
    rows = rows[rows["url_norm"] != ""].reset_index(drop=True)
    if start_index > 0:
        rows = rows.iloc[start_index:].reset_index(drop=True)
    if max_rows > 0:
        rows = rows.head(max_rows).copy()

    records: list[dict] = []
    done_ids = set()
    if SCRAPED_PATH.exists() and not force_rescrape:
        old = pd.read_csv(SCRAPED_PATH)
        records = old.to_dict("records")
        done_ids = set(old["course_id"].tolist())
        print(f"resume_loaded={len(done_ids)}")

    total = len(rows)
    started = time.time()

    with sync_playwright() as p:
        # Persistent context keeps cookies/session and helps with anti-bot checks.
        # If the Chrome profile is locked, fallback to an ephemeral context.
        browser = None
        using_persistent = True
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                channel="chrome",
                headless=headless,
                ignore_https_errors=True,
                args=[f"--profile-directory={profile_dir}", "--disable-blink-features=AutomationControlled"],
                viewport={"width": 1400, "height": 1100},
            )
            print("context_mode=persistent")
        except Exception as e:
            using_persistent = False
            print(f"context_mode=fallback reason={type(e).__name__}")
            browser = p.chromium.launch(channel="chrome", headless=headless)
            context = browser.new_context(ignore_https_errors=True, viewport={"width": 1400, "height": 1100})

        for idx, row in rows.iterrows():
            cid = row["course_id"]
            if cid in done_ids:
                continue

            page = context.new_page()
            url = row["url_norm"]
            status = 0
            blocked = False
            price_text = "N/D"
            price_source = "none"
            price_conf = 0.0

            try:
                resp = page.goto(url, wait_until="domcontentloaded", timeout=120000)
                status = resp.status if resp else 0
                click_cookie_buttons(page)
                page.wait_for_timeout(1400)

                title = page.title() or ""
                html = page.content()
                if looks_blocked(title, html):
                    waited = 0
                    while waited < cf_max_wait_ms and looks_blocked(title, html):
                        page.wait_for_timeout(challenge_wait_ms)
                        waited += challenge_wait_ms
                        title = page.title() or ""
                        html = page.content()
                    if waited > 0:
                        print(f"cf_wait_ms={waited} course_id={cid}")

                if looks_blocked(title, html):
                    blocked = True
                else:
                    price_text, price_source, price_conf = extract_from_dom(page)
                    if price_text == "N/D":
                        price_text, price_source, price_conf = extract_from_html(html)
            except PWTimeout:
                status = -1
            except Exception:
                status = -1
            finally:
                try:
                    page.close()
                except Exception:
                    pass

            parsed = parse_price_token(price_text)
            valid = is_valid_price_value(parsed)
            rec = {
                "course_id": cid,
                "url": row["url"],
                "url_normalized": url,
                "price_text": price_text if valid else "N/D",
                "price_value_eur": (float(parsed) if valid else None),
                "http_status": int(status),
                "blocked_cf": bool(blocked),
                "price_source": (price_source if valid else "none"),
                "price_confidence": (float(price_conf) if valid else 0.0),
                "price_ts": now_iso(),
            }
            records.append(rec)
            done_ids.add(cid)

            if len(done_ids) % save_every == 0:
                save_progress(records)
                print(f"processed={len(done_ids)}/{total} idx={idx+1} elapsed_s={time.time()-started:.1f}")

        context.close()
        if browser is not None:
            browser.close()

    save_progress(records)

    scraped = pd.read_csv(SCRAPED_PATH)
    priced = int((scraped["price_text"].astype(str) != "N/D").sum())
    print(f"scraped_rows={len(scraped)} priced={priced} coverage={priced/max(1,len(scraped)):.2%}")

    # Merge to courses_features with canonical columns.
    merge_cols = scraped[["course_id", "price_text", "price_source", "price_ts", "price_confidence"]].rename(
        columns={
            "price_text": "PRIC",
            "price_source": "PRIC_SOURCE",
            "price_ts": "PRIC_TS",
            "price_confidence": "PRIC_CONFIDENCE",
        }
    )

    out = courses.drop(columns=[c for c in ["pric"] if c in courses.columns], errors="ignore")
    out = out.merge(merge_cols, on="course_id", how="left", suffixes=("", "_new"))

    # Coalesce existing and newly scraped columns robustly.
    if "PRIC_new" in out.columns:
        base_pric = out["PRIC"] if "PRIC" in out.columns else pd.Series([""] * len(out))
        out["PRIC"] = out["PRIC_new"].fillna(base_pric)
        out = out.drop(columns=["PRIC_new"])
    if "PRIC_SOURCE_new" in out.columns:
        base_src = out["PRIC_SOURCE"] if "PRIC_SOURCE" in out.columns else pd.Series([""] * len(out))
        out["PRIC_SOURCE"] = out["PRIC_SOURCE_new"].fillna(base_src)
        out = out.drop(columns=["PRIC_SOURCE_new"])
    if "PRIC_TS_new" in out.columns:
        base_ts = out["PRIC_TS"] if "PRIC_TS" in out.columns else pd.Series([""] * len(out))
        out["PRIC_TS"] = out["PRIC_TS_new"].fillna(base_ts)
        out = out.drop(columns=["PRIC_TS_new"])
    if "PRIC_CONFIDENCE_new" in out.columns:
        base_cf = out["PRIC_CONFIDENCE"] if "PRIC_CONFIDENCE" in out.columns else pd.Series([0.0] * len(out))
        out["PRIC_CONFIDENCE"] = out["PRIC_CONFIDENCE_new"].fillna(base_cf)
        out = out.drop(columns=["PRIC_CONFIDENCE_new"])

    if "PRIC" not in out.columns:
        out["PRIC"] = "N/D"
    if "PRIC_SOURCE" not in out.columns:
        out["PRIC_SOURCE"] = "none"
    if "PRIC_TS" not in out.columns:
        out["PRIC_TS"] = ""
    if "PRIC_CONFIDENCE" not in out.columns:
        out["PRIC_CONFIDENCE"] = 0.0

    out["PRIC"] = out["PRIC"].fillna("N/D")
    out["PRIC_SOURCE"] = out["PRIC_SOURCE"].fillna("none")
    out["PRIC_TS"] = out["PRIC_TS"].fillna("")
    out["PRIC_CONFIDENCE"] = pd.to_numeric(out["PRIC_CONFIDENCE"], errors="coerce").fillna(0.0)
    out.to_csv(COURSES_PATH, index=False, encoding="utf-8")
    print(f"updated_courses={COURSES_PATH} with PRIC metadata")


if __name__ == "__main__":
    main()
