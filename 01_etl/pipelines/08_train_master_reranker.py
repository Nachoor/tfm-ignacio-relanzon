"""08_train_master_reranker.py
Train supervised reranker for master recommendations.
Outputs:
- outputs/model/master_reranker.pkl
- outputs/evaluation/master_reranker_trainset.csv
- reports/master_reranker_report.json
"""
import argparse
import importlib.util
import json
import pickle
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


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


def ndcg_at_k(y_true: np.ndarray, y_pred: np.ndarray, k: int = 10) -> float:
    if y_true.size == 0:
        return 0.0
    order = np.argsort(-y_pred)[:k]
    gains = y_true[order]
    discounts = 1.0 / np.log2(np.arange(2, 2 + len(gains)))
    dcg = float(np.sum(gains * discounts))

    ideal = np.sort(y_true)[::-1][:k]
    idcg = float(np.sum(ideal * discounts[: len(ideal)])) if ideal.size else 0.0
    return dcg / idcg if idcg > 0 else 0.0


def main():
    ap = argparse.ArgumentParser(description="Train master reranker")
    ap.add_argument("--etl-dir", default=None)
    ap.add_argument("--max-candidates", type=int, default=120)
    ap.add_argument("--negatives-per-candidate", type=int, default=30)
    ap.add_argument("--random-seed", type=int, default=42)
    args = ap.parse_args()

    rng = np.random.default_rng(args.random_seed)

    etl_dir = Path(args.etl_dir)
    cdir = etl_dir / "outputs" / "curated"
    sdir = etl_dir / "outputs" / "semantic"
    edir = etl_dir / "outputs" / "evaluation"
    mdir = etl_dir / "outputs" / "model"
    rdir = etl_dir / "reports"
    edir.mkdir(parents=True, exist_ok=True)
    mdir.mkdir(parents=True, exist_ok=True)
    rdir.mkdir(parents=True, exist_ok=True)

    model_mod = load_module(etl_dir / "pipelines" / "build_datapath_model_advanced.py", "datapath_model_rerank")

    profile = pd.read_csv(cdir / "candidate_profile.csv")
    cand_sk = pd.read_csv(cdir / "candidate_skills.csv")
    masters_feat = pd.read_csv(sdir / "masters_features.csv")
    role_skill = pd.read_csv(sdir / "role_skill_demand.csv")
    master_sk = pd.read_csv(cdir / "master_skills.csv")

    master_sk = master_sk.copy()
    master_sk["skill"] = master_sk["skill"].astype(str)
    master_skill_map = master_sk.groupby("master_id")["skill"].apply(lambda s: set(s.tolist())).to_dict()

    skill_map = cand_sk.groupby("candidate_id")["skill"].apply(lambda s: set(s.astype(str))).to_dict()
    profile = profile.copy()
    profile["target_role"] = profile["job_position_name"].map(role_from_title)

    candidates = []
    for _, row in profile.iterrows():
        cid = int(row["candidate_id"])
        if cid not in skill_map:
            continue
        sk = set(skill_map[cid])
        if len(sk) < 6:
            continue
        candidates.append((cid, row["target_role"], sk))
    candidates = candidates[: args.max_candidates]

    all_master_ids = masters_feat["master_id"].dropna().astype(int).unique().tolist()
    all_master_set = set(all_master_ids)

    rows = []
    for cid, role, sk in candidates:
        # Holdout aleatorio con seed por candidato: reproducible y sin sesgo alfabético
        ordered = sorted(sk)
        rng_cand = np.random.default_rng(cid)
        rng_cand.shuffle(ordered)
        holdout_n = max(1, int(round(0.2 * len(ordered))))
        holdout = set(ordered[:holdout_n])
        observed = set(ordered[holdout_n:])

        demand = role_skill[role_skill["role_family"].str.lower() == role.lower()].copy()
        if demand.empty:
            demand = role_skill.copy()
        demand = demand.sort_values("demand_count", ascending=False)
        target_skills = set(demand["skill"].dropna().astype(str).head(40).tolist())
        gap_set = target_skills - observed
        gap_text = " ".join(sorted(gap_set)) if gap_set else " ".join(sorted(target_skills))

        m = masters_feat.copy()
        m["master_id"] = m["master_id"].astype(int)
        m["gap_coverage"] = m["master_id"].map(lambda mid: len(master_skill_map.get(mid, set()) & gap_set)).astype(float)
        m["coverage_score"] = m["gap_coverage"] / max(float(m["gap_coverage"].max()), 1.0)

        texts = [gap_text] + m["master_text"].fillna("").astype(str).tolist()
        emb, _ = model_mod.embed_texts(texts)
        sim = model_mod.cosine_similarity_matrix(emb[:1], emb[1:]).ravel()
        m["semantic_score"] = sim

        f = model_mod.build_master_rerank_features(m, master_sk, gap_text)

        # weak supervision target
        hold_cov = f["master_id"].map(lambda mid: len(master_skill_map.get(int(mid), set()) & holdout)).astype(float)
        hold_ratio = hold_cov / max(len(holdout), 1)
        gap_ratio = f["gap_coverage"] / max(len(gap_set), 1)
        y = 0.7 * hold_ratio + 0.3 * gap_ratio

        f = f.assign(
            candidate_id=cid,
            target_role=role,
            label=y,
            holdout_cov=hold_cov,
        )

        pos = f[(f["holdout_cov"] > 0) | (f["gap_coverage"] > 0)]
        neg = f[(f["holdout_cov"] <= 0) & (f["gap_coverage"] <= 0)]

        n_neg = min(len(neg), args.negatives_per_candidate)
        neg_sample = neg.sample(n=n_neg, random_state=args.random_seed) if n_neg > 0 else neg.head(0)

        out = pd.concat([pos, neg_sample], ignore_index=True)
        rows.append(out)

    if not rows:
        raise RuntimeError("No training rows generated for reranker")

    train_df = pd.concat(rows, ignore_index=True)
    train_df.to_csv(edir / "master_reranker_trainset.csv", index=False, encoding="utf-8")

    feature_cols = [
        "coverage_score",
        "semantic_score",
        "gap_coverage",
        "master_skill_count",
        "price_missing",
        "price_filled",
        "study_len",
        "lexical_overlap",
        "gap_ratio",
    ]

    candidate_ids = train_df["candidate_id"].drop_duplicates().tolist()
    rng.shuffle(candidate_ids)
    split = int(0.8 * len(candidate_ids))
    train_ids = set(candidate_ids[:split])
    test_ids = set(candidate_ids[split:])

    tr = train_df[train_df["candidate_id"].isin(train_ids)].copy()
    te = train_df[train_df["candidate_id"].isin(test_ids)].copy()

    x_tr = tr[feature_cols].fillna(0.0).to_numpy()
    y_tr = tr["label"].to_numpy()
    x_te = te[feature_cols].fillna(0.0).to_numpy()
    y_te = te["label"].to_numpy()

    model = GradientBoostingRegressor(
        max_depth=6,
        learning_rate=0.05,
        n_estimators=300,
        random_state=args.random_seed,
    )
    model.fit(x_tr, y_tr)

    pred = model.predict(x_te)
    rmse = float(np.sqrt(mean_squared_error(y_te, pred))) if len(y_te) else None
    mae = float(mean_absolute_error(y_te, pred)) if len(y_te) else None
    r2 = float(r2_score(y_te, pred)) if len(y_te) else None

    ndcg_vals = []
    for cid, g in te.groupby("candidate_id"):
        yp = model.predict(g[feature_cols].fillna(0.0).to_numpy())
        yt = g["label"].to_numpy()
        ndcg_vals.append(ndcg_at_k(yt, yp, k=10))
    avg_ndcg10 = float(np.mean(ndcg_vals)) if ndcg_vals else None

    with (mdir / "master_reranker.pkl").open("wb") as f:
        pickle.dump(model, f)

    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "n_candidates_total": int(len(candidates)),
        "n_candidates_train": int(len(train_ids)),
        "n_candidates_test": int(len(test_ids)),
        "rows_trainset": int(len(train_df)),
        "rows_train": int(len(tr)),
        "rows_test": int(len(te)),
        "features": feature_cols,
        "metrics": {
            "rmse": rmse,
            "mae": mae,
            "r2": r2,
            "avg_ndcg10": avg_ndcg10,
        },
        "artifacts": {
            "model_path": str(mdir / "master_reranker.pkl"),
            "trainset_path": str(edir / "master_reranker_trainset.csv"),
        },
    }
    (rdir / "master_reranker_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
