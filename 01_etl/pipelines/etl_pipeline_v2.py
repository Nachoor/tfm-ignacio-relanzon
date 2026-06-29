import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Set

import pandas as pd


@dataclass
class ETLConfig:
    raw_dir: Path
    out_dir: Path
    curated_dir: Path
    reports_dir: Path
    taxonomy_path: Path
    sample_rows: int
    overwrite: bool


def setup_logger(out_dir: Path) -> logging.Logger:
    out_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("etl_v2")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    fh = logging.FileHandler(out_dir / "etl_pipeline_v2.log", encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


def norm_text(x: object) -> str:
    if pd.isna(x):
        return ""
    return re.sub(r"\s+", " ", str(x)).strip()


def read_csv_safe(path: Path, logger: logging.Logger, usecols=None, nrows: int = 0) -> pd.DataFrame:
    encodings = ["utf-8-sig", "utf-8", "latin-1"]
    last_exc = None
    for enc in encodings:
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False, usecols=usecols, nrows=nrows or None)
        except Exception as exc:
            last_exc = exc
    raise RuntimeError(f"Failed reading {path}: {last_exc}")


def write_csv_atomic(df: pd.DataFrame, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    df.to_csv(tmp, index=False, encoding="utf-8")
    tmp.replace(target)


def validate_required_columns(df: pd.DataFrame, required: Iterable[str], dataset_name: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{dataset_name}: missing required columns: {missing}")


def contains_term(text: str, term: str) -> bool:
    t = f" {text.lower()} "
    q = term.lower()
    if q.startswith(" ") or q.endswith(" "):
        return q in t
    return re.search(rf"\b{re.escape(q)}\b", t) is not None


def extract_skills(text: str, taxonomy: Dict[str, List[str]]) -> List[str]:
    txt = norm_text(text).lower()
    if not txt:
        return []
    found = []
    for skill, aliases in taxonomy.items():
        for alias in aliases:
            if contains_term(txt, alias):
                found.append(skill)
                break
    return sorted(set(found))


def split_skills_field(raw: str, taxonomy: Dict[str, List[str]]) -> List[str]:
    txt = norm_text(raw)
    if not txt:
        return []
    parts = re.split(r"[|,;/]+", txt)
    out: List[str] = []
    for p in parts:
        p = norm_text(p)
        if p:
            out.extend(extract_skills(p, taxonomy))
    if not out:
        out = extract_skills(txt, taxonomy)
    return sorted(set(out))


def normalize_role(title: str) -> str:
    t = norm_text(title).lower()
    if not t:
        return "unknown"
    # MLOps / ML Engineer (antes de "machine learning" genérico)
    if any(kw in t for kw in ("mlops", "ml ops", "machine learning ops",
                               "ml platform", "model deployment", "ml infrastructure",
                               "machine learning engineer", "ml engineer")):
        return "mlops"
    if "machine learning" in t:
        return "ml_engineer"
    if "data engineer" in t:
        return "data_engineer"
    if "data scientist" in t:
        return "data_scientist"
    # Business Intelligence (antes de "analyst" genérico)
    if any(kw in t for kw in ("business intelligence", "bi analyst", "bi developer",
                               "bi engineer", "bi lead", "bi manager", "power bi",
                               "analytics engineer", "reporting analyst")):
        return "business_intelligence"
    if "business analyst" in t:
        return "business_intelligence"
    if "analyst" in t:
        return "data_analyst"
    return "other_data_role"


def load_resume(cfg: ETLConfig, taxonomy: Dict[str, List[str]], logger: logging.Logger) -> Dict[str, int]:
    path = cfg.raw_dir / "resume_data.csv"
    logger.info("E resume_data.csv")
    df = read_csv_safe(path, logger, nrows=cfg.sample_rows)

    position_col = "job_position_name"
    if position_col not in df.columns and "\ufeffjob_position_name" in df.columns:
        position_col = "\ufeffjob_position_name"

    df = df.reset_index(drop=True)
    df["candidate_id"] = df.index + 1

    profile = pd.DataFrame(
        {
            "candidate_id": df["candidate_id"],
            "job_position_name": df[position_col].map(norm_text) if position_col in df.columns else "",
            "career_objective": df.get("career_objective", "").map(norm_text) if "career_objective" in df.columns else "",
            "major_field_of_studies": df.get("major_field_of_studies", "").map(norm_text)
            if "major_field_of_studies" in df.columns
            else "",
        }
    )

    skills_rows = []
    for _, row in df.iterrows():
        cid = int(row["candidate_id"])
        skills = set()
        skills.update(split_skills_field(row.get("skills", ""), taxonomy))
        skills.update(split_skills_field(row.get("related_skils_in_job", ""), taxonomy))
        skills.update(extract_skills(f"{row.get('career_objective','')} {row.get(position_col,'')}", taxonomy))
        for sk in sorted(skills):
            skills_rows.append({"candidate_id": cid, "skill": sk})

    candidate_skills = pd.DataFrame(skills_rows).drop_duplicates()

    write_csv_atomic(profile, cfg.curated_dir / "candidate_profile.csv")
    write_csv_atomic(candidate_skills, cfg.curated_dir / "candidate_skills.csv")

    return {
        "candidate_rows": int(len(profile)),
        "candidate_skill_rows": int(len(candidate_skills)),
        "candidate_skills_unique": int(candidate_skills["skill"].nunique() if not candidate_skills.empty else 0),
    }


def load_jobs(cfg: ETLConfig, taxonomy: Dict[str, List[str]], logger: logging.Logger) -> Dict[str, int]:
    path = cfg.raw_dir / "massive_jobs_final.csv"
    logger.info("E massive_jobs_final.csv")
    usecols = ["id", "site", "title", "company", "location", "date_posted", "job_type", "is_remote", "job_level", "job_function", "description"]
    df = read_csv_safe(path, logger, usecols=lambda c: c in set(usecols), nrows=cfg.sample_rows)
    validate_required_columns(df, ["id", "title", "description"], "massive_jobs_final.csv")

    df = df.drop_duplicates(subset=["id", "title", "company", "location"], keep="first").copy()
    df["job_id"] = df["id"].astype(str).map(norm_text)
    for c in ["site", "title", "company", "location", "date_posted", "job_type", "job_level", "job_function", "description"]:
        if c in df.columns:
            df[c] = df[c].map(norm_text)
        else:
            df[c] = ""
    if "is_remote" not in df.columns:
        df["is_remote"] = ""

    df["role_family"] = df["title"].map(normalize_role)

    jobs_clean = df[["job_id", "site", "title", "company", "location", "date_posted", "job_type", "is_remote", "job_level", "job_function", "role_family", "description"]]

    skill_rows = []
    for _, row in jobs_clean.iterrows():
        text = f"{row['title']} {row['description']} {row['job_function']} {row['job_level']}"
        for sk in extract_skills(text, taxonomy):
            skill_rows.append({"job_id": row["job_id"], "skill": sk, "role_family": row["role_family"]})

    job_skills = pd.DataFrame(skill_rows).drop_duplicates()

    # role_job_count: número de ofertas únicas por familia de rol (denominador de demand_ratio)
    role_job_count = (
        jobs_clean.groupby("role_family", as_index=False)["job_id"]
        .nunique()
        .rename(columns={"job_id": "role_job_count"})
    )

    role_skill_demand = (
        job_skills.groupby(["role_family", "skill"], as_index=False)
        .size()
        .rename(columns={"size": "demand_count"})
        .merge(role_job_count, on="role_family", how="left")
        .assign(
            demand_ratio=lambda df: df["demand_count"] / df["role_job_count"].clip(lower=1)
        )
        .sort_values(["role_family", "demand_count"], ascending=[True, False])
    )

    write_csv_atomic(jobs_clean, cfg.curated_dir / "job_postings_clean.csv")
    write_csv_atomic(job_skills, cfg.curated_dir / "job_skills.csv")
    write_csv_atomic(role_skill_demand, cfg.curated_dir / "role_skill_demand.csv")

    return {
        "jobs_rows": int(len(jobs_clean)),
        "jobs_skill_rows": int(len(job_skills)),
        "jobs_skills_unique": int(job_skills["skill"].nunique() if not job_skills.empty else 0),
    }


def load_masters(cfg: ETLConfig, taxonomy: Dict[str, List[str]], logger: logging.Logger) -> Dict[str, int]:
    path = cfg.raw_dir / "Masters.csv"
    logger.info("E Masters.csv")
    df = read_csv_safe(path, logger, nrows=cfg.sample_rows)
    validate_required_columns(df, ["program_name", "url", "study_content"], "Masters.csv")

    for c in ["program_name", "university", "rating", "reviews", "location", "tuition", "duration", "url", "study_content"]:
        if c in df.columns:
            df[c] = df[c].map(norm_text)
        else:
            df[c] = ""

    df = df.drop_duplicates(subset=["url"], keep="first").copy()
    df["master_id"] = range(1, len(df) + 1)

    masters_clean = df[["master_id", "program_name", "university", "rating", "reviews", "location", "tuition", "duration", "url", "study_content"]]

    skill_rows = []
    for _, row in masters_clean.iterrows():
        txt = f"{row['program_name']} {row['study_content']}"
        for sk in extract_skills(txt, taxonomy):
            skill_rows.append({"master_id": int(row["master_id"]), "skill": sk})

    master_skills = pd.DataFrame(skill_rows).drop_duplicates()

    write_csv_atomic(masters_clean, cfg.curated_dir / "masters_catalog_clean.csv")
    write_csv_atomic(master_skills, cfg.curated_dir / "master_skills.csv")

    return {
        "masters_rows": int(len(masters_clean)),
        "masters_skill_rows": int(len(master_skills)),
        "masters_skills_unique": int(master_skills["skill"].nunique() if not master_skills.empty else 0),
    }


def load_courses(cfg: ETLConfig, taxonomy: Dict[str, List[str]], logger: logging.Logger) -> Dict[str, int]:
    path = cfg.raw_dir / "courses.csv"
    logger.info("E courses.csv")
    usecols = ["id", "title", "url", "rating", "num_reviews", "duration", "last_update_date"]
    df = read_csv_safe(path, logger, usecols=lambda c: c in set(usecols), nrows=cfg.sample_rows)
    validate_required_columns(df, ["id", "title", "url"], "courses.csv")

    for c in ["title", "url", "duration", "last_update_date"]:
        if c in df.columns:
            df[c] = df[c].map(norm_text)
        else:
            df[c] = ""

    df = df.drop_duplicates(subset=["id", "title", "url"], keep="first").copy()
    df["course_id"] = df["id"].astype(str).map(norm_text)

    courses_clean = df[["course_id", "title", "url", "rating", "num_reviews", "duration", "last_update_date"]]

    skill_rows = []
    for _, row in courses_clean.iterrows():
        for sk in extract_skills(row["title"], taxonomy):
            skill_rows.append({"course_id": row["course_id"], "skill": sk})

    course_skills = pd.DataFrame(skill_rows).drop_duplicates()

    write_csv_atomic(courses_clean, cfg.curated_dir / "courses_catalog_clean.csv")
    write_csv_atomic(course_skills, cfg.curated_dir / "course_skills.csv")

    return {
        "courses_rows": int(len(courses_clean)),
        "courses_skill_rows": int(len(course_skills)),
        "courses_skills_unique": int(course_skills["skill"].nunique() if not course_skills.empty else 0),
    }


def build_dim_skills(cfg: ETLConfig, logger: logging.Logger) -> Dict[str, int]:
    src_files = [
        cfg.curated_dir / "candidate_skills.csv",
        cfg.curated_dir / "job_skills.csv",
        cfg.curated_dir / "master_skills.csv",
        cfg.curated_dir / "course_skills.csv",
    ]
    all_skills: Set[str] = set()
    for p in src_files:
        if p.exists():
            df = pd.read_csv(p)
            if "skill" in df.columns:
                all_skills.update(df["skill"].dropna().astype(str).map(norm_text))

    dim = pd.DataFrame({"skill": sorted([s for s in all_skills if s])})
    dim["skill_id"] = range(1, len(dim) + 1)
    dim = dim[["skill_id", "skill"]]
    write_csv_atomic(dim, cfg.curated_dir / "dim_skills.csv")
    return {"dim_skills_rows": int(len(dim))}


def run_quality_checks(cfg: ETLConfig, metrics: Dict[str, int], logger: logging.Logger) -> None:
    checks = {
        "candidate_rows>0": metrics.get("candidate_rows", 0) > 0,
        "jobs_rows>0": metrics.get("jobs_rows", 0) > 0,
        "masters_rows>0": metrics.get("masters_rows", 0) > 0,
        "courses_rows>0": metrics.get("courses_rows", 0) > 0,
        "dim_skills_rows>=20": metrics.get("dim_skills_rows", 0) >= 20,
    }
    failed = [k for k, ok in checks.items() if not ok]
    if failed:
        raise RuntimeError(f"Quality checks failed: {failed}")
    logger.info("Quality checks passed")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ETL v2 - professional data engineering pipeline")
    p.add_argument("--raw-dir", default=None)
    p.add_argument("--out-dir", default=None)
    p.add_argument("--taxonomy-path", default=None)
    p.add_argument("--sample-rows", type=int, default=0, help="Use only first N rows from each source for fast testing")
    p.add_argument("--overwrite", action="store_true", help="Reserved flag for future incremental controls")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = ETLConfig(
        raw_dir=Path(args.raw_dir),
        out_dir=Path(args.out_dir),
        curated_dir=Path(args.out_dir) / "outputs" / "curated",
        reports_dir=Path(args.out_dir) / "reports",
        taxonomy_path=Path(args.taxonomy_path),
        sample_rows=args.sample_rows,
        overwrite=args.overwrite,
    )

    logger = setup_logger(cfg.out_dir)
    logger.info("Starting ETL v2")

    if not cfg.raw_dir.exists():
        raise FileNotFoundError(f"Raw directory not found: {cfg.raw_dir}")
    if not cfg.taxonomy_path.exists():
        raise FileNotFoundError(f"Taxonomy file not found: {cfg.taxonomy_path}")

    taxonomy = json.loads(cfg.taxonomy_path.read_text(encoding="utf-8-sig"))

    metrics: Dict[str, int | str | List[str]] = {
        "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "raw_dir": str(cfg.raw_dir),
        "out_dir": str(cfg.out_dir),
        "sample_rows": int(cfg.sample_rows),
        "raw_files": sorted([p.name for p in cfg.raw_dir.glob("*.csv")]),
    }

    metrics.update(load_resume(cfg, taxonomy, logger))
    metrics.update(load_jobs(cfg, taxonomy, logger))
    metrics.update(load_masters(cfg, taxonomy, logger))
    metrics.update(load_courses(cfg, taxonomy, logger))
    metrics.update(build_dim_skills(cfg, logger))

    run_quality_checks(cfg, metrics, logger)

    metrics["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_path = cfg.reports_dir / "etl_report_v2.json"
    report_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"ETL v2 completed. Report saved to {report_path}")


if __name__ == "__main__":
    main()