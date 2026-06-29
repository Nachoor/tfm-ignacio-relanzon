import argparse
import functools
import json
import os
import pickle
import re
from pathlib import Path

import numpy as np
import pandas as pd


def norm_text(x):
    if pd.isna(x):
        return ""
    return re.sub(r"\s+", " ", str(x)).strip()


def fix_spaced_letters(text: str) -> str:
    # Convert patterns like "P y t h o n" -> "Python"
    pattern = re.compile(r"(?:\b[A-Za-z]\s){2,}[A-Za-z]\b")

    def _join_letters(match):
        return match.group(0).replace(" ", "")

    out = pattern.sub(_join_letters, text)
    return norm_text(out)


def read_resume_pdf_text(path: Path) -> str:
    # Primary parser
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return fix_spaced_letters(" ".join(parts))
    except Exception:
        pass

    # Fallback parser
    try:
        import pdfplumber

        parts = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
        return fix_spaced_letters(" ".join(parts))
    except Exception:
        pass

    return ""


def load_taxonomy(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def contains_term(text: str, term: str) -> bool:
    t = f" {text.lower()} "
    q = term.lower()
    if q.startswith(" ") or q.endswith(" "):
        return q in t
    return re.search(rf"\b{re.escape(q)}\b", t) is not None


def extract_skills(text: str, taxonomy: dict) -> list[str]:
    txt = norm_text(text).lower()
    if not txt:
        return []
    found = []
    for skill, aliases in taxonomy.items():
        for alias in aliases:
            if contains_term(txt, alias):
                found.append(skill)
                break
    return sorted(set(found))


def cosine_similarity_matrix(a, b):
    try:
        from scipy import sparse
        from sklearn.metrics.pairwise import cosine_similarity

        if sparse.issparse(a) or sparse.issparse(b):
            return cosine_similarity(a, b)
    except Exception:
        pass

    a_norm = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-9)
    b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-9)
    return a_norm @ b_norm.T


