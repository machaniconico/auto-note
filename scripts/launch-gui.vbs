Option Explicit

Dim fso, shell, scriptDir, projectDir, batPath, logPath, command, exitCode, message

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
projectDir = fso.GetParentFolderName(scriptDir)
batPath = fso.BuildPath(projectDir, "auto-note-gui.bat")
logPath = fso.BuildPath(fso.BuildPath(projectDir, ".auto-note"), "gui-error.log")

command = "cmd.exe /c """ & batPath & """"

If shell.Environment("PROCESS")("AUTO_NOTE_LAUNCHER_CHECK") = "1" Then
  WScript.Quit 0
End If

If Not fso.FileExists(batPath) Then
  MsgBox "auto-note-gui.bat was not found." & vbCrLf & batPath, vbExclamation, "auto-note"
  WScript.Quit 1
End If

exitCode = shell.Run(command, 0, True)

If exitCode <> 0 Then
  message = "Failed to start auto-note GUI." & vbCrLf & vbCrLf
  If fso.FileExists(logPath) Then
    message = message & TruncateText(ReadText(logPath), 3500)
  Else
    message = message & "Log was not found: " & logPath
  End If
  MsgBox message, vbExclamation, "auto-note"
End If

Function ReadText(path)
  Dim stream
  Set stream = CreateObject("ADODB.Stream")
  stream.Type = 2
  stream.Charset = "utf-8"
  stream.Open
  stream.LoadFromFile path
  ReadText = stream.ReadText
  stream.Close
End Function

Function TruncateText(text, maxLength)
  If Len(text) <= maxLength Then
    TruncateText = text
  Else
    TruncateText = Left(text, maxLength) & vbCrLf & vbCrLf & "(Log truncated. Full log: .auto-note\gui-error.log)"
  End If
End Function
