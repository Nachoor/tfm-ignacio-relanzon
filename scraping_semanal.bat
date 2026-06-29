@echo off
:: ============================================================
:: CAIQ - Actualización semanal de ofertas de empleo
:: Ejecutar desde: C:\Users\Nacho\Documents\TFM\
:: O configurar en Programador de tareas de Windows
:: ============================================================

cd /d "C:\Users\Nacho\Documents\TFM"

chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo [%date% %time%] Iniciando scraping semanal CAIQ... >> logs\scraping_log.txt

python actualizar_ofertas.py --results 300 --hours-old 168 --keep-days 90 >> logs\scraping_log.txt 2>&1

if %ERRORLEVEL% EQU 0 (
    echo [%date% %time%] Scraping completado con exito. >> logs\scraping_log.txt
) else (
    echo [%date% %time%] ERROR en el scraping. Revisar log. >> logs\scraping_log.txt
)
