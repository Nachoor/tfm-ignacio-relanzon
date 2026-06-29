"""Safe update flow for course prices (no data loss).

Steps:
1) Create timestamped backups of key files.
2) Merge source CSV prices into manual master CSV without overwriting valid prices.
3) Emit update report.

Usage:
  python pipelines/safe_price_update.py
Env:
  SRC_FILE=course_prices_manual_priority.csv
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import shutil

import os
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
SEM_DIR = BASE_DIR / "outputs" / "semantic"
BACKUP_DIR = BASE_DIR / "outputs" / "backups"

MANUAL = SEM_DIR / "course_prices_manual.csv"
SOURCE = SEM_DIR / os.getenv("SRC_FILE", "course_prices_manual_priority.csv")
COURSES = SEM_DIR / "courses_features.csv"
REPORT = SEM_DIR / "course_prices_update_report.csv"


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


def valid_price_text(txt: str) -> bool:
    v = parse_price_token(txt)
    return v is not None and 5 <= float(v) <= 50000


def backup_files(files: list[Path]) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bdir = BACKUP_DIR / f"price_update_{ts}"
    bdir.mkdir(parents=True, exist_ok=True)
    for f in files:
        if f.exists():
            shutil.copy2(f, bdir / f.name)
    return str(bdir)


def ensure_cols(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c not in out.columns:
            out[c] = ""
    return out


def main() -> None:
    if not MANUAL.exists():
        raise FileNotFoundError(f"Manual file missing: {MANUAL}")
    if not SOURCE.exists():
        raise FileNotFoundError(f"Source file missing: {SOURCE}")

    backup_path = backup_files([MANUAL, SOURCE, COURSES])
    print(f"backup={backup_path}")

    man = pd.read_csv(MANUAL)
    src = pd.read_csv(SOURCE)

    man = ensure_cols(man, ["course_id", "PRIC", "PRIC_SOURCE", "PRIC_CONFIDENCE"])
    src = ensure_cols(src, ["course_id", "PRIC", "PRIC_SOURCE", "PRIC_CONFIDENCE"])

    man["course_id"] = pd.to_numeric(man["course_id"], errors="coerce").astype("Int64")
    src["course_id"] = pd.to_numeric(src["course_id"], errors="coerce").astype("Int64")
    man = man.dropna(subset=["course_id"]).copy()
    src = src.dropna(subset=["course_id"]).copy()

    src = src.drop_duplicates(subset=["course_id"], keep="first")
    man_idx = {int(cid): i for i, cid in enumerate(man["course_id"].tolist())}

    updates = []
    inserted = 0
    filled = 0
    skipped_existing = 0
    skipped_invalid = 0

    for _, r in src.iterrows():
        cid = int(r["course_id"])
        s_pric = str(r.get("PRIC", "") or "").strip()
        s_source = str(r.get("PRIC_SOURCE", "manual_import") or "manual_import").strip()
        s_conf = r.get("PRIC_CONFIDENCE", 1.0)

        if not valid_price_text(s_pric):
            skipped_invalid += 1
            updates.append({"course_id": cid, "action": "skip_invalid_source", "source_pric": s_pric})
            continue

        if cid in man_idx:
            i = man_idx[cid]
            m_pric = str(man.at[i, "PRIC"] if "PRIC" in man.columns else "").strip()
            if valid_price_text(m_pric):
                skipped_existing += 1
                updates.append({"course_id": cid, "action": "skip_existing_valid", "manual_pric": m_pric, "source_pric": s_pric})
                continue
            man.at[i, "PRIC"] = s_pric
            man.at[i, "PRIC_SOURCE"] = s_source
            man.at[i, "PRIC_CONFIDENCE"] = s_conf
            filled += 1
            updates.append({"course_id": cid, "action": "filled_missing", "source_pric": s_pric})
        else:
            man = pd.concat(
                [
                    man,
                    pd.DataFrame([{
                        "course_id": cid,
                        "PRIC": s_pric,
                        "PRIC_SOURCE": s_source,
                        "PRIC_CONFIDENCE": s_conf,
                    }]),
                ],
                ignore_index=True,
            )
            inserted += 1
            updates.append({"course_id": cid, "action": "inserted_new", "source_pric": s_pric})

    man.to_csv(MANUAL, index=False, encoding="utf-8")
    pd.DataFrame(updates).to_csv(REPORT, index=False, encoding="utf-8")

    valid_after = int(man["PRIC"].astype(str).map(valid_price_text).sum())
    print(f"manual_saved={MANUAL}")
    print(f"report_saved={REPORT}")
    print(f"filled={filled} inserted={inserted} skipped_existing={skipped_existing} skipped_invalid={skipped_invalid}")
    print(f"valid_prices_after={valid_after}")


if __name__ == "__main__":
    main()

