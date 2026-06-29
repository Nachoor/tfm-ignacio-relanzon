# CAIQ - Career Alignment and Insight Qualifier

Trabajo Fin de Master de Ignacio Relanzon. Sistema de orientacion profesional para perfiles en transicion hacia el mercado de datos: extrae competencias desde CV, estima skill gaps frente a roles objetivo y recomienda formacion, masters y ofertas.

Aplicacion en produccion: https://huggingface.co/spaces/relan02/caiq

## Estructura

```text
.
├── 01_etl/                     # Pipelines de datos, entrenamiento, evaluacion y reportes de investigacion
│   ├── pipelines/
│   ├── reports/
│   └── tests/
├── app/datanex_clean2/          # Aplicacion Streamlit canonica desplegable en Hugging Face
│   ├── app.py
│   ├── datanex_app.py
│   ├── config/
│   ├── pipelines/
│   ├── reports/
│   └── requirements.txt
├── docs/validation/             # Validacion del parser de CVs y scripts auxiliares
│   ├── datasets/
│   └── scripts/
├── scripts/
│   ├── automation/              # Automatizacion: scraping semanal y subida a Hugging Face
│   └── windows/                 # Lanzadores .bat/.ps1 para Windows Task Scheduler
├── thesis/                      # Memoria LaTeX y figuras finales del TFM
│   ├── main.tex
│   ├── chapters/
│   └── figures/
└── .gitignore
```

Las carpetas antiguas duplicadas (`02_modelo`, `03_aplicacion`, `04_validacion/figuras_tfm`, `figures`, `docs/figures`) se retiraron del repositorio. La fuente canonica es la estructura anterior.

## Uso Local

### Aplicacion

```bash
cd app/datanex_clean2
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

## Datos Excluidos

No se versionan datos personales, outputs regenerables, logs, modelos binarios, borradores Word ni historicos pesados. Ver `.gitignore`.

## Autor

Ignacio Relanzon - Master en Big Data Science - Universidad de Navarra / DATAI.
