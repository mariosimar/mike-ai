@echo off
REM ============================================================
REM  LIBERA SPAZIO — kit portatile di Mike
REM  Trova ed elimina i file NASCOSTI di sistema che riempiono il
REM  disco e che non riesci a cancellare a mano (cache aggiornamenti,
REM  temp di sistema, component store, cestino, miniature...).
REM  Si auto-eleva ad amministratore (necessario per i file nascosti).
REM ============================================================
setlocal EnableDelayedExpansion

REM --- Auto-elevazione ad amministratore (chiede conferma UAC) ---
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  Servono i diritti di amministratore per liberare i file nascosti.
    echo  Confermo la richiesta di Windows...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
title Mike - Libera Spazio (Amministratore)

echo.
echo  ========== ANALISI SPAZIO (prima) ==========
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0mike\riparazione\spazio.ps1"
echo.
echo  ============================================================
echo   Sto per eliminare le CACHE DI SISTEMA sicure (recuperabili):
echo    - File temporanei (utente e Windows)
echo    - Cestino
echo    - Cache Aggiornamenti Windows
echo    - Cache Delivery Optimization
echo    - Cache miniature
echo    - Report errori vecchi
echo    - Pulizia archivio componenti (DISM)
echo   Nessun documento o file personale viene toccato.
echo  ============================================================
echo.
set /p OK=  Procedo con la pulizia? (S/N):
if /i not "%OK%"=="S" ( echo  Annullato. & pause & exit /b )

echo.
echo  [1/8] Cestino...
powershell -NoProfile -Command "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"

echo  [2/8] File temporanei...
del /f /s /q "%TEMP%\*" >nul 2>&1
del /f /s /q "%SystemRoot%\Temp\*" >nul 2>&1

echo  [3/8] Cache Aggiornamenti Windows...
net stop wuauserv >nul 2>&1
net stop bits >nul 2>&1
del /f /s /q "%SystemRoot%\SoftwareDistribution\Download\*" >nul 2>&1
net start bits >nul 2>&1
net start wuauserv >nul 2>&1

echo  [4/8] Cache Delivery Optimization...
powershell -NoProfile -Command "Delete-DeliveryOptimizationCache -Force -ErrorAction SilentlyContinue"

echo  [5/8] Cache miniature...
del /f /s /q "%LOCALAPPDATA%\Microsoft\Windows\Explorer\thumbcache_*.db" >nul 2>&1

echo  [6/8] Report errori vecchi (WER)...
del /f /s /q "%ProgramData%\Microsoft\Windows\WER\ReportArchive\*" >nul 2>&1
del /f /s /q "%ProgramData%\Microsoft\Windows\WER\ReportQueue\*" >nul 2>&1

echo  [7/8] Prefetch...
del /f /s /q "%SystemRoot%\Prefetch\*" >nul 2>&1

echo  [8/8] Pulizia archivio componenti Windows (DISM, puo' durare qualche minuto)...
Dism.exe /Online /Cleanup-Image /StartComponentCleanup >nul 2>&1

echo.
echo  ========== ANALISI SPAZIO (dopo) ==========
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0mike\riparazione\spazio.ps1"
echo.
echo  ============================================================
echo   PULIZIA COMPLETATA.
echo.
echo   NOTA: se vedi ancora "Windows.old" o "hiberfil.sys" occupare
echo   molti GB, dimmelo in Mike: sono decisioni a parte (recupero
echo   sistema / ibernazione) e le gestiamo con attenzione.
echo  ============================================================
echo.
pause
endlocal
