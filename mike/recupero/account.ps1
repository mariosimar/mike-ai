# account.ps1 — Analisi degli account utente di Windows (SOLA LETTURA).
# Non modifica niente: serve solo a capire la situazione per recuperare l'accesso.
# Uso:  powershell -ExecutionPolicy Bypass -File account.ps1

$ErrorActionPreference = "SilentlyContinue"
$OutputEncoding = [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
$out = [ordered]@{}

# Sono amministratore adesso?
$id = [Security.Principal.WindowsIdentity]::GetCurrent()
$pr = New-Object Security.Principal.WindowsPrincipal($id)
$out["amministratore"] = $pr.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

# Membri del gruppo Administrators (per sapere chi e' admin)
$adminMembers = @()
try {
    Get-LocalGroupMember -Group "Administrators" | ForEach-Object { $adminMembers += $_.Name }
} catch {
    # In alcune lingue il gruppo si chiama "Administratoren"/"Amministratori": prova per SID note
    try { Get-LocalGroupMember -SID "S-1-5-32-544" | ForEach-Object { $adminMembers += $_.Name } } catch {}
}

# Elenco account locali
$utenti = @()
Get-LocalUser | ForEach-Object {
    $nome = $_.Name
    $isAdmin = $false
    foreach ($a in $adminMembers) { if ($a -like "*\$nome" -or $a -eq $nome) { $isAdmin = $true } }
    $tipo = "$($_.PrincipalSource)"
    $utenti += [ordered]@{
        nome             = $nome
        abilitato        = [bool]$_.Enabled
        tipo             = if ($tipo) { $tipo } else { "Local" }   # Local / MicrosoftAccount / AzureAD
        amministratore   = $isAdmin
        password_richiesta = [bool]$_.PasswordRequired
        ultimo_accesso   = if ($_.LastLogon) { $_.LastLogon.ToString("yyyy-MM-dd HH:mm") } else { "mai/sconosciuto" }
        descrizione      = $_.Description
    }
}
$out["account"] = $utenti

# Administrator integrato: abilitato o no?
$adminBuiltin = Get-LocalUser -Name "Administrator" -ErrorAction SilentlyContinue
$out["administrator_integrato_abilitato"] = if ($adminBuiltin) { [bool]$adminBuiltin.Enabled } else { $false }

# BitLocker: se attivo, resettare la password puo' far perdere i dati senza la chiave!
$bitlocker = @()
try {
    Get-BitLockerVolume -ErrorAction Stop | ForEach-Object {
        $bitlocker += [ordered]@{ unita = "$($_.MountPoint)"; protezione = "$($_.ProtectionStatus)" }
    }
    $out["bitlocker"] = $bitlocker
    $out["bitlocker_leggibile"] = $true
} catch {
    $out["bitlocker"] = @()
    $out["bitlocker_leggibile"] = $false
}

$out | ConvertTo-Json -Depth 5
