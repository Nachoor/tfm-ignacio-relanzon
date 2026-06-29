"""02_build_semantic_features.py
Build semantic-ready feature layer for advanced recommender.
"""
import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser(description="Build semantic feature layer")
    p.add_argument("--etl-dir", default=None)
    args = p.parse_args()

    etl_dir = Path(args.etl_dir)
    script = etl_dir / "pipelines" / "etl_semantic_layer.py"
    subprocess.run([sys.executable, str(script), "--etl-dir", str(etl_dir)], check=True)


if __name__ == "__main__":
    main()
