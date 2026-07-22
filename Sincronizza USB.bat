@echo off
REM ============================================================
REM  Sincronizza Mike sulla chiavetta USB.
REM  1) Scarica l'ultima versione da GitHub (se collegato)
REM  2) Copia tutto Mike sulla USB (senza le tue chiavi e i dati)
REM  Cosi' porti sempre l'ultima versione dai clienti.
REM ============================================================
setlocal
cd /d "%~dp0"
title Mike - Sincronizza USB

echo.
echo  [1/2] Scarico l'ultima versione da GitHub...
git pull 2>nul
if errorlevel 1 (
    echo        ^(salto: GitHub non collegato o nessuna modifica^)
)

echo.
echo  Inserisci la chiavetta USB e guarda la sua lettera (es. E, F, G).
set /p LETTERA=  Lettera dell'unita' USB:
set "LETTERA=%LETTERA::=%"
set "LETTERA=%LETTERA: =%"
if not exist "%LETTERA%:\" (
    echo  L'unita' %LETTERA%: non esiste. Riprova.
    pause
    exit /b 1
)

set "DEST=%LETTERA%:\Mike AI"
echo.
echo  [2/2] Copio Mike in "%DEST%" ...
REM Esclude chiavi, dati personali, cache e cartella git.
robocopy "%~dp0." "%DEST%" /MIR /XD __pycache__ dati progetti .git .claude Report /XF config.json *.pyc /NFL /NDL /NP /R:1 /W:1 >nul

REM Copia l'esempio di config (senza chiavi) se sulla USB non c'e' un config
if not exist "%DEST%\config.json" copy "%~dp0config.example.json" "%DEST%\config.json" >nul

echo.
echo  ============================================================
echo   FATTO! Sulla chiavetta c'e' l'ultima versione di Mike.
echo.
echo   Sul PC del cliente, dalla USB, puoi usare SUBITO (senza Python):
echo    - "Diagnosi PC.bat"      (analisi del PC)
echo    - "Libera Spazio.bat"    (libera memoria, anche file nascosti)
echo    - "Manutenzione PC.bat"  (pulizia completa)
echo   Per Mike completo serve Python + Ollama sul PC del cliente.
echo  ============================================================
echo.
pause
endlocal
