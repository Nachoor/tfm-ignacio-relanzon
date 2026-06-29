# CAIQ — Career Alignment and Insight Qualifier

**Trabajo Fin de Máster · Ignacio Relanzón · Máster en Big Data Science · Universidad de Navarra / DATAI · 2025-26**

Sistema de orientación profesional para personas en transición hacia el mercado laboral de datos. A partir del CV del candidato, detecta sus competencias, cuantifica su _skill gap_ respecto a un rol objetivo y genera recomendaciones personalizadas de formación (cursos y másteres) y empleo, ordenadas por su contribución al cierre de la brecha.

🔗 **Aplicación en producción:** https://huggingface.co/spaces/relan02/caiq

---

## Estructura del repositorio

```
caiq/
├── actualizar_ofertas.py          # Pipeline semanal de scraping y mantenimiento del corpus
├── actualizar_ofertas.bat         # Lanzador Windows para el pipeline
├── scraping_semanal.bat           # Tarea programada semanal
├── setup_tarea_programada.ps1     # Configura la tarea en el Programador de tareas de Windows
│
├── 01_etl/
│   ├── pipelines/
│   │   ├── 01_etl_curated_layer.py           # Normalización y limpieza de datos
│   │   ├── 02_build_semantic_features.py     # Embeddings y features semánticas
│   │   ├── 03_train_and_tune_recommender.py  # Entrenamiento y calibración del motor
│   │   ├── 04_evaluate_recommender_metrics.py
│   │   └── 05_ablation_study_recommender.py  # Estudio de ablación (4 variantes, n=482)
│   ├── reports/                              # Métricas y parámetros del modelo (JSON)
│   └── tests/
│       ├── test_etl_pipeline_v2.py
│       └── test_skill_parser.py
│
├── 02_modelo/
│   └── pipelines/
│       ├── build_datapath_model_advanced.py
│       └── evaluate_datapath_model.py
│
├── 03_aplicacion/
│   ├── datanex_app.py             # Aplicación Streamlit principal
│   ├── app.py                     # Entry point
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .streamlit/config.toml
│   ├── config/
│   │   ├── skills_taxonomy.json          # Taxonomía: 71 competencias, 477 aliases
│   │   └── skills_taxonomy_CHANGELOG.md
│   └── pipelines/                        # Pipelines de enriquecimiento y monitorización
│
├── 04_validacion/
│   └── figuras_tfm/               # Figuras y diagramas incluidos en la memoria
│
└── figures/                       # Figuras definitivas del TFM (PNG + PDF)
```

> Los datos scrapeados, artefactos de modelo y CVs de validación no se incluyen en este repositorio (ver `.gitignore`).

---

## Componentes principales

### Pipeline de scraping (`actualizar_ofertas.py`)

Script principal de actualización del corpus. Se ejecuta automáticamente cada lunes a las 08:00 mediante el Programador de tareas de Windows.

- Scraping multi-fuente (LinkedIn, Indeed, Glassdoor) vía [JobSpy](https://github.com/Bunsly/JobSpy)
- Deduplicación por URL y fusión incremental con el histórico
- Caducidad temporal: se descartan ofertas con más de 90 días (`keep_days=90`)
- Verificación activa de URLs vía HTTP HEAD, con caché persistente (`job_url_status.csv`, TTL 7 días, máx. 300 URLs/ciclo)
- Estados de URL: `active`, `dead`, `blocked`, `unknown`
- La capa de aplicación muestra solo las últimas ofertas de 60 días con `url_status != 'dead'`

### Extractor de competencias

Taxonomía controlada con reglas de coincidencia léxica. No requiere GPU ni corpus anotado.

- 71 competencias canónicas, 477 aliases léxicos (media 6,7 por competencia)
- Normalización previa: minúsculas, eliminación de acentos, resolución de solapamientos
- Inferencia de seniority (señales léxicas + umbrales de años de experiencia)
- Inferencia de orientación de rol (7 familias: `data_analyst`, `data_scientist`, `data_engineer`, `ml_engineer`, `business_intelligence`, `mlops`, `other_data_role`)
- Representación semántica: embeddings `paraphrase-multilingual-MiniLM-L12-v2` (384 dims)

**Validación sobre n=87 CVs anotados manualmente:**

| Métrica | Valor |
|---------|-------|
| Precisión | 0,698 |
| Recall | 0,995 |
| F1 | 0,820 |

### Motor de recomendación híbrido

Combina cobertura léxica y similitud semántica. Variante seleccionada: `hybrid_tuned` (α_cov = 0,65 · α_sem = 0,35).

**Estudio de ablación (n=482 candidatos, 4 variantes):**

| Variante | Recall@10 | Gap Reduction |
|----------|-----------|---------------|
| coverage_only | 0,406 | 0,732 |
| semantic_only | 0,408 | 0,739 |
| hybrid_equal | 0,412 | 0,745 |
| **hybrid_tuned** | **0,413** | **0,750** |

### Aplicación web

Streamlit + Docker, desplegada en Hugging Face Spaces (sin GPU).

- Vista de **resumen del perfil**: competencias detectadas, seniority, skill gap por banda
- Vista de **recomendaciones**: cursos, másteres y ofertas ordenados por contribución al gap
- Vista de **inteligencia de skills**: demanda de competencias filtrable por rol

---

## Corpus de datos

| Dataset | Registros |
|---------|-----------|
| Ofertas de empleo (corpus activo) | 37.829 |
| Cursos online | 89.332 |
| Másteres | 3.503 |
| Competencias canónicas | 71 (477 aliases) |
| Familias de rol | 7 |

---

## Instalación y uso local

```bash
# 1. Instalar dependencias de la aplicación
cd 03_aplicacion
pip install -r requirements.txt

# 2. Lanzar la app
streamlit run app.py
```

```bash
# Con Docker
cd 03_aplicacion
docker build -t caiq-app .
docker run -p 8501:8501 caiq-app
```

```bash
# Ejecutar el ETL completo desde cero
cd 01_etl
python pipelines/01_etl_curated_layer.py
python pipelines/02_build_semantic_features.py
python pipelines/03_train_and_tune_recommender.py
```

> **Nota:** para ejecutar el sistema completo se necesitan los datasets de ofertas, cursos y másteres, que no se distribuyen en este repositorio por su volumen.

---

## Stack tecnológico

| Componente | Tecnología |
|------------|------------|
| Lenguaje | Python 3.11 |
| UI | Streamlit |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` (sentence-transformers) |
| Scraping | JobSpy (LinkedIn, Indeed, Glassdoor) |
| Contenedor | Docker |
| Despliegue | Hugging Face Spaces |
| Automatización | Windows Task Scheduler |

---

## Autor

**Ignacio Relanzón** · nacho.relanzon@gmail.com  
Máster en Big Data Science · Universidad de Navarra / DATAI · 2025-26
