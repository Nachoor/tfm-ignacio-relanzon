"""
calibrate_semantic_threshold.py
================================
Calibración empírica del threshold de similitud semántica para la inferencia
de skills en CAIQ (build_datapath_model_advanced.py → SEMANTIC_INFERENCE_THRESHOLDS).

Ejecutar desde la raíz del proyecto:
    python docs/validation/scripts/calibrate_semantic_threshold.py

Requiere:
    - Los 13 CVs anotados en docs/validation/cv_cases/
    - El fichero docs/validation/outputs/cv_parser_manual_validation_metrics.csv
    - sentence-transformers instalado (pip install sentence-transformers)

Salida:
    - Curva Precision/Recall/F1 por threshold para SBERT y TF-IDF
    - Threshold óptimo (F1 máximo) para cada modo de embedding
    - Gráfico guardado en docs/validation/outputs/semantic_threshold_calibration.png
"""

import sys
import os
import csv
import json
from pathlib import Path

# ── Rutas ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
VALIDATION   = SCRIPT_DIR.parent
CASES_DIR    = VALIDATION / "cv_cases"
METRICS_CSV  = VALIDATION / "outputs" / "cv_parser_manual_validation_metrics.csv"
OUTPUT_DIR   = VALIDATION / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Añadir el path del modelo al sys.path
PROJECT_ROOT = VALIDATION.parent.parent / "app" / "caiq"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "pipelines"))

# ── Importaciones del modelo ────────────────────────────────────────────────────
try:
    from build_datapath_model_advanced import (
        extract_text_from_file,
        split_resume_sections,
        extract_skills,
        infer_implicit_skills,
        _build_resume_semantic_chunks,
        SEMANTIC_FREE_INFERENCE_ALLOWLIST,
        canonical_skill_name,
        _skill_display_name,
        norm_text,
        normalize_match_text,
        embed_texts,
        cosine_similarity_matrix,
    )
    import numpy as np
except ImportError as e:
    print(f"ERROR importando módulos del modelo: {e}")
    print("Asegúrate de ejecutar desde el entorno virtual del proyecto.")
    sys.exit(1)


def load_taxonomy() -> dict:
    """Carga la taxonomía de skills desde el config del proyecto."""
    config_dir = PROJECT_ROOT / "config"
    for fname in ["skill_taxonomy.json", "taxonomy.json", "skills.json"]:
        p = config_dir / fname
        if p.exists():
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError(f"No se encontró la taxonomía en {config_dir}")


