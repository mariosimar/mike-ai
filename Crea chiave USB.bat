@echo off
REM ============================================================
REM  Copia Mike su una chiave USB (o qualsiasi cartella).
REM  Esegui questo file dal computer dove Mike e' gia' installato.
REM ============================================================
setlocal
cd /d "%~dp0"

echo.
echo  ====== Creazione chiave USB di Mike ======
echo.
echo  Inserisci la chiavetta USB e guarda quale lettera ha (es. E:, F:, G:).
echo.
set /p LETTERA=  Scrivi la lettera dell'unita' USB (es. E):

REM Toglie eventuali due punti e spazi
set "LETTERA=%LETTERA::=%"
set "LETTERA=%LETTERA: =%"

if not exist "%LETTERA%:\" (
    echo.
    echo  ERRORE: l'unita' %LETTERA%: non esiste. Controlla la lettera e riprova.
    echo.
    pause
    exit /b 1
)

set "DEST=%LETTERA%:\Mike AI"
echo.
echo  Copio Mike in "%DEST%" ...
echo.

REM robocopy e' incluso in Windows. Esclude le cartelle inutili.
robocopy "%~dp0." "%DEST%" /E /XD __pycache__ Report /XF *.pyc /NFL /NDL /NP

echo.
echo  ====== Fatto! ======
echo  Sulla chiavetta trovi la cartella "Mike AI".
echo  - Per la diagnosi su un PC: doppio clic su "Diagnosi PC.bat"
echo  - Per usare Mike (chat + agenti): serve Python sul PC, poi "Avvia Mike.bat"
echo.
pause
endlocal
