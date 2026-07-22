@echo off
REM Avvia Mike facendo doppio clic su questo file.
cd /d "%~dp0"
python avvia.py
if errorlevel 1 (
    echo.
    echo Qualcosa e' andato storto. Premi un tasto per chiudere.
    pause >nul
)
