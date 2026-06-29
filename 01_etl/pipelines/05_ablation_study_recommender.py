"""05_ablation_study_recommender.py
Run ablation variants and compare against tuned hybrid model.
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


def evaluate_variant(rec_fn, candidates, role_skill, masters_feat, master_sk, courses_feat, course_sk, wc, ws):
    recalls, gaps = [], []
    for cid, role, sk in candidates:
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
        recall = len(holdout & set(rec["final_skill_set"])) / max(len(holdout), 1)
        gap_before = len(rec["gap_skills"])
        gap_after = len(rec["remaining_gap"])
        gap_reduction = (gap_before - gap_after) / max(gap_before, 1)
        recalls.append(recall)
        gaps.append(gap_reduction)

    if not recalls:
        return {"avg_recall": None, "avg_gap_reduction": None, "objective": None, "n": 0}
    avg_r = float(np.mean(recalls))
    avg_g = float(np.mean(gaps))
    return {
        "avg_recall": avg_r,
        "avg_gap_reduction": avg_g,
        "objective": float(0.6 * avg_r + 0.4 * avg_g),
        "n": len(recalls),
    }


def main():
    ap = argparse.ArgumentParser(description="Ablation study for recommender")
    ap.add_argument("--etl-dir", default=None)
    ap.add_argument("--max-candidates", type=int, default=300)
    args = ap.parse_args()

    etl_dir = Path(args.etl_dir)
    cdir = etl_dir / "outputs" / "curated"
    sdir = etl_dir / "outputs" / "semantic"
    edir = etl_dir / "outputs" / "evaluation"
    rdir = etl_dir / "reports"
    edir.mkdir(parents=True, exist_ok=True)
    rdir.mkdir(parents=True, exist_ok=True)

    model_mod = load_module(etl_dir / "pipelines" / "build_datapath_model_advanced.py", "datapath_model_ablation")
    rec_fn = model_mod.recommend_learning_path

    tuned_path = rdir / "model_tuned_params.json"
    if tuned_path.exists():
        tuned = json.loads(tuned_path.read_text(encoding="utf-8"))
        tuned_w = (float(tuned.get("weight_coverage", 0.6)), float(tuned.get("weight_semantic", 0.4)))
    else:
        tuned_w = (0.6, 0.4)

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

    candidates = []
    for _, row in profile.iterrows():
        cid = int(row["candidate_id"])
        if cid in skill_map and skill_map[cid]:
            candidates.append((cid, row["target_role"], skill_map[cid]))
    candidates = candidates[: args.max_candidates]

    variants = {
        "coverage_only": (1.0, 0.0),
        "semantic_only": (0.0, 1.0),
        "balanced_50_50": (0.5, 0.5),
        "hybrid_tuned": tuned_w,
    }

    rows = []
    for name, (wc, ws) in variants.items():
        out = evaluate_variant(rec_fn, candidates, role_skill, masters_feat, master_sk, courses_feat, course_sk, wc, ws)
        rows.append({"variant": name, "weight_coverage": wc, "weight_semantic": ws, **out})

    df = pd.DataFrame(rows).sort_values("objective", ascending=False)
    df.to_csv(edir / "ablation_results.csv", index=False, encoding="utf-8")

    best_obj = float(df["objective"].max()) if not df.empty else None
    baseline = df.loc[df["variant"] == "coverage_only", "objective"]
    baseline_obj = float(baseline.iloc[0]) if len(baseline) else None
    lift = (best_obj - baseline_obj) / max(abs(baseline_obj), 1e-9) if baseline_obj is not None and best_obj is not None else None

    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "n_candidates": int(args.max_candidates),
        "best_variant": df.iloc[0].to_dict() if not df.empty else {},
        "baseline_objective": baseline_obj,
        "relative_lift_vs_coverage_only": lift,
        "results_path": str(edir / "ablation_results.csv"),
    }
    (rdir / "ablation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
