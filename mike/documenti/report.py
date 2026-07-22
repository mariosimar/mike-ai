"""Genera un REPORT completo del progetto Mike, pensato per una revisione esterna
(es. da parte di Gemini): riassunto, architettura, confini di sicurezza, domande
di revisione e tutto il codice sorgente.
"""
import ast
import os
import time

from .. import config as cfg_mod

RADICE = cfg_mod.RADICE

PROMPT_REVISIONE = (
    "Sei un revisore software esperto (sicurezza + qualità del codice). "
    "Ti passo il report completo di un progetto chiamato «Mike» (assistente AI per "
    "un tecnico informatico, in Python, su Windows). Fai un controllo critico e "
    "rispondi in italiano con: 1) bug o errori che vedi; 2) rischi di sicurezza; "
    "3) se i confini etici dichiarati sono rispettati nel codice; 4) miglioramenti "
    "concreti consigliati; 5) un giudizio complessivo. Sii specifico e severo.\n\n"
    "=== REPORT ===\n"
)

CONFINI = """\
Durante lo sviluppo sono stati rifiutati (per scelta etica e di sicurezza):
- estrazione/cracking di password (furto credenziali) → si usa solo il RESET legittimo;
- bypass dei controlli di amministratore/UAC → si usa l'elevazione consensuale;
- auto-riscrittura/esecuzione di codice non supervisionata → l'auto-update è con
  conferma, backup, verifica sintassi, hash SHA-256 e ripristino automatico.
Le azioni che modificano il sistema richiedono sempre conferma esplicita (/conferma).
"""

DOMANDE = """\
1. Ci sono BUG o errori logici? (gestione errori, encoding, casi limite)
2. Ci sono RISCHI DI SICUREZZA? (esecuzione comandi, percorsi, input non validati,
   il provider Ollama locale, l'auto-aggiornamento, il reset password)
3. I CONFINI ETICI dichiarati sono davvero rispettati nel codice?
4. L'AUTO-AGGIORNAMENTO è sicuro? (backup, rollback, verifica hash, validazione)
5. Suggerimenti CONCRETI di miglioramento (qualità, robustezza, struttura).
6. Giudizio complessivo e priorità degli interventi.
"""


def _docstring(percorso):
    """Prima riga del docstring di un file .py (descrizione del modulo)."""
    try:
        with open(percorso, "r", encoding="utf-8") as f:
            albero = ast.parse(f.read())
        doc = ast.get_docstring(albero) or ""
        return doc.strip().splitlines()[0] if doc.strip() else ""
    except Exception:
        return ""


def _raccogli_file():
    elenco = []
    for radice, _dirs, files in os.walk(os.path.join(RADICE, "mike")):
        if "__pycache__" in radice:
            continue
        for f in sorted(files):
            if f.endswith((".py", ".ps1")):
                elenco.append(os.path.join(radice, f))
    for f in ["avvia.py", "crea_manifesto.py", "config.example.json", "version.json"]:
        p = os.path.join(RADICE, f)
        if os.path.exists(p):
            elenco.append(p)
    return elenco


def _versione():
    try:
        import json
        with open(os.path.join(RADICE, "version.json"), encoding="utf-8") as f:
            return json.load(f).get("versione", "?")
    except Exception:
        return "?"


def genera():
    """Crea il file del report e restituisce (percorso, testo)."""
    file_progetto = _raccogli_file()
    righe = []
    A = righe.append

    A(f"# REPORT PROGETTO «MIKE» — per revisione esterna")
    A(f"Versione {_versione()} — generato il {time.strftime('%Y-%m-%d %H:%M')}\n")

    A("## 1. Cos'è Mike")
    A("Assistente AI personale per un tecnico informatico, scritto in **Python** "
      "(solo libreria standard) con interfaccia **tkinter**. Gira su **Windows**. "
      "Cervello AI: **Ollama in locale** (predefinito, senza chiave) con riserva "
      "**Claude/Gemini** via API. Funzioni: chat, sistema **multi-agente** con "
      "verifica incrociata, **diagnostica PC**, analisi **crash/log**, **recupero "
      "accesso** (reset password), **riparazione/pulizia** con conferma, **voce**, "
      "**auto-miglioramento**, **auto-aggiornamento** del codice, kit USB.\n")

    A("## 2. Architettura (moduli)")
    conta_righe = 0
    for p in file_progetto:
        rel = os.path.relpath(p, RADICE).replace(os.sep, "/")
        try:
            n = sum(1 for _ in open(p, encoding="utf-8", errors="replace"))
        except Exception:
            n = 0
        conta_righe += n
        desc = _docstring(p) if p.endswith(".py") else ""
        A(f"- `{rel}` ({n} righe) — {desc}")
    A(f"\n**Totale: {len(file_progetto)} file, ~{conta_righe} righe.**\n")

    A("## 3. Confini di sicurezza dichiarati")
    A(CONFINI)

    A("## 4. Domande per il revisore")
    A(DOMANDE)

    A("## 5. Codice sorgente completo\n")
    for p in file_progetto:
        rel = os.path.relpath(p, RADICE).replace(os.sep, "/")
        ext = "python" if p.endswith(".py") else ("powershell" if p.endswith(".ps1") else "")
        A(f"### {rel}")
        A(f"```{ext}")
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                A(f.read().rstrip())
        except Exception as e:
            A(f"(impossibile leggere: {e})")
        A("```\n")

    testo = "\n".join(righe)

    cartella = os.path.join(RADICE, "dati", "Report")
    os.makedirs(cartella, exist_ok=True)
    percorso = os.path.join(cartella, f"REPORT_PER_GEMINI_{time.strftime('%Y%m%d_%H%M%S')}.md")
    with open(percorso, "w", encoding="utf-8") as f:
        f.write(testo)
    return percorso, testo


