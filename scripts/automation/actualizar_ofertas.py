"""
actualizar_ofertas.py
=====================
Pipeline completo de refresco de ofertas de empleo para CAIQ.

Pasos:
  1. Scraping  â€” JobSpy: LinkedIn (EspaÃ±a + USA)
  2. Limpieza  â€” normalizaciÃ³n y role_family
  3. Skills    â€” extracciÃ³n con skills_taxonomy.json
  4. Outputs   â€” escribe los 3 CSVs que consume la app
  5. Upload    â€” sube solo los CSVs de jobs a HuggingFace

Uso rÃ¡pido (lanzar desde C:\\Users\\Nacho\\Documents\\TFM):
    python scripts\\automation\\actualizar_ofertas.py

Solo scraping sin subir:
    python scripts\\automation\\actualizar_ofertas.py --no-upload

Solo USA o solo EspaÃ±a:
    python scripts\\automation\\actualizar_ofertas.py --locations Spain
    python scripts\\automation\\actualizar_ofertas.py --locations "United States"

MÃ¡s resultados / mÃ¡s recientes:
    python scripts\\automation\\actualizar_ofertas.py --results 300 --hours-old 72
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

try:
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")
except Exception:
    pass

# â”€â”€â”€ Rutas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
ROOT      = Path(__file__).resolve().parents[2]
APP_DIR   = ROOT / "app" / "caiq"
OUT_SEM   = APP_DIR / "outputs" / "semantic"
OUT_CUR   = APP_DIR / "outputs" / "curated"
TAXONOMY  = APP_DIR / "config" / "skills_taxonomy.json"
SCRAPER   = ROOT / "_historico" / "scraping_raw" / "JOB_POSTS" / "JobSpy-main"
URL_STATUS = OUT_SEM / "job_url_status.csv"

HF_TOKEN  = os.environ.get("HF_TOKEN", "")
HF_SPACE  = "relan02/caiq"

DEFAULT_LOCATIONS = [
    "Spain",
    "Portugal",
    "France",
    "Italy",
    "Germany",
    "Netherlands",
    "Belgium",
    "United Kingdom",
    "Ireland",
    "United States",
    "Canada",
    "Mexico",
]

DEFAULT_SITES = ["linkedin", "indeed"]

SEARCH_TERMS = [
    '"data scientist"',
    '"data analyst"',
    '"data engineer"',
    '"machine learning engineer"',
    '"ml engineer"',
    '"business intelligence" OR "bi analyst"',
    '"analytics engineer"',
    '"data science"',
]

# â”€â”€â”€ Role family â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def normalize_role(title: str) -> str:
    t = re.sub(r"\s+", " ", str(title or "")).strip().lower()
    if not t:
        return "other_data_role"
    if any(kw in t for kw in ("mlops", "ml ops", "ml platform", "model deployment",
                               "machine learning engineer", "ml engineer")):
        return "ml_engineer"
    if "machine learning" in t:
        return "ml_engineer"
    if "data engineer" in t:
        return "data_engineer"
    if "data scientist" in t:
        return "data_scientist"
    if any(kw in t for kw in ("business intelligence", "bi analyst", "bi developer",
                               "analytics engineer", "reporting analyst")):
        return "data_analyst"
    if "analyst" in t:
        return "data_analyst"
    return "other_data_role"


# â”€â”€â”€ Skill extraction â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def load_taxonomy(path: Path) -> dict[str, list[str]]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _contains_term(text: str, term: str) -> bool:
    pattern = r"(?<![a-z0-9_])" + re.escape(term) + r"(?![a-z0-9_])"
    return bool(re.search(pattern, text, re.IGNORECASE))


def extract_skills(text: str, taxonomy: dict[str, list[str]]) -> list[str]:
    txt = re.sub(r"\s+", " ", str(text or "")).lower()
    found = []
    for skill, aliases in taxonomy.items():
        for alias in aliases:
            if _contains_term(txt, alias):
                found.append(skill)
                break
    return sorted(set(found))


# â”€â”€â”€ Scraping â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def scrape_location(location: str, results: int, hours_old: int, verbose: int,
                    sites: list[str] | None = None) -> pd.DataFrame:
    try:
        from jobspy import scrape_jobs
    except ImportError:
        print("  [ERROR] jobspy no instalado. Ejecuta: pip install jobspy")
        return pd.DataFrame()

    frames = []
    sites = sites or DEFAULT_SITES
    for term in SEARCH_TERMS:
        try:
            df = scrape_jobs(
                site_name=sites,
                search_term=term,
                location=location,
                country_indeed=location,
                results_wanted=results,
                hours_old=hours_old,
                linkedin_fetch_description=False,
                verbose=verbose,
            )
            if df is not None and not df.empty:
                df["query_term"] = term
                df["search_location"] = location
                frames.append(df)
                print(f"    term={term!r:40s}  rows={len(df)}")
        except Exception as exc:
            print(f"    [WARN] term={term!r} â†’ {exc}")
        time.sleep(random.uniform(6, 14))

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


# â”€â”€â”€ Processing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def process(raw: pd.DataFrame, taxonomy: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Returns (job_postings_clean, jobs_features, job_skills)"""
    df = raw.copy()

    # Dedup by URL
    if "job_url" in df.columns:
        df = df.drop_duplicates(subset=["job_url"], keep="first")

    # Assign stable job_id
    if "job_id" not in df.columns or df["job_id"].isna().all():
        df["job_id"] = [str(uuid.uuid4())[:8] for _ in range(len(df))]

    df["role_family"]     = df.get("title", "").fillna("").map(normalize_role)
    df["normalized_role"] = df["role_family"]
    df["date_posted"]     = pd.to_datetime(df.get("date_posted"), errors="coerce").dt.strftime("%Y-%m-%d")

    # â”€â”€ job_postings_clean â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    keep_clean = ["job_id", "site", "job_url", "title", "company", "location",
                  "date_posted", "job_type", "is_remote", "job_level",
                  "job_function", "role_family", "description"]
    clean_cols = [c for c in keep_clean if c in df.columns]
    job_postings_clean = df[clean_cols].copy()

    # â”€â”€ jobs_features (sin description para ahorrar memoria) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    keep_feat = ["job_id", "site", "job_url", "job_url_direct", "title",
                 "company", "location", "search_location", "date_posted",
                 "job_level", "job_function", "role_family", "normalized_role"]
    feat_cols = [c for c in keep_feat if c in df.columns]
    jobs_features = df[feat_cols].copy()

    # â”€â”€ job_skills â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    skill_rows = []
    desc_col = "description" if "description" in df.columns else None
    for _, row in df.iterrows():
        text = " ".join([
            str(row.get("title", "") or ""),
            str(row.get(desc_col, "") or "") if desc_col else "",
        ])
        for sk in extract_skills(text, taxonomy):
            skill_rows.append({
                "job_id":      row["job_id"],
                "skill":       sk,
                "role_family": row["role_family"],
            })
    job_skills = pd.DataFrame(skill_rows).drop_duplicates() if skill_rows else pd.DataFrame(
        columns=["job_id", "skill", "role_family"])

    return job_postings_clean, jobs_features, job_skills


