"""10_tune_reranker_blend.py
Tune reranker blend and decide default activation policy.
Outputs:
- outputs/evaluation/reranker_blend_grid.csv
- reports/reranker_tuned_params.json
- reports/reranker_blend_report.json
"""
import argparse
import importlib.util
import json
import pickle
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


def evaluate_candidate(rec: dict, holdout: set[str], observed: set[str]):
    final_sk = set(rec["final_skill_set"])
    recovered = len(holdout & final_sk)
    recall = recovered / max(len(holdout), 1)
    miss_rate = 1.0 - recall

    gap_before = len(rec["gap_skills"])
    gap_after = len(rec["remaining_gap"])
    gap_reduction = (gap_before - gap_after) / max(gap_before, 1)

    precision_like = recovered / max(len(final_sk - observed), 1)

    # Higher is better objective, prioritizing coverage/gap then precision.
    objective = 0.45 * gap_reduction + 0.45 * recall + 0.10 * precision_like
    return recall, miss_rate, gap_reduction, precision_like, objective


def main():
    ap = argparse.ArgumentParser(description="Tune reranker blend policy")
    ap.add_argument("--etl-dir", default=None)
    ap.add_argument("--max-candidates", type=int, default=50)
    args = ap.parse_args()

    etl_dir = Path(args.etl_dir)
    cdir = etl_dir / "outputs" / "curated"
    sdir = etl_dir / "outputs" / "semantic"
    edir = etl_dir / "outputs" / "evaluation"
    rdir = etl_dir / "reports"
    mdir = etl_dir / "outputs" / "model"
    edir.mkdir(parents=True, exist_ok=True)
    rdir.mkdir(parents=True, exist_ok=True)

    reranker_path = mdir / "master_reranker.pkl"
    if not reranker_path.exists():
        raise FileNotFoundError(f"Reranker model not found: {reranker_path}")

    with reranker_path.open("rb") as f:
        reranker = pickle.load(f)

    mod = load_module(etl_dir / "pipelines" / "build_datapath_model_advanced.py", "datapath_model_blend")
    rec_fn = mod.recommend_learning_path

    tuned_path = rdir / "model_tuned_params.json"
    if tuned_path.exists():
        tuned = json.loads(tuned_path.read_text(encoding="utf-8"))
        wc = float(tuned.get("weight_coverage", 0.65))
        ws = float(tuned.get("weight_semantic", 0.35))
    else:
        wc, ws = 0.65, 0.35

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
        sk = skill_map.get(cid)
        if not sk or len(sk) < 5:
            continue
        candidates.append((cid, row["target_role"], set(sk)))
        if len(candidates) >= args.max_candidates:
            break

    blends = [0.0, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.5, 0.7]
    rows = []

    for blend in blends:
        recs, misses, gaps, precs, objs = [], [], [], [], []
        for _, role, sk in candidates:
            ordered = sorted(sk)
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
                master_reranker_model=reranker if blend > 0 else None,
                reranker_blend=blend,
            )
            r, m, g, p, o = evaluate_candidate(rec, holdout, observed)
            recs.append(r)
            misses.append(m)
            gaps.append(g)
            precs.append(p)
            objs.append(o)

        rows.append(
            {
                "blend": blend,
                "avg_recall": float(np.mean(recs)) if recs else None,
                "avg_miss_rate": float(np.mean(misses)) if misses else None,
                "avg_gap_reduction": float(np.mean(gaps)) if gaps else None,
                "avg_precision_like": float(np.mean(precs)) if precs else None,
                "avg_objective": float(np.mean(objs)) if objs else None,
                "n_candidates": len(recs),
            }
        )

    grid = pd.DataFrame(rows).sort_values("avg_objective", ascending=False)
    grid_path = edir / "reranker_blend_grid.csv"
    grid.to_csv(grid_path, index=False, encoding="utf-8")

    base_row = grid.loc[grid["blend"] == 0.0].iloc[0].to_dict()
    best_row = grid.iloc[0].to_dict()

    # Policy: enable reranker by default only if global objective improves
    # and no harmful drop in core coverage metrics.
    use_reranker_default = False
    chosen_blend = 0.0
    if float(best_row["blend"]) > 0.0:
        obj_gain = float(best_row["avg_objective"] - base_row["avg_objective"])
        recall_drop = float(base_row["avg_recall"] - best_row["avg_recall"])
        gap_drop = float(base_row["avg_gap_reduction"] - best_row["avg_gap_reduction"])
        if obj_gain > 0.002 and recall_drop <= 0.01 and gap_drop <= 0.02:
            use_reranker_default = True
            chosen_blend = float(best_row["blend"])

    tuned_params = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "use_reranker_default": use_reranker_default,
        "reranker_blend": chosen_blend,
        "base_blend": 0.0,
    }
    (rdir / "reranker_tuned_params.json").write_text(json.dumps(tuned_params, indent=2), encoding="utf-8")

    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "weights": {"coverage": wc, "semantic": ws},
        "base": base_row,
        "best": best_row,
        "policy": tuned_params,
        "grid_path": str(grid_path),
    }
    (rdir / "reranker_blend_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
