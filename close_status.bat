@echo off
REM Cierra SOLO layer_status_script.py aunque no tenga ventana

wmic process where "CommandLine like '%%layer_status_script.py%%'" call terminate

exit
