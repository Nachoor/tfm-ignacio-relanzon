# CAIQ - Career Alignment and Insight Qualifier

Trabajo Fin de Master de Ignacio Relanzon. CAIQ es un sistema de orientacion profesional para perfiles en transicion hacia el mercado de datos: extrae competencias desde CV, estima skill gaps frente a roles objetivo y recomienda formacion, masters y ofertas.

Aplicacion en produccion: https://huggingface.co/spaces/relan02/caiq

## Estructura

```text
.
|-- 01_etl/                 # Pipelines de datos, entrenamiento, evaluacion y reportes
|   |-- pipelines/
|   |-- reports/
|   `-- tests/
|-- app/
|   `-- caiq/               # Aplicacion Streamlit canonica desplegable en Hugging Face
|       |-- app.py
|       |-- caiq_app.py
|       |-- config/
|       |-- pipelines/
|       |-- reports/
|       `-- requirements.txt
|-- data/
|   `-- private/            # Datos personales locales, excluidos de git
|-- docs/
|   `-- validation/         # Validacion del parser de CVs y scripts auxiliares
|       |-- datasets/
|       |-- cv_cases/
|       `-- scripts/
|-- scripts/
|   |-- automation/         # Automatizacion: scraping semanal y subida a Hugging Face
|   `-- windows/            # Lanzadores .bat/.ps1 para Windows Task Scheduler
|-- thesis/                 # Memoria LaTeX, figuras finales y borradores locales excluidos
|   |-- main.tex
|   |-- chapters/
|   |-- figures/
|   `-- drafts/
`-- .gitignore
```

La raiz queda reducida a codigo, documentacion, memoria y carpetas locales ignoradas. Las copias antiguas y duplicadas viven fuera del repo versionado.

## Uso local

### Aplicacion

```bash
cd app/caiq
pip install -r requirements.txt
streamlit run app.py
```

### ETL y entrenamiento

```bash
python 01_etl/pipelines/01_etl_curated_layer.py
python 01_etl/pipelines/02_build_semantic_features.py
python 01_etl/pipelines/03_train_and_tune_recommender.py
```

### Actualizacion semanal de ofertas

```bash
python scripts/automation/actualizar_ofertas.py --results 300 --hours-old 168 --keep-days 90
```

Para subir datos a Hugging Face, define `HF_TOKEN` como variable de entorno y ejecuta:

```bash
python scripts/automation/subir_a_huggingface.py
```

### Memoria LaTeX

Compilar desde la carpeta `thesis`:

```bash
cd thesis
pdflatex main.tex
```

## Datos excluidos

No se versionan datos personales, outputs regenerables, logs, modelos binarios, borradores Word ni historicos pesados. Ver `.gitignore`.

## Autor

Ignacio Relanzon - Master en Big Data Science - Universidad de Navarra / DATAI.
