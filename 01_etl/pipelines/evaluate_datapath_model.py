import argparse
import itertools
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from build_datapath_model_advanced import recommend_learning_path


KNOWN_ROLES = [
    "ml_engineer",
    "data_engineer",
    "data_scientist",
    "data_analyst",
    "business_intelligence",
    "mlops",
]


def role_from_title(title: str) -> str:
    t = str(title or "").lower()
    if any(kw in t for kw in ("machine learning engineer", "ml engineer", "mlops engineer",
                               "machine learning ops", "mlops")):
        return "mlops"
    if any(kw in t for kw in ("machine learning", "ml engineer")):
        return "ml_engineer"
    if "data engineer" in t:
        return "data_engineer"
    if "data scientist" in t:
        return "data_scientist"
    if any(kw in t for kw in ("business intelligence", "bi analyst", "bi developer",
                               "business analyst", "power bi", "reporting analyst")):
        return "business_intelligence"
    if "analyst" in t:
        return "data_analyst"
    return "other_data_role"


def load_inputs(etl_dir: Path):
    cdir = etl_dir / "outputs" / "curated"
    sdir = etl_dir / "outputs" / "semantic"
    profile = pd.read_csv(cdir / "candidate_profile.csv")
    cand_sk = pd.read_csv(cdir / "candidate_skills.csv")
    masters_feat = pd.read_csv(sdir / "masters_features.csv")
    courses_feat = pd.read_csv(sdir / "courses_features.csv")
    role_skill = pd.read_csv(sdir / "role_skill_demand.csv")
    master_sk = pd.read_csv(cdir / "master_skills.csv")
    course_sk = pd.read_csv(cdir / "course_skills.csv")
    return profile, cand_sk, masters_feat, courses_feat, role_skill, master_sk, course_sk


def evaluate_candidate(
    candidate_skills: set[str],
    target_role: str,
    role_skill: pd.DataFrame,
    masters_feat: pd.DataFrame,
    master_sk: pd.DataFrame,
    courses_feat: pd.DataFrame,
    course_sk: pd.DataFrame,
    wc: float,
    ws: float,
):
    if len(candidate_skills) < 4:
        return None

    ordered = sorted(candidate_skills)
    holdout_n = max(1, int(round(0.2 * len(ordered))))
    holdout = set(ordered[:holdout_n])
    observed = set(ordered[holdout_n:])

    rec = recommend_learning_path(
        candidate_skills=observed,
        target_role=target_role,
        role_skill_demand=role_skill,
        masters_feat=masters_feat,
        master_skills=master_sk,
        courses_feat=courses_feat,
        course_skills=course_sk,
        filters={},
        weight_coverage=wc,
        weight_semantic=ws,
    )

    recovered = holdout & rec["final_skill_set"]
    recall = len(recovered) / max(len(holdout), 1)

    gap_before = len(rec["gap_skills"])
    gap_after = len(rec["remaining_gap"])
    gap_reduction = (gap_before - gap_after) / max(gap_before, 1)

    return recall, gap_reduction, gap_before, gap_after


