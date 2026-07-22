# logs.ps1 — Raccolta di log ed eventi di errore/crash (SOLA LETTURA).
# Serve a Mike per analizzare crash, blocchi e malfunzionamenti.
# Uso:  powershell -ExecutionPolicy Bypass -File logs.ps1

$ErrorActionPreference = "SilentlyContinue"
# Forza l'output in UTF-8 così gli accenti italiani arrivano corretti a Python.
$OutputEncoding = [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
$out = [ordered]@{}
$da = (Get-Date).AddDays(-7)

function Taglia($t, $n = 220) {
    if (-not $t) { return "" }
    $t = ($t -replace "\s+", " ").Trim()
    if ($t.Length -gt $n) { return $t.Substring(0, $n) + "…" } else { return $t }
}

# Crash / spegnimenti anomali / riavvii inattesi
$crash = @()
Get-WinEvent -FilterHashtable @{ LogName = "System"; Id = 41, 6008, 1001, 1018 } -MaxEvents 15 -ErrorAction SilentlyContinue |
    ForEach-Object {
        $crash += [ordered]@{ ora = $_.TimeCreated.ToString("yyyy-MM-dd HH:mm"); id = $_.Id; origine = $_.ProviderName; messaggio = (Taglia $_.Message) }
    }
$out["crash_spegnimenti"] = $crash

# Errori critici di sistema (ultimi 7 giorni)
$sys = @()
Get-WinEvent -FilterHashtable @{ LogName = "System"; Level = 1, 2; StartTime = $da } -MaxEvents 20 -ErrorAction SilentlyContinue |
    ForEach-Object { $sys += [ordered]@{ ora = $_.TimeCreated.ToString("yyyy-MM-dd HH:mm"); origine = $_.ProviderName; messaggio = (Taglia $_.Message) } }
$out["errori_sistema"] = $sys

# Errori delle applicazioni (crash di programmi)
$app = @()
Get-WinEvent -FilterHashtable @{ LogName = "Application"; Level = 1, 2; StartTime = $da } -MaxEvents 20 -ErrorAction SilentlyContinue |
    ForEach-Object { $app += [ordered]@{ ora = $_.TimeCreated.ToString("yyyy-MM-dd HH:mm"); origine = $_.ProviderName; messaggio = (Taglia $_.Message) } }
$out["errori_applicazioni"] = $app

# File di dump dei crash (BSOD)
$dumps = @()
foreach ($p in @("C:\Windows\Minidump", "C:\Windows\MEMORY.DMP")) {
    Get-ChildItem $p -ErrorAction SilentlyContinue | ForEach-Object {
        $dumps += [ordered]@{ file = $_.FullName; quando = $_.LastWriteTime.ToString("yyyy-MM-dd HH:mm"); mb = [math]::Round($_.Length / 1MB, 1) }
    }
}
$out["dump_crash"] = $dumps

# Report di Windows Error Reporting (segnalazioni problemi)
$wer = @()
Get-WinEvent -FilterHashtable @{ LogName = "Application"; ProviderName = "Windows Error Reporting" } -MaxEvents 10 -ErrorAction SilentlyContinue |
    ForEach-Object { $wer += [ordered]@{ ora = $_.TimeCreated.ToString("yyyy-MM-dd HH:mm"); messaggio = (Taglia $_.Message 260) } }
$out["segnalazioni_errori"] = $wer

$out | ConvertTo-Json -Depth 5
