"""11_prepare_hf_space_bundle.py
Create a lightweight Hugging Face Spaces bundle for Datanex.

Output:
- hf_space_bundle/ (ready-to-upload Space folder)
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import pandas as pd


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def main() -> None:
    ap = argparse.ArgumentParser(description="Prepare Hugging Face Space bundle for Datanex")
    ap.add_argument("--etl-dir", default=None)
    ap.add_argument("--out-dir", default="")
    ap.add_argument("--max-jobs", type=int, default=120000, help="Max rows for jobs_features compact export")
    ap.add_argument("--max-courses", type=int, default=3000, help="Max rows for courses_features compact export")
    args = ap.parse_args()

    etl_dir = Path(args.etl_dir)
    out_dir = Path(args.out_dir) if args.out_dir else (etl_dir / "hf_space_bundle")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # App entry + dependencies
    copy_file(etl_dir / "app.py", out_dir / "app.py")
    copy_file(etl_dir / "datanex_app.py", out_dir / "datanex_app.py")
    copy_file(etl_dir / "requirements.txt", out_dir / "requirements.txt")
    # Keep compatibility with Spaces templates that use src/streamlit_app.py as launcher.
    src_streamlit = out_dir / "src" / "streamlit_app.py"
    src_streamlit.parent.mkdir(parents=True, exist_ok=True)
    src_streamlit.write_text(
        "from datanex_app import main\n\nif __name__ == '__main__':\n    main()\n",
        encoding="utf-8",
    )

    # Core model code
    copy_file(
        etl_dir / "pipelines" / "build_datapath_model_advanced.py",
        out_dir / "pipelines" / "build_datapath_model_advanced.py",
    )

    # Config
    copy_file(
        etl_dir / "config" / "skills_taxonomy.json",
        out_dir / "config" / "skills_taxonomy.json",
    )

    # Curated skill tables required by the app/model.
    for name in ["master_skills.csv", "course_skills.csv", "job_skills.csv"]:
        copy_file(etl_dir / "outputs" / "curated" / name, out_dir / "outputs" / "curated" / name)

    # Semantic tables required by the app/model.
    for name in ["masters_features.csv", "role_skill_demand.csv"]:
        copy_file(etl_dir / "outputs" / "semantic" / name, out_dir / "outputs" / "semantic" / name)

    # Compact courses features to avoid >10MB file limit in HF Spaces git push.
    courses_src = etl_dir / "outputs" / "semantic" / "courses_features.csv"
    courses_dst = out_dir / "outputs" / "semantic" / "courses_features.csv"
    courses_df = pd.read_csv(courses_src)
    courses_df = courses_df.head(args.max_courses)
    courses_df.to_csv(courses_dst, index=False, encoding="utf-8")

    # Compact jobs features for Space-size friendliness.
    jobs_src = etl_dir / "outputs" / "semantic" / "jobs_features.csv"
    jobs_dst = out_dir / "outputs" / "semantic" / "jobs_features.csv"
    jobs_df = pd.read_csv(jobs_src, usecols=["job_id", "site", "title", "company", "location", "job_level", "job_function", "role_family"])
    jobs_df = jobs_df.head(args.max_jobs)
    jobs_df.to_csv(jobs_dst, index=False, encoding="utf-8")

    # Keep Space lightweight and avoid binary push constraints.
    # Reranker model is not bundled; app will fallback to base recommender.
    for name in ["model_tuned_params.json", "reranker_tuned_params.json"]:
        p = etl_dir / "reports" / name
        if p.exists():
            copy_file(p, out_dir / "reports" / name)

    # Space README metadata.
    readme = out_dir / "README.md"
    readme.write_text(
        "\n".join(
            [
                "---",
                "title: Datanex",
                "sdk: streamlit",
                "app_file: src/streamlit_app.py",
                "---",
                "",
                "# Datanex",
                "",
                "Demo app for data-career guidance:",
                "- CV/Resume -> skill extraction",
                "- Skill gap vs target role",
                "- Master and course recommendations",
                "- Matching jobs",
            ]
        ),
        encoding="utf-8",
    )

    size_mb = sum(f.stat().st_size for f in out_dir.rglob("*") if f.is_file()) / (1024 * 1024)
    print(f"bundle_dir={out_dir}")
    print(f"bundle_size_mb={size_mb:.2f}")


if __name__ == "__main__":
    main()
