@echo off
cd /d "%~dp0"
if not exist ".ready" (
  echo Preparando o aplicativo na primeira execucao...
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Preparar.ps1"
  if errorlevel 1 (
    echo A preparacao falhou. Consulte a mensagem acima.
    pause
    exit /b 1
  )
)
start "" "%~dp0portable\pythonw.exe" "%~dp0run.py"
exit /b

