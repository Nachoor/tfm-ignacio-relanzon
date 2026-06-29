# Validacion del parser de CV

Esta carpeta contiene los artefactos usados para validar manualmente el modulo de extraccion de skills del parser de CV.

## Estructura

- `cv_cases/`: CVs PDF usados como casos de validacion (originales anonimizados + sinteticos generados).
- `datasets/`: dataset auxiliar usado en tareas de validacion.
- `scripts/`: scripts reproducibles de evaluacion.
- `outputs/`: salidas generadas por los scripts, metricas y textos extraidos.
- `outputs/extracted_text/`: texto extraido desde los PDFs para inspeccion manual.

## Script principal

Ejecutar desde cualquier ubicacion:

```powershell
python C:\Users\Nacho\Documents\TFM\docs\validation\scripts\run_manual_parser_validation.py
```

El script compara las skills detectadas por el parser real de CAIQ contra una anotacion manual restringida al vocabulario soportado por la taxonomia del sistema. Genera:

- `outputs/cv_parser_manual_validation_metrics.csv`: metricas por CV.
- `outputs/cv_parser_manual_validation_summary.json`: resumen agregado.

## Composicion del dataset de validacion

- CVs originales (anonimizados): 14
- CVs sinteticos generados (batch 1): 18
- CVs sinteticos generados (extra): 8
- CVs sinteticos generados (batch 2): 48
- **Total: 88 CVs**

Los CVs sinteticos cubren perfiles variados: junior/mid/senior, con y sin master, perfiles atipicos (biologos, economistas, medicos, periodistas, psicologos, etc.), distintas ciudades espanolas y perfil internacional. Todos usan universidades espanolas reales y empresas inventadas.

## Resultado agregado actual

- CVs PDF disponibles: 88
- CVs evaluados: 87
- CVs excluidos por texto vacio: 1
- **Micro-precision: 0.7275**
- **Micro-recall: 0.9893**
- **Micro-F1: 0.8384**
- Macro-precision: 0.7320
- Macro-recall: 0.9850
- Macro-F1: 0.8312

El caso excluido corresponde a un PDF para el que la extraccion textual devolvio contenido vacio. Se reporta como limitacion del parser PDF y no se incluye en el calculo agregado de precision, recall y F1.

## Evolucion de metricas

| Dataset | n CVs evaluados | Micro-F1 | Micro-recall | Micro-precision |
|---------|----------------|----------|-------------|----------------|
| Original | 13 | 0.764 | 0.911 | 0.657 |
| Ampliado (sinteticos batch 1+extra) | 31 | - | - | - |
| **Ampliado (todos los sinteticos)** | **87** | **0.838** | **0.989** | **0.728** |
