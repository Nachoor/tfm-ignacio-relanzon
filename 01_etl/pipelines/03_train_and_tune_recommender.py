"""03_train_and_tune_recommender.py
Calibrate recommender weights using holdout-skill validation.
Outputs:
- reports/model_training_report.json
- reports/model_tuned_params.json
- outputs/evaluation/training_grid_results.csv
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


def _split_holdout(sk: set[str], seed: int) -> tuple[set[str], set[str]]:
    """Holdout aleatorio con seed reproducible: evita el sesgo de ordenación alfabética."""
    ordered = sorted(sk)
    rng = np.random.default_rng(seed)
    rng.shuffle(ordered)
    holdout_n = max(1, int(round(0.2 * len(ordered))))
    return set(ordered[:holdout_n]), set(ordered[holdout_n:])


def evaluate_candidate(rec_fn, sk: set[str], role: str, role_skill, masters_feat, master_sk, courses_feat, course_sk, wc: float, ws: float, seed: int = 42):
    if len(sk) < 5:
        return None

    holdout, observed = _split_holdout(sk, seed)

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

    recovered = len(holdout & rec["final_skill_set"])
    recall = recovered / max(len(holdout), 1)

    gap_before = len(rec["gap_skills"])
    gap_after = len(rec["remaining_gap"])
    gap_reduction = (gap_before - gap_after) / max(gap_before, 1)

    return recall, gap_reduction, gap_before, gap_after


def main():
    ap = argparse.ArgumentParser(description="Train/tune DataPath recommender weights")
    ap.add_argument("--etl-dir", default=None)
    ap.add_argument("--max-candidates", type=int, default=600)
    args = ap.parse_args()

    etl_dir = Path(args.etl_dir)
    cdir = etl_dir / "outputs" / "curated"
    sdir = etl_dir / "outputs" / "semantic"
    rdir = etl_dir / "reports"
    edir = etl_dir / "outputs" / "evaluation"
    rdir.mkdir(parents=True, exist_ok=True)
    edir.mkdir(parents=True, exist_ok=True)

    model_mod = load_module(etl_dir / "pipelines" / "build_datapath_model_advanced.py", "datapath_model")
    rec_fn = model_mod.recommend_learning_path

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

    # Grid ampliado: cubre todo el espacio desde semántico puro hasta cobertura pura
    grid = [
        (0.25, 0.75),
        (0.30, 0.70),
        (0.40, 0.60),
        (0.50, 0.50),
        (0.55, 0.45),
        (0.60, 0.40),
        (0.65, 0.35),
        (0.70, 0.30),
        (0.75, 0.25),
        (0.80, 0.20),
    ]

    rows = []
    for wc, ws in grid:
        recalls, gapreds, used = [], [], 0
        for cid, role, sk in candidates:
            out = evaluate_candidate(rec_fn, sk, role, role_skill, masters_feat, master_sk, courses_feat, course_sk, wc, ws, seed=cid)
            if out is None:
                continue
            recall, gapred, _, _ = out
            recalls.append(recall)
            gapreds.append(gapred)
            used += 1
        if used == 0:
            continue

        rows.append({
            "weight_coverage": wc,
            "weight_semantic": ws,
            "n_candidates": used,
            "avg_recall_holdout": float(np.mean(recalls)),
            "std_recall_holdout": float(np.std(recalls)),
            "avg_gap_reduction": float(np.mean(gapreds)),
            "std_gap_reduction": float(np.std(gapreds)),
            "objective": float(0.6 * np.mean(recalls) + 0.4 * np.mean(gapreds)),
        })

    res = pd.DataFrame(rows).sort_values("objective", ascending=False)
    res.to_csv(edir / "training_grid_results.csv", index=False, encoding="utf-8")

    best = res.iloc[0].to_dict() if not res.empty else {"weight_coverage": 0.6, "weight_semantic": 0.4}
    tuned = {
        "weight_coverage": float(best["weight_coverage"]),
        "weight_semantic": float(best["weight_semantic"]),
    }
    (rdir / "model_tuned_params.json").write_text(json.dumps(tuned, indent=2), encoding="utf-8")

    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "max_candidates": args.max_candidates,
        "best": best,
        "grid_rows": int(len(res)),
        "output_grid": str(edir / "training_grid_results.csv"),
    }
    (rdir / "model_training_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
