"""
run_validation_500cvs.py
========================
Re-ejecuta la validación del parser y el estudio de ablación del recomendador
usando los 500 CVs del corpus ampliado (data/private/cv_cases/).

- Parser validation: combina las 88 anotaciones manuales existentes con
  auto-anotaciones extraídas de la sección HABILIDADES del PDF para los CVs nuevos.
- Ablación holdout 80/20: igual que antes pero con n=500 candidatos.

Salida (en docs/validation/outputs/):
  validation_500_parser_summary.json
  validation_500_parser_metrics.csv
  validation_500_ablation_results.json

Ejecutar desde la raíz del TFM:
  python docs/validation/scripts/run_validation_500cvs.py
"""

import csv
import importlib.util
import json
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pdfplumber

# ── Rutas ──────────────────────────────────────────────────────────────────────
ROOT         = Path(__file__).resolve().parents[3]
SCRIPT_DIR   = Path(__file__).resolve().parent
VALIDATION   = SCRIPT_DIR.parent
CV_DIR       = ROOT / "data" / "private" / "cv_cases"       # 500 CVs
OLD_CV_DIR   = VALIDATION / "cv_cases"                      # 88 CVs originales
OUT_DIR      = VALIDATION / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

APP_DIR      = ROOT / "app" / "caiq"
MODEL_PATH   = APP_DIR / "pipelines" / "build_datapath_model_advanced.py"
TAXONOMY_PATH = APP_DIR / "config" / "skills_taxonomy.json"
ETL_CURATED  = ROOT / "01_etl" / "outputs" / "curated"
ETL_SEMANTIC = ROOT / "01_etl" / "outputs" / "semantic"