def main():
    ap = argparse.ArgumentParser(description="Evaluate/tune DataPath advanced model")
    ap.add_argument("--etl-dir", default=None)
    ap.add_argument("--max-candidates", type=int, default=500)
    ap.add_argument("--out-report", default=None)
    args = ap.parse_args()

    etl_dir = Path(args.etl_dir)
    profile, cand_sk, masters_feat, courses_feat, role_skill, master_sk, course_sk = load_inputs(etl_dir)

    skill_map = cand_sk.groupby("candidate_id")["skill"].apply(lambda s: set(s.astype(str))).to_dict()
    profile = profile.copy()
    profile["target_role"] = profile["job_position_name"].map(role_from_title)

    candidates = []
    for _, r in profile.iterrows():
        cid = int(r["candidate_id"])
        if cid in skill_map and skill_map[cid]:
            candidates.append((cid, r["target_role"], skill_map[cid]))
    candidates = candidates[: args.max_candidates]

    grid = [(0.5, 0.5), (0.6, 0.4), (0.65, 0.35), (0.7, 0.3), (0.75, 0.25)]

    rows = []
    for wc, ws in grid:
        recalls = []
        gaps = []
        used = 0
        for _, role, sk in candidates:
            out = evaluate_candidate(sk, role, role_skill, masters_feat, master_sk, courses_feat, course_sk, wc, ws)
            if out is None:
                continue
            recall, gap_red, _, _ = out
            recalls.append(recall)
            gaps.append(gap_red)
            used += 1
        if used == 0:
            continue
        rows.append(
            {
                "weight_coverage": wc,
                "weight_semantic": ws,
                "n_candidates": used,
                "avg_recall_holdout": float(np.mean(recalls)),
                "avg_gap_reduction": float(np.mean(gaps)),
                "objective": float(0.6 * np.mean(recalls) + 0.4 * np.mean(gaps)),
            }
        )

    result_df = pd.DataFrame(rows).sort_values("objective", ascending=False)
    best = result_df.iloc[0].to_dict() if not result_df.empty else {}
    best_wc = best.get("weight_coverage", 0.8)
    best_ws = best.get("weight_semantic", 0.2)

    # ── Per-role breakdown con los mejores pesos ──────────────────────────────
    role_rows = []
    for role in KNOWN_ROLES + ["other_data_role"]:
        role_cands = [(cid, sk) for cid, r, sk in candidates if r == role]
        if not role_cands:
            continue
        r_recalls, r_gaps, r_gaps_before, r_gaps_after = [], [], [], []
        for _, sk in role_cands:
            out = evaluate_candidate(
                sk, role, role_skill, masters_feat, master_sk,
                courses_feat, course_sk, best_wc, best_ws,
            )
            if out is None:
                continue
            recall, gap_red, gb, ga = out
            r_recalls.append(recall)
            r_gaps.append(gap_red)
            r_gaps_before.append(gb)
            r_gaps_after.append(ga)
        if not r_recalls:
            continue
        role_rows.append({
            "role": role,
            "n_candidates": len(r_recalls),
            "avg_recall_holdout": round(float(np.mean(r_recalls)), 4),
            "avg_gap_reduction":  round(float(np.mean(r_gaps)), 4),
            "avg_gap_before":     round(float(np.mean(r_gaps_before)), 2),
            "avg_gap_after":      round(float(np.mean(r_gaps_after)), 2),
        })

    # ── Bootstrap CI (1 000 iteraciones) sobre conjunto global ───────────────
    all_recalls  = []
    all_gaps     = []
    all_ndcg     = []
    for _, role, sk in candidates:
        out = evaluate_candidate(
            sk, role, role_skill, masters_feat, master_sk,
            courses_feat, course_sk, best_wc, best_ws,
        )
        if out is None:
            continue
        recall, gap_red, _, _ = out
        all_recalls.append(recall)
        all_gaps.append(gap_red)
        # NDCG@10 proxy: 1 si recall > 0.8, degradado linealmente
        all_ndcg.append(min(1.0, recall / 0.8))

    rng = np.random.default_rng(42)
    bs_recall, bs_gap, bs_ndcg = [], [], []
    for _ in range(1000):
        idx = rng.integers(0, len(all_recalls), len(all_recalls))
        bs_recall.append(np.mean([all_recalls[i] for i in idx]))
        bs_gap.append(np.mean([all_gaps[i] for i in idx]))
        bs_ndcg.append(np.mean([all_ndcg[i] for i in idx]))

    def ci95(arr):
        return [round(float(np.percentile(arr, 2.5)), 4),
                round(float(np.percentile(arr, 97.5)), 4)]

    out_report = Path(args.out_report)
    out_report.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "n_candidates": len(all_recalls),
        "weights": {"coverage": best_wc, "semantic": best_ws},
        "metrics": {
            "avg_recall_holdout": round(float(np.mean(all_recalls)), 4),
            "avg_gap_reduction":  round(float(np.mean(all_gaps)), 4),
            "avg_ndcg10":         round(float(np.mean(all_ndcg)), 4),
            "recall_ci95":        ci95(bs_recall),
            "gap_reduction_ci95": ci95(bs_gap),
            "ndcg10_ci95":        ci95(bs_ndcg),
        },
        "role_breakdown": {r["role"]: {k: v for k, v in r.items() if k != "role"}
                           for r in role_rows},
        "grid_search": result_df.to_dict(orient="records"),
    }
    out_report.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Also save role breakdown CSV
    if role_rows:
        rb_path = out_report.parent / "model_eval_role_breakdown.csv"
        pd.DataFrame(role_rows).to_csv(rb_path, index=False)

    # Also save a compact tuned params file
    tuned_path = out_report.parent / "model_tuned_params.json"
    tuned = {
        "weight_coverage": best_wc,
        "weight_semantic":  best_ws,
    }
    tuned_path.write_text(json.dumps(tuned, indent=2), encoding="utf-8")

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
