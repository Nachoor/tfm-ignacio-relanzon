import argparse
import json
from pathlib import Path
import importlib.util

import numpy as np
import pandas as pd


def _load_model_module(path: Path):
    spec = importlib.util.spec_from_file_location("caiq_model_eval", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def main():
    ap = argparse.ArgumentParser(description="Evaluate role matching quality with labeled CV set.")
    ap.add_argument("--app-root", default=None)
    ap.add_argument("--labels", default=None)
    ap.add_argument("--cv-dir", default=None)
    ap.add_argument("--target-role", default="data_scientist")
    ap.add_argument("--target-score-col", default="ds_score")
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--out-csv", default=None)
    args = ap.parse_args()

    app_root = Path(args.app_root)
    labels_path = Path(args.labels)
    cv_dir = Path(args.cv_dir)
    out_json = Path(args.out_json)
    out_csv = Path(args.out_csv)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    model_mod = _load_model_module(app_root / "pipelines" / "build_caiq_model_advanced.py")
    taxonomy = model_mod.load_taxonomy(app_root / "config" / "skills_taxonomy.json")
    masters_feat = pd.read_csv(app_root / "outputs" / "semantic" / "masters_features.csv")
    courses_feat = pd.read_csv(app_root / "outputs" / "semantic" / "courses_features.csv")
    role_skill_demand = pd.read_csv(app_root / "outputs" / "semantic" / "role_skill_demand.csv")
    master_skills = pd.read_csv(app_root / "outputs" / "curated" / "master_skills.csv")
    course_skills = pd.read_csv(app_root / "outputs" / "curated" / "course_skills.csv")

    labels = pd.read_csv(labels_path)
    if args.target_score_col not in labels.columns:
        raise ValueError(f"Missing target score column: {args.target_score_col}")

    rows = []
    for _, r in labels.iterrows():
        cv_file = str(r.get("cv_file", "")).strip()
        if not cv_file:
            continue
        pdf_path = cv_dir / cv_file
        if not pdf_path.exists():
            continue
        resume_text = model_mod.norm_text(model_mod.read_resume_pdf_text(pdf_path))
        profile = model_mod.build_candidate_profile_hybrid(resume_text, taxonomy)
        candidate_skills = set(profile.get("skills_detected", []))
        rec = model_mod.recommend_learning_path(
            candidate_skills=candidate_skills,
            target_role=args.target_role,
            role_skill_demand=role_skill_demand,
            masters_feat=masters_feat,
            master_skills=master_skills,
            courses_feat=courses_feat,
            course_skills=course_skills,
            filters={"max_price": None, "location": "", "study_keyword": ""},
            candidate_profile=profile,
            taxonomy=taxonomy,
        )
        y_true = float(r.get(args.target_score_col, 0.0) or 0.0)
        y_pred = float(rec.get("role_match_score_current", 0.0) or 0.0) / 100.0
        rows.append(
            {
                "cv_file": cv_file,
                "target_role": args.target_role,
                "y_true": y_true,
                "y_pred": y_pred,
                "abs_error": abs(y_true - y_pred),
                "skills_count": int(len(candidate_skills)),
                "stage": str(r.get("ds_stage", "")),
            }
        )

    details = pd.DataFrame(rows)
    details.to_csv(out_csv, index=False, encoding="utf-8")

    if details.empty:
        summary = {"n": 0, "target_role": args.target_role}
    else:
        yt = details["y_true"].to_numpy(dtype=float)
        yp = details["y_pred"].to_numpy(dtype=float)
        mae = float(np.mean(np.abs(yt - yp)))
        out = {
            "n": int(len(details)),
            "target_role": args.target_role,
            "mae": round(mae, 4),
            "rmse": round(rmse(yt, yp), 4),
            "corr": round(float(np.corrcoef(yt, yp)[0, 1]) if len(details) > 1 else 0.0, 4),
            "p50_abs_error": round(float(np.quantile(np.abs(yt - yp), 0.5)), 4),
            "p90_abs_error": round(float(np.quantile(np.abs(yt - yp), 0.9)), 4),
            "details_csv": str(out_csv),
        }
        summary = out

    out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