PROMPT_REVISIONE_CLAUDE = (
    "Sei Claude, un revisore software di livello mondiale, esperto in Python, sicurezza e interfacce Tkinter.\n"
    "Ti viene fornito il report completo del progetto «Mike» (un assistente AI locale per tecnici PC Windows).\n"
    "Analizza attentamente tutto il codice sorgente allegato e rispondi in italiano in modo approfondito e severo ai seguenti punti:\n"
    "1. BUG O ERRORI LOGICI: Cerca bug di concorrenza con thread in Tkinter, problemi di encoding su Windows (es. con open() senza specificare encoding), race conditions, eccezioni non catturate o crash del programma.\n"
    "2. RISCHI DI SICUREZZA: Controlla la sicurezza dei comandi eseguiti con subprocess/os.system, la gestione delle chiavi API, la vulnerabilità di Path Traversal, la robustezza della procedura di auto-aggiornamento (hash SHA-256) e il reset delle password locali.\n"
    "3. CONFINI ETICI: Verifica se il codice rispetta i confini dichiarati (nessun furto di password o bypass UAC) e se ci sono comportamenti da malware o spyware nascosti.\n"
    "4. AUTO-AGGIORNAMENTO: La procedura di update, backup, rollback e validazione è solida al 100%? Come può essere resa ancora più a prova di bomba?\n"
    "5. MIGLIORAMENTI ARCHITETTURALI E DI CODICE: Suggerisci modifiche pratiche per rendere il codice più pulito, scalabile, robusto ed efficiente.\n"
    "6. GIUDIZIO COMPLESSIVO E PRIORITÀ: Fornisci una valutazione complessiva e un elenco delle modifiche urgenti in ordine di priorità.\n\n"
    "=== REPORT ===\n"
)


def genera_claude():
    """Crea il file del report per Claude e restituisce (percorso, testo)."""
    file_progetto = _raccogli_file()
    righe = []
    A = righe.append

    A(f"# REPORT PROGETTO «MIKE» — per revisione con CLAUDE")
    A(f"Versione {_versione()} — generato il {time.strftime('%Y-%m-%d %H:%M')}\n")

    A("## 1. Cos'è Mike")
    A("Assistente AI personale per un tecnico informatico, scritto in **Python** "
      "(solo libreria standard) con interfaccia **tkinter**. Gira su **Windows**. "
      "Cervello AI: **Ollama in locale** (predefinito, senza chiave) con riserva "
      "**Claude/Gemini** via API. Funzioni: chat, sistema **multi-agente** con "
      "verifica incrociata, **diagnostica PC**, analisi **crash/log**, **recupero "
      "accesso** (reset password), **riparazione/pulizia** con conferma, **voce**, "
      "**auto-miglioramento**, **auto-aggiornamento** del codice, kit USB.\n")

    A("## 2. Architettura (moduli)")
    conta_righe = 0
    for p in file_progetto:
        rel = os.path.relpath(p, RADICE).replace(os.sep, "/")
        try:
            n = sum(1 for _ in open(p, encoding="utf-8", errors="replace"))
        except Exception:
            n = 0
        conta_righe += n
        desc = _docstring(p) if p.endswith(".py") else ""
        A(f"- `{rel}` ({n} righe) — {desc}")
    A(f"\n**Totale: {len(file_progetto)} file, ~{conta_righe} righe.**\n")

    A("## 3. Confini di sicurezza dichiarati")
    A(CONFINI)

    A("## 4. Domande per Claude")
    A("1. Ci sono BUG o errori logici? (concorrenza thread, Tkinter, encoding, casi limite)\n"
      "2. Ci sono RISCHI DI SICUREZZA? (comandi eseguiti con subprocess/os, chiavi API, Path Traversal, auto-update, reset password)\n"
      "3. I CONFINI ETICI sono rispettati nel codice?\n"
      "4. L'AUTO-AGGIORNAMENTO è sicuro al 100%? Come blindarlo?\n"
      "5. Suggerimenti pratici di miglioramento (pulizia, robustezza, struttura).\n"
      "6. Valutazione complessiva e priorità degli interventi.\n")

    A("## 5. Istruzioni per la revisione")
    A("Copia tutto questo file e incollalo in Claude, oppure trascina il file nella chat di Claude e chiedi:\n"
      f"\"{PROMPT_REVISIONE_CLAUDE.strip()}\"\n")

    A("## 6. Codice sorgente completo\n")
    for p in file_progetto:
        rel = os.path.relpath(p, RADICE).replace(os.sep, "/")
        ext = "python" if p.endswith(".py") else ("powershell" if p.endswith(".ps1") else "")
        A(f"### {rel}")
        A(f"```{ext}")
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                A(f.read().rstrip())
        except Exception as e:
            A(f"(impossibile leggere: {e})")
        A("```\n")

    testo = "\n".join(righe)

    cartella = os.path.join(RADICE, "dati", "Report")
    os.makedirs(cartella, exist_ok=True)
    percorso = os.path.join(cartella, f"REPORT_PER_CLAUDE_{time.strftime('%Y%m%d_%H%M%S')}.md")
    with open(percorso, "w", encoding="utf-8") as f:
        f.write(testo)
    return percorso, testo