# â”€â”€â”€ Merge con datos existentes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def merge_with_existing(new_df: pd.DataFrame, existing_path: Path,
                        dedup_col: str = "job_url", keep_days: int = 90) -> pd.DataFrame:
    if existing_path.exists():
        try:
            existing = pd.read_csv(existing_path, low_memory=False)
            combined = pd.concat([new_df, existing], ignore_index=True)
        except Exception:
            combined = new_df.copy()
    else:
        combined = new_df.copy()

    if dedup_col in combined.columns:
        combined = combined.drop_duplicates(subset=[dedup_col], keep="first")

    # Eliminar ofertas muy antiguas
    if "date_posted" in combined.columns:
        dates = pd.to_datetime(combined["date_posted"], errors="coerce")
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=keep_days)
        mask_recent = dates.isna() | (dates >= cutoff)
        combined = combined[mask_recent].copy()

    return combined



# â”€â”€â”€ VerificaciÃ³n de URLs activas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _legacy_verify_job_urls(df: pd.DataFrame, min_age_days: int = 7,
                    batch_size: int = 20, pause: float = 1.0,
                    max_checks: int | None = 80) -> pd.DataFrame:
    """
    Filtra ofertas cuya URL ya no es vÃ¡lida en LinkedIn.
    Solo verifica las que tienen mÃ¡s de min_age_days dÃ­as (las recientes se asumen activas).
    Hace peticiones HEAD con follow_redirects y comprueba que la URL final
    sigue siendo una pÃ¡gina de oferta (/jobs/view/).
    """
    try:
        import requests as req_lib
    except ImportError:
        print("  [WARN] requests no instalado â€” omitiendo verificaciÃ³n de URLs")
        return df

    if "job_url" not in df.columns:
        return df

    now = pd.Timestamp.now()
    dates = pd.to_datetime(df.get("date_posted", pd.Series(dtype="object")), errors="coerce")
    age_days = (now - dates).dt.total_seconds() / 86400.0

    # Ãndices a verificar: mÃ¡s de min_age_days dÃ­as o fecha desconocida
    to_check = df.index[(age_days.isna()) | (age_days >= min_age_days)].tolist()
    if not to_check:
        print(f"  [VERIFY] Ninguna oferta supera {min_age_days} dÃ­as â€” todo activo")
        return df
    if max_checks is not None and max_checks > 0 and len(to_check) > max_checks:
        to_check = (
            df.loc[to_check]
              .sample(n=max_checks, random_state=pd.Timestamp.now().dayofyear)
              .index
              .tolist()
        )
        print(f"  [VERIFY] Muestreo limitado a {len(to_check)} URLs antiguas")

    print(f"  [VERIFY] Verificando {len(to_check)} URLs (>{min_age_days}d) en lotes de {batch_size}...")
    dead_idx = set()
    session = req_lib.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    })

    for i in range(0, len(to_check), batch_size):
        batch = to_check[i : i + batch_size]
        for idx in batch:
            url = str(df.at[idx, "job_url"] or "")
            if not url.startswith("http"):
                continue
            try:
                r = session.head(url, timeout=6, allow_redirects=True)
                final_url = r.url
                # LinkedIn redirige las ofertas eliminadas fuera de /jobs/view/
                if "/jobs/view/" not in final_url:
                    dead_idx.add(idx)
            except Exception:
                pass  # timeout / error de red â†’ conservamos la oferta por precauciÃ³n
        time.sleep(pause + random.uniform(0, 1.5))

    if dead_idx:
        print(f"  [VERIFY] {len(dead_idx)} ofertas eliminadas de LinkedIn â€” se descartan")
        df = df.drop(index=list(dead_idx)).reset_index(drop=True)
    else:
        print(f"  [VERIFY] Todas las URLs verificadas siguen activas")

    return df


