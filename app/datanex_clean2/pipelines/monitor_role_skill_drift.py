import argparse
import json
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd


def _safe_ratio(a: float, b: float) -> float:
    if abs(b) < 1e-12:
        return 0.0
    return float(a / b)


def main():
    ap = argparse.ArgumentParser(description="Track drift in role_skill_demand over time.")
    ap.add_argument("--current", default=None)
    ap.add_argument("--snapshots-dir", default=None)
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args()

    current_path = Path(args.current)
    snaps = Path(args.snapshots_dir)
    out_json = Path(args.out_json)
    snaps.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    cur = pd.read_csv(current_path)
    cur["role_family"] = cur["role_family"].astype(str).str.lower().str.strip()
    cur["skill"] = cur["skill"].astype(str).str.lower().str.strip()
    cur["demand_ratio"] = pd.to_numeric(cur.get("demand_ratio"), errors="coerce").fillna(0.0).clip(0.0, 1.0)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    cur_snap = snaps / f"role_skill_demand_{ts}.csv"
    cur.to_csv(cur_snap, index=False, encoding="utf-8")

    prev_files = sorted(snaps.glob("role_skill_demand_*.csv"))
    prev_files = [p for p in prev_files if p.name != cur_snap.name]
    if not prev_files:
        obj = {
            "timestamp": ts,
            "status": "no_previous_snapshot",
            "current_snapshot": str(cur_snap),
        }
        out_json.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(obj, indent=2, ensure_ascii=False))
        return

    prev_path = prev_files[-1]
    prev = pd.read_csv(prev_path)
    prev["role_family"] = prev["role_family"].astype(str).str.lower().str.strip()
    prev["skill"] = prev["skill"].astype(str).str.lower().str.strip()
    prev["demand_ratio"] = pd.to_numeric(prev.get("demand_ratio"), errors="coerce").fillna(0.0).clip(0.0, 1.0)

    key = ["role_family", "skill"]
    m = cur[key + ["demand_ratio"]].merge(
        prev[key + ["demand_ratio"]],
        on=key,
        how="outer",
        suffixes=("_cur", "_prev"),
    ).fillna(0.0)
    m["abs_delta"] = (m["demand_ratio_cur"] - m["demand_ratio_prev"]).abs()
    m["pct_delta"] = m.apply(
        lambda r: _safe_ratio(float(r["demand_ratio_cur"] - r["demand_ratio_prev"]), max(float(r["demand_ratio_prev"]), 1e-6)),
        axis=1,
    )

    drift_global = float(m["abs_delta"].mean()) if len(m) else 0.0
    role_rows = []
    for role, g in m.groupby("role_family"):
        role_rows.append(
            {
                "role_family": role,
                "mean_abs_delta": float(g["abs_delta"].mean()),
                "p90_abs_delta": float(np.quantile(g["abs_delta"], 0.9)) if len(g) else 0.0,
                "skills_changed_gt_0_02": int((g["abs_delta"] >= 0.02).sum()),
            }
        )

    top_changes = (
        m.sort_values("abs_delta", ascending=False)
        .head(25)[["role_family", "skill", "demand_ratio_prev", "demand_ratio_cur", "abs_delta"]]
        .to_dict(orient="records")
    )

    obj = {
        "timestamp": ts,
        "status": "ok",
        "current_snapshot": str(cur_snap),
        "previous_snapshot": str(prev_path),
        "global_mean_abs_delta": round(drift_global, 6),
        "role_drift": role_rows,
        "top_skill_changes": top_changes,
    }
    out_json.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(obj, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

