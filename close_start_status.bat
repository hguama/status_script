@echo off
REM -----------------------------------------
REM Cerrar layer_status_script.py (aunque no tenga ventana)
REM -----------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*layer_status_script.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"

REM -----------------------------------------
REM Ir a la carpeta del script
REM -----------------------------------------
cd /d "%~dp0"

REM -----------------------------------------
REM Iniciar nuevamente la aplicación
REM -----------------------------------------
start "" python layer_status_script.py






