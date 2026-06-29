import argparse
import json
import re
from pathlib import Path

import pandas as pd


SECTOR_KEYWORDS = {
    "Technology": ["software", "tech", "data", "ai", "machine learning", "cloud", "cyber", "developer", "engineer"],
    "Finance": ["bank", "banking", "fintech", "investment", "trading", "asset", "insurance", "audit", "risk"],
    "Healthcare": ["health", "clinical", "hospital", "medical", "pharma", "biotech"],
    "Consulting": ["consultant", "consulting", "advisory", "strategy"],
    "Retail/Ecommerce": ["retail", "ecommerce", "commerce", "marketplace", "merchandising"],
    "Manufacturing/Industrial": ["manufacturing", "industrial", "automotive", "supply chain", "operations"],
    "Public/Education": ["public", "government", "university", "education", "nonprofit"],
}

WORK_MODE_KEYWORDS = {
    "remote": ["remote", "work from home", "wfh", "fully remote", "home-based"],
    "hybrid": ["hybrid", "2 days office", "3 days office", "flexible office"],
    "onsite": ["on-site", "onsite", "in office", "office-based"],
}

EMPLOYMENT_TYPE_KEYWORDS = {
    "internship": ["intern", "internship", "trainee"],
    "contract": ["contract", "contractor", "freelance", "temp", "temporary"],
    "part_time": ["part-time", "part time"],
    "full_time": ["full-time", "full time", "permanent"],
}

SENIORITY_KEYWORDS = {
    "lead": ["head", "director", "principal", "lead", "manager"],
    "senior": ["senior", "sr.", "sr ", "staff"],
    "junior": ["junior", "jr.", "jr ", "entry level", "graduate", "new grad"],
    "intern": ["intern", "internship", "trainee"],
}

LANGUAGE_PATTERNS = {
    "English": [r"\benglish\b", r"\bfluent in english\b", r"\bbusiness english\b"],
    "Spanish": [r"\bspanish\b", r"\bespañol\b", r"\bcastellano\b"],
    "French": [r"\bfrench\b", r"\bfrançais\b"],
    "German": [r"\bgerman\b", r"\bdeutsch\b"],
    "Portuguese": [r"\bportuguese\b", r"\bportuguês\b"],
    "Italian": [r"\bitalian\b", r"\bitaliano\b"],
}

LEVEL_PATTERNS = [
    (r"\bc2\b", "C2"),
    (r"\bc1\b", "C1"),
    (r"\bb2\b", "B2"),
    (r"\bb1\b", "B1"),
    (r"\bnative\b", "Native"),
    (r"\bfluent\b", "Fluent"),
]

COUNTRY_ALIASES = {
    "US": "United States",
    "USA": "United States",
    "UK": "United Kingdom",
    "UAE": "United Arab Emirates",
}


def norm(x) -> str:
    if pd.isna(x):
        return ""
    return re.sub(r"\s+", " ", str(x)).strip()


def infer_sector(text: str) -> tuple[str, str]:
    t = text.lower()
    best = ("Other", 0)
    for sector, kws in SECTOR_KEYWORDS.items():
        score = sum(1 for k in kws if k in t)
        if score > best[1]:
            best = (sector, score)
    if best[1] >= 2:
        return best[0], "high"
    if best[1] == 1:
        return best[0], "medium"
    return "Other", "low"


def infer_work_mode(text: str, location: str) -> tuple[str, str]:
    t = f"{text} {location}".lower()
    for mode, kws in WORK_MODE_KEYWORDS.items():
        if any(k in t for k in kws):
            return mode, "high"
    if "remote" in location.lower():
        return "remote", "medium"
    return "unknown", "low"


def infer_employment_type(text: str) -> tuple[str, str]:
    t = text.lower()
    for typ, kws in EMPLOYMENT_TYPE_KEYWORDS.items():
        if any(k in t for k in kws):
            return typ, "high"
    return "unknown", "low"


