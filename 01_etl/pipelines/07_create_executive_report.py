"""07_create_executive_report.py
Generate executive markdown report and figures for the DataPath model.
Outputs:
- reports/figures/*.png
- reports/final_model_report.md
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def safe_read_csv(path: Path):
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def safe_read_json(path: Path):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def plot_training_grid(df: pd.DataFrame, out_path: Path):
    if df.empty:
        return False
    d = df.sort_values("weight_coverage")
    plt.figure(figsize=(8, 4.5))
    plt.plot(d["weight_coverage"], d["avg_recall_holdout"], marker="o", label="Recall holdout")
    plt.plot(d["weight_coverage"], d["avg_gap_reduction"], marker="s", label="Gap reduction")
    plt.plot(d["weight_coverage"], d["objective"], marker="^", label="Objective")
    plt.title("Grid Search: pesos coverage vs semantic")
    plt.xlabel("weight_coverage")
    plt.ylabel("score")
    plt.ylim(0, 1.05)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()
    return True


def plot_ablation(df: pd.DataFrame, out_path: Path):
    if df.empty:
        return False
    d = df.sort_values("objective", ascending=False)
    plt.figure(figsize=(8.5, 4.8))
    plt.bar(d["variant"], d["objective"])
    plt.title("Ablation Study: objective por variante")
    plt.ylabel("objective")
    plt.ylim(0, max(0.01, d["objective"].max() * 1.1))
    plt.xticks(rotation=15, ha="right")
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()
    return True


def plot_metric_distributions(df: pd.DataFrame, out_path: Path):
    if df.empty:
        return False
    cols = ["recall_holdout", "miss_rate", "gap_reduction", "precision_like", "normalized_gap_error"]
    cols = [c for c in cols if c in df.columns]
    if not cols:
        return False
    fig, axes = plt.subplots(1, len(cols), figsize=(4.2 * len(cols), 4.2))
    if len(cols) == 1:
        axes = [axes]
    for ax, c in zip(axes, cols):
        ax.hist(df[c].dropna(), bins=20)
        ax.set_title(c)
        ax.grid(alpha=0.25)
    fig.suptitle("Distribuciones de metricas por candidato")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    return True


def plot_role_breakdown(df: pd.DataFrame, out_path: Path):
    if df.empty or "role" not in df.columns or "avg_recall_holdout" not in df.columns:
        return False
    d = df.sort_values("n_candidates", ascending=False)
    plt.figure(figsize=(8, 4.5))
    plt.bar(d["role"], d["avg_recall_holdout"], label="avg_recall_holdout")
    if "avg_gap_reduction" in d.columns:
        plt.plot(d["role"], d["avg_gap_reduction"], marker="o", label="avg_gap_reduction")
    plt.title("Rendimiento por familia de rol")
    plt.ylabel("score")
    plt.ylim(0, 1.05)
    plt.xticks(rotation=20, ha="right")
    plt.grid(alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()
    return True


def plot_base_vs_reranker(df: pd.DataFrame, out_path: Path):
    if df.empty:
        return False
    metrics = {
        "recall": (df["base_recall"].mean(), df["rerank_recall"].mean()),
        "gap_reduction": (df["base_gap_reduction"].mean(), df["rerank_gap_reduction"].mean()),
        "precision_like": (df["base_precision_like"].mean(), df["rerank_precision_like"].mean()),
    }
    x = list(metrics.keys())
    base_vals = [metrics[k][0] for k in x]
    rerank_vals = [metrics[k][1] for k in x]

    idx = range(len(x))
    w = 0.35
    plt.figure(figsize=(8.2, 4.8))
    plt.bar([i - w / 2 for i in idx], base_vals, width=w, label="base")
    plt.bar([i + w / 2 for i in idx], rerank_vals, width=w, label="reranker")
    plt.xticks(list(idx), x)
    plt.ylim(0, 1.05)
    plt.title("Base vs Reranker")
    plt.grid(alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()
    return True


def top_skills_table(path: Path, col: str = "skill", n: int = 20):
    df = safe_read_csv(path)
    if df.empty or col not in df.columns:
        return pd.DataFrame()
    return (
        df[col]
        .astype(str)
        .str.strip()
        .value_counts()
        .head(n)
        .rename_axis("skill")
        .reset_index(name="count")
    )


def main():
    ap = argparse.ArgumentParser(description="Create executive report and figures")
    ap.add_argument("--etl-dir", default=None)
    args = ap.parse_args()

    etl_dir = Path(args.etl_dir)
    reports_dir = etl_dir / "reports"
    figures_dir = reports_dir / "figures"
    eval_dir = etl_dir / "outputs" / "evaluation"
    curated_dir = etl_dir / "outputs" / "curated"

    reports_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    etl_report = safe_read_json(reports_dir / "etl_report_v2.json")
    sem_report = safe_read_json(reports_dir / "semantic_layer_report.json")
    train_report = safe_read_json(reports_dir / "model_training_report.json")
    eval_report = safe_read_json(reports_dir / "model_eval_report.json")
    ablation_report = safe_read_json(reports_dir / "ablation_report.json")
    reranker_report = safe_read_json(reports_dir / "master_reranker_report.json")
    reranker_blend_report = safe_read_json(reports_dir / "reranker_blend_report.json")
    compare_report = safe_read_json(reports_dir / "base_vs_reranker_report.json")

    grid_df = safe_read_csv(eval_dir / "training_grid_results.csv")
    ablation_df = safe_read_csv(eval_dir / "ablation_results.csv")
    metrics_df = safe_read_csv(eval_dir / "candidate_level_metrics.csv")
    role_df = safe_read_csv(reports_dir / "model_eval_role_breakdown.csv")
    cmp_df = safe_read_csv(eval_dir / "base_vs_reranker.csv")

    fig_training = figures_dir / "01_training_grid.png"
    fig_ablation = figures_dir / "02_ablation.png"
    fig_dist = figures_dir / "03_metric_distributions.png"
    fig_roles = figures_dir / "04_role_breakdown.png"
    fig_compare = figures_dir / "05_base_vs_reranker.png"

    generated = []
    if plot_training_grid(grid_df, fig_training):
        generated.append(fig_training.name)
    if plot_ablation(ablation_df, fig_ablation):
        generated.append(fig_ablation.name)
    if plot_metric_distributions(metrics_df, fig_dist):
        generated.append(fig_dist.name)
    if plot_role_breakdown(role_df, fig_roles):
        generated.append(fig_roles.name)
    if plot_base_vs_reranker(cmp_df, fig_compare):
        generated.append(fig_compare.name)

    top_master_skills = top_skills_table(curated_dir / "master_skills.csv")
    top_job_skills = top_skills_table(curated_dir / "job_skills.csv")

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = []
    lines.append("# DataPath - Final Model Report")
    lines.append("")
    lines.append(f"Generated at: {ts}")
    lines.append("")
    lines.append("## 1. ETL & Feature Layer Status")
    lines.append(f"- ETL rows summary: {json.dumps(etl_report.get('rows', {}), ensure_ascii=False)}")
    lines.append(f"- Semantic rows summary: {json.dumps(sem_report.get('rows', {}), ensure_ascii=False)}")
    lines.append("")
    lines.append("## 2. Training (Hyperparameter Search)")
    lines.append(f"- Training report: {json.dumps(train_report, ensure_ascii=False)}")
    lines.append("")
    lines.append("## 3. Evaluation Metrics")
    lines.append(f"- Eval report: {json.dumps(eval_report, ensure_ascii=False)}")
    lines.append("")
    lines.append("## 4. Ablation Study")
    lines.append(f"- Ablation report: {json.dumps(ablation_report, ensure_ascii=False)}")
    lines.append("")
    lines.append("## 5. Reranker Layer")
    lines.append(f"- Reranker training report: {json.dumps(reranker_report, ensure_ascii=False)}")
    lines.append(f"- Reranker blend tuning report: {json.dumps(reranker_blend_report, ensure_ascii=False)}")
    lines.append(f"- Base vs reranker report: {json.dumps(compare_report, ensure_ascii=False)}")
    lines.append("")
    lines.append("## 6. Key Data Signals")
    lines.append(f"- Candidates evaluated: {len(metrics_df)}")
    if not top_master_skills.empty:
        lines.append("- Top master skills (top 10):")
        for _, r in top_master_skills.head(10).iterrows():
            lines.append(f"  - {r['skill']}: {int(r['count'])}")
    if not top_job_skills.empty:
        lines.append("- Top job skills (top 10):")
        for _, r in top_job_skills.head(10).iterrows():
            lines.append(f"  - {r['skill']}: {int(r['count'])}")
    lines.append("")
    lines.append("## 7. Figures")
    for f in generated:
        lines.append(f"- reports/figures/{f}")

    report_path = reports_dir / "final_model_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")

    summary = {
        "generated_at": ts,
        "report_path": str(report_path),
        "figures": generated,
        "n_candidates_evaluated": int(len(metrics_df)),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
