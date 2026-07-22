@echo off
REM Avvia Mike nella nuova interfaccia WEB (fluida e moderna).
cd /d "%~dp0"
title Mike - Cognitive Neural Link (WEB)
python avvia_web.py
if errorlevel 1 (
    echo.
    echo Qualcosa e' andato storto. Premi un tasto per chiudere.
    pause >nul
)