# ── Anotaciones manuales originales (88 CVs) ──────────────────────────────────
MANUAL_EXPECTED = {
    "CV - Alba Sanchez.pdf": {"data analysis","data visualization"},
    "CV - Alejandro Ã_lvarez VÃ¡zquez.pdf": {"data analysis","data science","data visualization","etl","excel","power bi","python","sql","tableau"},
    "CV - Cristina Sanjuan .pdf": {"java","power bi","r"},
    "CV _Maria Gonzalez.pdf": {"mathematics"},
    "CV-Diego_Aguilar.pdf": {"aws","azure","big data","data analysis","data engineering","data science","data visualization","docker","etl","hadoop","java","kubernetes","machine learning","nosql","python","r","scikit_learn","spark","sql","statistics"},
    "CV_Ana Valverde.pdf": {"data analysis","data visualization","excel","power bi"},
    "CV_Carlota Palao.pdf": {"data analysis","data visualization","power bi"},
    "CV_Carmen Galán.pdf": set(),
    "CV_Gabriel Rezola.pdf": {"c++","data analysis","data visualization","excel","java","mathematics","power bi","r","sql","statistics"},
    "CV_Ignacio Relanzon.pdf": {"a/b testing","big data","data analysis","data engineering","data science","data visualization","etl","excel","power bi","python","r","sql","tableau"},
    "CV_IÑIGO_MARTINEZ.pdf": {"big data","data analysis","data engineering","data science","data visualization","excel","java","machine learning","mathematics","numpy","pandas","python","r","sas","sql","statistics","time series"},
    "CV_Maria_Rodriguez.pdf": {"aws","big data","data analysis","data science","data visualization","deep learning","generative ai","machine learning","nosql","power bi","python","r","scikit_learn","spark","sql","statistics","tensorflow"},
    "CV_Paulo_Gonzalez_ES.pdf": {"azure","data analysis","data engineering","data visualization","etl","excel","gcp","machine learning","power bi","python","r","sql","tableau"},
    "Pablo Merino.pdf": {"big data","data analysis","data science","data visualization","machine learning","mathematics","statistics"},
    "CV_SynthJunior_DataScientist_Madrid.pdf": {"python","pandas","numpy","scikit_learn","statistics","machine learning","data visualization","sql","git","excel","mathematics","data analysis"},
    "CV_SynthSenior_DataEngineer_Barcelona.pdf": {"python","sql","spark","hadoop","hdfs","hive","yarn","mapreduce","airflow","aws","azure","docker","kubernetes","etl","dbt","snowflake","databricks","scala","git","big data","data engineering","nosql","redshift"},
    "CV_SynthMid_MLEngineer_Bilbao.pdf": {"python","pytorch","tensorflow","keras","scikit_learn","xgboost","nlp","llm","deep learning","machine learning","computer vision","docker","aws","git","sql","feature engineering","time series","forecasting","generative ai","api"},
    "CV_SynthJunior_DataAnalyst_Valencia.pdf": {"power bi","tableau","sql","excel","python","pandas","data visualization","data analysis","statistics","etl"},
    "CV_SynthAtipico_Biologo_DataScientist_Sevilla.pdf": {"python","r","statistics","machine learning","nlp","scikit_learn","pandas","numpy","data analysis","data visualization","tableau","sql","mathematics","deep learning"},
    "CV_SynthAtipico_Economista_DataAnalyst_Madrid.pdf": {"excel","r","statistics","power bi","data visualization","data analysis","python","sql","mathematics","spss","time series","forecasting"},
    "CV_SynthSenior_DataScientist_PhD_Zaragoza.pdf": {"python","r","machine learning","deep learning","nlp","llm","pytorch","tensorflow","scikit_learn","xgboost","statistics","mathematics","feature engineering","a/b testing","time series","forecasting","sql","aws","docker","git","data science","generative ai"},
    "CV_SynthMid_DataEngineer_Malaga.pdf": {"python","sql","etl","azure","snowflake","dbt","talend","data engineering","git","docker","nosql","redshift","databricks","big data","microsoft fabric"},
    "CV_SynthJunior_MLEngineer_Granada.pdf": {"python","pytorch","tensorflow","keras","deep learning","computer vision","machine learning","scikit_learn","numpy","pandas","statistics","git","docker"},
    "CV_SynthAtipico_Telecom_DataEngineer_Valencia.pdf": {"python","java","scala","spark","hadoop","hdfs","yarn","big data","etl","data engineering","sql","nosql","docker","kubernetes","databricks","aws","git","api"},
    "CV_SynthSenior_DataAnalyst_Madrid.pdf": {"tableau","power bi","sql","r","statistics","data visualization","data analysis","excel","python","pandas","a/b testing","etl","redshift","sas","mathematics"},
    "CV_SynthMid_DataScientist_NLP_Barcelona.pdf": {"python","nlp","llm","deep learning","pytorch","tensorflow","machine learning","scikit_learn","generative ai","data science","sql","git","docker","aws","feature engineering","statistics"},
    "CV_SynthJunior_DataEngineer_Bootcamp_Bilbao.pdf": {"python","sql","etl","airflow","aws","spark","data engineering","git","docker","nosql","mathematics","statistics","pandas"},
    "CV_SynthAtipico_Profesor_DataAnalyst_Salamanca.pdf": {"r","statistics","mathematics","python","pandas","data analysis","power bi","data visualization","excel","sql"},
    "CV_SynthSenior_MLResearcher_Madrid.pdf": {"python","pytorch","tensorflow","deep learning","machine learning","computer vision","nlp","generative ai","scikit_learn","numpy","statistics","mathematics","spark","kubernetes","docker","aws","git","feature engineering","keras"},
    "CV_SynthAtipico_Medico_HealthDS_Santiago.pdf": {"r","statistics","mathematics","python","scikit_learn","xgboost","data analysis","data visualization","tableau","machine learning","pandas"},
    "CV_SynthMid_DataScientist_Forecasting_Bilbao.pdf": {"python","r","statistics","machine learning","deep learning","time series","forecasting","scikit_learn","xgboost","pandas","numpy","power bi","sql","data science","feature engineering","a/b testing","mathematics"},
    "CV_SynthJunior_DS_Autodidacta_Murcia.pdf": {"python","pandas","numpy","scikit_learn","machine learning","data visualization","data science","statistics","sql","git","docker","api","feature engineering","excel"},
    "CV_SynthCareerShift_FinanceML_Madrid.pdf": {"python","sql","statistics","machine learning","xgboost","pandas","numpy","data analysis","data visualization","power bi","a/b testing","forecasting"},
    "CV_SynthBIEngineer_Looker_Berlin.pdf": {"sql","looker","power bi","tableau","excel","etl","airflow","dbt","snowflake","redshift","data visualization","data analysis","python"},
    "CV_SynthMLOps_Remote.pdf": {"python","aws","azure","docker","kubernetes","api","git","machine learning","pytorch","tensorflow","airflow","databricks"},
    "CV_SynthResearch_NLP_Valencia.pdf": {"python","nlp","llm","generative ai","pytorch","tensorflow","deep learning","machine learning","statistics","sql","git"},
    "CV_SynthJunior_Analytics_Sevilla.pdf": {"excel","power bi","sql","python","pandas","data analysis","data visualization","statistics"},
    "CV_SynthDataEngineer_GCP_Lisbon.pdf": {"python","sql","spark","hadoop","hdfs","hive","yarn","airflow","gcp","etl","data engineering","dbt","big data","scala"},
    "CV_SynthHealth_Analyst_Barcelona.pdf": {"r","spss","statistics","sql","tableau","data analysis","data visualization","excel","python"},
    "CV_SynthMultiCloud_DS_Alicante.pdf": {"python","pandas","numpy","scikit_learn","machine learning","aws","azure","gcp","sql","data science","data analysis","feature engineering"},
    "CV_Synth_Junior_DS_Valladolid.pdf": {"python","scikit_learn","pytorch","numpy","pandas","machine learning","deep learning","computer vision","sql","git","statistics","mathematics"},
    "CV_Synth_Junior_DataAnalyst_Malaga.pdf": {"r","statistics","power bi","sql","python","pandas","data visualization","data analysis","excel","mathematics"},
    "CV_Synth_Junior_DE_Madrid.pdf": {"python","sql","etl","airflow","aws","docker","git","data engineering","nosql","pandas","api"},
    "CV_Synth_Junior_ML_Oviedo.pdf": {"python","pytorch","tensorflow","keras","deep learning","machine learning","time series","statistics","numpy","pandas","scikit_learn","git"},
    "CV_Synth_Junior_Analytics_Zaragoza.pdf": {"excel","power bi","python","pandas","data analysis","data visualization","statistics","sql","a/b testing"},
    "CV_Synth_Mid_DS_Logistica_Pamplona.pdf": {"python","scikit_learn","xgboost","machine learning","time series","forecasting","feature engineering","tableau","snowflake","sql","statistics","pandas","numpy","data science"},
    "CV_Synth_Mid_DE_Streaming_Madrid.pdf": {"python","spark","kafka","hadoop","airflow","aws","azure","databricks","snowflake","etl","data engineering","sql","nosql","docker","kubernetes","scala","git"},
    "CV_Synth_Mid_CV_Engineer_Barcelona.pdf": {"python","pytorch","tensorflow","keras","deep learning","computer vision","machine learning","numpy","docker","git","statistics","feature engineering","generative ai"},
    "CV_Synth_Mid_BI_Analyst_Bilbao.pdf": {"power bi","tableau","sql","dbt","snowflake","azure","etl","data visualization","data analysis","excel","python","statistics","data engineering"},
    "CV_Synth_Mid_NLP_Researcher_Madrid.pdf": {"python","nlp","llm","generative ai","pytorch","tensorflow","machine learning","deep learning","scikit_learn","statistics","sql","git","docker","api","feature engineering"},
    "CV_Synth_Mid_Quant_DS_Madrid.pdf": {"python","scikit_learn","xgboost","machine learning","statistics","mathematics","a/b testing","feature engineering","sql","pandas","numpy","deep learning","api","time series","forecasting","data science"},
    "CV_Synth_Senior_DE_GCP_Valencia.pdf": {"python","sql","spark","hadoop","gcp","airflow","dbt","etl","data engineering","big data","scala","docker","kubernetes","git","nosql","databricks"},
    "CV_Synth_Senior_DS_Retail_Sevilla.pdf": {"python","pytorch","scikit_learn","xgboost","machine learning","deep learning","statistics","sql","feature engineering","a/b testing","time series","forecasting","data science","pandas","numpy","mathematics"},
    "CV_Synth_Senior_MLE_Remoto.pdf": {"python","pytorch","tensorflow","machine learning","deep learning","nlp","llm","docker","kubernetes","aws","azure","git","airflow","databricks","api","feature engineering","scikit_learn"},
    "CV_Synth_Senior_Analytics_Eng_Madrid.pdf": {"sql","dbt","python","looker","tableau","power bi","redshift","snowflake","data analysis","data visualization","etl","statistics","git","data engineering"},
    "CV_Synth_Senior_DataArch_Barcelona.pdf": {"python","sql","spark","databricks","azure","aws","gcp","docker","kubernetes","etl","dbt","snowflake","big data","data engineering","hadoop","nosql","scala","git","microsoft fabric"},
    "CV_Synth_Atipico_Periodista_DA_Madrid.pdf": {"python","r","statistics","data visualization","data analysis","excel","sql","mathematics"},
    "CV_Synth_Atipico_Arquitecto_DE_Bilbao.pdf": {"python","sql","etl","airflow","aws","kafka","spark","docker","kubernetes","git","data engineering","nosql","redshift","dbt","api","java"},
    "CV_Synth_Atipico_Farmaceutico_DS_Granada.pdf": {"python","r","statistics","scikit_learn","xgboost","machine learning","data analysis","data visualization","tableau","sql","pandas","mathematics"},
    "CV_Synth_Atipico_Psicologo_DS_Madrid.pdf": {"r","statistics","mathematics","python","pandas","data analysis","data visualization","power bi","spss","sql","a/b testing"},
    "CV_Synth_Atipico_Quimico_DE_Tarragona.pdf": {"python","sql","spark","kafka","etl","data engineering","azure","snowflake","dbt","nosql","docker","git","big data"},
    "CV_Synth_Atipico_Musico_DS_Valencia.pdf": {"python","scikit_learn","pytorch","machine learning","statistics","mathematics","numpy","pandas","sql","feature engineering","data analysis"},
    "CV_Synth_Atipico_Juridico_DataAnalyst_Madrid.pdf": {"python","nlp","sql","power bi","data analysis","data visualization","statistics","pandas"},
    "CV_Synth_Atipico_Veterinario_DA_Santiago.pdf": {"r","statistics","mathematics","data analysis","data visualization","python","sql","excel","pandas"},
    "CV_Synth_Atipico_RRHH_PeopleAnalytics_Madrid.pdf": {"python","pandas","scikit_learn","machine learning","power bi","data analysis","data visualization","statistics","sql","excel"},
    "CV_Synth_Senior_DS_Erasmus_Berlin.pdf": {"python","pytorch","tensorflow","machine learning","deep learning","statistics","mathematics","aws","docker","kubernetes","git","nlp","feature engineering","time series","forecasting","data science"},
    "CV_Synth_Mid_DS_Latam_Madrid.pdf": {"python","scikit_learn","xgboost","machine learning","statistics","mathematics","sql","pandas","numpy","feature engineering","data analysis","data visualization","tableau","a/b testing"},
    "CV_Synth_Junior_DS_Erasmus_Paris.pdf": {"python","r","statistics","mathematics","machine learning","scikit_learn","deep learning","pytorch","pandas","numpy","sql","git"},
    "CV_Synth_DataGovernance_Specialist_Madrid.pdf": {"sql","python","data analysis","statistics","etl","informatica","excel","data engineering"},
    "CV_Synth_MLOps_Engineer_Madrid.pdf": {"python","docker","kubernetes","aws","azure","airflow","databricks","git","machine learning","pytorch","tensorflow","api","data engineering","sql"},
    "CV_Synth_DataScience_Salud_Madrid.pdf": {"python","r","pytorch","tensorflow","scikit_learn","xgboost","machine learning","deep learning","computer vision","statistics","mathematics","sql","pandas","numpy","data science","data analysis"},
    "CV_Synth_DataSci_Energia_Bilbao.pdf": {"python","machine learning","deep learning","time series","forecasting","pytorch","scikit_learn","xgboost","statistics","mathematics","spark","kafka","sql","data science","feature engineering","pandas"},
    "CV_Synth_Junior_Bioinf_Barcelona.pdf": {"python","r","statistics","mathematics","machine learning","scikit_learn","pandas","numpy","data analysis","data visualization","sql","git"},
    "CV_Synth_Senior_DS_Telecomunicaciones_Madrid.pdf": {"python","scikit_learn","xgboost","pytorch","machine learning","deep learning","statistics","sql","feature engineering","a/b testing","time series","data science","pandas","numpy","aws","docker"},
    "CV_Synth_Mid_DataEng_Azure_Galicia.pdf": {"python","sql","etl","azure","databricks","dbt","data engineering","docker","git","nosql","snowflake","power bi","microsoft fabric"},
    "CV_Synth_Senior_Scientist_Agronomia_Cordoba.pdf": {"python","scikit_learn","xgboost","machine learning","computer vision","deep learning","time series","forecasting","statistics","mathematics","r","sql","pandas","numpy","data science"},
    "CV_Synth_DS_Turismo_Palma.pdf": {"python","scikit_learn","xgboost","machine learning","time series","forecasting","statistics","sql","tableau","data visualization","data analysis","pandas","a/b testing"},
    "CV_Synth_Ecommerce_DS_Barcelona.pdf": {"python","machine learning","scikit_learn","xgboost","statistics","sql","a/b testing","feature engineering","data science","data analysis","pandas","numpy","tableau","gcp"},
    "CV_Synth_Junior_Geoespacial_DS_Pamplona.pdf": {"python","pandas","scikit_learn","machine learning","statistics","sql","data analysis","data visualization","mathematics"},
    "CV_Synth_Senior_DE_Fintech_Madrid.pdf": {"python","sql","spark","kafka","hadoop","aws","etl","data engineering","nosql","docker","kubernetes","scala","git","airflow","redshift","big data"},
    "CV_Synth_Mid_MLResearch_NLP_Madrid.pdf": {"python","nlp","llm","pytorch","tensorflow","deep learning","machine learning","generative ai","statistics","sql","git","feature engineering","scikit_learn"},
    "CV_Synth_Senior_Analytics_Pharma_Madrid.pdf": {"r","sas","statistics","mathematics","python","scikit_learn","machine learning","data analysis","data visualization","tableau","sql","spss","excel"},
    "CV_Synth_DataEng_Snowflake_Madrid.pdf": {"python","sql","snowflake","dbt","etl","airflow","data engineering","git","docker","aws","azure","redshift","databricks","microsoft fabric"},
    "CV_Synth_IA_Generativa_Specialist_Barcelona.pdf": {"python","nlp","llm","generative ai","pytorch","machine learning","deep learning","aws","docker","kubernetes","git","api","feature engineering","statistics"},
    "CV_Synth_Mid_Forecasting_Retail_Zaragoza.pdf": {"python","r","statistics","mathematics","machine learning","time series","forecasting","scikit_learn","xgboost","pandas","numpy","sql","airflow","feature engineering","data science"},
    "CV_Synth_Junior_IA_Generativa_Sevilla.pdf": {"python","nlp","llm","generative ai","pytorch","deep learning","machine learning","scikit_learn","sql","git","docker"},
    "CV_Synth_Senior_DataEng_Spark_Madrid.pdf": {"python","sql","spark","hadoop","hdfs","hive","yarn","mapreduce","airflow","aws","azure","databricks","etl","data engineering","big data","scala","nosql","docker","kubernetes","git"},
    "CV_Synth_Data_Product_Manager_Barcelona.pdf": {"sql","tableau","python","pandas","statistics","data analysis","data visualization","power bi","excel","a/b testing"},
}


