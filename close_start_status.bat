@echo off
REM -----------------------------------------
REM Cerrar layer_status_script.py (aunque no tenga ventana)
REM -----------------------------------------
wmic process where "CommandLine like '%%layer_status_script.py%%'" call terminate >nul 2>&1

REM -----------------------------------------
REM Ir a la carpeta del script
REM -----------------------------------------
cd /d "D:\scripts\status script"

REM -----------------------------------------
REM Iniciar nuevamente la aplicación
REM -----------------------------------------
start "" python layer_status_script.py

exit

