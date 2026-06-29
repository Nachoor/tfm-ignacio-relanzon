"""Run one autonomous price enrichment cycle.

Cycle:
1) Build priority queue
2) Try browser scraping batch (best effort)
3) Import UiPath output prices
4) Export valid scraped prices
5) Safe merge UiPath prices
6) Safe merge scraped prices
7) Print coverage summary
"""
from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
SEM_DIR = BASE_DIR / "outputs" / "semantic"
PIPE_DIR = BASE_DIR / "pipelines"


def run(cmd: list[str], env: dict | None = None) -> int:
    e = os.environ.copy()
    if env:
        e.update(env)
    p = subprocess.run(cmd, cwd=str(BASE_DIR), env=e)
    return p.returncode


def coverage() -> tuple[int, int, float]:
    m = SEM_DIR / "course_prices_manual.csv"
    if not m.exists():
        return (0, 0, 0.0)
    df = pd.read_csv(m)
    total = len(df)
    if "PRIC" not in df.columns:
        return (0, total, 0.0)
    s = df["PRIC"].astype(str)
    ok = s.str.contains(r"\d").sum()
    return (int(ok), int(total), (float(ok) / max(1, total)))


def main() -> None:
    python = sys.executable
    print("step=build_priority_queue")
    run([python, str(PIPE_DIR / "build_course_price_priority_queue.py")])

    print("step=scrape_batch_best_effort")
    run(
        [python, str(PIPE_DIR / "scrape_course_prices_playwright.py")],
        env={
            "FORCE_RESCRAPE": "0",
            "START_INDEX": os.getenv("START_INDEX", "0"),
            "MAX_ROWS": os.getenv("MAX_ROWS", "120"),
            "SAVE_EVERY": os.getenv("SAVE_EVERY", "20"),
            "HEADLESS": os.getenv("HEADLESS", "0"),
            "CHALLENGE_WAIT_MS": os.getenv("CHALLENGE_WAIT_MS", "8000"),
            "CF_MAX_WAIT_MS": os.getenv("CF_MAX_WAIT_MS", "60000"),
        },
    )

    print("step=import_uipath")
    run([python, str(PIPE_DIR / "import_uipath_output_prices.py")])

    print("step=export_scraped_safe")
    run([python, str(PIPE_DIR / "export_scraped_prices_for_safe_update.py")])

    print("step=safe_merge_uipath")
    run(
        [python, str(PIPE_DIR / "safe_price_update.py")],
        env={"SRC_FILE": "course_prices_from_uipath.csv"},
    )

    print("step=safe_merge_scraped")
    run(
        [python, str(PIPE_DIR / "safe_price_update.py")],
        env={"SRC_FILE": "course_prices_from_scraped.csv"},
    )

    ok, total, cov = coverage()
    print(f"coverage_valid={ok}/{total} ({cov:.2%})")


if __name__ == "__main__":
    main()