# ── Taxonomía: alias → skill canónico ─────────────────────────────────────────
def build_alias_map(taxonomy: dict) -> dict[str, str]:
    """Devuelve {alias_normalizado: skill_canonico}."""
    alias_map: dict[str, str] = {}
    for skill, aliases in taxonomy.items():
        canon = skill.strip().lower()
        alias_map[canon] = canon
        for alias in (aliases or []):
            alias_map[alias.strip().lower()] = canon
    return alias_map


def norm(text: str) -> str:
    text = str(text or "").lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.strip()


def extract_skills_from_text_section(text: str, alias_map: dict[str, str]) -> set[str]:
    """
    Extrae skills de la sección HABILIDADES/SKILLS del PDF
    buscando coincidencias con los alias de la taxonomía.
    """
    found: set[str] = set()
    text_norm = norm(text)

    # Primero extraer la sección de habilidades
    # NOTA: el cabecero de cada patrón se marca como case-insensitive con
    # (?i:...) de forma localizada, pero el resto del patrón (incluido el
    # terminador "\n[A-ZÁÉÍÓÚÑ]{4,}" que detecta el INICIO de la siguiente
    # sección) se mantiene sensible a mayúsculas. Si se aplicara
    # re.IGNORECASE de forma global, ese terminador también haría match con
    # líneas separadoras compuestas por minúsculas repetidas (p.ej. "nnnn...n",
    # un artefacto de extracción de pdfplumber), cortando la sección de
    # habilidades justo después del título y dejando "found" prácticamente
    # vacío.
    patterns = [
        r"(?i:habilidades?\s+t[eé]cnicas?)(.*?)(?:\n[A-ZÁÉÍÓÚÑ]{4,}|\Z)",
        r"(?i:skills?\s+t[eé]cnicas?)(.*?)(?:\n[A-ZÁÉÍÓÚÑ]{4,}|\Z)",
        r"(?i:competencias?\s+t[eé]cnicas?)(.*?)(?:\n[A-ZÁÉÍÓÚÑ]{4,}|\Z)",
        r"(?i:habilidades?)(.*?)(?:\n[A-ZÁÉÍÓÚÑ]{4,}|\Z)",
        r"(?i:skills?)(.*?)(?:\n[A-ZÁÉÍÓÚÑ]{4,}|\Z)",
    ]

    section_text = text  # Fallback: usar todo el texto si no se encuentra sección
    for pattern in patterns:
        m = re.search(pattern, text, re.DOTALL)
        if m:
            section_text = m.group(0)
            break

    section_norm = norm(section_text)

    # Buscar cada alias en el texto de la sección
    for alias, canon in alias_map.items():
        if len(alias) < 2:
            continue
        # Búsqueda con word boundaries aproximada
        alias_esc = re.escape(alias)
        if re.search(r'(?<![a-z0-9])' + alias_esc + r'(?![a-z0-9])', section_norm):
            found.add(canon)

    return found


