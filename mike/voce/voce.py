"""Voce di Mike.

- parla(testo): Mike legge ad alta voce (TTS) con la voce italiana se disponibile.
- ascolta(): cattura una frase dal microfono e la trasforma in testo (STT).

Usa il sistema vocale di Windows (System.Speech via PowerShell): nessuna installazione.
Il TTS funziona quasi sempre. Lo STT richiede il riconoscitore vocale della lingua
installato in Windows (Impostazioni → Ora e lingua → Voce).
"""
import os
import subprocess
import tempfile

CARTELLA = os.path.dirname(os.path.abspath(__file__))
SCRIPT_STT = os.path.join(CARTELLA, "voce_stt.ps1")

# Comando TTS: legge il testo da un file (per gestire testi lunghi e caratteri speciali).
_TTS = (
    "Add-Type -AssemblyName System.Speech; "
    "$t = Get-Content -Raw -Encoding UTF8 '{percorso}'; "
    "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
    "$it = $s.GetInstalledVoices() | Where-Object {{ $_.VoiceInfo.Culture.Name -eq 'it-IT' -and $_.Enabled }} | Select-Object -First 1; "
    "if ($it) {{ $s.SelectVoice($it.VoiceInfo.Name) }}; "
    "$s.Speak($t); $s.Dispose()"
)


def parla(testo):
    """Pronuncia il testo ad alta voce, senza bloccare il programma. True se avviato."""
    if not testo:
        return False
    try:
        # Salva il testo in un file temporaneo
        fd, percorso = tempfile.mkstemp(suffix=".txt", text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(testo)
        comando = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                   "-Command", _TTS.format(percorso=percorso)]
        # Popen = non blocca: Mike continua mentre parla
        subprocess.Popen(comando, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def ascolta(timeout_sec=8, cultura="it-IT"):
    """Ascolta una frase dal microfono. Restituisce (testo, errore)."""
    if not os.path.exists(SCRIPT_STT):
        return None, "Script di ascolto non trovato."
    comando = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
               "-File", SCRIPT_STT, "-TimeoutSec", str(timeout_sec), "-Cultura", cultura]
    try:
        c = subprocess.run(comando, capture_output=True, text=True,
                           timeout=timeout_sec + 15, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return None, "Tempo scaduto: non ho sentito nulla."
    if c.returncode != 0 or "STT_NON_DISPONIBILE" in (c.stderr or ""):
        return None, ("Riconoscimento vocale non disponibile in questa lingua.\n"
                      "Installa la voce in: Impostazioni → Ora e lingua → Voce. "
                      "Per ora scrivi pure la domanda.")
    testo = (c.stdout or "").strip()
    if not testo:
        return None, "Non ho capito (silenzio o audio poco chiaro). Riprova."
    return testo, None
