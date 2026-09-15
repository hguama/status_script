@echo off
REM ========================================
REM  Cornell Ready — Reinicio completo
REM  1. Mata TODAS las instancias de Python
REM  2. Lanza el script principal desde cero
REM ========================================

echo 🔄 Cerrando todas las instancias de Python...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM pythonw.exe >nul 2>&1

timeout /t 1 /nobreak >nul

echo 🚀 Iniciando Cornell Ready...
cd /d "%~dp0"
start "" python layer_status_script.py

echo ✅ Listo.
exit



