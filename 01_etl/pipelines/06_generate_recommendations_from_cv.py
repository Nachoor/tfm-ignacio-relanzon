"""06_generate_recommendations_from_cv.py
Inference script for final recommendations using tuned weights and tuned reranker policy.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate recommendations from CV")
    ap.add_argument("--etl-dir", default=None)
    ap.add_argument("--resume-text", default="")
    ap.add_argument("--resume-pdf", default="")
    ap.add_argument("--target-role", default="ml_engineer")
    ap.add_argument("--max-price", type=float, default=None)
    ap.add_argument("--location", default="")
    ap.add_argument("--study-keyword", default="")
    ap.add_argument("--use-master-reranker", action="store_true")
    ap.add_argument("--disable-master-reranker", action="store_true")
    ap.add_argument("--reranker-blend", type=float, default=None)
    args = ap.parse_args()

    etl_dir = Path(args.etl_dir)
    tuned_path = etl_dir / "reports" / "model_tuned_params.json"
    reranker_tuned_path = etl_dir / "reports" / "reranker_tuned_params.json"
    reranker_path = etl_dir / "outputs" / "model" / "master_reranker.pkl"

    wc, ws = 0.6, 0.4
    if tuned_path.exists():
        tuned = json.loads(tuned_path.read_text(encoding="utf-8"))
        wc = float(tuned.get("weight_coverage", wc))
        ws = float(tuned.get("weight_semantic", ws))

    use_reranker_default = False
    tuned_blend = 0.25
    if reranker_tuned_path.exists():
        rt = json.loads(reranker_tuned_path.read_text(encoding="utf-8"))
        use_reranker_default = bool(rt.get("use_reranker_default", False))
        tuned_blend = float(rt.get("reranker_blend", tuned_blend))

    if args.reranker_blend is not None:
        final_blend = float(args.reranker_blend)
    else:
        final_blend = tuned_blend

    # Priority: explicit disable > explicit enable > tuned default
    if args.disable_master_reranker:
        use_reranker = False
    elif args.use_master_reranker:
        use_reranker = True
    else:
        use_reranker = use_reranker_default

    use_reranker = use_reranker and reranker_path.exists()

    script = etl_dir / "pipelines" / "build_datapath_model_advanced.py"
    cmd = [
        sys.executable,
        str(script),
        "--etl-dir", str(etl_dir),
        "--taxonomy", str(etl_dir / "config" / "skills_taxonomy.json"),
        "--target-role", args.target_role,
        "--out-dir", str(etl_dir / "outputs" / "model"),
        "--weight-coverage", str(wc),
        "--weight-semantic", str(ws),
    ]

    if use_reranker:
        cmd += [
            "--use-master-reranker",
            "--master-reranker-path", str(reranker_path),
            "--reranker-blend", str(final_blend),
        ]

    if args.resume_pdf:
        cmd += ["--resume-pdf", args.resume_pdf]
    else:
        cmd += ["--resume-text", args.resume_text]

    if args.max_price is not None:
        cmd += ["--max-price", str(args.max_price)]
    if args.location:
        cmd += ["--location", args.location]
    if args.study_keyword:
        cmd += ["--study-keyword", args.study_keyword]

    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
