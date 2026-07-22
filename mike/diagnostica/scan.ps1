# scan.ps1 — Diagnostica PC di SOLA LETTURA per Mike.
# Non modifica niente sul sistema: raccoglie solo informazioni e le stampa in JSON.
# Funziona anche senza diritti di amministratore (alcune sezioni saranno piu'
# complete se lanciato "come amministratore").
#
# Uso:  powershell -ExecutionPolicy Bypass -File scan.ps1

$ErrorActionPreference = "SilentlyContinue"
$OutputEncoding = [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
$report = [ordered]@{}
$problemi = New-Object System.Collections.ArrayList

function Aggiungi-Problema($gravita, $testo) {
    [void]$problemi.Add([ordered]@{ gravita = $gravita; descrizione = $testo })
}

# --- Privilegi correnti ---
$identita = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identita)
$admin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$report["amministratore"] = $admin

# --- Sistema operativo ---
try {
    $os = Get-CimInstance Win32_OperatingSystem
    $cs = Get-CimInstance Win32_ComputerSystem
    $uptime = (Get-Date) - $os.LastBootUpTime
    $report["sistema"] = [ordered]@{
        nome_pc        = $env:COMPUTERNAME
        utente         = $env:USERNAME
        os             = $os.Caption
        versione       = $os.Version
        build          = $os.BuildNumber
        architettura   = $os.OSArchitecture
        produttore     = $cs.Manufacturer
        modello        = $cs.Model
        uptime_ore     = [math]::Round($uptime.TotalHours, 1)
    }
    if ($uptime.TotalDays -gt 14) {
        Aggiungi-Problema "info" "Il PC e' acceso da $([math]::Round($uptime.TotalDays,0)) giorni: un riavvio potrebbe aiutare."
    }
} catch {}

# --- Memoria RAM ---
try {
    $ramTot = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
    $ramLib = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
    $ramUsoPerc = [math]::Round((($ramTot - $ramLib) / $ramTot) * 100, 0)
    $report["memoria"] = [ordered]@{
        totale_gb = $ramTot; libera_gb = $ramLib; uso_percento = $ramUsoPerc
    }
    if ($ramUsoPerc -gt 90) { Aggiungi-Problema "alta" "RAM quasi esaurita ($ramUsoPerc% in uso)." }
} catch {}

# --- Dischi ---
try {
    $dischi = @()
    Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
        $totGb = [math]::Round($_.Size / 1GB, 1)
        $libGb = [math]::Round($_.FreeSpace / 1GB, 1)
        $libPerc = if ($_.Size -gt 0) { [math]::Round(($_.FreeSpace / $_.Size) * 100, 0) } else { 0 }
        $dischi += [ordered]@{ unita = $_.DeviceID; totale_gb = $totGb; libero_gb = $libGb; libero_percento = $libPerc }
        if ($libPerc -lt 10) { Aggiungi-Problema "alta" "Disco $($_.DeviceID) quasi pieno (solo $libPerc% libero)." }
        elseif ($libPerc -lt 20) { Aggiungi-Problema "media" "Disco $($_.DeviceID) con poco spazio ($libPerc% libero)." }
    }
    $report["dischi"] = $dischi
} catch {}

# --- Salute fisica dei dischi (SSD/HDD) ---
try {
    $salute = @()
    Get-PhysicalDisk | ForEach-Object {
        $salute += [ordered]@{ modello = $_.FriendlyName; tipo = $_.MediaType; salute = $_.HealthStatus }
        if ($_.HealthStatus -and $_.HealthStatus -ne "Healthy") {
            Aggiungi-Problema "critica" "Disco fisico '$($_.FriendlyName)' in stato '$($_.HealthStatus)': rischio guasto!"
        }
    }
    if ($salute.Count -gt 0) { $report["salute_dischi"] = $salute }
} catch {}

# --- Processi che consumano piu' memoria ---
try {
    $top = Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 8 |
        ForEach-Object { [ordered]@{ nome = $_.ProcessName; ram_mb = [math]::Round($_.WorkingSet64 / 1MB, 0) } }
    $report["processi_top"] = $top
} catch {}

# --- Programmi all'avvio ---
try {
    $avvio = Get-CimInstance Win32_StartupCommand |
        Select-Object -First 25 |
        ForEach-Object { [ordered]@{ nome = $_.Name; comando = $_.Command; posizione = $_.Location } }
    $report["avvio"] = $avvio
    if ($avvio.Count -gt 15) { Aggiungi-Problema "media" "Molti programmi all'avvio ($($avvio.Count)): possono rallentare l'accensione." }
} catch {}

# --- Errori recenti nel registro eventi (ultime 24h) ---
try {
    $da = (Get-Date).AddDays(-1)
    $errori = Get-WinEvent -FilterHashtable @{ LogName = "System"; Level = 1, 2; StartTime = $da } -MaxEvents 15 |
        ForEach-Object { [ordered]@{ ora = $_.TimeCreated.ToString("yyyy-MM-dd HH:mm"); origine = $_.ProviderName; messaggio = ($_.Message -replace "\s+", " ").Substring(0, [math]::Min(200, $_.Message.Length)) } }
    $report["errori_sistema_24h"] = $errori
    if ($errori.Count -gt 10) { Aggiungi-Problema "media" "Molti errori di sistema nelle ultime 24h ($($errori.Count))." }
} catch {}

# --- Rete ---
try {
    $rete = Get-NetIPConfiguration | Where-Object { $_.IPv4Address } |
        Select-Object -First 5 |
        ForEach-Object { [ordered]@{ scheda = $_.InterfaceAlias; ip = $_.IPv4Address.IPAddress; gateway = $_.IPv4DefaultGateway.NextHop } }
    $ping = Test-Connection -ComputerName 8.8.8.8 -Count 1 -Quiet
    $report["rete"] = [ordered]@{ schede = $rete; internet = $ping }
    if (-not $ping) { Aggiungi-Problema "media" "Nessuna risposta da internet (ping a 8.8.8.8 fallito)." }
} catch {}

# --- Riavvio in sospeso ---
try {
    $pending = Test-Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired"
    $report["riavvio_in_sospeso"] = $pending
    if ($pending) { Aggiungi-Problema "media" "C'e' un riavvio in sospeso (aggiornamenti Windows)." }
} catch {}

# --- Cartelle temporanee (spazio recuperabile) ---
try {
    $temp = "$env:TEMP"
    $dimMb = [math]::Round(((Get-ChildItem $temp -Recurse -Force | Measure-Object Length -Sum).Sum) / 1MB, 0)
    $report["temp_mb"] = $dimMb
    if ($dimMb -gt 1000) { Aggiungi-Problema "info" "Cartella temporanea grande ($dimMb MB): si puo' pulire." }
} catch {}

$report["problemi_rilevati"] = $problemi
$report["nota_admin"] = if ($admin) { "Eseguito come amministratore: diagnosi completa." } else { "Eseguito SENZA admin: per una diagnosi piu' profonda, lancia come amministratore." }

# Stampa il report in JSON (profondita' alta per non troncare gli oggetti annidati)
$report | ConvertTo-Json -Depth 6
