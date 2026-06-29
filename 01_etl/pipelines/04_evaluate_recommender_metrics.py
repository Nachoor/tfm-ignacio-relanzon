"""04_evaluate_recommender_metrics.py
Comprehensive statistical evaluation for the recommender.
Metrics:
- Recall@All (holdout skills recovered)
- Gap Reduction
- Precision-like skill efficiency
- Error metrics: miss_rate, MAE gap, normalized gap error
- Role-wise diagnostics
- Bootstrap confidence intervals
Outputs:
- outputs/evaluation/candidate_level_metrics.csv
- reports/model_eval_report.json
- reports/model_eval_role_breakdown.csv
"""
import argparse
import importlib.util
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


def load_module(module_path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, str(module_path))
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def role_from_title(title: str) -> str:
    t = str(title or "").lower()
    if "machine learning" in t or "ml engineer" in t:
        return "ml_engineer"
    if "data engineer" in t:
        return "data_engineer"
    if "data scientist" in t:
        return "data_scientist"
    if "analyst" in t:
        return "data_analyst"
    return "other_data_role"


def bootstrap_ci(values: np.ndarray, n_boot: int = 500, alpha: float = 0.05):
    if len(values) == 0:
        return None, None
    rng = np.random.default_rng(42)
    means = []
    for _ in range(n_boot):
        sample = rng.choice(values, size=len(values), replace=True)
        means.append(np.mean(sample))
    lo = float(np.percentile(means, 100 * (alpha / 2)))
    hi = float(np.percentile(means, 100 * (1 - alpha / 2)))
    return lo, hi


