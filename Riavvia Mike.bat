@echo off
REM ============================================================
REM  Riavvia Mike WEB (come amministratore) con l'ultima versione.
REM  Usalo dopo un aggiornamento (/aggiorna-mike) o dopo modifiche.
REM ============================================================

REM --- Auto-elevazione ad amministratore ---
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
title Riavvia Mike [Amministratore]

echo  Fermo Mike se e' gia' in esecuzione...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | Where-Object { $_.CommandLine -like '*avvia_web.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

timeout /t 2 >nul
echo  Avvio Mike aggiornato ^(amministratore^)...
start "" python avvia_web.py
echo  Fatto! Mike si apre nel browser tra poco.
timeout /t 3 >nul
