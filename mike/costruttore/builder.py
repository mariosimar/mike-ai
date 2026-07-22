"""Generatore di software di Mike.

Dato un obiettivo in linguaggio naturale ("creami un bot che…", "un programma
che…"), il modello genera un progetto COMPLETO (uno o più file), che Mike scrive
in una cartella dentro 'progetti/'. Poi il programma può essere avviato (con conferma).

Formato robusto (niente JSON fragile per il codice): il modello risponde con blocchi
delimitati, molto più affidabili con i modelli locali:

    === FILE: main.py ===
    <codice completo>
    === FILE: requirements.txt ===
    <contenuto>
    === AVVIO: python main.py ===
    === NOTE: cosa fa e come si usa ===
"""
import os
import re
import time

from .. import config as cfg_mod
from ..agents import llm as agent_llm

CARTELLA_PROGETTI = os.path.join(cfg_mod.RADICE, "progetti")

SISTEMA = (
    "Sei un ingegnere del software SENIOR. Crei programmi COMPLETI, funzionanti e "
    "puliti. Preferisci Python (solo librerie standard quando possibile). "
    "Scrivi codice reale e completo: niente segnaposto, niente '...', niente parti "
    "da completare. Commenti in italiano.\n\n"
    "Rispondi SOLO con i file del progetto in questo formato ESATTO, senza testo "
    "prima o dopo, senza recinti markdown:\n"
    "=== FILE: nomefile ===\n<contenuto completo del file>\n"
    "=== FILE: altrofile ===\n<contenuto>\n"
    "=== AVVIO: comando per eseguirlo ===\n"
    "=== NOTE: 2-3 righe su cosa fa e come si usa ===\n"
)

_HEADER = re.compile(r"===\s*(FILE|AVVIO|NOTE)\s*:\s*(.*?)\s*===", re.IGNORECASE)


def _slug(testo, massimo=32):
    testo = re.sub(r"[^a-zA-Z0-9]+", "_", testo.lower()).strip("_")
    return (testo[:massimo] or "progetto").strip("_")


def _percorso_sicuro(percorso):
    """Impedisce di scrivere fuori dalla cartella del progetto (niente .. o assoluti)."""
    percorso = percorso.replace("\\", "/").lstrip("/")
    parti = [p for p in percorso.split("/") if p not in ("", ".", "..")]
    return "/".join(parti) or "file.txt"


def _parse(risposta):
    """Estrae (files, avvio, note) dalla risposta del modello."""
    files, avvio, note = [], "", ""
    matches = list(_HEADER.finditer(risposta))
    for i, mt in enumerate(matches):
        tipo = mt.group(1).upper()
        arg = mt.group(2).strip()
        inizio = mt.end()
        fine = matches[i + 1].start() if i + 1 < len(matches) else len(risposta)
        corpo = risposta[inizio:fine].strip("\n")
        # toglie eventuali recinti markdown ```
        corpo = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", corpo).strip("\n")
        if tipo == "FILE" and arg:
            files.append((_percorso_sicuro(arg), corpo))
        elif tipo == "AVVIO":
            avvio = (arg or corpo).strip()
        elif tipo == "NOTE":
            note = (arg + "\n" + corpo).strip()
    return files, avvio, note


def crea_progetto(descrizione, cfg, log=None):
    """Genera il progetto e scrive i file. Restituisce (ok, messaggio, info)."""
    log = log or (lambda s: None)
    provider = agent_llm.provider_predefinito(cfg)
    if not provider:
        return False, "Per creare software mi serve un cervello attivo (Ollama o una chiave).", None

    log("Sto progettando e scrivendo il codice…")
    try:
        risposta = agent_llm.chiedi(cfg, provider, SISTEMA,
                                    f"Crea questo software: {descrizione}", max_token=3500)
    except Exception as e:
        return False, f"Generazione non riuscita: {e}", None

    files, avvio, note = _parse(risposta)
    if not files:
        return False, ("Non sono riuscito a produrre file validi. Riprova con una descrizione "
                       "più precisa, o passa a un modello più potente (/cervello gpt-oss:20b)."), None

    nome = _slug(descrizione) + "_" + time.strftime("%H%M%S")
    cartella = os.path.join(CARTELLA_PROGETTI, nome)
    os.makedirs(cartella, exist_ok=True)

    creati = []
    for rel, contenuto in files:
        dest = os.path.join(cartella, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(contenuto)
        creati.append(rel)

    righe = [f"✅ Progetto creato in: {cartella}", "", "📄 File:"]
    righe += [f"  • {c}" for c in creati]
    if note:
        righe += ["", "ℹ️ " + note]
    if avvio:
        righe += ["", f"▶️ Per avviarlo: {avvio}"]
    messaggio = "\n".join(righe)
    info = {"cartella": cartella, "avvio": avvio, "files": creati}
    return True, messaggio, info


def avvia_progetto(info):
    """Avvia il programma generato (da chiamare SOLO dopo conferma dell'utente)."""
    import subprocess
    cartella = info.get("cartella")
    avvio = (info.get("avvio") or "").strip()
    if not cartella or not os.path.isdir(cartella):
        return False, "Cartella del progetto non trovata."
    if not avvio:
        # prova a indovinare: primo .py
        py = [f for f in info.get("files", []) if f.endswith(".py")]
        if not py:
            return False, "Non so come avviarlo (nessun comando di avvio)."
        avvio = f"python {py[0]}"
    try:
        subprocess.Popen(avvio, shell=True, cwd=cartella)
        return True, f"▶️ Avviato: {avvio}\n(nella cartella {cartella})"
    except Exception as e:
        return False, f"Avvio non riuscito: {e}"
