"""01_etl_curated_layer.py
Run curated ETL layer from raw datasets into outputs/curated.
"""
import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser(description="Run curated ETL layer")
    p.add_argument("--sample-rows", type=int, default=0)
    p.add_argument("--raw-dir", default=None)
    p.add_argument("--etl-dir", default=None)
    args = p.parse_args()

    etl_dir = Path(args.etl_dir)
    script = etl_dir / "pipelines" / "etl_pipeline_v2.py"

    cmd = [
        sys.executable,
        str(script),
        "--raw-dir", args.raw_dir,
        "--out-dir", str(etl_dir),
        "--taxonomy-path", str(etl_dir / "config" / "skills_taxonomy.json"),
    ]
    if args.sample_rows > 0:
        cmd += ["--sample-rows", str(args.sample_rows)]

    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
