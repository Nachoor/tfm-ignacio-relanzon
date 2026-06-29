"""09_compare_base_vs_reranker.py
Compare baseline recommender vs reranker-enhanced recommender.
Outputs:
- outputs/evaluation/base_vs_reranker.csv
- reports/base_vs_reranker_report.json
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


def eval_one(rec):
    final_sk = set(rec["final_skill_set"])
    holdout = set(rec["_holdout"])
    observed = set(rec["_observed"])
    recovered = len(final_sk & holdout)
    recall = recovered / max(len(holdout), 1)
    miss_rate = 1.0 - recall
    gap_before = len(rec["gap_skills"])
    gap_after = len(rec["remaining_gap"])
    gap_reduction = (gap_before - gap_after) / max(gap_before, 1)
    precision_like = recovered / max(len(final_sk - observed), 1)
    return recall, miss_rate, gap_reduction, precision_like


def main():
    ap = argparse.ArgumentParser(description="Compare baseline and reranker")
    ap.add_argument("--etl-dir", default=None)
    ap.add_argument("--max-candidates", type=int, default=80)
    args = ap.parse_args()

    etl_dir = Path(args.etl_dir)
    cdir = etl_dir / "outputs" / "curated"
    sdir = etl_dir / "outputs" / "semantic"
    edir = etl_dir / "outputs" / "evaluation"
    rdir = etl_dir / "reports"
    mpath = etl_dir / "outputs" / "model" / "master_reranker.pkl"
    edir.mkdir(parents=True, exist_ok=True)
    rdir.mkdir(parents=True, exist_ok=True)

    mod = load_module(etl_dir / "pipelines" / "build_datapath_model_advanced.py", "datapath_model_cmp")
    rec_fn = mod.recommend_learning_path

    tuned_path = rdir / "model_tuned_params.json"
    if tuned_path.exists():
        tuned = json.loads(tuned_path.read_text(encoding="utf-8"))
        wc = float(tuned.get("weight_coverage", 0.65))
        ws = float(tuned.get("weight_semantic", 0.35))
    else:
        wc, ws = 0.65, 0.35

    reranker = None
    if mpath.exists():
        with mpath.open("rb") as f:
            reranker = pickle.load(f)

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

    out_rows = []
    n = 0
    for _, row in profile.iterrows():
        if n >= args.max_candidates:
            break
        cid = int(row["candidate_id"])
        sk = skill_map.get(cid)
        if not sk or len(sk) < 5:
            continue

        ordered = sorted(sk)
        holdout_n = max(1, int(round(0.2 * len(ordered))))
        holdout = set(ordered[:holdout_n])
        observed = set(ordered[holdout_n:])

        common_kwargs = dict(
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

        rec_base = rec_fn(**common_kwargs)
        rec_base["_holdout"] = holdout
        rec_base["_observed"] = observed

        rec_rerank = rec_fn(**common_kwargs, master_reranker_model=reranker, reranker_blend=0.7)
        rec_rerank["_holdout"] = holdout
        rec_rerank["_observed"] = observed

        b_recall, b_miss, b_gapred, b_prec = eval_one(rec_base)
        r_recall, r_miss, r_gapred, r_prec = eval_one(rec_rerank)

        out_rows.append(
            {
                "candidate_id": cid,
                "role": row["target_role"],
                "base_recall": b_recall,
                "rerank_recall": r_recall,
                "base_miss_rate": b_miss,
                "rerank_miss_rate": r_miss,
                "base_gap_reduction": b_gapred,
                "rerank_gap_reduction": r_gapred,
                "base_precision_like": b_prec,
                "rerank_precision_like": r_prec,
            }
        )
        n += 1

    df = pd.DataFrame(out_rows)
    df.to_csv(edir / "base_vs_reranker.csv", index=False, encoding="utf-8")

    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "n_candidates": int(len(df)),
        "base": {
            "avg_recall": float(df["base_recall"].mean()) if not df.empty else None,
            "avg_miss_rate": float(df["base_miss_rate"].mean()) if not df.empty else None,
            "avg_gap_reduction": float(df["base_gap_reduction"].mean()) if not df.empty else None,
            "avg_precision_like": float(df["base_precision_like"].mean()) if not df.empty else None,
        },
        "reranker": {
            "avg_recall": float(df["rerank_recall"].mean()) if not df.empty else None,
            "avg_miss_rate": float(df["rerank_miss_rate"].mean()) if not df.empty else None,
            "avg_gap_reduction": float(df["rerank_gap_reduction"].mean()) if not df.empty else None,
            "avg_precision_like": float(df["rerank_precision_like"].mean()) if not df.empty else None,
        },
        "delta": {
            "recall": float((df["rerank_recall"] - df["base_recall"]).mean()) if not df.empty else None,
            "miss_rate": float((df["rerank_miss_rate"] - df["base_miss_rate"]).mean()) if not df.empty else None,
            "gap_reduction": float((df["rerank_gap_reduction"] - df["base_gap_reduction"]).mean()) if not df.empty else None,
            "precision_like": float((df["rerank_precision_like"] - df["base_precision_like"]).mean()) if not df.empty else None,
        },
        "artifact": str(edir / "base_vs_reranker.csv"),
    }
    (rdir / "base_vs_reranker_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
