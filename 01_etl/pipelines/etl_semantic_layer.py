import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd


def norm_text(x):
    if pd.isna(x):
        return ""
    return re.sub(r"\s+", " ", str(x)).strip()


def parse_price_eur(text: str):
    s = norm_text(text).lower().replace("eur", "€")
    if not s:
        return None
    m = re.findall(r"\d+[\.,]?\d*", s)
    if not m:
        return None
    raw = m[0].replace(",", ".")
    try:
        return float(raw)
    except Exception:
        return None


def parse_duration_months(text: str):
    s = norm_text(text).lower()
    if not s:
        return None
    num = re.findall(r"\d+[\.,]?\d*", s)
    if not num:
        return None
    v = float(num[0].replace(",", "."))
    if "year" in s:
        return v * 12
    if "month" in s:
        return v
    if "week" in s:
        return v / 4.345
    if "day" in s:
        return v / 30
    return None


def main():
    p = argparse.ArgumentParser(description="Build semantic ETL layer for advanced DataPath model")
    p.add_argument("--etl-dir", default=None)
    args = p.parse_args()

    etl_dir = Path(args.etl_dir)
    out_dir = etl_dir / "outputs" / "semantic"
    out_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = etl_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    curated = etl_dir / "outputs" / "curated"
    masters = pd.read_csv(curated / "masters_catalog_clean.csv")
    courses = pd.read_csv(curated / "courses_catalog_clean.csv")
    jobs = pd.read_csv(curated / "job_postings_clean.csv")
    role_demand = pd.read_csv(curated / "role_skill_demand.csv")

    for c in ["program_name", "university", "location", "tuition", "duration", "study_content", "url"]:
        if c in masters.columns:
            masters[c] = masters[c].map(norm_text)
    masters["price_value_eur"] = masters["tuition"].map(parse_price_eur)
    masters["duration_months"] = masters["duration"].map(parse_duration_months)
    masters["master_text"] = (
        masters["program_name"].fillna("") + " | " +
        masters["university"].fillna("") + " | " +
        masters["location"].fillna("") + " | " +
        masters["study_content"].fillna("")
    ).map(norm_text)

    for c in ["title", "url", "duration", "description", "headline", "objectives", "requirements"]:
        if c in courses.columns:
            courses[c] = courses[c].map(norm_text)
    courses["duration_months"] = courses["duration"].map(parse_duration_months)
    # course_text enriquecido: título + descripción/headline si están disponibles
    # Los embeddings semánticos ganan mucho con más contexto que solo el título
    _course_desc = (
        courses.get("description", pd.Series("", index=courses.index)).fillna("").astype(str)
        .where(lambda s: s.str.len() > 0, other="")
    )
    _course_headline = (
        courses.get("headline", pd.Series("", index=courses.index)).fillna("").astype(str)
        .where(lambda s: s.str.len() > 0, other="")
    )
    _course_objectives = (
        courses.get("objectives", pd.Series("", index=courses.index)).fillna("").astype(str)
        .where(lambda s: s.str.len() > 0, other="")
    )
    courses["course_text"] = (
        courses["title"].fillna("") + " | " +
        _course_headline + " | " +
        _course_objectives + " | " +
        _course_desc
    ).map(lambda x: re.sub(r"(\s*\|\s*)+", " | ", x).strip(" |")).map(norm_text)

    for c in ["title", "company", "location", "job_level", "job_function", "description", "role_family"]:
        if c in jobs.columns:
            jobs[c] = jobs[c].map(norm_text)
    jobs["job_text"] = (
        jobs["title"].fillna("") + " | " +
        jobs["company"].fillna("") + " | " +
        jobs["location"].fillna("") + " | " +
        jobs["job_level"].fillna("") + " | " +
        jobs["job_function"].fillna("") + " | " +
        jobs["description"].fillna("")
    ).map(norm_text)

    masters_out_cols = [
        "master_id", "program_name", "university", "location", "tuition", "price_value_eur",
        "duration", "duration_months", "url", "study_content", "master_text"
    ]
    courses_out_cols = [
        "course_id", "title", "url", "rating", "num_reviews", "duration", "duration_months", "course_text"
    ]
    jobs_out_cols = [
        "job_id", "site", "title", "company", "location", "job_level", "job_function", "role_family", "job_text"
    ]

    masters[masters_out_cols].to_csv(out_dir / "masters_features.csv", index=False, encoding="utf-8")
    courses[courses_out_cols].to_csv(out_dir / "courses_features.csv", index=False, encoding="utf-8")
    jobs[jobs_out_cols].to_csv(out_dir / "jobs_features.csv", index=False, encoding="utf-8")
    role_demand.to_csv(out_dir / "role_skill_demand.csv", index=False, encoding="utf-8")

    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "masters_rows": int(len(masters)),
        "courses_rows": int(len(courses)),
        "jobs_rows": int(len(jobs)),
        "role_skill_rows": int(len(role_demand)),
        "output_dir": str(out_dir),
    }
    (reports_dir / "semantic_layer_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
