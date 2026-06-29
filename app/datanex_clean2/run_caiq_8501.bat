@echo off
setlocal

set "APP_DIR=C:\Users\Nacho\Documents\TFM\app\datanex_clean2"
set "APP_URL=http://localhost:8501"

cd /d "%APP_DIR%"

start "CAIQ Streamlit" cmd /k "cd /d %APP_DIR% && python -m streamlit run app.py --server.port 8501 --server.address 127.0.0.1 --server.headless true"

timeout /t 6 /nobreak >nul
start "" "%APP_URL%"
