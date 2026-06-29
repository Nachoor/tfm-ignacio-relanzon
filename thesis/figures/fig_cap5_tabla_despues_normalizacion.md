# Tabla sugerida: después de la normalización

Usa esta tabla en el apartado `5.3 Normalización, limpieza y enriquecimiento` para mostrar el resultado de la transformación sobre una capa ya estructurada y comparable.

## Tabla X+1. Ejemplo ilustrativo de registros después de la normalización

| job_id | site | role_title_clean | role_family | location_clean | date_posted_parsed | salary_min | salary_max | remote_mode | seniority | description_clean |
|---|---|---|---|---|---|---:|---:|---|---|---|
| in-5698c5514e2ecb00 | indeed | internal control and risk management analyst | data_analyst | milano, italy | 2026-03-18 |  |  | onsite | mid | integrated european energy company, risk management, analytical responsibilities |
| in-36657e9d3919b729 | indeed | investigative analyst | data_analyst | manhattan, us | 2026-02-21 | 56942 | 60410 | onsite | mid | analyst role with structured extraction over long legal and investigative description |
| norm-example-03 | glassdoor | senior data scientist | data_scientist | spain | 2026-02-18 |  |  | remote | senior | analytics experimentation remote role with cleaned and normalized textual content |

## Qué ilustra esta tabla

- títulos de puesto normalizados
- localizaciones armonizadas en un formato comparable
- fechas transformadas a un mismo estándar
- salario separado en variables numéricas cuando existe
- modalidad remota convertida en variable interpretable
- asignación de familia de rol y seniority
- descripción textual reducida a contenido útil para análisis posterior

## Pie sugerido

`Tabla X+1. Ejemplo ilustrativo de registros tras la fase de normalización, limpieza y enriquecimiento. La salida resultante presenta una estructura homogénea y directamente utilizable en las etapas posteriores del sistema.`
