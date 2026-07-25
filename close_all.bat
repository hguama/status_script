@echo off
REM Cierra el script de voice.py

REM Busca procesos de python.exe y los termina
taskkill /F /IM python.exe
taskkill /IM pythonw.exe /F


echo Script de dictado detenido.
exit