def read_pdf_text(pdf_path: Path) -> str:
    try:
        with pdfplumber.open(str(pdf_path)) as doc:
            return "\n".join(page.extract_text() or "" for page in doc.pages)
    except Exception:
        return ""


def canonical_filename(name: str) -> str:
    txt = str(name or "").lower().strip()
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", txt)


# ── Módulo de modelo ───────────────────────────────────────────────────────────
def load_model_module():
    spec = importlib.util.spec_from_file_location("caiq_model", MODEL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


# ── Métricas ──────────────────────────────────────────────────────────────────
def safe_div(a, b):
    return a / b if b else 0.0


# ═══════════════════════════════════════════════════════════════════════════════
#  PARTE 1: PARSER VALIDATION (precisión / recall / F1)
# ═══════════════════════════════════════════════════════════════════════════════
def run_parser_validation(taxonomy: dict, model_mod) -> dict:
    print("\n" + "="*60)
    print("PARTE 1: VALIDACIÓN DEL PARSER (500 CVs)")
    print("="*60)

    alias_map = build_alias_map(taxonomy)
    manual_canon = {canonical_filename(k): {s.lower() for s in v}
                    for k, v in MANUAL_EXPECTED.items()}

    pdf_files = sorted(CV_DIR.glob("*.pdf"))
    rows = []
    n_auto = 0

    for pdf in pdf_files:
        canon_name = canonical_filename(pdf.name)

        # ── Determinar expected skills ──────────────────────────────────────
        if canon_name in manual_canon:
            expected = manual_canon[canon_name]
            annotation = "manual"
        else:
            # Auto-anotación: extraer de sección HABILIDADES del PDF
            raw_text = read_pdf_text(pdf)
            expected = extract_skills_from_text_section(raw_text, alias_map)
            annotation = "auto"
            n_auto += 1

        # ── Ejecutar parser ─────────────────────────────────────────────────
        try:
            with pdfplumber.open(str(pdf)) as doc:
                text = "\n".join(page.extract_text() or "" for page in doc.pages)
        except Exception as e:
            rows.append({
                "cv_file": pdf.name, "status": "error", "annotation": annotation,
                "expected_n": len(expected), "detected_n": 0,
                "tp": 0, "fp": 0, "fn": len(expected),
                "precision": 0.0, "recall": 0.0, "f1": 0.0,
                "expected_skills": "; ".join(sorted(expected)),
                "detected_skills": "", "false_positives": "",
                "false_negatives": "; ".join(sorted(expected)),
                "notes": f"PDF read error: {e}"
            })
            continue

        if not text.strip():
            rows.append({
                "cv_file": pdf.name, "status": "excluded_empty_text", "annotation": annotation,
                "expected_n": len(expected), "detected_n": 0,
                "tp": 0, "fp": 0, "fn": len(expected),
                "precision": 0.0, "recall": 0.0, "f1": 0.0,
                "expected_skills": "; ".join(sorted(expected)),
                "detected_skills": "", "false_positives": "",
                "false_negatives": "; ".join(sorted(expected)),
                "notes": "PDF text extraction returned empty content; excluded."
            })
            continue

        profile = model_mod.build_candidate_profile_hybrid(text, taxonomy)
        detected = {s.strip().lower() for s in profile.get("skills_detected", []) if s.strip()}

        # Para auto-anotados: los expected ya son skills del taxonomy; restringir detected igual
        tp_set = expected & detected
        fp_set = detected - expected if expected else set()  # Si no hay expected, no hay FP medible
        fn_set = expected - detected

        # Si no hay expected skills (e.g. CV no técnico), no medir precisión
        if not expected:
            rows.append({
                "cv_file": pdf.name, "status": "no_expected_skills", "annotation": annotation,
                "expected_n": 0, "detected_n": len(detected),
                "tp": 0, "fp": len(detected), "fn": 0,
                "precision": 0.0, "recall": 1.0, "f1": 0.0,
                "expected_skills": "",
                "detected_skills": "; ".join(sorted(detected)),
                "false_positives": "; ".join(sorted(detected)),
                "false_negatives": "",
                "notes": "No expected skills defined for this CV (non-technical profile or unannotated)."
            })
            continue

        precision = safe_div(len(tp_set), len(tp_set) + len(fp_set))
        recall    = safe_div(len(tp_set), len(tp_set) + len(fn_set))
        f1        = safe_div(2 * precision * recall, precision + recall)

        rows.append({
            "cv_file": pdf.name, "status": "evaluated", "annotation": annotation,
            "expected_n": len(expected), "detected_n": len(detected),
            "tp": len(tp_set), "fp": len(fp_set), "fn": len(fn_set),
            "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4),
            "expected_skills": "; ".join(sorted(expected)),
            "detected_skills": "; ".join(sorted(detected)),
            "false_positives": "; ".join(sorted(fp_set)),
            "false_negatives": "; ".join(sorted(fn_set)),
            "notes": ""
        })

    # ── Guardar CSV ─────────────────────────────────────────────────────────
    out_csv = OUT_DIR / "validation_500_parser_metrics.csv"
    with out_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # ── Calcular métricas agregadas ──────────────────────────────────────────
    eval_rows  = [r for r in rows if r["status"] == "evaluated"]
    manual_rows = [r for r in eval_rows if r["annotation"] == "manual"]
    auto_rows   = [r for r in eval_rows if r["annotation"] == "auto"]

    def micro_metrics(rlist):
        tp = sum(int(r["tp"]) for r in rlist)
        fp = sum(int(r["fp"]) for r in rlist)
        fn = sum(int(r["fn"]) for r in rlist)
        p  = safe_div(tp, tp + fp)
        r_ = safe_div(tp, tp + fn)
        f  = safe_div(2 * p * r_, p + r_)
        return tp, fp, fn, round(p, 4), round(r_, 4), round(f, 4)

    def macro_metrics(rlist):
        p  = sum(float(r["precision"]) for r in rlist) / max(len(rlist), 1)
        r_ = sum(float(r["recall"])    for r in rlist) / max(len(rlist), 1)
        f  = sum(float(r["f1"])        for r in rlist) / max(len(rlist), 1)
        return round(p, 4), round(r_, 4), round(f, 4)

    tp_all, fp_all, fn_all, mp_all, mr_all, mf_all = micro_metrics(eval_rows)
    mp_mac, mr_mac, mf_mac = macro_metrics(eval_rows)

    # Métricas sólo sobre los 88 manuales (para comparar con baseline)
    tp_m, fp_m, fn_m, mp_m, mr_m, mf_m = micro_metrics(manual_rows)

    summary = {
        "n_pdf_files": len(rows),
        "n_evaluated": len(eval_rows),
        "n_manual_annotation": len(manual_rows),
        "n_auto_annotation": len(auto_rows),
        "n_excluded_empty_text": len([r for r in rows if r["status"] == "excluded_empty_text"]),
        "n_no_expected_skills": len([r for r in rows if r["status"] == "no_expected_skills"]),
        "excluded_files": [r["cv_file"] for r in rows if r["status"] != "evaluated"],
        # Métricas globales (500 CVs)
        "global": {
            "total_tp": tp_all, "total_fp": fp_all, "total_fn": fn_all,
            "micro_precision": mp_all, "micro_recall": mr_all, "micro_f1": mf_all,
            "macro_precision": mp_mac, "macro_recall": mr_mac, "macro_f1": mf_mac,
            "mean_expected_skills": round(sum(int(r["expected_n"]) for r in eval_rows) / max(len(eval_rows), 1), 2),
            "mean_detected_skills": round(sum(int(r["detected_n"]) for r in eval_rows) / max(len(eval_rows), 1), 2),
        },
        # Métricas sobre anotaciones manuales (para compatibilidad con baseline)
        "manual_only": {
            "n": len(manual_rows),
            "total_tp": tp_m, "total_fp": fp_m, "total_fn": fn_m,
            "micro_precision": mp_m, "micro_recall": mr_m, "micro_f1": mf_m,
        },
        "annotation_policy": (
            "88 CVs with manual reference labels; "
            f"{n_auto} CVs with auto-extracted labels from HABILIDADES section mapped to taxonomy. "
            "Empty-text PDFs excluded from aggregates."
        ),
    }

    out_json = OUT_DIR / "validation_500_parser_summary.json"
    out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


# ═══════════════════════════════════════════════════════════════════════════════
#  PARTE 2: ABLACIÓN HOLDOUT 80/20 (recomendador)
# ═══════════════════════════════════════════════════════════════════════════════
def run_ablation(taxonomy: dict, model_mod) -> dict:
    print("\n" + "="*60)
    print("PARTE 2: ABLACIÓN HOLDOUT 80/20 (500 CVs)")
    print("="*60)

    import pandas as pd

    # Cargar datos ETL para el recomendador
    try:
        masters_feat = pd.read_csv(ETL_SEMANTIC / "masters_features.csv")
        courses_feat = pd.read_csv(ETL_SEMANTIC / "courses_features.csv")
        role_skill   = pd.read_csv(ETL_SEMANTIC / "role_skill_demand.csv")
        master_sk    = pd.read_csv(ETL_CURATED  / "master_skills.csv")
        course_sk    = pd.read_csv(ETL_CURATED  / "course_skills.csv")
    except FileNotFoundError as e:
        print(f"ERROR: No se encontraron datos ETL: {e}")
        print("Saltando ablación.")
        return {}

    rec_fn = model_mod.recommend_learning_path

    # Variantes a evaluar
    VARIANTS = [
        ("coverage_only",   1.00, 0.00),
        ("hybrid_tuned",    0.65, 0.35),
        ("balanced_50_50",  0.50, 0.50),
        ("semantic_only",   0.00, 1.00),
    ]

    # Parsear todos los CVs y obtener skills
    print("Parseando CVs...")
    pdf_files = sorted(CV_DIR.glob("*.pdf"))
    candidates = []  # [(cv_id, skills_set)]

    for i, pdf in enumerate(pdf_files):
        try:
            with pdfplumber.open(str(pdf)) as doc:
                text = "\n".join(page.extract_text() or "" for page in doc.pages)
        except Exception:
            continue
        if not text.strip():
            continue
        profile = model_mod.build_candidate_profile_hybrid(text, taxonomy)
        skills = {s.strip().lower() for s in profile.get("skills_detected", []) if s.strip()}
        role   = str(profile.get("detected_best_role", "data_scientist") or "data_scientist")
        if len(skills) >= 5:
            candidates.append((i, role, skills))

    print(f"CVs válidos (≥5 skills): {len(candidates)}")

    # Evaluar cada variante
    results = {}
    for variant_name, wc, ws in VARIANTS:
        recalls, gaps = [], []
        for cid, role, sk in candidates:
            ordered = sorted(sk)
            rng_cand = np.random.default_rng(cid)
            rng_cand.shuffle(ordered)
            holdout_n = max(1, int(round(0.2 * len(ordered))))
            holdout  = set(ordered[:holdout_n])
            observed = set(ordered[holdout_n:])

            try:
                rec = rec_fn(
                    candidate_skills=observed,
                    target_role=role,
                    role_skill_demand=role_skill,
                    masters_feat=masters_feat,
                    master_skills=master_sk,
                    courses_feat=courses_feat,
                    course_skills=course_sk,
                    filters={},
                    weight_coverage=wc,
                    weight_semantic=ws,
                )
            except Exception as e:
                continue

            recall      = len(holdout & set(rec.get("final_skill_set", []))) / max(len(holdout), 1)
            gap_before  = len(rec.get("gap_skills", []))
            gap_after   = len(rec.get("remaining_gap", []))
            gap_red     = (gap_before - gap_after) / max(gap_before, 1)
            recalls.append(recall)
            gaps.append(gap_red)

        if recalls:
            avg_r = float(np.mean(recalls))
            avg_g = float(np.mean(gaps))
            results[variant_name] = {
                "weight_coverage": wc,
                "weight_semantic": ws,
                "n_candidates": len(recalls),
                "avg_recall_holdout": round(avg_r, 4),
                "avg_gap_reduction": round(avg_g, 4),
                "objective": round(0.6 * avg_r + 0.4 * avg_g, 4),
            }
            print(f"  {variant_name:20s}  recall={avg_r:.3f}  gap_red={avg_g:.3f}  obj={0.6*avg_r+0.4*avg_g:.3f}  n={len(recalls)}")

    out_json = OUT_DIR / "validation_500_ablation_results.json"
    out_json.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nAblación guardada en: {out_json}")
    return results


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    print("Cargando taxonomía y módulo del modelo...")
    taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    sys.path.insert(0, str(APP_DIR / "pipelines"))
    model_mod = load_model_module()
    print(f"Taxonomía: {len(taxonomy)} skills | CVs en corpus: {len(list(CV_DIR.glob('*.pdf')))}")

    parser_summary = run_parser_validation(taxonomy, model_mod)
    ablation_results = run_ablation(taxonomy, model_mod)

    print("\n" + "="*60)
    print("RESUMEN FINAL")
    print("="*60)
    if parser_summary:
        g = parser_summary.get("global", {})
        print(f"Parser  — n={parser_summary['n_evaluated']}  "
              f"micro_P={g.get('micro_precision')}  "
              f"micro_R={g.get('micro_recall')}  "
              f"micro_F1={g.get('micro_f1')}")
    if ablation_results:
        for v, m in ablation_results.items():
            print(f"Ablación {v:20s} — recall={m['avg_recall_holdout']}  "
                  f"gap_red={m['avg_gap_reduction']}  "
                  f"obj={m['objective']}  n={m['n_candidates']}")


if __name__ == "__main__":
    main()
