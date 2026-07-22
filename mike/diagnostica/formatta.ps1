# formatta.ps1 - legge un report JSON prodotto da scan.ps1 e lo stampa in
# formato leggibile da un umano (per il tecnico, anche su PC senza Python).
# Uso:  powershell -ExecutionPolicy Bypass -File formatta.ps1 -Percorso report.json

param([Parameter(Mandatory=$true)][string]$Percorso)

$ErrorActionPreference = "SilentlyContinue"
$r = Get-Content $Percorso -Raw | ConvertFrom-Json

"==================================================="
"   DIAGNOSI PC - generata da Mike"
"==================================================="
$s = $r.sistema
"PC:        $($s.nome_pc)  ($($s.produttore) $($s.modello))"
"Sistema:   $($s.os)  build $($s.build)  $($s.architettura)"
"Utente:    $($s.utente)"
"Acceso da: $($s.uptime_ore) ore"
"Admin:     $($r.amministratore)"
""
$m = $r.memoria
if ($m) { "RAM:       $($m.libera_gb) GB liberi su $($m.totale_gb) GB  ($($m.uso_percento)% in uso)" }
foreach ($d in $r.dischi) {
    "Disco $($d.unita)  $($d.libero_gb) GB liberi su $($d.totale_gb) GB  ($($d.libero_percento)% libero)"
}
foreach ($sd in $r.salute_dischi) {
    "Salute disco: $($sd.modello) [$($sd.tipo)] -> $($sd.salute)"
}
if ($r.rete) { "Internet:  $(if ($r.rete.internet) {'OK'} else {'NON RAGGIUNGIBILE'})" }
if ($r.riavvio_in_sospeso) { "Riavvio in sospeso: SI" }
if ($null -ne $r.temp_mb) { "Temp:      $($r.temp_mb) MB (pulibili)" }
""
"--- PROBLEMI RILEVATI ---"
if ($r.problemi_rilevati -and $r.problemi_rilevati.Count -gt 0) {
    foreach ($p in $r.problemi_rilevati) {
        "  [$($p.gravita.ToUpper())]  $($p.descrizione)"
    }
} else {
    "  Nessun problema evidente."
}
""
"--- PROGRAMMI ALL'AVVIO ---"
foreach ($a in $r.avvio) { "  $($a.nome)" }
""
"--- ERRORI DI SISTEMA (24h) ---"
if ($r.errori_sistema_24h -and $r.errori_sistema_24h.Count -gt 0) {
    foreach ($e in $r.errori_sistema_24h) { "  $($e.ora)  [$($e.origine)]  $($e.messaggio)" }
} else {
    "  Nessuno."
}
""
$r.nota_admin
