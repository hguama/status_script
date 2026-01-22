Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "D:\scripts\status script\script.bat" & chr(34), 0
Set WshShell = Nothing
