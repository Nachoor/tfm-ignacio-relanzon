import textwrap
from pathlib import Path


VALIDATION_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = VALIDATION_DIR / "cv_cases"


CASES = {
    "CV_SynthCareerShift_FinanceML_Madrid.pdf": {
        "name": "Lucia Moreno",
        "title": "Career Switch to Machine Learning",
        "location": "Madrid, Spain",
        "summary": (
            "Finance analyst transitioning into data science. Built forecasting and churn models in Python "
            "and SQL, automated dashboards, and supported experimentation with a/b testing."
        ),
        "skills": [
            "python", "sql", "statistics", "machine learning", "xgboost", "pandas",
            "numpy", "data analysis", "data visualization", "power bi", "a/b testing",
            "forecasting",
        ],
        "experience": [
            "Senior financial analyst at retail group. Designed KPI reporting and data analysis for pricing decisions.",
            "Built forecasting models in Python with pandas, numpy and xgboost for monthly demand planning.",
            "Created Power BI dashboards, SQL pipelines and experiment readouts for a/b testing of campaigns.",
        ],
        "education": [
            "MSc in Business Analytics, Universidad Carlos III.",
            "Specialization in machine learning and statistics.",
        ],
    },
    "CV_SynthBIEngineer_Looker_Berlin.pdf": {
        "name": "Mario Keller",
        "title": "BI Engineer",
        "location": "Berlin, Germany",
        "summary": (
            "BI engineer focused on data warehousing, analytics engineering and executive reporting across sales and operations."
        ),
        "skills": [
            "sql", "looker", "power bi", "tableau", "excel", "etl", "airflow", "dbt",
            "snowflake", "redshift", "data visualization", "data analysis", "python",
        ],
        "experience": [
            "Owned ETL jobs in Airflow and dbt for finance and sales reporting.",
            "Modeled marts in Snowflake and Redshift and maintained Looker semantic layers.",
            "Produced KPI packs in Power BI, Tableau and Excel for weekly business reviews.",
        ],
        "education": [
            "BSc in Information Systems.",
        ],
    },
    "CV_SynthMLOps_Remote.pdf": {
        "name": "Sara Vega",
        "title": "MLOps Engineer",
        "location": "Remote",
        "summary": (
            "Engineer deploying ML services in cloud environments with strong platform and container orchestration experience."
        ),
        "skills": [
            "python", "aws", "azure", "docker", "kubernetes", "api", "git", "machine learning",
            "pytorch", "tensorflow", "airflow", "databricks",
        ],
        "experience": [
            "Deployed machine learning APIs in Python on AWS and Azure.",
            "Containerized services with Docker and managed production rollouts on Kubernetes.",
            "Scheduled retraining with Airflow and operationalized experimentation notebooks in Databricks.",
        ],
        "education": [
            "MSc in Computer Engineering.",
        ],
    },
    "CV_SynthResearch_NLP_Valencia.pdf": {
        "name": "Daniel Ferrer",
        "title": "NLP Research Scientist",
        "location": "Valencia, Spain",
        "summary": (
            "Research-oriented profile in natural language processing and generative systems for multilingual document understanding."
        ),
        "skills": [
            "python", "nlp", "llm", "generative ai", "pytorch", "tensorflow", "deep learning",
            "machine learning", "statistics", "sql", "git",
        ],
        "experience": [
            "Built NLP pipelines for entity extraction and document classification in Python.",
            "Fine-tuned llm and deep learning models with PyTorch and TensorFlow.",
            "Tracked experiments in SQL-backed datasets and versioned code with Git.",
        ],
        "education": [
            "PhD track in Language Technologies.",
        ],
    },
    "CV_SynthJunior_Analytics_Sevilla.pdf": {
        "name": "Paula Ortega",
        "title": "Junior Data Analyst",
        "location": "Sevilla, Spain",
        "summary": (
            "Entry-level analyst with internship experience in reporting, dashboards and commercial analytics."
        ),
        "skills": [
            "excel", "power bi", "sql", "python", "pandas", "data analysis",
            "data visualization", "statistics",
        ],
        "experience": [
            "Prepared weekly Excel and Power BI reports for commercial performance.",
            "Queried customer data in SQL and cleaned datasets with Python and pandas.",
            "Presented insights and data visualization for churn and funnel analysis.",
        ],
        "education": [
            "BSc in Economics.",
        ],
    },
    "CV_SynthDataEngineer_GCP_Lisbon.pdf": {
        "name": "Ruben Costa",
        "title": "Data Engineer",
        "location": "Lisbon, Portugal",
        "summary": (
            "Data engineer working on batch pipelines and warehouse modernization with cloud and big data tooling."
        ),
        "skills": [
            "python", "sql", "spark", "hadoop", "hdfs", "hive", "yarn", "airflow",
            "gcp", "etl", "data engineering", "dbt", "big data", "scala",
        ],
        "experience": [
            "Maintained Spark and Hadoop workloads with HDFS, Hive and Yarn.",
            "Migrated ETL jobs to GCP and orchestrated them in Airflow.",
            "Built dbt models and Scala data processing components for analytics consumption.",
        ],
        "education": [
            "MSc in Data Engineering.",
        ],
    },
    "CV_SynthHealth_Analyst_Barcelona.pdf": {
        "name": "Elena Soler",
        "title": "Health Data Analyst",
        "location": "Barcelona, Spain",
        "summary": (
            "Health analytics profile combining hospital outcomes analysis, dashboarding and statistical reporting."
        ),
        "skills": [
            "r", "spss", "statistics", "sql", "tableau", "data analysis",
            "data visualization", "excel", "python",
        ],
        "experience": [
            "Analyzed patient cohorts in R and SPSS for quality-of-care studies.",
            "Prepared Tableau dashboards and SQL extracts for management reporting.",
            "Supported epidemiology projects with Python, Excel and statistical analysis.",
        ],
        "education": [
            "MSc in Public Health.",
        ],
    },
    "CV_SynthMultiCloud_DS_Alicante.pdf": {
        "name": "Javier Mena",
        "title": "Data Scientist",
        "location": "Alicante, Spain",
        "summary": (
            "Data scientist with end-to-end modeling experience across cloud environments and product analytics."
        ),
        "skills": [
            "python", "pandas", "numpy", "scikit_learn", "machine learning", "aws",
            "azure", "gcp", "sql", "data science", "data analysis", "feature engineering",
        ],
        "experience": [
            "Built machine learning models in Python with scikit_learn and feature engineering pipelines.",
            "Worked with AWS, Azure and GCP environments for experimentation and deployment support.",
            "Delivered SQL analysis and data science reports for product and growth teams.",
        ],
        "education": [
            "BSc in Mathematics.",
        ],
    },
}


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_lines(case: dict) -> list[str]:
    lines = [
        case["name"],
        f'{case["title"]} | {case["location"]}',
        "",
        "PROFILE",
    ]
    lines.extend(textwrap.wrap(case["summary"], width=88))
    lines.extend(["", "CORE SKILLS", ", ".join(case["skills"]), "", "EXPERIENCE"])
    for item in case["experience"]:
        lines.extend(textwrap.wrap(f"- {item}", width=88))
    lines.extend(["", "EDUCATION"])
    for item in case["education"]:
        lines.extend(textwrap.wrap(f"- {item}", width=88))
    return lines


def write_simple_pdf(path: Path, lines: list[str]) -> None:
    stream_lines = ["BT", "/F1 11 Tf", "50 790 Td", "14 TL"]
    for idx, line in enumerate(lines):
        safe = pdf_escape(line)
        if idx == 0:
            stream_lines.append(f"({safe}) Tj")
        else:
            stream_lines.append(f"T* ({safe}) Tj")
    stream_lines.append("ET")
    content = "\n".join(stream_lines).encode("latin-1", errors="replace")

    objects = []
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objects.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n"
    )
    objects.append(b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
    objects.append(
        b"5 0 obj\n<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" +
        content + b"\nendstream\nendobj\n"
    )

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)
    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )
    path.write_bytes(pdf)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, case in CASES.items():
        lines = build_lines(case)
        write_simple_pdf(OUT_DIR / filename, lines)
        print(f"generated={filename}")


if __name__ == "__main__":
    main()
