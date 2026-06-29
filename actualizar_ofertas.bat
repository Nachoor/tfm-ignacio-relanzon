@echo off
cd /d C:\Users\Nacho\Documents\TFM
echo [%date% %time%] Iniciando actualizacion de ofertas... >> actualizar_ofertas.log
python actualizar_ofertas.py --keep-days 30 >> actualizar_ofertas.log 2>&1
echo [%date% %time%] Finalizado. >> actualizar_ofertas.log
