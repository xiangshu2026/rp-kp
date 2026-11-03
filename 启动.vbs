Set ws = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
appDir = fso.GetParentFolderName(WScript.ScriptFullName)
ws.CurrentDirectory = appDir
py = appDir & "\\server.py"

cmd = "cmd /c chcp 65001 >nul && python """ & py & """"
ws.Run cmd, 0, False
WScript.Sleep 2400
ws.Run "http://127.0.0.1:8760", 1, False