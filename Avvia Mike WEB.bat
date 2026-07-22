@echo off
REM Avvia Mike (interfaccia WEB) GIA' con i privilegi di amministratore.
REM Se non e' admin, chiede il permesso a Windows (finestra UAC) e riparte elevato.

REM --- Auto-elevazione ad amministratore ---
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  Avvio Mike come amministratore ^(conferma la richiesta di Windows^)...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
title Mike - Cognitive Neural Link (WEB) [Amministratore]
python avvia_web.py
if errorlevel 1 (
    echo.
    echo Qualcosa e' andato storto. Premi un tasto per chiudere.
    pause >nul
)
