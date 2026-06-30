"""Create a manual template to curate course prices without scraping.

Output:
  outputs/semantic/course_prices_manual.csv
"""
from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
COURSES_PATH = BASE_DIR / "outputs" / "semantic" / "courses_features.csv"
OUT_PATH = BASE_DIR / "outputs" / "semantic" / "course_prices_manual.csv"


def main() -> None:
    courses = pd.read_csv(COURSES_PATH)
    cols = [c for c in ["course_id", "title", "url"] if c in courses.columns]
    tpl = courses[cols].drop_duplicates(subset=["course_id"]).copy()
    tpl["PRIC"] = ""
    tpl["PRIC_SOURCE"] = "manual"
    tpl["PRIC_CONFIDENCE"] = 1.0
    tpl.to_csv(OUT_PATH, index=False, encoding="utf-8")
    print(f"saved={OUT_PATH} rows={len(tpl)}")


if __name__ == "__main__":
    main()

