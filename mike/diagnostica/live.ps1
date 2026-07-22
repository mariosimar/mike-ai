# live.ps1 — Istantanea in tempo reale di cosa sta facendo il PC (SOLA LETTURA).
# Serve a Mike per "vedere" davvero i processi attivi e lo stato del sistema.
# Uso:  powershell -ExecutionPolicy Bypass -File live.ps1

$ErrorActionPreference = "SilentlyContinue"
$OutputEncoding = [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false

$os = Get-CimInstance Win32_OperatingSystem
$ramTot = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
$ramLib = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
$ramUso = [math]::Round($ramTot - $ramLib, 1)
$uptime = (Get-Date) - $os.LastBootUpTime
$nproc = (Get-Process).Count

"ISTANTANEA SISTEMA (in tempo reale)"
"RAM in uso: $ramUso GB su $ramTot GB"
"Acceso da: $([math]::Round($uptime.TotalHours,1)) ore"
"Processi attivi totali: $nproc"
""
"Programmi che consumano piu' MEMORIA adesso:"
Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 12 | ForEach-Object {
    "  - {0}  ({1} MB)" -f $_.ProcessName, [math]::Round($_.WorkingSet64 / 1MB)
}
""
"Programmi che hanno usato piu' CPU finora:"
Get-Process | Sort-Object CPU -Descending | Select-Object -First 8 | ForEach-Object {
    "  - {0}  (CPU {1}s)" -f $_.ProcessName, [math]::Round($_.CPU)
}