def main():
    ap = argparse.ArgumentParser(description="Evaluate recommender metrics")
    ap.add_argument("--etl-dir", default=None)
    ap.add_argument("--max-candidates", type=int, default=800)
    args = ap.parse_args()

    etl_dir = Path(args.etl_dir)
    cdir = etl_dir / "outputs" / "curated"
    sdir = etl_dir / "outputs" / "semantic"
    edir = etl_dir / "outputs" / "evaluation"
    rdir = etl_dir / "reports"
    edir.mkdir(parents=True, exist_ok=True)
    rdir.mkdir(parents=True, exist_ok=True)

    model_mod = load_module(etl_dir / "pipelines" / "build_datapath_model_advanced.py", "datapath_model_eval")
    rec_fn = model_mod.recommend_learning_path

    tuned_path = rdir / "model_tuned_params.json"
    if tuned_path.exists():
        tuned = json.loads(tuned_path.read_text(encoding="utf-8"))
        wc = float(tuned.get("weight_coverage", 0.6))
        ws = float(tuned.get("weight_semantic", 0.4))
    else:
        wc, ws = 0.6, 0.4

    profile = pd.read_csv(cdir / "candidate_profile.csv")
    cand_sk = pd.read_csv(cdir / "candidate_skills.csv")
    masters_feat = pd.read_csv(sdir / "masters_features.csv")
    courses_feat = pd.read_csv(sdir / "courses_features.csv")
    role_skill = pd.read_csv(sdir / "role_skill_demand.csv")
    master_sk = pd.read_csv(cdir / "master_skills.csv")
    course_sk = pd.read_csv(cdir / "course_skills.csv")

    skill_map = cand_sk.groupby("candidate_id")["skill"].apply(lambda s: set(s.astype(str))).to_dict()
    profile = profile.copy()
    profile["target_role"] = profile["job_position_name"].map(role_from_title)

    rows = []
    used = 0
    for _, row in profile.iterrows():
        if used >= args.max_candidates:
            break
        cid = int(row["candidate_id"])
        if cid not in skill_map:
            continue
        sk = set(skill_map[cid])
        if len(sk) < 5:
            continue

        # Holdout aleatorio con seed por candidato: reproducible y sin sesgo alfabético
        ordered = sorted(sk)
        rng_cand = np.random.default_rng(cid)
        rng_cand.shuffle(ordered)
        holdout_n = max(1, int(round(0.2 * len(ordered))))
        holdout = set(ordered[:holdout_n])
        observed = set(ordered[holdout_n:])

        rec = rec_fn(
            candidate_skills=observed,
            target_role=row["target_role"],
            role_skill_demand=role_skill,
            masters_feat=masters_feat,
            master_skills=master_sk,
            courses_feat=courses_feat,
            course_skills=course_sk,
            filters={},
            weight_coverage=wc,
            weight_semantic=ws,
        )

        final_sk = set(rec["final_skill_set"])
        recovered = len(holdout & final_sk)
        recall = recovered / max(len(holdout), 1)
        miss_rate = 1.0 - recall

        recommended_new = len(final_sk - observed)
        precision_like = recovered / max(recommended_new, 1)

        gap_before = len(rec["gap_skills"])
        gap_after = len(rec["remaining_gap"])
        gap_reduction = (gap_before - gap_after) / max(gap_before, 1)
        gap_error_abs = abs(gap_after)
        normalized_gap_error = gap_after / max(gap_before, 1)

        rows.append(
            {
                "candidate_id": cid,
                "role": row["target_role"],
                "skills_total": len(sk),
                "holdout_n": len(holdout),
                "recovered_holdout": recovered,
                "recall_holdout": recall,
                "miss_rate": miss_rate,
                "precision_like": precision_like,
                "gap_before": gap_before,
                "gap_after": gap_after,
                "gap_reduction": gap_reduction,
                "gap_error_abs": gap_error_abs,
                "normalized_gap_error": normalized_gap_error,
                "recommended_new_skills": recommended_new,
            }
        )
        used += 1

    mdf = pd.DataFrame(rows)
    mdf.to_csv(edir / "candidate_level_metrics.csv", index=False, encoding="utf-8")

    recall_vals = mdf["recall_holdout"].to_numpy() if not mdf.empty else np.array([])
    gap_vals = mdf["gap_reduction"].to_numpy() if not mdf.empty else np.array([])
    prec_vals = mdf["precision_like"].to_numpy() if not mdf.empty else np.array([])
    miss_vals = mdf["miss_rate"].to_numpy() if not mdf.empty else np.array([])
    nge_vals = mdf["normalized_gap_error"].to_numpy() if not mdf.empty else np.array([])

    recall_ci = bootstrap_ci(recall_vals)
    gap_ci = bootstrap_ci(gap_vals)
    prec_ci = bootstrap_ci(prec_vals)
    miss_ci = bootstrap_ci(miss_vals)
    nge_ci = bootstrap_ci(nge_vals)

    role_breakdown = (
        mdf.groupby("role", as_index=False)
        .agg(
            n_candidates=("candidate_id", "count"),
            avg_recall_holdout=("recall_holdout", "mean"),
            avg_miss_rate=("miss_rate", "mean"),
            avg_gap_reduction=("gap_reduction", "mean"),
            avg_precision_like=("precision_like", "mean"),
            avg_gap_error_abs=("gap_error_abs", "mean"),
            avg_normalized_gap_error=("normalized_gap_error", "mean"),
            avg_gap_before=("gap_before", "mean"),
            avg_gap_after=("gap_after", "mean"),
        )
        .sort_values("n_candidates", ascending=False)
    )
    role_breakdown.to_csv(rdir / "model_eval_role_breakdown.csv", index=False, encoding="utf-8")

    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "n_candidates_evaluated": int(len(mdf)),
        "weights": {"coverage": wc, "semantic": ws},
        "metrics": {
            "avg_recall_holdout": float(mdf["recall_holdout"].mean()) if not mdf.empty else None,
            "avg_miss_rate": float(mdf["miss_rate"].mean()) if not mdf.empty else None,
            "avg_gap_reduction": float(mdf["gap_reduction"].mean()) if not mdf.empty else None,
            "avg_precision_like": float(mdf["precision_like"].mean()) if not mdf.empty else None,
            "mae_gap_error_abs": float(mdf["gap_error_abs"].mean()) if not mdf.empty else None,
            "avg_normalized_gap_error": float(mdf["normalized_gap_error"].mean()) if not mdf.empty else None,
            "recall_holdout_ci95": list(recall_ci) if recall_ci[0] is not None else None,
            "miss_rate_ci95": list(miss_ci) if miss_ci[0] is not None else None,
            "gap_reduction_ci95": list(gap_ci) if gap_ci[0] is not None else None,
            "precision_like_ci95": list(prec_ci) if prec_ci[0] is not None else None,
            "normalized_gap_error_ci95": list(nge_ci) if nge_ci[0] is not None else None,
        },
        "outputs": {
            "candidate_level_metrics": str(edir / "candidate_level_metrics.csv"),
            "role_breakdown": str(rdir / "model_eval_role_breakdown.csv"),
        },
    }
    (rdir / "model_eval_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
