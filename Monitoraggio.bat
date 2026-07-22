@echo off
REM ============================================================
REM  Monitoraggio PC di Mike (portatile).
REM  Controlla ogni 5 minuti spazio disco e RAM: se scendono
REM  sotto le soglie, mostra un avviso sullo schermo.
REM  Lascialo aperto sul PC del cliente per tenerlo d'occhio.
REM ============================================================
title Mike - Monitoraggio PC
echo.
echo  Monitoraggio attivo. Controllo ogni 5 minuti.
echo  (Chiudi questa finestra per fermarlo.)
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
 "Add-Type -AssemblyName System.Windows.Forms; while($true){" ^
 "$d=Get-CimInstance Win32_LogicalDisk -Filter \"DeviceID='C:'\";" ^
 "$gb=[math]::Round($d.FreeSpace/1GB,1);" ^
 "$os=Get-CimInstance Win32_OperatingSystem;" ^
 "$ram=[math]::Round((($os.TotalVisibleMemorySize-$os.FreePhysicalMemory)/$os.TotalVisibleMemorySize)*100,0);" ^
 "$ora=Get-Date -Format 'HH:mm';" ^
 "Write-Host \"[$ora] Disco liberi: $gb GB  |  RAM usata: $ram%%\";" ^
 "if($gb -lt 10){[System.Windows.Forms.MessageBox]::Show(\"Spazio disco basso: solo $gb GB liberi su C:.`nConviene liberare spazio.\",'Mike - Avviso PC')};" ^
 "if($ram -gt 92){[System.Windows.Forms.MessageBox]::Show(\"RAM quasi esaurita ($ram%% usata).`nConviene chiudere qualche programma.\",'Mike - Avviso PC')};" ^
 "Start-Sleep -Seconds 300 }"

pause