def load_url_status(path: Path = URL_STATUS) -> pd.DataFrame:
    cols = ["job_url", "url_status", "last_checked_at", "http_status", "final_url", "check_error"]
    if not path.exists():
        return pd.DataFrame(columns=cols)
    try:
        status = pd.read_csv(path, dtype=str).fillna("")
    except Exception:
        return pd.DataFrame(columns=cols)
    for col in cols:
        if col not in status.columns:
            status[col] = ""
    return status[cols].drop_duplicates(subset=["job_url"], keep="last")


def save_url_status(status: pd.DataFrame, path: Path = URL_STATUS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    status.drop_duplicates(subset=["job_url"], keep="last").to_csv(
        path, index=False, quoting=csv.QUOTE_NONNUMERIC
    )


def merge_url_status(df: pd.DataFrame, status: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "job_url" not in df.columns or status.empty:
        return df
    keep = ["job_url", "url_status", "last_checked_at", "http_status", "final_url"]
    drop_cols = [c for c in keep if c in df.columns and c != "job_url"]
    base = df.drop(columns=drop_cols) if drop_cols else df
    return base.merge(status[keep].drop_duplicates(subset=["job_url"]), on="job_url", how="left")


def verify_job_urls(df: pd.DataFrame, visible_days: int = 60, ttl_days: int = 7,
                    batch_size: int = 20, pause: float = 1.0,
                    max_checks: int | None = 200,
                    status_path: Path = URL_STATUS) -> pd.DataFrame:
    try:
        import requests as req_lib
    except ImportError:
        print("  [WARN] requests no instalado - omitiendo verificacion de URLs")
        return load_url_status(status_path)

    if "job_url" not in df.columns:
        return load_url_status(status_path)

    now = pd.Timestamp.now()
    status = load_url_status(status_path)
    cols = ["job_url"] + (["date_posted"] if "date_posted" in df.columns else [])
    work = df[cols].dropna(subset=["job_url"]).drop_duplicates(subset=["job_url"]).copy()
    work["job_url"] = work["job_url"].astype(str)
    work = work[work["job_url"].str.startswith("http", na=False)].copy()
    if work.empty:
        return status

    if "date_posted" in work.columns:
        dates = pd.to_datetime(work["date_posted"], errors="coerce")
        cutoff = now - pd.Timedelta(days=visible_days)
        work["priority_visible"] = dates.notna() & (dates >= cutoff) & (dates <= now + pd.Timedelta(days=1))
    else:
        work["priority_visible"] = True

    if not status.empty:
        work = work.merge(
            status[["job_url", "url_status", "last_checked_at"]].drop_duplicates(subset=["job_url"]),
            on="job_url",
            how="left",
        )
    else:
        work["url_status"] = ""
        work["last_checked_at"] = ""

    checked_at = pd.to_datetime(work["last_checked_at"], errors="coerce", utc=True)
    ttl_cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=ttl_days)
    candidates = work[(checked_at.isna() | (checked_at < ttl_cutoff)) & work["url_status"].fillna("").ne("dead")].copy()
    if candidates.empty:
        print(f"  [VERIFY] URLs cacheadas: sin checks pendientes (ttl={ttl_days}d)")
        return status

    candidates = candidates.sort_values("priority_visible", ascending=False)
    to_check = candidates["job_url"].tolist()
    if max_checks is not None and max_checks > 0 and len(to_check) > max_checks:
        to_check = to_check[:max_checks]
        print(f"  [VERIFY] Limite de verificacion: {len(to_check)} URLs")

    print(f"  [VERIFY] Verificando {len(to_check)} URLs en lotes de {batch_size}...")
    session = req_lib.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    })

    records = []
    for i in range(0, len(to_check), batch_size):
        batch = to_check[i : i + batch_size]
        for url in batch:
            record = {
                "job_url": url,
                "url_status": "unknown",
                "last_checked_at": datetime.now(timezone.utc).isoformat(),
                "http_status": "",
                "final_url": "",
                "check_error": "",
            }
            try:
                r = session.head(url, timeout=6, allow_redirects=True)
                final_url = str(r.url or "")
                record["http_status"] = str(getattr(r, "status_code", ""))
                record["final_url"] = final_url
                if r.status_code in {401, 403, 429}:
                    record["url_status"] = "blocked"
                elif r.status_code >= 400:
                    record["url_status"] = "dead"
                elif "linkedin.com" in url and "/jobs/view/" not in final_url:
                    record["url_status"] = "dead"
                else:
                    record["url_status"] = "active"
            except Exception as exc:
                record["url_status"] = "unknown"
                record["check_error"] = type(exc).__name__
            records.append(record)
        time.sleep(pause + random.uniform(0, 1.5))

    updates = pd.DataFrame(records)
    combined = pd.concat([status, updates], ignore_index=True) if not status.empty else updates
    combined = combined.drop_duplicates(subset=["job_url"], keep="last")
    save_url_status(combined, status_path)
    print(f"  [VERIFY] Estado URLs actualizado: {updates['url_status'].value_counts().to_dict()}")
    return combined

