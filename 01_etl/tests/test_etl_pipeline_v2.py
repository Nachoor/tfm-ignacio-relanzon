"""
test_etl_pipeline_v2.py
Tests de integración del pipeline ETL de CAIQ.

Uso:
    python test_etl_pipeline_v2.py [--out-dir PATH]

El directorio de salida se resuelve en este orden de prioridad:
  1. Argumento --out-dir
  2. Variable de entorno CAIQ_ETL_DIR
  3. Ruta relativa al propio script: ../../outputs  (funciona en cualquier máquina)
"""
import argparse
import json
import os
from pathlib import Path

import pandas as pd


def resolve_out_dir(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    if os.environ.get("CAIQ_ETL_DIR"):
        return Path(os.environ["CAIQ_ETL_DIR"])
    # Fallback: dos niveles arriba del directorio tests/
    return Path(__file__).resolve().parents[1] / "outputs"


def assert_file(path: Path):
    assert path.exists(), f"Archivo esperado no encontrado: {path}"


def assert_cols(path: Path, cols: list[str]):
    df = pd.read_csv(path, nrows=3)
    missing = [c for c in cols if c not in df.columns]
    assert not missing, f"{path.name} — columnas faltantes: {missing}"


def main():
    ap = argparse.ArgumentParser(description="Tests de integración ETL de CAIQ")
    ap.add_argument(
        "--out-dir",
        default=None,
        help="Directorio raíz de outputs del ETL (sobreescribe CAIQ_ETL_DIR y la ruta relativa por defecto)",
    )
    args = ap.parse_args()
    OUT = resolve_out_dir(args.out_dir)
    print(f"Directorio de outputs: {OUT}")

    # ── Existencia de archivos ────────────────────────────────────────────────
    expected_files = [
        "candidate_profile.csv",
        "candidate_skills.csv",
        "job_postings_clean.csv",
        "job_skills.csv",
        "role_skill_demand.csv",
        "masters_catalog_clean.csv",
        "master_skills.csv",
        "courses_catalog_clean.csv",
        "course_skills.csv",
        "dim_skills.csv",
        "etl_report_v2.json",
    ]
    for name in expected_files:
        assert_file(OUT / name)

    # ── Columnas mínimas por archivo ─────────────────────────────────────────
    assert_cols(OUT / "candidate_profile.csv",    ["candidate_id", "job_position_name"])
    assert_cols(OUT / "candidate_skills.csv",     ["candidate_id", "skill"])
    assert_cols(OUT / "job_postings_clean.csv",   ["job_id", "title", "description", "role_family"])
    assert_cols(OUT / "job_skills.csv",           ["job_id", "skill", "role_family"])
    assert_cols(OUT / "masters_catalog_clean.csv",["master_id", "program_name", "url", "study_content"])
    assert_cols(OUT / "master_skills.csv",        ["master_id", "skill"])
    assert_cols(OUT / "courses_catalog_clean.csv",["course_id", "title", "url"])
    assert_cols(OUT / "course_skills.csv",        ["course_id", "skill"])
    assert_cols(OUT / "dim_skills.csv",           ["skill_id", "skill"])

    # ── Sanity check del reporte ETL ─────────────────────────────────────────
    report = json.loads((OUT / "etl_report_v2.json").read_text(encoding="utf-8"))
    assert report.get("dim_skills_rows", 0) >= 20, \
        f"dim_skills_rows demasiado bajo: {report.get('dim_skills_rows')}"

    print("✅ ETL v2 — todos los tests pasados correctamente")


if __name__ == "__main__":
    main()