def load_validation_labels() -> dict:
    """Carga las skills esperadas por CV desde el CSV de validación manual."""
    labels = {}
    with open(METRICS_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row["status"] != "evaluated":
                continue
            fname = row["cv_file"]
            expected = {s.strip().lower() for s in row["expected_skills"].split(";") if s.strip()}
            labels[fname] = expected
    return labels


def compute_semantic_skills(resume_text: str, taxonomy: dict,
                             existing_skills: set, threshold: float,
                             emb_mode_override: str | None = None) -> list[str]:
    """
    Ejecuta la inferencia semántica con un threshold dado.
    Devuelve la lista de skills inferidas que superan el threshold.
    """
    sections = split_resume_sections(resume_text)
    chunks   = _build_resume_semantic_chunks(sections or {})
    if not chunks or not taxonomy:
        return []

    existing = {canonical_skill_name(s) for s in existing_skills if canonical_skill_name(s)}

    skill_rows, skill_docs = [], []
    for skill, aliases in taxonomy.items():
        can = canonical_skill_name(skill)
        if not can or can in existing or can not in SEMANTIC_FREE_INFERENCE_ALLOWLIST:
            continue
        alias_terms = []
        for alias in ([skill] + list(aliases or [])):
            a = norm_text(alias)
            if not a:
                continue
            norm_alias = normalize_match_text(a)
            if norm_alias not in alias_terms:
                alias_terms.append(norm_alias)
            if len(alias_terms) >= 8:
                break
        if not alias_terms:
            continue
        skill_rows.append({"skill": can, "display": _skill_display_name(skill), "aliases": alias_terms})
        skill_docs.append(" ; ".join(alias_terms))

    if not skill_docs:
        return []

    chunk_docs = [c["text"] for c in chunks]
    try:
        emb, emb_mode = embed_texts(skill_docs + chunk_docs)
        if emb_mode_override:
            emb_mode = emb_mode_override
        skill_emb  = emb[:len(skill_docs)]
        chunk_emb  = emb[len(skill_docs):]
        sim        = cosine_similarity_matrix(skill_emb, chunk_emb)
    except Exception as exc:
        print(f"  [WARN] embed_texts falló: {exc}")
        return []

    detected = []
    for idx, row in enumerate(skill_rows):
        score_vec = np.asarray(sim[idx]).ravel()
        if score_vec.size < 1:
            continue
        best_idx  = int(np.argmax(score_vec))
        best_sim  = float(score_vec[best_idx])
        if best_sim < threshold:
            continue
        # Solo en secciones relevantes
        section = str(chunks[best_idx].get("section", "resume") or "resume")
        if section not in {"experience", "projects", "skills"}:
            continue
        detected.append(row["skill"])

    return detected


def evaluate_threshold(threshold: float, cv_data: list[dict]) -> dict:
    """Calcula Precision, Recall y F1 micro para un threshold dado."""
    total_tp = total_fp = total_fn = 0
    for item in cv_data:
        detected_sem  = set(item["semantic_by_threshold"](threshold))
        existing_rule = item["rule_skills"]   # skills ya detectadas por reglas
        expected      = item["expected"]

        # Skills finales = reglas + semánticas (sin duplicar)
        detected_all = existing_rule | detected_sem

        tp = len(detected_all & expected)
        fp = len(detected_all - expected)
        fn = len(expected - detected_all)
        total_tp += tp
        total_fp += fp
        total_fn += fn

    prec = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    rec  = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    f1   = 2 * prec * rec / (prec + rec)   if (prec + rec) > 0         else 0.0
    return {"precision": prec, "recall": rec, "f1": f1,
            "tp": total_tp, "fp": total_fp, "fn": total_fn}


def main():
    print("=" * 60)
    print("CALIBRACIÓN DEL THRESHOLD SEMÁNTICO — CAIQ")
    print("=" * 60)

    print("\n[1/4] Cargando taxonomía...")
    taxonomy = load_taxonomy()
    print(f"      {len(taxonomy)} skills en taxonomía.")

    print("[2/4] Cargando etiquetas de validación manual...")
    labels = load_validation_labels()
    print(f"      {len(labels)} CVs con anotaciones.")

    print("[3/4] Procesando CVs con el extractor de reglas...")
    cv_data = []
    for cv_file, expected_skills in labels.items():
        cv_path = CASES_DIR / cv_file
        if not cv_path.exists():
            print(f"      [SKIP] No encontrado: {cv_file}")
            continue

        try:
            text = extract_text_from_file(str(cv_path))
        except Exception as exc:
            print(f"      [ERROR] {cv_file}: {exc}")
            continue

        if not text or len(text.strip()) < 50:
            print(f"      [SKIP] Texto vacío: {cv_file}")
            continue

        # Skills detectadas por reglas (sin semántica)
        sections = split_resume_sections(text)
        rule_skills_raw = extract_skills(text, taxonomy)
        edu_inf, exp_inf = infer_implicit_skills(sections)
        rule_skills = (
            {canonical_skill_name(s["skill"]) for s in rule_skills_raw if s.get("skill")}
            | {canonical_skill_name(s["skill"]) for s in edu_inf if s.get("skill")}
            | {canonical_skill_name(s["skill"]) for s in exp_inf if s.get("skill")}
        )
        rule_skills = {s for s in rule_skills if s}

        # Precalcular similitudes para no repetir embedding en cada threshold
        # (closure que acepta threshold como argumento)
        resume_text_captured = text
        taxonomy_captured    = taxonomy
        rule_skills_captured = rule_skills

        def make_sem_fn(rt, tax, rs):
            def _sem(thr):
                return compute_semantic_skills(rt, tax, rs, thr)
            return _sem

        cv_data.append({
            "file":                  cv_file,
            "rule_skills":           rule_skills,
            "expected":              {canonical_skill_name(s) for s in expected_skills if canonical_skill_name(s)},
            "semantic_by_threshold": make_sem_fn(resume_text_captured, taxonomy_captured, rule_skills_captured),
        })
        print(f"      ✓ {cv_file[:45]:45s} reglas={len(rule_skills):2d} esperadas={len(expected_skills):2d}")

    if not cv_data:
        print("\nERROR: No se procesó ningún CV. Verifica las rutas.")
        sys.exit(1)

    print(f"\n[4/4] Barrido de thresholds (0.20 → 0.70, paso 0.02)...")
    thresholds = [round(t, 2) for t in np.arange(0.20, 0.71, 0.02)]
    results    = []

    for thr in thresholds:
        metrics = evaluate_threshold(thr, cv_data)
        results.append({"threshold": thr, **metrics})
        print(f"  thr={thr:.2f}  P={metrics['precision']:.3f}  R={metrics['recall']:.3f}  F1={metrics['f1']:.3f}")

    # Threshold óptimo (máximo F1)
    best = max(results, key=lambda x: x["f1"])
    print(f"\n{'='*60}")
    print(f"  THRESHOLD ÓPTIMO (F1 máx): {best['threshold']:.2f}")
    print(f"  Precision: {best['precision']:.3f}")
    print(f"  Recall:    {best['recall']:.3f}")
    print(f"  F1:        {best['f1']:.3f}")
    print(f"  TP={best['tp']}  FP={best['fp']}  FN={best['fn']}")
    print(f"{'='*60}")
    print(f"\n  → Actualiza SEMANTIC_INFERENCE_THRESHOLDS['sentence-transformers'] = {best['threshold']:.2f}")
    print(f"    en build_datapath_model_advanced.py")

    # Guardar resultados en CSV
    out_csv = OUTPUT_DIR / "semantic_threshold_calibration.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["threshold", "precision", "recall", "f1", "tp", "fp", "fn"])
        writer.writeheader()
        writer.writerows(results)
    print(f"\n  Resultados guardados en: {out_csv}")

    # Intentar generar gráfico (opcional)
    try:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(9, 5))
        x   = [r["threshold"] for r in results]
        ax.plot(x, [r["precision"] for r in results], "b-o", markersize=4, label="Precision")
        ax.plot(x, [r["recall"]    for r in results], "g-s", markersize=4, label="Recall")
        ax.plot(x, [r["f1"]        for r in results], "r-^", markersize=5, label="F1", linewidth=2)
        ax.axvline(best["threshold"], color="red", linestyle="--", alpha=0.6,
                   label=f"Óptimo={best['threshold']:.2f} (F1={best['f1']:.3f})")
        ax.axvline(0.42, color="gray", linestyle=":", alpha=0.7, label="Threshold original (0.42)")
        ax.set_xlabel("Threshold de similitud semántica (SBERT)")
        ax.set_ylabel("Métrica")
        ax.set_title("Calibración empírica del threshold semántico — CAIQ (n=13 CVs)")
        ax.legend()
        ax.grid(alpha=0.3)
        ax.set_ylim(0, 1.05)
        out_png = OUTPUT_DIR / "semantic_threshold_calibration.png"
        fig.savefig(out_png, dpi=150, bbox_inches="tight")
        print(f"  Gráfico guardado en: {out_png}")
    except ImportError:
        print("  (matplotlib no instalado — gráfico no generado)")


if __name__ == "__main__":
    main()
