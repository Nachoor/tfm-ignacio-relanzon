import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression


def _fit_piecewise_isotonic(y_pred: np.ndarray, y_true: np.ndarray) -> dict:
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    iso.fit(y_pred, y_true)
    grid = np.linspace(0.0, 1.0, 21)
    mapped = iso.predict(grid)
    return {"x": [round(float(v), 6) for v in grid], "y": [round(float(v), 6) for v in mapped]}


def main():
    ap = argparse.ArgumentParser(description="Train score calibration map from evaluation details.")
    ap.add_argument("--eval-csv", default=None)
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args()

    eval_csv = Path(args.eval_csv)
    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    if not eval_csv.exists():
        raise FileNotFoundError(f"Missing eval csv: {eval_csv}")
    df = pd.read_csv(eval_csv)
    df = df.dropna(subset=["y_true", "y_pred"]).copy()
    if df.empty or len(df) < 6:
        obj = {
            "version": 1,
            "kind": "isotonic_piecewise",
            "enabled": False,
            "note": "insufficient_data_identity_map",
            "x": [0.0, 1.0],
            "y": [0.0, 1.0],
            "by_role": {},
        }
        out_json.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(obj, indent=2, ensure_ascii=False))
        return

    y_true = np.clip(df["y_true"].to_numpy(dtype=float), 0.0, 1.0)
    y_pred = np.clip(df["y_pred"].to_numpy(dtype=float), 0.0, 1.0)
    global_map = _fit_piecewise_isotonic(y_pred, y_true)

    by_role = {}
    if "target_role" in df.columns:
        for role, g in df.groupby("target_role"):
            if len(g) < 6:
                continue
            r_true = np.clip(g["y_true"].to_numpy(dtype=float), 0.0, 1.0)
            r_pred = np.clip(g["y_pred"].to_numpy(dtype=float), 0.0, 1.0)
            by_role[str(role)] = _fit_piecewise_isotonic(r_pred, r_true)

    out = {
        "version": 1,
        "kind": "isotonic_piecewise",
        "n_samples": int(len(df)),
        "enabled": bool(len(df) >= 40 and len(by_role) >= 3),
        "apply_global": bool(len(by_role) >= 3),
        "x": global_map["x"],
        "y": global_map["y"],
        "by_role": by_role,
    }
    out_json.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