@functools.lru_cache(maxsize=4)
def _get_sentence_transformer(model_name: str):
    """Singleton: carga el modelo una sola vez por proceso y lo reutiliza."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_name)


# Modelo multilingüe (ES + EN). Env: CAIQ_EMBED_MODEL para sobrescribir.
_DEFAULT_EMBED_MODEL = os.getenv("CAIQ_EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")

def embed_texts(texts: list[str], model_name: str | None = None):
    if model_name is None:
        model_name = _DEFAULT_EMBED_MODEL
    if os.getenv("CAIQ_EMBED_MODE", "").lower() == "tfidf":
        from sklearn.feature_extraction.text import TfidfVectorizer

        vec = TfidfVectorizer(max_features=40000, ngram_range=(1, 2))
        mat = vec.fit_transform(texts)
        return mat, "tfidf"

    # Try sentence-transformers first, fallback to TF-IDF.
    try:
        model = _get_sentence_transformer(model_name)
        emb = model.encode(texts, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=False)
        return emb, "sentence-transformers"
    except Exception:
        from sklearn.feature_extraction.text import TfidfVectorizer

        vec = TfidfVectorizer(max_features=40000, ngram_range=(1, 2))
        mat = vec.fit_transform(texts)
        return mat, "tfidf"


def tokenize_words(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z]{3,}", norm_text(text).lower()))


def build_master_rerank_features(
    mdf: pd.DataFrame,
    ms: pd.DataFrame,
    gap_text: str,
) -> pd.DataFrame:
    feat = mdf.copy()
    skill_count_map = ms.groupby("master_id")["skill"].nunique().to_dict()
    feat["master_skill_count"] = feat["master_id"].map(skill_count_map).fillna(0).astype(float)
    feat["price_missing"] = feat["price_value_eur"].isna().astype(int)
    price_median = float(feat["price_value_eur"].dropna().median()) if feat["price_value_eur"].notna().any() else 0.0
    feat["price_filled"] = feat["price_value_eur"].fillna(price_median).astype(float)
    feat["study_len"] = feat["study_content"].fillna("").astype(str).str.len().astype(float)

    q_tokens = tokenize_words(gap_text)

    def lexical_overlap(text: str) -> float:
        t = tokenize_words(text)
        if not q_tokens or not t:
            return 0.0
        return len(q_tokens & t) / max(len(q_tokens), 1)

    feat["lexical_overlap"] = feat["master_text"].fillna("").astype(str).map(lexical_overlap).astype(float)
    feat["gap_ratio"] = feat["gap_coverage"] / np.maximum(feat["master_skill_count"], 1.0)
    feat["gap_ratio"] = feat["gap_ratio"].replace([np.inf, -np.inf], 0.0).fillna(0.0)
    return feat


def try_load_reranker_model(model_path: str):
    if not model_path:
        return None
    p = Path(model_path)
    if not p.exists():
        return None
    try:
        with p.open("rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def build_candidate_skills_from_resume(resume_text: str, taxonomy: dict) -> set[str]:
    return set(extract_skills(resume_text, taxonomy))


def recommend_learning_path(
    candidate_skills: set[str],
    target_role: str,
    role_skill_demand: pd.DataFrame,
    masters_feat: pd.DataFrame,
    master_skills: pd.DataFrame,
    courses_feat: pd.DataFrame,
    course_skills: pd.DataFrame,
    filters: dict,
    weight_coverage: float = 0.65,
    weight_semantic: float = 0.35,
    master_reranker_model=None,
    reranker_blend: float = 0.7,
):
    demand = role_skill_demand[role_skill_demand["role_family"].str.lower() == target_role.lower()].copy()
    if demand.empty:
        demand = role_skill_demand.copy()

    demand = demand.sort_values("demand_count", ascending=False)
    target_skills = list(demand["skill"].dropna().astype(str).head(40))
    target_set = set(target_skills)

    gap = sorted(target_set - candidate_skills)
    gap_set = set(gap)

    # Apply filters
    m = masters_feat.copy()
    if filters.get("max_price") is not None:
        m = m[(m["price_value_eur"].isna()) | (m["price_value_eur"] <= filters["max_price"])]
    if filters.get("location"):
        loc = filters["location"].lower()
        m = m[m["location"].fillna("").str.lower().str.contains(loc, na=False)]
    if filters.get("study_keyword"):
        kw = filters["study_keyword"].lower()
        m = m[m["study_content"].fillna("").str.lower().str.contains(kw, na=False)]

    # Coverage score
    ms = master_skills.copy()
    ms["skill"] = ms["skill"].astype(str)
    master_cov = []
    for mid, g in ms.groupby("master_id"):
        sset = set(g["skill"].tolist())
        cov = len(sset & gap_set)
        master_cov.append((mid, cov, sset))
    cov_df = pd.DataFrame(master_cov, columns=["master_id", "gap_coverage", "skill_set"])
    m = m.merge(cov_df[["master_id", "gap_coverage"]], on="master_id", how="left").fillna({"gap_coverage": 0})

    # Semantic score for masters
    gap_text = " ".join(gap) if gap else " ".join(target_skills)
    m_texts = m["master_text"].fillna("").astype(str).tolist()
    if m_texts:
        emb, emb_mode = embed_texts([gap_text] + m_texts)
        sim = cosine_similarity_matrix(emb[:1], emb[1:]).ravel()
        m["semantic_score"] = sim
    else:
        emb_mode = "none"
        m["semantic_score"] = 0.0

    # Score coverage against the candidate's actual gap size, not only against
    # the best catalog item in the current slice. This favors options that
    # close more of the real missing-skill set.
    gap_size = max(float(len(gap_set)), 1.0)
    m["coverage_score"] = m["gap_coverage"] / gap_size
    m["master_score"] = weight_coverage * m["coverage_score"] + weight_semantic * m["semantic_score"]

    # Optional supervised reranking for masters.
    m["reranker_score"] = np.nan
    if master_reranker_model is not None and len(m):
        feat = build_master_rerank_features(m, ms, gap_text)
        cols = [
            "coverage_score",
            "semantic_score",
            "gap_coverage",
            "master_skill_count",
            "price_missing",
            "price_filled",
            "study_len",
            "lexical_overlap",
            "gap_ratio",
        ]
        x = feat[cols].fillna(0.0).to_numpy()
        try:
            pred = master_reranker_model.predict(x)
            pmin = float(np.min(pred))
            pmax = float(np.max(pred))
            if pmax > pmin:
                pred = (pred - pmin) / (pmax - pmin)
            else:
                pred = np.zeros_like(pred)
            m["reranker_score"] = pred
            blend = min(max(float(reranker_blend), 0.0), 1.0)
            m["master_score"] = (1.0 - blend) * m["master_score"] + blend * m["reranker_score"]
        except Exception:
            pass

    m = m.sort_values("master_score", ascending=False)

    top_masters = m.head(5).copy()

    # Remaining gap after masters
    covered_by_masters = set()
    for mid in top_masters["master_id"].tolist():
        s = ms.loc[ms["master_id"] == mid, "skill"].astype(str).tolist()
        covered_by_masters.update(s)
    remaining_gap = sorted(gap_set - covered_by_masters)
    rem_set = set(remaining_gap)

    cs = course_skills.copy()
    cs["skill"] = cs["skill"].astype(str)
    course_cov = []
    for cid, g in cs.groupby("course_id"):
        sset = set(g["skill"].tolist())
        cov = len(sset & rem_set)
        course_cov.append((cid, cov))
    c_cov_df = pd.DataFrame(course_cov, columns=["course_id", "remaining_gap_coverage"])

    c = courses_feat.merge(c_cov_df, on="course_id", how="left").fillna({"remaining_gap_coverage": 0})
    c_texts = c["course_text"].fillna("").astype(str).tolist()
    c_query = " ".join(remaining_gap) if remaining_gap else gap_text
    if c_texts:
        c_emb, _ = embed_texts([c_query] + c_texts)
        c_sim = cosine_similarity_matrix(c_emb[:1], c_emb[1:]).ravel()
        c["semantic_score"] = c_sim
    else:
        c["semantic_score"] = 0.0

    remaining_gap_size = max(float(len(rem_set)), 1.0)
    c["coverage_score"] = c["remaining_gap_coverage"] / remaining_gap_size
    c["course_score"] = weight_coverage * c["coverage_score"] + weight_semantic * c["semantic_score"]
    top_courses = c.sort_values("course_score", ascending=False).head(8).copy()

    final_skill_set = set(candidate_skills)
    for mid in top_masters["master_id"].tolist():
        final_skill_set.update(ms.loc[ms["master_id"] == mid, "skill"].astype(str).tolist())
    for cid in top_courses["course_id"].tolist():
        final_skill_set.update(cs.loc[cs["course_id"] == cid, "skill"].astype(str).tolist())

    return {
        "target_skills": target_skills,
        "gap_skills": gap,
        "remaining_gap": sorted(set(target_skills) - final_skill_set),
        "top_masters": top_masters,
        "top_courses": top_courses,
        "embedding_mode": emb_mode,
        "reranker_used": master_reranker_model is not None,
        "final_skill_set": final_skill_set,
    }


def recommend_jobs(target_role: str, final_skill_set: set[str], jobs_feat: pd.DataFrame, job_skills: pd.DataFrame):
    jobs = jobs_feat.copy()
    if "role_family" in jobs.columns:
        filt = jobs["role_family"].fillna("").str.lower() == target_role.lower()
        if filt.any():
            jobs = jobs[filt].copy()

    js = job_skills.copy()
    js["skill"] = js["skill"].astype(str)

    rec = []
    for jid, grp in js.groupby("job_id"):
        jskills = set(grp["skill"].tolist())
        if not jskills:
            continue
        overlap = len(jskills & final_skill_set)
        score = overlap / max(len(jskills), 1)
        rec.append((jid, overlap, len(jskills), score))

    rec_df = pd.DataFrame(rec, columns=["job_id", "skill_overlap", "job_skill_count", "match_score"])
    out = jobs.merge(rec_df, on="job_id", how="inner").sort_values(["match_score", "skill_overlap"], ascending=[False, False])
    return out.head(25)


def main():
    p = argparse.ArgumentParser(description="Advanced CAIQ model: CV -> gap -> masters/courses -> jobs")
    p.add_argument("--etl-dir", default=None)
    p.add_argument("--taxonomy", default=None)
    p.add_argument("--resume-text", default="", help="Resume/CV text")
    p.add_argument("--resume-pdf", default="", help="Path to CV PDF")
    p.add_argument("--target-role", default="ml_engineer", choices=["ml_engineer", "data_engineer", "data_scientist", "data_analyst", "other_data_role"])
    p.add_argument("--max-price", type=float, default=None)
    p.add_argument("--location", default="")
    p.add_argument("--study-keyword", default="")
    p.add_argument("--out-dir", default=None)
    p.add_argument("--weight-coverage", type=float, default=0.6)
    p.add_argument("--weight-semantic", type=float, default=0.4)
    p.add_argument("--use-master-reranker", action="store_true")
    p.add_argument("--master-reranker-path", default=None)
    p.add_argument("--reranker-blend", type=float, default=0.7)
    args = p.parse_args()

    etl_dir = Path(args.etl_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    taxonomy = load_taxonomy(Path(args.taxonomy))

    resume_text = norm_text(args.resume_text)
    if args.resume_pdf:
        pdf_text = read_resume_pdf_text(Path(args.resume_pdf))
        if pdf_text:
            resume_text = pdf_text
    if not resume_text:
        raise ValueError("Provide --resume-text or --resume-pdf with readable content")

    masters_feat = pd.read_csv(etl_dir / "outputs" / "semantic" / "masters_features.csv")
    courses_feat = pd.read_csv(etl_dir / "outputs" / "semantic" / "courses_features.csv")
    jobs_feat = pd.read_csv(etl_dir / "outputs" / "semantic" / "jobs_features.csv")
    role_skill_demand = pd.read_csv(etl_dir / "outputs" / "semantic" / "role_skill_demand.csv")
    master_skills = pd.read_csv(etl_dir / "outputs" / "curated" / "master_skills.csv")
    course_skills = pd.read_csv(etl_dir / "outputs" / "curated" / "course_skills.csv")
    job_skills = pd.read_csv(etl_dir / "outputs" / "curated" / "job_skills.csv")

    candidate_skills = build_candidate_skills_from_resume(resume_text, taxonomy)

    master_reranker = try_load_reranker_model(args.master_reranker_path) if args.use_master_reranker else None

    rec = recommend_learning_path(
        candidate_skills=candidate_skills,
        target_role=args.target_role,
        role_skill_demand=role_skill_demand,
        masters_feat=masters_feat,
        master_skills=master_skills,
        courses_feat=courses_feat,
        course_skills=course_skills,
        filters={"max_price": args.max_price, "location": args.location, "study_keyword": args.study_keyword},
        weight_coverage=args.weight_coverage,
        weight_semantic=args.weight_semantic,
        master_reranker_model=master_reranker,
        reranker_blend=args.reranker_blend,
    )

    jobs = recommend_jobs(args.target_role, rec["final_skill_set"], jobs_feat, job_skills)

    rec["top_masters"].to_csv(out_dir / "recommended_masters.csv", index=False, encoding="utf-8")
    rec["top_courses"].to_csv(out_dir / "recommended_courses.csv", index=False, encoding="utf-8")
    jobs.to_csv(out_dir / "recommended_jobs.csv", index=False, encoding="utf-8")

    summary = {
        "target_role": args.target_role,
        "embedding_mode": rec["embedding_mode"],
        "reranker_used": bool(rec.get("reranker_used", False)),
        "candidate_skills_count": len(candidate_skills),
        "candidate_skills": sorted(candidate_skills),
        "gap_skills_count": len(rec["gap_skills"]),
        "gap_skills": rec["gap_skills"],
        "remaining_gap_count": len(rec["remaining_gap"]),
        "remaining_gap": rec["remaining_gap"],
        "top_masters_rows": int(len(rec["top_masters"])),
        "top_courses_rows": int(len(rec["top_courses"])),
        "top_jobs_rows": int(len(jobs)),
        "filters": {
            "max_price": args.max_price,
            "location": args.location,
            "study_keyword": args.study_keyword,
        },
    }
    (out_dir / "recommendation_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
