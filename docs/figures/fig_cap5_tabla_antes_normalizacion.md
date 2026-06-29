# Tabla sugerida: antes de la normalización

Usa esta tabla en el apartado `5.3 Normalización, limpieza y enriquecimiento` para ilustrar el estado de los datos tras el scraping bruto y antes de la capa curada.

## Tabla X. Ejemplo ilustrativo de registros antes de la normalización

| id | site | title | company | location | date_posted | min_amount | max_amount | is_remote | description |
|---|---|---|---|---|---|---:|---:|---|---|
| in-5698c5514e2ecb00 | indeed | Senior Internal Control and Risk Management Analyst - with energy experience | MET Group | Milano, LOM, IT | 2026-03-18 |  |  | False | Company Description **MET Group** is an integrated European energy company... |
| in-36657e9d3919b729 | indeed | Investigative Analyst |  | Manhattan, NY, US | 2026-02-21 | 56942 | 60410 | False | **Investigative Analyst** ... salary range, legal context, repeated boilerplate and long description text... |
| raw-example-03 | glassdoor | Senior Data Scientist \| Remote | Not specified | Spain | 2 days ago |  |  | True | Remote role for analytics and experimentation with unstructured text and mixed formatting... |

## Qué ilustra esta tabla

- coexistencia de formatos distintos de localización
- fechas en formatos no homogéneos o relativos
- salarios ausentes o incompletos
- nombres de puesto heterogéneos
- descripciones extensas con ruido, boilerplate y fragmentos poco útiles
- campos vacíos en empresa o variables de contexto

## Pie sugerido

`Tabla X. Ejemplo ilustrativo de registros procedentes del scraping bruto antes del proceso de normalización. Puede observarse la heterogeneidad de formatos, la presencia de campos incompletos y el ruido textual en las descripciones.`
