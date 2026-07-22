# voce_stt.ps1 — Ascolta dal microfono UNA frase e la stampa come testo.
# Usa il riconoscimento vocale di Windows (System.Speech), nessuna installazione.
# Richiede che sia installato il riconoscitore vocale per la lingua scelta.
# Uso:  powershell -ExecutionPolicy Bypass -File voce_stt.ps1 -TimeoutSec 8 -Cultura it-IT

param([int]$TimeoutSec = 8, [string]$Cultura = "it-IT")
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech
try {
    try {
        $ci = New-Object System.Globalization.CultureInfo($Cultura)
        $rec = New-Object System.Speech.Recognition.SpeechRecognitionEngine($ci)
    } catch {
        # Lingua non installata: usa il riconoscitore predefinito disponibile
        $rec = New-Object System.Speech.Recognition.SpeechRecognitionEngine
    }
    $rec.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
    $rec.SetInputToDefaultAudioDevice()
    $res = $rec.Recognize([TimeSpan]::FromSeconds($TimeoutSec))
    if ($res) { Write-Output $res.Text } else { Write-Output "" }
    $rec.Dispose()
} catch {
    Write-Error ("STT_NON_DISPONIBILE: " + $_.Exception.Message)
}
