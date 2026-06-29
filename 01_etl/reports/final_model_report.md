# DataPath - Final Model Report

Generated at: 2026-03-08 12:09:11

## 1. ETL & Feature Layer Status
- ETL rows summary: {}
- Semantic rows summary: {}

## 2. Training (Hyperparameter Search)
- Training report: {"timestamp": "2026-03-07 18:40:48", "max_candidates": 40, "best": {"weight_coverage": 0.65, "weight_semantic": 0.35, "n_candidates": 19.0, "avg_recall_holdout": 0.9473684210526315, "std_recall_holdout": 0.22329687826943603, "avg_gap_reduction": 0.7191767659259919, "std_gap_reduction": 0.039429098231935814, "objective": 0.8560917590019756}, "grid_rows": 6, "output_grid": "C:\\Users\\Nacho\\Documents\\TFM\\ETL\\outputs\\evaluation\\training_grid_results.csv"}

## 3. Evaluation Metrics
- Eval report: {"timestamp": "2026-03-07 18:43:34", "n_candidates_evaluated": 50, "weights": {"coverage": 0.65, "semantic": 0.35}, "metrics": {"avg_recall_holdout": 0.96, "avg_miss_rate": 0.04, "avg_gap_reduction": 0.7347349078452019, "avg_precision_like": 0.0503637613205829, "mae_gap_error_abs": 9.18, "avg_normalized_gap_error": 0.26526509215479804, "recall_holdout_ci95": [0.91, 1.0], "miss_rate_ci95": [0.0, 0.09], "gap_reduction_ci95": [0.7249755688915616, 0.7438831565140389], "precision_like_ci95": [0.04432257518038627, 0.057226514932676845], "normalized_gap_error_ci95": [0.25611684348596114, 0.2750244311084385]}, "outputs": {"candidate_level_metrics": "C:\\Users\\Nacho\\Documents\\TFM\\ETL\\outputs\\evaluation\\candidate_level_metrics.csv", "role_breakdown": "C:\\Users\\Nacho\\Documents\\TFM\\ETL\\reports\\model_eval_role_breakdown.csv"}}

## 4. Ablation Study
- Ablation report: {"timestamp": "2026-03-07 18:44:13", "n_candidates": 30, "best_variant": {"variant": "hybrid_tuned", "weight_coverage": 0.65, "weight_semantic": 0.35, "avg_recall": 0.9333333333333333, "avg_gap_reduction": 0.7176021170138817, "objective": 0.8470408468055526, "n": 15}, "baseline_objective": 0.8446707509648685, "relative_lift_vs_coverage_only": 0.002805940466124434, "results_path": "C:\\Users\\Nacho\\Documents\\TFM\\ETL\\outputs\\evaluation\\ablation_results.csv"}

## 5. Reranker Layer
- Reranker training report: {"timestamp": "2026-03-07 19:04:07", "n_candidates_total": 80, "n_candidates_train": 64, "n_candidates_test": 16, "rows_trainset": 153811, "rows_train": 121956, "rows_test": 31855, "features": ["coverage_score", "semantic_score", "gap_coverage", "master_skill_count", "price_missing", "price_filled", "study_len", "lexical_overlap", "gap_ratio"], "metrics": {"rmse": 0.25722102215302983, "mae": 0.2123063612551352, "r2": 0.11934680335982994, "avg_ndcg10": 0.5864539758582521}, "artifacts": {"model_path": "C:\\Users\\Nacho\\Documents\\TFM\\ETL\\outputs\\model\\master_reranker.pkl", "trainset_path": "C:\\Users\\Nacho\\Documents\\TFM\\ETL\\outputs\\evaluation\\master_reranker_trainset.csv"}}
- Reranker blend tuning report: {"timestamp": "2026-03-08 12:08:16", "weights": {"coverage": 0.65, "semantic": 0.35}, "base": {"blend": 0.0, "avg_recall": 0.96, "avg_miss_rate": 0.04, "avg_gap_reduction": 0.7347349078452019, "avg_precision_like": 0.0503637613205829, "avg_objective": 0.7676670846623992, "n_candidates": 50.0}, "best": {"blend": 0.0, "avg_recall": 0.96, "avg_miss_rate": 0.04, "avg_gap_reduction": 0.7347349078452019, "avg_precision_like": 0.0503637613205829, "avg_objective": 0.7676670846623992, "n_candidates": 50.0}, "policy": {"timestamp": "2026-03-08 12:08:16", "use_reranker_default": false, "reranker_blend": 0.0, "base_blend": 0.0}, "grid_path": "C:\\Users\\Nacho\\Documents\\TFM\\ETL\\outputs\\evaluation\\reranker_blend_grid.csv"}
- Base vs reranker report: {"timestamp": "2026-03-07 19:07:50", "n_candidates": 50, "base": {"avg_recall": 0.96, "avg_miss_rate": 0.04, "avg_gap_reduction": 0.7347349078452019, "avg_precision_like": 0.0503637613205829}, "reranker": {"avg_recall": 0.96, "avg_miss_rate": 0.04, "avg_gap_reduction": 0.6624733790322026, "avg_precision_like": 0.056852694607924546}, "delta": {"recall": 0.0, "miss_rate": 0.0, "gap_reduction": -0.07226152881299941, "precision_like": 0.006488933287341638}, "artifact": "C:\\Users\\Nacho\\Documents\\TFM\\ETL\\outputs\\evaluation\\base_vs_reranker.csv"}

## 6. Key Data Signals
- Candidates evaluated: 50
- Top master skills (top 10):
  - data analysis: 1302
  - machine learning: 952
  - statistics: 898
  - data visualization: 403
  - mathematics: 230
  - deep learning: 205
  - python: 193
  - nlp: 125
  - r: 87
  - computer vision: 86
- Top job skills (top 10):
  - data analysis: 12219
  - python: 11256
  - sql: 9397
  - machine learning: 8336
  - aws: 6700
  - azure: 5586
  - excel: 5538
  - statistics: 4585
  - data engineering: 4140
  - gcp: 3869

## 7. Figures
- reports/figures/01_training_grid.png
- reports/figures/02_ablation.png
- reports/figures/03_metric_distributions.png
- reports/figures/04_role_breakdown.png
- reports/figures/05_base_vs_reranker.png