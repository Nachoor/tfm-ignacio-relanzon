""None""
from __future__ import annotations

from pathlib import Path
import os
import re

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
SEM_DIR = BASE_DIR / "outputs" / "semantic"
COURSES_PATH = SEM_DIR / "courses_features.csv"
OUT_PATH = SEM_DIR / "course_prices_from_uipath.csv"
UIPATH_OUT_DIR = Path(
    os.getenv(
        "UIPATH_OUT_DIR",
        None,
    )
)


def parse_price_token(token) -> float | None:
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


def normalize_udemy_path(url: str) -> str:
    u = str(url or "").strip()
    if not u:
        return ""
    u = u.replace("https://www.udemy.com", "").replace("http://www.udemy.com", "")
    if not u.startswith("/"):
        u = "/" + u
    return u.rstrip("/") + "/"


def main() -> None:
    if not UIPATH_OUT_DIR.exists():
        raise FileNotFoundError(f"UiPath output folder not found: {UIPATH_OUT_DIR}")

    files = sorted(UIPATH_OUT_DIR.glob("*.txt"))
    if not files:
        raise FileNotFoundError(f"No .txt files found in {UIPATH_OUT_DIR}")

    chunks = []
    for fp in files:
        try:
            df = pd.read_csv(fp)
        except Exception:
            continue
        if "Url" not in df.columns or "Price" not in df.columns:
            continue
        df = df.copy()
        df["src_file"] = fp.name
        chunks.append(df)

    if not chunks:
        raise RuntimeError("No readable UiPath output with Url/Price columns.")

    raw = pd.concat(chunks, ignore_index=True)
    raw["url_norm"] = raw["Url"].map(normalize_udemy_path)
    raw["price_value"] = raw["Price"].map(parse_price_token)
    raw = raw[(raw["price_value"].notna()) & (raw["price_value"] >= 5) & (raw["price_value"] <= 50000)].copy()

    courses = pd.read_csv(COURSES_PATH)[["course_id", "url"]].drop_duplicates()
    courses["url_norm"] = courses["url"].map(normalize_udemy_path)

    merged = raw.merge(courses[["course_id", "url_norm"]], on="url_norm", how="inner")
    if merged.empty:
        print("No matches against courses_features URLs.")
        out = pd.DataFrame(columns=["course_id", "PRIC", "PRIC_SOURCE", "PRIC_CONFIDENCE"])
        out.to_csv(OUT_PATH, index=False, encoding="utf-8")
        print(f"saved={OUT_PATH} rows=0")
        return

    merged = merged.sort_values(["price_value"], ascending=[True]).drop_duplicates(subset=["course_id"], keep="first")
    out = pd.DataFrame({
        "course_id": merged["course_id"].astype(int),
        "PRIC": merged["Price"].astype(str),
        "PRIC_SOURCE": "uipath_bot_output",
        "PRIC_CONFIDENCE": 0.9,
    })
    out.to_csv(OUT_PATH, index=False, encoding="utf-8")
    print(f"saved={OUT_PATH} rows={len(out)}")


if __name__ == "__main__":
    main()
