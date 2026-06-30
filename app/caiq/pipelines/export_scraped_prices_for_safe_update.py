"""Export valid scraped prices into safe-update format.

Input:
  outputs/semantic/course_prices_scraped.csv
Output:
  outputs/semantic/course_prices_from_scraped.csv
"""
from __future__ import annotations

from pathlib import Path
import re

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
SEM_DIR = BASE_DIR / "outputs" / "semantic"
IN_PATH = SEM_DIR / "course_prices_scraped.csv"
OUT_PATH = SEM_DIR / "course_prices_from_scraped.csv"


def parse_price_token(token) -> float | None:
    t = str(token or "").strip()
    if not t or t.upper() == "N/D":
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


def main() -> None:
    if not IN_PATH.exists():
        pd.DataFrame(columns=["course_id", "PRIC", "PRIC_SOURCE", "PRIC_CONFIDENCE"]).to_csv(OUT_PATH, index=False, encoding="utf-8")
        print(f"saved={OUT_PATH} rows=0")
        return

    df = pd.read_csv(IN_PATH)
    if "course_id" not in df.columns:
        raise ValueError("course_prices_scraped.csv missing course_id")

    if "price_text" not in df.columns:
        df["price_text"] = ""
    if "price_confidence" not in df.columns:
        df["price_confidence"] = 0.75
    if "price_source" not in df.columns:
        df["price_source"] = "scraped"

    df["price_val"] = df["price_text"].map(parse_price_token)
    df = df[(df["price_val"].notna()) & (df["price_val"] >= 5) & (df["price_val"] <= 50000)].copy()
    if df.empty:
        pd.DataFrame(columns=["course_id", "PRIC", "PRIC_SOURCE", "PRIC_CONFIDENCE"]).to_csv(OUT_PATH, index=False, encoding="utf-8")
        print(f"saved={OUT_PATH} rows=0")
        return

    df = df.sort_values(["course_id", "price_confidence", "price_val"], ascending=[True, False, True]).drop_duplicates(subset=["course_id"], keep="first")
    out = pd.DataFrame({
        "course_id": pd.to_numeric(df["course_id"], errors="coerce").astype("Int64"),
        "PRIC": df["price_text"].astype(str),
        "PRIC_SOURCE": df["price_source"].fillna("scraped"),
        "PRIC_CONFIDENCE": pd.to_numeric(df["price_confidence"], errors="coerce").fillna(0.75),
    }).dropna(subset=["course_id"])
    out["course_id"] = out["course_id"].astype(int)
    out.to_csv(OUT_PATH, index=False, encoding="utf-8")
    print(f"saved={OUT_PATH} rows={len(out)}")


if __name__ == "__main__":
    main()

