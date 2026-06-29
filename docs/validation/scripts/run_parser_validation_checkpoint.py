"""
Checkpointed runner for the parser-only part of run_validation_500cvs.py.

It reuses the validation helpers from run_validation_500cvs.py, writes one
JSON row per processed CV, and then materializes the standard CSV/JSON outputs.
Run with python -B to avoid stale bytecode.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
SOURCE = BASE / "run_validation_500cvs.py"

spec = importlib.util.spec_from_file_location("run_validation_500cvs_source", SOURCE)
rv = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(rv)

CHECKPOINT = rv.OUT_DIR / "validation_500_parser_metrics.checkpoint.jsonl"
OUT_CSV = rv.OUT_DIR / "validation_500_parser_metrics.csv"
OUT_JSON = rv.OUT_DIR / "validation_500_parser_summary.json"


def row_for_pdf(pdf: Path, taxonomy: dict, alias_map: dict[str, str], manual_canon: dict[str, set[str]], model_mod) -> dict:
    canon_name = rv.canonical_filename(pdf.name)

    if canon_name in manual_canon:
        expected = manual_canon[canon_name]
        annotation = "manual"
    else:
        raw_text = rv.read_pdf_text(pdf)
        expected = rv.extract_skills_from_text_section(raw_text, alias_map)
        annotation = "auto"

    try:
        with rv.pdfplumber.open(str(pdf)) as doc:
            text = "\n".join(page.extract_text() or "" for page in doc.pages)
    except Exception as e:
        return {
            "cv_file": pdf.name, "status": "error", "annotation": annotation,
            "expected_n": len(expected), "detected_n": 0,
            "tp": 0, "fp": 0, "fn": len(expected),
            "precision": 0.0, "recall": 0.0, "f1": 0.0,
            "expected_skills": "; ".join(sorted(expected)),
            "detected_skills": "", "false_positives": "",
            "false_negatives": "; ".join(sorted(expected)),
            "notes": f"PDF read error: {e}",
        }

    if not text.strip():
        return {
            "cv_file": pdf.name, "status": "excluded_empty_text", "annotation": annotation,
            "expected_n": len(expected), "detected_n": 0,
            "tp": 0, "fp": 0, "fn": len(expected),
            "precision": 0.0, "recall": 0.0, "f1": 0.0,
            "expected_skills": "; ".join(sorted(expected)),
            "detected_skills": "", "false_positives": "",
            "false_negatives": "; ".join(sorted(expected)),
            "notes": "PDF text extraction returned empty content; excluded.",
        }

    profile = model_mod.build_candidate_profile_hybrid(text, taxonomy)
    detected = {s.strip().lower() for s in profile.get("skills_detected", []) if s.strip()}

    tp_set = expected & detected
    fp_set = detected - expected if expected else set()
    fn_set = expected - detected

    if not expected:
        return {
            "cv_file": pdf.name, "status": "no_expected_skills", "annotation": annotation,
            "expected_n": 0, "detected_n": len(detected),
            "tp": 0, "fp": len(detected), "fn": 0,
            "precision": 0.0, "recall": 1.0, "f1": 0.0,
            "expected_skills": "",
            "detected_skills": "; ".join(sorted(detected)),
            "false_positives": "; ".join(sorted(detected)),
            "false_negatives": "",
            "notes": "No expected skills defined for this CV (non-technical profile or unannotated).",
        }

    precision = rv.safe_div(len(tp_set), len(tp_set) + len(fp_set))
    recall = rv.safe_div(len(tp_set), len(tp_set) + len(fn_set))
    f1 = rv.safe_div(2 * precision * recall, precision + recall)

    return {
        "cv_file": pdf.name, "status": "evaluated", "annotation": annotation,
        "expected_n": len(expected), "detected_n": len(detected),
        "tp": len(tp_set), "fp": len(fp_set), "fn": len(fn_set),
        "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4),
        "expected_skills": "; ".join(sorted(expected)),
        "detected_skills": "; ".join(sorted(detected)),
        "false_positives": "; ".join(sorted(fp_set)),
        "false_negatives": "; ".join(sorted(fn_set)),
        "notes": "",
    }


def load_checkpoint() -> dict[str, dict]:
    rows: dict[str, dict] = {}
    if CHECKPOINT.exists():
        for line in CHECKPOINT.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                rows[row["cv_file"]] = row
    return rows


def write_outputs(rows: list[dict], n_auto_source: int) -> dict:
    if not rows:
        raise RuntimeError("No rows to write.")

    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    eval_rows = [r for r in rows if r["status"] == "evaluated"]
    manual_rows = [r for r in eval_rows if r["annotation"] == "manual"]
    auto_rows = [r for r in eval_rows if r["annotation"] == "auto"]

    def micro_metrics(rlist):
        tp = sum(int(r["tp"]) for r in rlist)
        fp = sum(int(r["fp"]) for r in rlist)
        fn = sum(int(r["fn"]) for r in rlist)
        p = rv.safe_div(tp, tp + fp)
        r_ = rv.safe_div(tp, tp + fn)
        f = rv.safe_div(2 * p * r_, p + r_)
        return tp, fp, fn, round(p, 4), round(r_, 4), round(f, 4)

    def macro_metrics(rlist):
        p = sum(float(r["precision"]) for r in rlist) / max(len(rlist), 1)
        r_ = sum(float(r["recall"]) for r in rlist) / max(len(rlist), 1)
        f = sum(float(r["f1"]) for r in rlist) / max(len(rlist), 1)
        return round(p, 4), round(r_, 4), round(f, 4)

    tp_all, fp_all, fn_all, mp_all, mr_all, mf_all = micro_metrics(eval_rows)
    mp_mac, mr_mac, mf_mac = macro_metrics(eval_rows)
    tp_m, fp_m, fn_m, mp_m, mr_m, mf_m = micro_metrics(manual_rows)

    summary = {
        "n_pdf_files": len(rows),
        "n_evaluated": len(eval_rows),
        "n_manual_annotation": len(manual_rows),
        "n_auto_annotation": len(auto_rows),
        "n_excluded_empty_text": len([r for r in rows if r["status"] == "excluded_empty_text"]),
        "n_no_expected_skills": len([r for r in rows if r["status"] == "no_expected_skills"]),
        "excluded_files": [r["cv_file"] for r in rows if r["status"] != "evaluated"],
        "global": {
            "total_tp": tp_all, "total_fp": fp_all, "total_fn": fn_all,
            "micro_precision": mp_all, "micro_recall": mr_all, "micro_f1": mf_all,
            "macro_precision": mp_mac, "macro_recall": mr_mac, "macro_f1": mf_mac,
            "mean_expected_skills": round(sum(int(r["expected_n"]) for r in eval_rows) / max(len(eval_rows), 1), 2),
            "mean_detected_skills": round(sum(int(r["detected_n"]) for r in eval_rows) / max(len(eval_rows), 1), 2),
        },
        "manual_only": {
            "n": len(manual_rows),
            "total_tp": tp_m, "total_fp": fp_m, "total_fn": fn_m,
            "micro_precision": mp_m, "micro_recall": mr_m, "micro_f1": mf_m,
        },
        "annotation_policy": (
            "88 CVs with manual reference labels; "
            f"{n_auto_source} CVs with auto-extracted labels from HABILIDADES section mapped to taxonomy. "
            "Empty-text PDFs excluded from aggregates."
        ),
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def main() -> None:
    taxonomy = json.loads(rv.TAXONOMY_PATH.read_text(encoding="utf-8"))
    sys.path.insert(0, str(rv.APP_DIR / "pipelines"))
    model_mod = rv.load_model_module()
    alias_map = rv.build_alias_map(taxonomy)
    manual_canon = {
        rv.canonical_filename(k): {s.lower() for s in v}
        for k, v in rv.MANUAL_EXPECTED.items()
    }

    pdf_files = sorted(rv.CV_DIR.glob("*.pdf"))
    rows_by_file = load_checkpoint()
    processed = set(rows_by_file)
    n_auto_source = sum(1 for pdf in pdf_files if rv.canonical_filename(pdf.name) not in manual_canon)

    rv.OUT_DIR.mkdir(parents=True, exist_ok=True)
    with CHECKPOINT.open("a", encoding="utf-8") as ckpt:
        for idx, pdf in enumerate(pdf_files, start=1):
            if pdf.name in processed:
                continue
            row = row_for_pdf(pdf, taxonomy, alias_map, manual_canon, model_mod)
            rows_by_file[pdf.name] = row
            ckpt.write(json.dumps(row, ensure_ascii=False) + "\n")
            ckpt.flush()
            safe_name = pdf.name.encode("ascii", "backslashreplace").decode("ascii")
            print(f"[{idx:03d}/{len(pdf_files)}] {safe_name}: {row['status']} exp={row['expected_n']} det={row['detected_n']}", flush=True)

    rows = [rows_by_file[pdf.name] for pdf in pdf_files if pdf.name in rows_by_file]
    summary = write_outputs(rows, n_auto_source)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
