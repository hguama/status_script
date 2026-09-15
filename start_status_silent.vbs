Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\scripts\status script"
WshShell.Run "python layer_status_script.py", 0, False
Set WshShell = Nothing
