' ============================================================================
' 🕷️ Spider-Buddy — Silent Desktop App Launcher
' Launches Spider-Buddy completely silently with zero console window flash.
' ============================================================================
Dim objShell, fso, currentDir, pythonwPath

Set objShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)

objShell.CurrentDirectory = currentDir

' Try local .venv pythonw, then Python 3.13 default, then standard PATH pythonw
pythonwPath = "pythonw.exe"
If fso.FileExists(currentDir & "\.venv\Scripts\pythonw.exe") Then
    pythonwPath = """" & currentDir & "\.venv\Scripts\pythonw.exe"""
ElseIf fso.FileExists("C:\Program Files\Python313\pythonw.exe") Then
    pythonwPath = """C:\Program Files\Python313\pythonw.exe"""
End If

objShell.Run pythonwPath & " """ & currentDir & "\main.py""", 0, False
