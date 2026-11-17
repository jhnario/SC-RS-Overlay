@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0CriarAtalho.ps1"
if errorlevel 1 pause
