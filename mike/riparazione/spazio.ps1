# spazio.ps1 — Analisi PROFONDA dello spazio disco (SOLA LETTURA).
# Trova dove finisce lo spazio, inclusi i file NASCOSTI e di SISTEMA che
# Esplora File non mostra e che non riesci a cancellare a mano.
# Uso:  powershell -ExecutionPolicy Bypass -File spazio.ps1

$ErrorActionPreference = "SilentlyContinue"
$OutputEncoding = [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false

function Dim($percorso) {
    # Usa robocopy in modalità SOLO ELENCO (/L): è molto più veloce della scansione
    # ricorsiva per calcolare la dimensione totale di una cartella (inclusi i nascosti).
    if (-not (Test-Path $percorso)) { return 0 }
    try {
        # Indipendente dalla lingua: nel riepilogo le 3 righe con tre numeri sono
        # Dir/File/Byte; la TERZA è i Byte totali (primo numero = Totale).
        $out = robocopy "$percorso" "$env:TEMP\__mike_nul__" /L /E /BYTES /NFL /NDL /NC /NP /NJH /R:0 /W:0 2>$null
        $nums = @()
        foreach ($riga in $out) {
            if ($riga -match ':\s+(\d+)\s+(\d+)\s+(\d+)') { $nums += [int64]$matches[1] }
        }
        if ($nums.Count -ge 3) { return [math]::Round($nums[2] / 1GB, 2) }
        return 0
    } catch { return 0 }
}
function FileDim($percorso) {
    if (Test-Path $percorso) { return [math]::Round((Get-Item $percorso -Force).Length / 1GB, 2) }
    return 0
}

$sysdrive = $env:SystemDrive
$win = "$sysdrive\Windows"

# Spazio del disco
$d = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$sysdrive'"
$totGb = [math]::Round($d.Size / 1GB, 1)
$libGb = [math]::Round($d.FreeSpace / 1GB, 1)

"=========================================="
"   ANALISI SPAZIO DISCO  ($sysdrive)"
"=========================================="
"Totale: $totGb GB   |   Libero: $libGb GB   |   Usato: $([math]::Round($totGb-$libGb,1)) GB"
""
"--- FILE E CACHE NASCOSTI CHE OCCUPANO SPAZIO (recuperabili) ---"

$voci = [ordered]@{
    "Cestino"                          = Dim "$sysdrive\`$Recycle.Bin"
    "Temp utente"                      = Dim $env:TEMP
    "Temp di Windows"                  = Dim "$win\Temp"
    "Cache Aggiornamenti Windows"      = Dim "$win\SoftwareDistribution\Download"
    "Cache Delivery Optimization"      = Dim "$win\SoftwareDistribution\DeliveryOptimization"
    "Prefetch"                         = Dim "$win\Prefetch"
    "Log di Windows (CBS/vecchi)"      = Dim "$win\Logs"
    "Report errori (WER)"              = Dim "$env:ProgramData\Microsoft\Windows\WER"
    "Cache miniature"                  = Dim "$env:LOCALAPPDATA\Microsoft\Windows\Explorer"
    "Download (utente)"                = Dim "$env:USERPROFILE\Downloads"
}
$tot = 0
foreach ($k in $voci.Keys) {
    $gb = $voci[$k]; $tot += $gb
    if ($gb -gt 0) { "{0,-38} {1,7} GB" -f $k, $gb }
}

"--- FILE DI SISTEMA GROSSI (decisione a parte) ---"
$hib = FileDim "$sysdrive\hiberfil.sys"
$page = FileDim "$sysdrive\pagefile.sys"
$winold = Dim "$sysdrive\Windows.old"
if ($hib -gt 0)   { "{0,-38} {1,7} GB   (ibernazione)" -f "hiberfil.sys", $hib }
if ($page -gt 0)  { "{0,-38} {1,7} GB   (memoria virtuale)" -f "pagefile.sys", $page }
if ($winold -gt 0){ "{0,-38} {1,7} GB   (vecchia installazione Windows)" -f "Windows.old", $winold }

# Component store (WinSxS) — grande ma NON è tutto cancellabile
$winsxs = Dim "$win\WinSxS"
if ($winsxs -gt 0) { "{0,-38} {1,7} GB   (WinSxS: pulibile in parte con DISM)" -f "Archivio componenti", $winsxs }

""
">> SPAZIO RECUPERABILE STIMATO (cache sicure): ~$([math]::Round($tot,1)) GB"
""
"--- CARTELLE PIU' GROSSE nella tua home ---"
Get-ChildItem $env:USERPROFILE -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object {
    [pscustomobject]@{ N = $_.Name; GB = (Dim $_.FullName) }
} | Sort-Object GB -Descending | Select-Object -First 6 | ForEach-Object {
    if ($_.GB -gt 0.1) { "{0,-38} {1,7} GB" -f $_.N, $_.GB }
}
