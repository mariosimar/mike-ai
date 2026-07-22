"""Lettura di log/eventi di crash (via logs.ps1) e lettura di singoli file.

Tutto in sola lettura: serve a far analizzare a Mike crash e malfunzionamenti.
"""
import json
import os
import subprocess

CARTELLA = os.path.dirname(os.path.abspath(__file__))
SCRIPT_LOG = os.path.join(CARTELLA, "logs.ps1")

# Limite per la lettura di un file (evita di mandare file enormi al modello).
MAX_BYTE_FILE = 60_000


def leggi_log_crash(timeout=90):
    """Esegue logs.ps1 e restituisce (report_dict, errore)."""
    if not os.path.exists(SCRIPT_LOG):
        return None, f"Script non trovato: {SCRIPT_LOG}"
    comando = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", SCRIPT_LOG]
    try:
        c = subprocess.run(comando, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return None, "PowerShell non trovato (sei su Windows?)."
    except subprocess.TimeoutExpired:
        return None, "Lettura log troppo lunga, interrotta."
    uscita = (c.stdout or "").strip()
    if not uscita:
        return None, f"Nessun output. Errore: {c.stderr.strip()}"
    try:
        return json.loads(uscita), None
    except json.JSONDecodeError as e:
        return None, f"Log non leggibili (JSON non valido): {e}"


def riassunto_log(report):
    """Trasforma il report dei log in testo leggibile / da dare all'agente."""
    if not report:
        return "(Nessun log.)"
    r = []

    def sezione(titolo, voci, campi):
        r.append(f"\n--- {titolo} ({len(voci)}) ---")
        if not voci:
            r.append("  nessuno")
        for v in voci[:15]:
            r.append("  " + "  ".join(str(v.get(c, "")) for c in campi))

    sezione("CRASH / SPEGNIMENTI ANOMALI", report.get("crash_spegnimenti", []),
            ["ora", "id", "origine", "messaggio"])
    sezione("ERRORI DI SISTEMA (7gg)", report.get("errori_sistema", []),
            ["ora", "origine", "messaggio"])
    sezione("CRASH APPLICAZIONI (7gg)", report.get("errori_applicazioni", []),
            ["ora", "origine", "messaggio"])
    sezione("DUMP DI CRASH (BSOD)", report.get("dump_crash", []),
            ["quando", "file", "mb"])
    sezione("SEGNALAZIONI ERRORI (WER)", report.get("segnalazioni_errori", []),
            ["ora", "messaggio"])
    return "\n".join(r)


def leggi_file(percorso):
    """Legge un file di testo/log (con limite di dimensione). Restituisce (testo, errore)."""
    percorso = percorso.strip().strip('"')
    if not os.path.exists(percorso):
        return None, f"File non trovato: {percorso}"
    if not os.path.isfile(percorso):
        return None, f"Non è un file: {percorso}"
    try:
        dimensione = os.path.getsize(percorso)
        with open(percorso, "r", encoding="utf-8", errors="replace") as f:
            contenuto = f.read(MAX_BYTE_FILE)
        nota = ""
        if dimensione > MAX_BYTE_FILE:
            nota = f"\n…(file troncato: letti {MAX_BYTE_FILE} byte su {dimensione})"
        return contenuto + nota, None
    except Exception as e:
        return None, f"Impossibile leggere il file: {e}"