# â”€â”€â”€ Upload HuggingFace â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def upload_to_hf(files: list[tuple[Path, str]]) -> None:
    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("  [ERROR] huggingface_hub no instalado. Ejecuta: pip install huggingface_hub")
        return

    api = HfApi(token=HF_TOKEN)
    msg = f"Auto-refresh ofertas {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC"
    for local, repo_path in files:
        if not local.exists():
            print(f"  [WARN] No encontrado: {local}")
            continue
        size_kb = local.stat().st_size // 1024
        print(f"  â¬†  {repo_path} ({size_kb} KB)...")
        api.upload_file(
            path_or_fileobj=str(local),
            path_in_repo=repo_path,
            repo_id=HF_SPACE,
            repo_type="space",
            commit_message=msg,
        )
        print(f"  âœ… {repo_path}")



# â”€â”€â”€ Enrich jobs (sector / seniority / work mode) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_SECTOR_KW = {
    "Technology":             ["software","tech","data","ai","machine learning","cloud","cyber","developer","engineer"],
    "Finance":                ["bank","banking","fintech","investment","trading","insurance","audit","risk"],
    "Healthcare":             ["health","clinical","hospital","medical","pharma","biotech"],
    "Consulting":             ["consultant","consulting","advisory","strategy"],
    "Retail/Ecommerce":       ["retail","ecommerce","commerce","marketplace"],
    "Manufacturing":          ["manufacturing","industrial","automotive","supply chain","operations"],
    "Public/Education":       ["public","government","university","education","nonprofit"],
}
_SENIORITY_KW = {
    "lead":   ["head","director","principal","lead","manager"],
    "senior": ["senior","sr.","sr ","staff"],
    "junior": ["junior","jr.","jr ","entry level","graduate","new grad"],
    "intern": ["intern","internship","trainee"],
}
_MODE_KW = {
    "remote":  ["remote","work from home","wfh","fully remote"],
    "hybrid":  ["hybrid","flexible office"],
    "onsite":  ["on-site","onsite","in office","office-based"],
}

