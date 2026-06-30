"""Build a priority queue to curate course prices with maximum impact.

Outputs:
- outputs/semantic/course_price_priority_queue.csv
- outputs/semantic/course_prices_manual_priority.csv

The queue prioritizes courses that:
1) cover high-demand skills for data roles
2) have higher quality signals (rating/reviews)
3) appear relevant to data/AI keywords
"""
from __future__ import annotations

from pathlib import Path
import math
import re

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
SEM_DIR = BASE_DIR / "outputs" / "semantic"
CUR_DIR = BASE_DIR / "outputs" / "curated"

COURSES_PATH = SEM_DIR / "courses_features.csv"
COURSE_SKILLS_PATH = CUR_DIR / "course_skills.csv"
ROLE_SKILL_PATH = SEM_DIR / "role_skill_demand.csv"
MANUAL_PRICE_PATH = SEM_DIR / "course_prices_manual.csv"

OUT_QUEUE = SEM_DIR / "course_price_priority_queue.csv"
OUT_MANUAL_PRIORITY = SEM_DIR / "course_prices_manual_priority.csv"


DATA_KEYWORDS = {
    "python", "sql", "machine learning", "deep learning", "data science",
    "data analysis", "data visualization", "statistics", "pandas", "numpy",
    "power bi", "tableau", "nlp", "llm", "ai", "artificial intelligence",
    "tensorflow", "pytorch", "spark", "aws", "azure", "gcp",
}


def norm_text(x: str) -> str:
    return re.sub(r"\s+", " ", str(x or "").strip().lower())


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


def has_verified_price(v: str) -> bool:
    n = parse_price_token(v)
    return n is not None and 5 <= n <= 50000


def main() -> None:
    courses = pd.read_csv(COURSES_PATH)
    cskills = pd.read_csv(COURSE_SKILLS_PATH)
    rsd = pd.read_csv(ROLE_SKILL_PATH)

    courses["title_norm"] = courses["title"].map(norm_text)
    courses["text_norm"] = courses.get("course_text", "").map(norm_text)

    rsd["skill"] = rsd["skill"].map(norm_text)
    skill_weight = rsd.groupby("skill", as_index=False)["demand_count"].sum()
    total_demand = float(skill_weight["demand_count"].sum()) or 1.0
    skill_weight["skill_weight"] = skill_weight["demand_count"] / total_demand

    cskills["skill"] = cskills["skill"].map(norm_text)
    course_skill_score = cskills.merge(skill_weight[["skill", "skill_weight"]], on="skill", how="left")
    course_skill_score["skill_weight"] = course_skill_score["skill_weight"].fillna(0.0)
    course_skill_score = course_skill_score.groupby("course_id", as_index=False)["skill_weight"].sum()
    course_skill_score = course_skill_score.rename(columns={"skill_weight": "demand_skill_score"})

    q = courses.merge(course_skill_score, on="course_id", how="left")
    q["demand_skill_score"] = q["demand_skill_score"].fillna(0.0)

    q["rating_num"] = pd.to_numeric(q.get("rating"), errors="coerce").fillna(0.0)
    q["reviews_num"] = pd.to_numeric(q.get("num_reviews"), errors="coerce").fillna(0.0)
    q["quality_score"] = (q["rating_num"] / 5.0) * q["reviews_num"].map(lambda x: math.log1p(float(x)))

    def keyword_score(row) -> float:
        txt = f"{row.get('title_norm', '')} {row.get('text_norm', '')}"
        score = 0.0
        for kw in DATA_KEYWORDS:
            if kw in txt:
                score += 1.0
        return score

    q["keyword_score"] = q.apply(keyword_score, axis=1)

    # Normalize components
    for c in ["demand_skill_score", "quality_score", "keyword_score"]:
        mx = float(q[c].max()) if len(q) else 0.0
        q[f"{c}_n"] = (q[c] / mx) if mx > 0 else 0.0

    q["priority_score"] = (
        0.55 * q["demand_skill_score_n"] +
        0.30 * q["quality_score_n"] +
        0.15 * q["keyword_score_n"]
    )

    # Merge manual price status
    if MANUAL_PRICE_PATH.exists():
        man = pd.read_csv(MANUAL_PRICE_PATH)
        man = man[[c for c in ["course_id", "PRIC", "PRIC_SOURCE", "PRIC_CONFIDENCE"] if c in man.columns]]
        q = q.merge(man, on="course_id", how="left", suffixes=("", "_manual"))
    else:
        q["PRIC"] = ""
        q["PRIC_SOURCE"] = ""
        q["PRIC_CONFIDENCE"] = ""

    q["price_verified"] = q["PRIC"].map(lambda x: has_verified_price(str(x or "")))

    out_cols = [
        "course_id", "title", "url", "rating", "num_reviews", "duration",
        "demand_skill_score", "quality_score", "keyword_score", "priority_score",
        "PRIC", "PRIC_SOURCE", "PRIC_CONFIDENCE", "price_verified",
    ]
    out = q[out_cols].sort_values(
        ["price_verified", "priority_score", "demand_skill_score", "quality_score"],
        ascending=[True, False, False, False],
    ).reset_index(drop=True)
    out["rank"] = out.index + 1

    OUT_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_QUEUE, index=False, encoding="utf-8")

    # Focused manual list: top courses without verified price
    manual = out[~out["price_verified"]].head(800).copy()
    manual = manual[["course_id", "title", "url"]]
    manual["PRIC"] = ""
    manual["PRIC_SOURCE"] = "manual_priority"
    manual["PRIC_CONFIDENCE"] = 1.0
    manual.to_csv(OUT_MANUAL_PRIORITY, index=False, encoding="utf-8")

    print(f"saved_queue={OUT_QUEUE} rows={len(out)}")
    print(f"saved_manual_priority={OUT_MANUAL_PRIORITY} rows={len(manual)}")


if __name__ == "__main__":
    main()

