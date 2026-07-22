@echo off
REM ============================================================
REM  Collega Mike al TUO repository GitHub (una volta sola).
REM  L'accesso viene gestito dal browser (Git Credential Manager):
REM  approvi tu, le credenziali NON passano da qui.
REM
REM  PRIMA: crea un repository VUOTO su https://github.com
REM         (in alto: + -> New repository -> nome: mike-ai -> Create)
REM ============================================================
setlocal
cd /d "%~dp0"
title Mike - Collega GitHub

echo.
echo  Assicurati di aver gia' creato il repository VUOTO su github.com
echo  (esempio nome: mike-ai). Poi rispondi qui sotto.
echo.
set /p GHUSER=  Il tuo nome utente GitHub:
if "%GHUSER%"=="" ( echo  Nome utente mancante. & pause & exit /b )
set /p GHREPO=  Nome del repository [Invio per "mike-ai"]:
if "%GHREPO%"=="" set GHREPO=mike-ai

echo.
echo  Collego a https://github.com/%GHUSER%/%GHREPO%.git ...
git remote remove origin >nul 2>&1
git remote add origin https://github.com/%GHUSER%/%GHREPO%.git
git branch -M main

echo  Genero il manifesto e preparo i file...
python crea_manifesto.py 0.14.0 "primo caricamento" >nul 2>&1
git add -A
git commit -m "Caricamento iniziale di Mike" >nul 2>&1

echo.
echo  Ora carico su GitHub. Se si apre il browser, ACCEDI/APPROVA tu:
echo.
git push -u origin main

echo.
if errorlevel 1 (
    echo  ============================================================
    echo   Il caricamento non e' riuscito. Possibili cause:
    echo    - il repository non esiste ancora su GitHub ^(crealo vuoto^)
    echo    - non hai approvato l'accesso nel browser
    echo   Riprova dopo aver sistemato.
    echo  ============================================================
) else (
    echo  ============================================================
    echo   FATTO! Mike e' su GitHub.
    echo.
    echo   ULTIMO PASSO: apri config.json e metti in "aggiornamento_sorgente":
    echo   https://raw.githubusercontent.com/%GHUSER%/%GHREPO%/main/manifesto.json
    echo.
    echo   Da ora, per pubblicare aggiornamenti: "Pubblica Aggiornamento.bat"
    echo  ============================================================
)
echo.
pause
endlocal
