@echo off
REM ============================================================
REM  Pubblica un aggiornamento di Mike su GitHub.
REM  (Prima devi aver collegato il repository: vedi GUIDA_GITHUB.md)
REM ============================================================
setlocal
cd /d "%~dp0"
title Mike - Pubblica Aggiornamento

git remote -v | findstr origin >nul 2>&1
if errorlevel 1 (
    echo.
    echo  Non hai ancora collegato GitHub. Apri GUIDA_GITHUB.md e fai i passi 2 e 3.
    echo.
    pause
    exit /b
)

echo.
set /p VER=  Nuovo numero di versione (es. 0.11.1):
if "%VER%"=="" ( echo  Versione mancante. & pause & exit /b )

set /p NOTE=  Cosa hai cambiato (breve):

echo.
echo  Genero il manifesto (con impronte di sicurezza)...
python crea_manifesto.py %VER% "%NOTE%"

echo  Carico su GitHub...
git add -A
git commit -m "Mike v%VER% - %NOTE%"
git push

echo.
echo  ============================================================
echo   FATTO! Versione %VER% pubblicata.
echo   Tutti i PC con Mike la vedranno all'avvio (/aggiorna-mike).
echo  ============================================================
echo.
pause
endlocal
