@echo off
REM ============================================================
REM  Riavvia Mike WEB con l'ultima versione del codice.
REM  Usalo dopo un aggiornamento (/aggiorna-mike) o dopo modifiche,
REM  cosi' non resta in esecuzione la versione vecchia.
REM ============================================================
cd /d "%~dp0"
title Riavvia Mike

echo  Fermo Mike se e' gia' in esecuzione...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | Where-Object { $_.CommandLine -like '*avvia_web.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

timeout /t 2 >nul
echo  Avvio Mike aggiornato...
start "" python avvia_web.py
echo  Fatto! Mike si apre nel browser tra poco.
timeout /t 3 >nul
