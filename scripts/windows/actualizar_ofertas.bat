@echo off
cd /d C:\Users\Nacho\Documents\TFM
if not exist logs mkdir logs
echo [%date% %time%] Iniciando actualizacion de ofertas... >> logs\actualizar_ofertas.log
python scripts\automation\actualizar_ofertas.py --keep-days 30 >> logs\actualizar_ofertas.log 2>&1
echo [%date% %time%] Finalizado. >> logs\actualizar_ofertas.log
