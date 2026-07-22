@echo off
REM ============================================================
REM  Manutenzione PC sicura — kit portatile di Mike
REM  Pulizia temp + cestino + cache DNS (e file di sistema se admin).
REM  Per la riparazione file di sistema: tasto destro -> Esegui come amministratore.
REM ============================================================
setlocal
echo.
echo  ====== Manutenzione PC (sicura) ======
echo.
echo  Verranno svuotati: file temporanei, cestino e cache DNS.
echo  Nessun dato personale viene toccato.
echo.
set /p OK=  Procedo? (S/N):
if /i not "%OK%"=="S" ( echo  Annullato. & pause & exit /b )

echo.
echo  [1/4] Svuoto la cache DNS...
ipconfig /flushdns >nul

echo  [2/4] Svuoto il cestino...
powershell -NoProfile -Command "Clear-RecycleBin -Force -ErrorAction SilentlyContinue" 2>nul

echo  [3/4] Elimino i file temporanei...
del /q /s "%TEMP%\*" >nul 2>&1
net session >nul 2>&1
if %errorlevel%==0 (
    del /q /s "C:\Windows\Temp\*" >nul 2>&1
    echo  [4/4] Riparo i file di sistema ^(sfc^)... ^(puo' durare diversi minuti^)
    sfc /scannow
) else (
    echo  [4/4] Riparazione file di sistema saltata: avvia come amministratore per includerla.
)

echo.
echo  ====== Manutenzione completata ======
echo.
pause
endlocal
