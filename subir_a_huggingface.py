import os
from pathlib import Path
from huggingface_hub import HfApi

TOKEN = os.environ.get("HF_TOKEN", "")
SPACE = "relan02/caiq"

APP_DIR = Path(__file__).parent / "app" / "datanex_clean2"
DATA_DIR = APP_DIR / "outputs" / "curated"

ARCHIVOS = [
    (APP_DIR / "datanex_app.py", "datanex_app.py"),
    (APP_DIR / "requirements.txt", "requirements.txt"),
    (APP_DIR / "packages.txt", "packages.txt"),
    (APP_DIR / "pipelines" / "build_datapath_model_advanced.py", "pipelines/build_datapath_model_advanced.py"),
    (APP_DIR / "outputs" / "semantic" / "jobs_features.csv", "outputs/semantic/jobs_features.csv"),
    (APP_DIR / "outputs" / "semantic" / "jobs_features_v2.csv", "outputs/semantic/jobs_features_v2.csv"),
    (APP_DIR / "outputs" / "semantic" / "role_skill_demand.csv", "outputs/semantic/role_skill_demand.csv"),
    (APP_DIR / "outputs" / "curated" / "job_skills.csv", "outputs/curated/job_skills.csv"),
    (APP_DIR / "outputs" / "curated" / "job_postings_clean.csv", "outputs/curated/job_postings_clean.csv"),
    (DATA_DIR / "course_skills_augmented.csv", "outputs/curated/course_skills_augmented.csv"),
    (DATA_DIR / "master_skills.csv", "outputs/curated/master_skills.csv"),
]

COMMIT_MSG = (
    "Fix i18n keys; UI country filter Spain+USA; US states alias; "
    "Recency scoring vs dataset max date (180d/30pct); "
    "Job pool always Spain+USA; CSS fixes; radar normalization"
)

api = HfApi(token=TOKEN)
print(f"Subiendo archivos al Space {SPACE}...")
for local, repo_path in ARCHIVOS:
    if not local.exists():
        print(f"  WARNING No encontrado: {local}")
        continue
    size_kb = local.stat().st_size // 1024
    print(f"  Subiendo {repo_path} ({size_kb} KB)...")
    api.upload_file(
        path_or_fileobj=str(local),
        path_in_repo=repo_path,
        repo_id=SPACE,
        repo_type="space",
        commit_message=COMMIT_MSG,
    )
    print(f"  OK {repo_path}")

print(f"\nListo. Visita https://huggingface.co/spaces/{SPACE}")
