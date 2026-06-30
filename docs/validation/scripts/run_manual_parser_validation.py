import csv
import importlib.util
import json
import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP_DIR = ROOT / "app" / "caiq"
MODEL_PATH = APP_DIR / "pipelines" / "build_datapath_model_advanced.py"
TAXONOMY_PATH = APP_DIR / "config" / "skills_taxonomy.json"
VALIDATION_DIR = Path(__file__).resolve().parents[1]
CV_DIR = VALIDATION_DIR / "cv_cases"
OUT_DIR = VALIDATION_DIR / "outputs"

EXPECTED_SKILLS = {
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


def load_model_module():
    spec = importlib.util.spec_from_file_location("caiq_model", MODEL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def canonical_set(skills):
    return {s.strip().lower() for s in skills if s.strip()}


def safe_div(a, b):
    return a / b if b else 0.0


def _repair_mojibake(text):
    cur = str(text or "")
    for _ in range(2):
        try:
            repaired = cur.encode("latin-1").decode("utf-8")
        except Exception:
            break
        if repaired == cur:
            break
        cur = repaired
    return cur


def canonical_filename(name):
    txt = _repair_mojibake(str(name or "")).strip().lower()
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
    txt = re.sub(r"\s+", " ", txt)
    return txt


def filename_tokens(name):
    txt = canonical_filename(name)
    toks = set(re.findall(r"[a-z0-9]+", txt))
    return {t for t in toks if len(t) >= 3}


def lookup_expected_skills(pdf_name, expected_map, expected_token_map):
    canon = canonical_filename(pdf_name)
    if canon in expected_map:
        return expected_map[canon]
    pdf_tokens = filename_tokens(pdf_name)
    best_key, best_overlap = None, 0
    for key, key_tokens in expected_token_map.items():
        overlap = len(pdf_tokens & key_tokens)
        if overlap > best_overlap:
            best_overlap = overlap
            best_key = key
    if best_key and best_overlap >= 2:
        return expected_map[best_key]
    return set()


def main():
    import pdfplumber

    mod = load_model_module()
    taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    expected_by_file = {canonical_filename(k): canonical_set(v) for k, v in EXPECTED_SKILLS.items()}
    expected_tokens = {canonical_filename(k): filename_tokens(k) for k in EXPECTED_SKILLS}

    pdf_files = sorted(CV_DIR.glob("*.pdf"))
    rows = []

    for pdf in pdf_files:
        expected = lookup_expected_skills(pdf.name, expected_by_file, expected_tokens)

        try:
            with pdfplumber.open(str(pdf)) as doc:
                text = "\n".join(page.extract_text() or "" for page in doc.pages)
        except Exception as e:
            rows.append({"cv_file": pdf.name, "status": "error",
                         "expected_n": len(expected), "detected_n": 0,
                         "tp": 0, "fp": 0, "fn": len(expected),
                         "precision": 0.0, "recall": 0.0, "f1": 0.0,
                         "expected_skills": "; ".join(sorted(expected)),
                         "detected_skills": "", "false_positives": "",
                         "false_negatives": "; ".join(sorted(expected)),
                         "notes": f"PDF read error: {e}"})
            continue

        if not text.strip():
            rows.append({"cv_file": pdf.name, "status": "excluded_empty_text",
                         "expected_n": len(expected), "detected_n": 0,
                         "tp": 0, "fp": 0, "fn": len(expected),
                         "precision": 0.0, "recall": 0.0, "f1": 0.0,
                         "expected_skills": "; ".join(sorted(expected)),
                         "detected_skills": "", "false_positives": "",
                         "false_negatives": "; ".join(sorted(expected)),
                         "notes": "PDF text extraction returned empty content; excluded from aggregate skill metrics."})
            continue

        profile = mod.build_candidate_profile_hybrid(text, taxonomy)
        detected = canonical_set(profile.get("skills_detected", []))
        tp_set = expected & detected
        fp_set = detected - expected
        fn_set = expected - detected
        precision = safe_div(len(tp_set), len(tp_set) + len(fp_set))
        recall = safe_div(len(tp_set), len(tp_set) + len(fn_set))
        f1 = safe_div(2 * precision * recall, precision + recall)

        rows.append({"cv_file": pdf.name, "status": "evaluated",
                     "expected_n": len(expected), "detected_n": len(detected),
                     "tp": len(tp_set), "fp": len(fp_set), "fn": len(fn_set),
                     "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4),
                     "expected_skills": "; ".join(sorted(expected)),
                     "detected_skills": "; ".join(sorted(detected)),
                     "false_positives": "; ".join(sorted(fp_set)),
                     "false_negatives": "; ".join(sorted(fn_set)),
                     "notes": ""})

    out_csv = OUT_DIR / "cv_parser_manual_validation_metrics.csv"
    with out_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    eval_rows = [r for r in rows if r["status"] == "evaluated"]
    total_tp = sum(int(r["tp"]) for r in eval_rows)
    total_fp = sum(int(r["fp"]) for r in eval_rows)
    total_fn = sum(int(r["fn"]) for r in eval_rows)
    micro_precision = safe_div(total_tp, total_tp + total_fp)
    micro_recall = safe_div(total_tp, total_tp + total_fn)
    micro_f1 = safe_div(2 * micro_precision * micro_recall, micro_precision + micro_recall)
    macro_precision = sum(float(r["precision"]) for r in eval_rows) / max(len(eval_rows), 1)
    macro_recall = sum(float(r["recall"]) for r in eval_rows) / max(len(eval_rows), 1)
    macro_f1 = sum(float(r["f1"]) for r in eval_rows) / max(len(eval_rows), 1)

    ne = lambda key: r["status"] != "evaluated"
    summary = {
        "n_pdf_files": len(rows),
        "n_evaluated": len(eval_rows),
        "n_excluded_empty_text": len(rows) - len(eval_rows),
        "excluded_files": [r["cv_file"] for r in rows if r["status"] != "evaluated"],
        "total_tp": total_tp, "total_fp": total_fp, "total_fn": total_fn,
        "micro_precision": round(micro_precision, 4),
        "micro_recall": round(micro_recall, 4),
        "micro_f1": round(micro_f1, 4),
        "macro_precision": round(macro_precision, 4),
        "macro_recall": round(macro_recall, 4),
        "macro_f1": round(macro_f1, 4),
        "mean_expected_skills": round(sum(int(r["expected_n"]) for r in eval_rows) / max(len(eval_rows), 1), 2),
        "mean_detected_skills": round(sum(int(r["detected_n"]) for r in eval_rows) / max(len(eval_rows), 1), 2),
        "metrics_csv": str(out_csv),
        "annotation_policy": "Manual reference labels restricted to skills supported by the CAIQ profile vocabulary. Empty-text PDFs are excluded from skill precision/recall aggregates and reported separately as extraction failures.",
    }

    out_json = OUT_DIR / "cv_parser_manual_validation_summary.json"
    out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