def infer_seniority(text: str) -> tuple[str, str]:
    t = text.lower()
    for level, kws in SENIORITY_KEYWORDS.items():
        if any(k in t for k in kws):
            return level, "high"

    years = re.search(r"(\d+)\+?\s+years", t)
    if years:
        y = int(years.group(1))
        if y >= 6:
            return "senior", "medium"
        if y <= 2:
            return "junior", "medium"
        return "mid", "medium"
    return "mid", "low"


def infer_languages(text: str) -> tuple[str, str]:
    t = text.lower()
    langs = []
    conf = "low"
    level = "Required"
    for pat, lvl in LEVEL_PATTERNS:
        if re.search(pat, t):
            level = lvl
            break

    for lang, patterns in LANGUAGE_PATTERNS.items():
        if any(re.search(p, t) for p in patterns):
            langs.append(f"{lang}:{level}")
    if langs:
        conf = "high"
    return "; ".join(sorted(set(langs))) if langs else "unknown", conf


def split_location(location: str) -> tuple[str, str]:
    txt = norm(location)
    if not txt:
        return "unknown", "unknown"
    parts = [p.strip() for p in txt.split(",") if p.strip()]
    if len(parts) == 1:
        country = COUNTRY_ALIASES.get(parts[0], parts[0])
        return "unknown", country
    city = parts[0]
    country_raw = parts[-1]
    country = COUNTRY_ALIASES.get(country_raw, country_raw)
    return city, country


def enrich_jobs(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["job_text_for_inference"] = (
        out.get("title", "").fillna("").astype(str)
        + " | "
        + out.get("job_function", "").fillna("").astype(str)
        + " | "
        + out.get("job_level", "").fillna("").astype(str)
        + " | "
        + out.get("company", "").fillna("").astype(str)
    ).map(norm)

    sectors = out["job_text_for_inference"].map(infer_sector)
    out["sector"] = sectors.map(lambda x: x[0])
    out["sector_confidence"] = sectors.map(lambda x: x[1])

    work = [
        infer_work_mode(t, l)
        for t, l in zip(out["job_text_for_inference"].tolist(), out.get("location", "").fillna("").astype(str).tolist())
    ]
    out["work_mode"] = [x[0] for x in work]
    out["work_mode_confidence"] = [x[1] for x in work]

    emp = out["job_text_for_inference"].map(infer_employment_type)
    out["employment_type"] = emp.map(lambda x: x[0])
    out["employment_type_confidence"] = emp.map(lambda x: x[1])

    sen = out["job_text_for_inference"].map(infer_seniority)
    out["seniority"] = sen.map(lambda x: x[0])
    out["seniority_confidence"] = sen.map(lambda x: x[1])

    langs = out["job_text_for_inference"].map(infer_languages)
    out["language_requirements"] = langs.map(lambda x: x[0])
    out["language_confidence"] = langs.map(lambda x: x[1])

    loc = out.get("location", "").fillna("").astype(str).map(split_location)
    out["city_norm"] = loc.map(lambda x: x[0])
    out["country_norm"] = loc.map(lambda x: x[1])

    out["enrichment_version"] = "v2_rule_based_2026_03_08"
    out["inference_source"] = "title_joblevel_jobfunction_company_location"
    return out.drop(columns=["job_text_for_inference"])


def main():
    parser = argparse.ArgumentParser(description="Enrich jobs dataset v2 with sector/mode/languages/seniority/type/location.")
    parser.add_argument(
        "--input",
        default=None,
    )
    parser.add_argument(
        "--output",
        default=None,
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(in_path)
    out = enrich_jobs(df)
    out.to_csv(out_path, index=False, encoding="utf-8")

    summary = {
        "input_rows": int(len(df)),
        "output_rows": int(len(out)),
        "sector_known_pct": round(float((out["sector"] != "Other").mean() * 100), 2),
        "work_mode_known_pct": round(float((out["work_mode"] != "unknown").mean() * 100), 2),
        "languages_known_pct": round(float((out["language_requirements"] != "unknown").mean() * 100), 2),
        "seniority_known_pct": round(float((out["seniority"] != "mid").mean() * 100), 2),
        "employment_type_known_pct": round(float((out["employment_type"] != "unknown").mean() * 100), 2),
        "output_file": str(out_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
