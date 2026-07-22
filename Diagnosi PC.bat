@echo off
REM ============================================================
REM  Diagnosi PC — kit portatile di Mike (sola lettura)
REM  Gira su QUALSIASI PC Windows senza installare niente.
REM  Per la diagnosi completa: tasto destro -> "Esegui come amministratore".
REM ============================================================
setlocal
cd /d "%~dp0"

set "SCAN=%~dp0mike\diagnostica\scan.ps1"
set "FMT=%~dp0mike\diagnostica\formatta.ps1"
set "DEST=%~dp0Report"
if not exist "%DEST%" mkdir "%DEST%"

REM Nome file con data e nome del PC
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%i"
set "JSON=%DEST%\report_%COMPUTERNAME%_%STAMP%.json"
set "TXT=%DEST%\report_%COMPUTERNAME%_%STAMP%.txt"

echo.
echo  Scansione del PC in corso (solo lettura, nessuna modifica)...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCAN%" > "%JSON%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%FMT%" -Percorso "%JSON%" > "%TXT%"

echo  Fatto! Report salvati nella cartella "Report":
echo    - %TXT%
echo    - %JSON%
echo.
echo  Apro il report leggibile...
start "" notepad "%TXT%"

echo.
echo  Suggerimento: porta il file .json dentro Mike e scrivi /diagnosi
echo  per avere l'analisi automatica con soluzioni.
echo.
pause
endlocal