def _classify(text: str, kw_dict: dict, default: str = "unknown") -> str:
    t = str(text or "").lower()
    for label, kws in kw_dict.items():
        if any(k in t for k in kws):
            return label
    return default

def enrich_jobs(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    combined = (
        out.get("title", pd.Series("", index=out.index)).fillna("").astype(str) + " " +
        out.get("company", pd.Series("", index=out.index)).fillna("").astype(str)
    )
    out["sector"]          = combined.map(lambda t: _classify(t, _SECTOR_KW, "Other"))
    out["seniority"]       = out.get("title", pd.Series("", index=out.index)).fillna("").map(
                                 lambda t: _classify(t, _SENIORITY_KW, "unknown"))
    out["work_mode"]       = out.get("title", pd.Series("", index=out.index)).fillna("").map(
                                 lambda t: _classify(t, _MODE_KW, "unknown"))
    return out


# â”€â”€â”€ Rebuild role_skill_demand from job_skills â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def rebuild_role_skill_demand(job_skills: pd.DataFrame) -> pd.DataFrame:
    if job_skills.empty or "skill" not in job_skills.columns:
        return pd.DataFrame(columns=["role_family", "skill", "demand_count", "demand_ratio"])
    grp = job_skills.groupby(["role_family", "skill"]).size().reset_index(name="demand_count")
    totals = job_skills.groupby("role_family")["job_id"].nunique().reset_index(name="total_jobs")
    grp = grp.merge(totals, on="role_family", how="left")
    grp["demand_ratio"] = (grp["demand_count"] / grp["total_jobs"].clip(lower=1)).round(4)
    return grp.sort_values(["role_family", "demand_ratio"], ascending=[True, False]).reset_index(drop=True)


# â”€â”€â”€ Main â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def main():
    p = argparse.ArgumentParser(description="Refresca ofertas de empleo para CAIQ")
    p.add_argument("--locations", nargs="+", default=DEFAULT_LOCATIONS,
                   help="Mercados a scrapear (default: paises soportados por la app)")
    p.add_argument("--sites", nargs="+", default=DEFAULT_SITES,
                   choices=["linkedin", "indeed", "glassdoor", "google", "zip_recruiter"],
                   help="Fuentes a scrapear (default: linkedin indeed)")
    p.add_argument("--results", type=int, default=200,
                   help="Resultados por tÃ©rmino y localizaciÃ³n (default: 200)")
    p.add_argument("--hours-old", type=int, default=72,
                   help="AntigÃ¼edad mÃ¡xima en horas (default: 72)")
    p.add_argument("--keep-days", type=int, default=90,
                   help="DÃ­as que se conservan en el histÃ³rico (default: 90)")
    p.add_argument("--no-upload", action="store_true",
                   help="No subir a HuggingFace (solo actualizar CSVs locales)")
    p.add_argument("--max-verify-urls", type=int, default=300,
                   help="Maximo de URLs a verificar por ejecucion (0 desactiva el limite)")
    p.add_argument("--url-check-ttl-days", type=int, default=7,
                   help="Dias antes de volver a verificar una URL ya cacheada")
    p.add_argument("--visible-job-days", type=int, default=60,
                   help="Ventana de ofertas visibles en la app; se prioriza para verificar URLs")
    p.add_argument("--verbose", type=int, default=0, choices=[0, 1, 2])
    args = p.parse_args()

    OUT_SEM.mkdir(parents=True, exist_ok=True)
    OUT_CUR.mkdir(parents=True, exist_ok=True)

    if not TAXONOMY.exists():
        print(f"[ERROR] Taxonomy no encontrada: {TAXONOMY}")
        return
    taxonomy = load_taxonomy(TAXONOMY)
    print(f"[INFO] Taxonomy cargada: {len(taxonomy)} skills")

    # â”€â”€ Scraping â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    all_frames = []
    print(f"[INFO] Fuentes activas: {', '.join(args.sites)}")
    for loc in args.locations:
        print(f"\n[SCRAPING] {loc} ...")
        df_loc = scrape_location(loc, results=args.results,
                                 hours_old=args.hours_old, verbose=args.verbose,
                                 sites=args.sites)
        print(f"  â†’ {len(df_loc)} ofertas scrapeadas en {loc}")
        if not df_loc.empty:
            all_frames.append(df_loc)

    if not all_frames:
        print("[ERROR] No se obtuvo ninguna oferta. Revisa tu conexiÃ³n o los tÃ©rminos.")
        return

    raw = pd.concat(all_frames, ignore_index=True)
    print(f"\n[INFO] Total raw: {len(raw)} filas")

    # â”€â”€ Procesado â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("[INFO] Procesando: role_family + skills...")
    new_clean, new_feat, new_skills = process(raw, taxonomy)

    # â”€â”€ Merge con histÃ³rico â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("[INFO] Mergeando con datos existentes...")
    job_postings_clean = merge_with_existing(
        new_clean, OUT_CUR / "job_postings_clean.csv",
        dedup_col="job_url", keep_days=args.keep_days)

    jobs_features = merge_with_existing(
        new_feat, OUT_SEM / "jobs_features.csv",
        dedup_col="job_url", keep_days=args.keep_days)

    # job_skills: rebuild from merged clean (mÃ¡s fiable que mergearlo por id)
    print("[INFO] Reconstruyendo job_skills...")
    skill_rows = []
    desc_col = "description" if "description" in job_postings_clean.columns else None
    for _, row in job_postings_clean.iterrows():
        text = " ".join([
            str(row.get("title", "") or ""),
            str(row.get(desc_col, "") or "") if desc_col else "",
        ])
        for sk in extract_skills(text, taxonomy):
            skill_rows.append({"job_id": row["job_id"], "skill": sk, "role_family": row["role_family"]})
    job_skills = pd.DataFrame(skill_rows).drop_duplicates() if skill_rows else pd.DataFrame(
        columns=["job_id", "skill", "role_family"])

    # â”€â”€ Guardar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    job_postings_clean.to_csv(OUT_CUR / "job_postings_clean.csv", index=False, quoting=csv.QUOTE_NONNUMERIC)
    jobs_features.to_csv(OUT_SEM / "jobs_features.csv", index=False, quoting=csv.QUOTE_NONNUMERIC)
    job_skills.to_csv(OUT_CUR / "job_skills.csv", index=False, quoting=csv.QUOTE_NONNUMERIC)

    print(f"\n[OK] job_postings_clean : {len(job_postings_clean):,} filas")
    print(f"[OK] jobs_features      : {len(jobs_features):,} filas")
    print(f"[OK] job_skills         : {len(job_skills):,} filas")

    # â”€â”€ Role summary â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if "role_family" in jobs_features.columns:
        print("\n[ROLES] DistribuciÃ³n en jobs_features:")
        for role, cnt in jobs_features["role_family"].value_counts().items():
            print(f"  {role:<25} {cnt:>5}")

    # â”€â”€ Verificar URLs activas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("[INFO] Verificando ofertas antiguas en LinkedIn...")
    max_verify = None if args.max_verify_urls == 0 else args.max_verify_urls
    url_status = verify_job_urls(
        job_postings_clean,
        visible_days=args.visible_job_days,
        ttl_days=args.url_check_ttl_days,
        max_checks=max_verify,
    )
    job_postings_clean = merge_url_status(job_postings_clean, url_status)
    jobs_features = merge_url_status(jobs_features, url_status)
    job_postings_clean.to_csv(OUT_CUR / "job_postings_clean.csv", index=False, quoting=csv.QUOTE_NONNUMERIC)
    jobs_features.to_csv(OUT_SEM / "jobs_features.csv", index=False, quoting=csv.QUOTE_NONNUMERIC)
    # Sincronizar jobs_features con las ofertas que han sobrevivido la verificaciÃ³n
    if "job_url" in jobs_features.columns and "job_url" in job_postings_clean.columns:
        valid_urls = set(job_postings_clean["job_url"].dropna())
        jobs_features = jobs_features[jobs_features["job_url"].isin(valid_urls)].reset_index(drop=True)

    # â”€â”€ Enrich jobs_features_v2 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("[INFO] Enriqueciendo jobs_features_v2 (sector/seniority/mode)...")
    jobs_features_v2 = enrich_jobs(jobs_features)
    jobs_features_v2.to_csv(OUT_SEM / "jobs_features_v2.csv", index=False, quoting=csv.QUOTE_NONNUMERIC)
    print(f"[OK] jobs_features_v2   : {len(jobs_features_v2):,} filas")

    # â”€â”€ Recalcular role_skill_demand â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("[INFO] Recalculando role_skill_demand...")
    role_skill_demand = rebuild_role_skill_demand(job_skills)
    role_skill_demand.to_csv(OUT_SEM / "role_skill_demand.csv", index=False, quoting=csv.QUOTE_NONNUMERIC)
    print(f"[OK] role_skill_demand  : {len(role_skill_demand):,} filas")

    # â”€â”€ Upload â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if not args.no_upload:
        print("\n[UPLOAD] Subiendo a HuggingFace...")
        upload_to_hf([
            (OUT_SEM / "jobs_features.csv",       "outputs/semantic/jobs_features.csv"),
            (OUT_SEM / "jobs_features_v2.csv",    "outputs/semantic/jobs_features_v2.csv"),
            (OUT_SEM / "job_url_status.csv",      "outputs/semantic/job_url_status.csv"),
            (OUT_SEM / "role_skill_demand.csv",   "outputs/semantic/role_skill_demand.csv"),
            (OUT_CUR / "job_postings_clean.csv",  "outputs/curated/job_postings_clean.csv"),
            (OUT_CUR / "job_skills.csv",          "outputs/curated/job_skills.csv"),
        ])
        print("[DONE] Space actualizado.")
    else:
        print("\n[INFO] --no-upload activo: CSVs guardados localmente, no subidos.")


if __name__ == "__main__":
    main()
