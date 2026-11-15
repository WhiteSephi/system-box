Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strDir
strArgs = ""
If WScript.Arguments.Count > 0 Then
    For i = 0 To WScript.Arguments.Count - 1
        strArgs = strArgs & " """ & WScript.Arguments(i) & """"
    Next
End If
strPythonw = strDir & "\.venv\Scripts\pythonw.exe"
If fso.FileExists(strPythonw) Then
    WshShell.Run """" & strPythonw & """ -m src.main" & strArgs, 0, False
Else
    WshShell.Run "pythonw -m src.main" & strArgs, 0, False
End If
