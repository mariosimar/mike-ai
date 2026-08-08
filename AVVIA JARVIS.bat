@echo off
REM ============================================================
REM  J.A.R.V.I.S. - il tuo assistente. Doppio clic qui.
REM  Si apre nel browser, gia' come amministratore.
REM ============================================================

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  Avvio Jarvis come amministratore ^(conferma la richiesta di Windows^)...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
title J.A.R.V.I.S.

REM Ferma eventuali istanze vecchie, poi avvia quella nuova (Jarvis, veloce)
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | Where-Object { $_.CommandLine -like '*avvia_web.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 2 >nul

python avvia_web.py
if errorlevel 1 (
    echo.
    echo Qualcosa e' andato storto. Premi un tasto per chiudere.
    pause >nul
)
