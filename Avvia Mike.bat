@echo off
REM Avvia JARVIS (interfaccia web) GIA' con i privilegi di amministratore.
REM (Questo pulsante ora apre Jarvis, non la vecchia finestra desktop.)

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  Avvio Jarvis come amministratore ^(conferma la richiesta di Windows^)...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
title JARVIS [Amministratore]
python avvia_web.py
if errorlevel 1 (
    echo.
    echo Qualcosa e' andato storto. Premi un tasto per chiudere.
    pause >nul
)
