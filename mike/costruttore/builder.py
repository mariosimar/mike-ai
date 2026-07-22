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
    "=== NOTE: 2-3 righe su cosa fa e come si usa ===\n\n"
    "IMPORTANTE: se il programma usa librerie NON standard (es. requests, "
    "python-telegram-bot, pillow…), includi SEMPRE un file 'requirements.txt' con "
    "i nomi pip delle librerie, una per riga."
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
    info = {"cartella": cartella, "avvio": avvio, "files": creati,
            "nome": nome, "descrizione": descrizione}
    return True, messaggio, info


SISTEMA_MODIFICA = (
    "Sei un ingegnere del software SENIOR. Ti do un progetto ESISTENTE e una modifica "
    "da applicare. Applica la modifica e restituisci TUTTI i file del progetto "
    "AGGIORNATI e COMPLETI (non solo le differenze, non abbreviare). Mantieni ciò che "
    "funziona, aggiungi/cambia solo il necessario. Commenti in italiano.\n\n"
    "Rispondi SOLO con i file nel formato ESATTO, senza testo prima o dopo:\n"
    "=== FILE: nomefile ===\n<contenuto completo>\n"
    "=== AVVIO: comando ===\n=== NOTE: cosa è cambiato ===\n"
)


def elenca_progetti():
    """Elenco delle cartelle di progetto create."""
    if not os.path.isdir(CARTELLA_PROGETTI):
        return []
    return sorted(d for d in os.listdir(CARTELLA_PROGETTI)
                  if os.path.isdir(os.path.join(CARTELLA_PROGETTI, d)))


def _leggi_progetto(cartella, max_totale=14000):
    """Legge i file di testo del progetto (con limite totale)."""
    files, tot = [], 0
    for radice, _dirs, fs in os.walk(cartella):
        for f in sorted(fs):
            p = os.path.join(radice, f)
            rel = os.path.relpath(p, cartella).replace(os.sep, "/")
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    c = fh.read()
            except Exception:
                continue
            files.append((rel, c))
            tot += len(c)
            if tot > max_totale:
                return files
    return files


def modifica_progetto(info, richiesta, cfg, log=None):
    """Modifica un progetto esistente secondo la richiesta. (ok, messaggio, info)."""
    log = log or (lambda s: None)
    provider = agent_llm.provider_predefinito(cfg)
    if not provider:
        return False, "Per modificare serve un cervello attivo.", info
    cartella = info.get("cartella")
    if not cartella or not os.path.isdir(cartella):
        return False, "Non trovo la cartella del progetto da modificare.", info

    correnti = _leggi_progetto(cartella)
    if not correnti:
        return False, "Il progetto è vuoto o illeggibile.", info
    blocco = "\n\n".join(f"=== FILE: {rel} ===\n{c}" for rel, c in correnti)

    log("Sto modificando il progetto…")
    try:
        risposta = agent_llm.chiedi(
            cfg, provider, SISTEMA_MODIFICA,
            f"PROGETTO ATTUALE:\n{blocco}\n\nMODIFICA DA APPLICARE: {richiesta}",
            max_token=3800)
    except Exception as e:
        return False, f"Modifica non riuscita: {e}", info

    files, avvio, note = _parse(risposta)
    if not files:
        return False, "Non sono riuscito a produrre la versione modificata. Riprova o usa gpt-oss:20b.", info

    creati = []
    for rel, contenuto in files:
        dest = os.path.join(cartella, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(contenuto)
        creati.append(rel)

    nuovo = dict(info)
    nuovo["files"] = creati
    if avvio:
        nuovo["avvio"] = avvio
    righe = [f"✅ Progetto aggiornato in: {cartella}", "", "📄 File aggiornati:"]
    righe += [f"  • {c}" for c in creati]
    if note:
        righe += ["", "ℹ️ " + note]
    return True, "\n".join(righe), nuovo


# Nomi di import che su pip si chiamano diversamente
_MAP_PIP = {
    "telegram": "python-telegram-bot", "cv2": "opencv-python", "PIL": "pillow",
    "bs4": "beautifulsoup4", "yaml": "pyyaml", "sklearn": "scikit-learn",
    "dotenv": "python-dotenv", "discord": "discord.py", "serial": "pyserial",
    "docx": "python-docx", "win32com": "pywin32", "win32api": "pywin32",
}


def dipendenze(cartella):
    """Trova le librerie extra (pip) usate dal progetto. Restituisce una lista di nomi."""
    req = os.path.join(cartella, "requirements.txt")
    if os.path.exists(req):
        try:
            with open(req, encoding="utf-8", errors="replace") as f:
                libs = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
            if libs:
                return libs
        except Exception:
            pass
    # Nessun requirements.txt: analizza gli import ed escludi la libreria standard
    import re
    import sys
    std = set(getattr(sys, "stdlib_module_names", set()))
    locali, trovati = set(), set()
    for radice, _dirs, fs in os.walk(cartella):
        for f in fs:
            if f.endswith(".py"):
                locali.add(os.path.splitext(f)[0])
    for radice, _dirs, fs in os.walk(cartella):
        for f in fs:
            if not f.endswith(".py"):
                continue
            try:
                with open(os.path.join(radice, f), encoding="utf-8", errors="replace") as fh:
                    testo = fh.read()
            except Exception:
                continue
            for m in re.findall(r"^\s*(?:import|from)\s+([a-zA-Z0-9_]+)", testo, re.MULTILINE):
                if m not in std and m not in locali and m != "__future__":
                    trovati.add(m)
    return sorted(_MAP_PIP.get(m, m) for m in trovati)


def _pip(args, timeout=900):
    """Esegue pip e restituisce (ok, output_completo)."""
    import subprocess
    import sys
    try:
        c = subprocess.run([sys.executable, "-m", "pip"] + args,
                           capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return c.returncode == 0, ((c.stdout or "") + "\n" + (c.stderr or "")).strip()
    except Exception as e:
        return False, str(e)


def installa_dipendenze(cartella, log=None):
    """Installa con pip le librerie del progetto, con AUTO-RIPARAZIONE se fallisce.

    Restituisce (ok, messaggio, errore_grezzo). errore_grezzo è "" se tutto ok.
    """
    log = log or (lambda s: None)
    import re
    libs = dipendenze(cartella)
    if not libs:
        return True, "Nessuna libreria extra da installare.", ""

    req = os.path.join(cartella, "requirements.txt")
    base = ["install", "-r", req] if os.path.exists(req) else ["install"] + libs

    ok, out = _pip(base)
    if ok:
        return True, "✅ Librerie installate: " + ", ".join(libs), ""

    # ---- auto-riparazione ----
    # 1) aggiorna pip/setuptools e riprova
    log("Installazione fallita: aggiorno pip e riprovo…")
    _pip(["install", "--upgrade", "pip", "setuptools", "wheel"])
    ok, out = _pip(base)
    if ok:
        return True, "✅ Librerie installate (dopo aggiornamento di pip): " + ", ".join(libs), ""

    # 2) riprova togliendo le versioni fissate (==, >=, …): spesso è quello il problema
    sciolte = [re.split(r"[=<>!~ ]", l)[0].strip() for l in libs]
    sciolte = [s for s in sciolte if s]
    if sciolte and sciolte != [l.strip() for l in libs]:
        log("Riprovo con le versioni più compatibili…")
        ok, out = _pip(["install"] + sciolte)
        if ok:
            return True, "✅ Installate con versioni compatibili: " + ", ".join(sciolte), ""

    # 3) riprova installando una alla volta (isola il pacchetto problematico)
    installati, falliti = [], []
    for lib in (sciolte or libs):
        ok1, o1 = _pip(["install", lib])
        (installati if ok1 else falliti).append(lib)
        if not ok1:
            out = o1
    if installati and not falliti:
        return True, "✅ Installate (una alla volta): " + ", ".join(installati), ""

    riassunto = (out or "")[-700:]
    messaggio = "⚠️ Non sono riuscito a installare: " + ", ".join(falliti or libs)
    if installati:
        messaggio += f"\n(Installate comunque: {', '.join(installati)})"
    return False, messaggio, riassunto


def _comando_avvio(info):
    avvio = (info.get("avvio") or "").strip()
    if avvio:
        return avvio
    py = [f for f in info.get("files", []) if f.endswith(".py")]
    return f"python {py[0]}" if py else ""


def avvia_progetto(info):
    """Avvia il programma generato in modo persistente (da chiamare dopo conferma)."""
    import subprocess
    cartella = info.get("cartella")
    avvio = _comando_avvio(info)
    if not cartella or not os.path.isdir(cartella):
        return False, "Cartella del progetto non trovata."
    if not avvio:
        return False, "Non so come avviarlo (nessun comando di avvio)."
    try:
        subprocess.Popen(avvio, shell=True, cwd=cartella)
        return True, f"▶️ Avviato: {avvio}\n(nella cartella {cartella})"
    except Exception as e:
        return False, f"Avvio non riuscito: {e}"


def esegui_con_diagnostica(info, timeout=18):
    """Esegue il programma catturando l'output. Restituisce (stato, testo):
      - "ok"      : terminato senza errori (testo = output)
      - "running" : non è terminato entro il timeout (probabile bot/server che gira)
      - "errore"  : è andato in errore (testo = traceback/stderr)
    """
    import subprocess
    cartella = info.get("cartella")
    avvio = _comando_avvio(info)
    if not cartella or not avvio:
        return "errore", "Impossibile avviare il progetto."
    try:
        c = subprocess.run(avvio, shell=True, cwd=cartella, capture_output=True,
                           text=True, timeout=timeout, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return "running", ""
    except Exception as e:
        return "errore", str(e)
    if c.returncode == 0:
        return "ok", (c.stdout or "").strip()
    return "errore", ((c.stderr or "") + "\n" + (c.stdout or "")).strip()


SISTEMA_CORREGGI = (
    "Sei un ingegnere Python SENIOR. Ti do un progetto e l'ERRORE (traceback) che "
    "produce quando viene eseguito. Trova e CORREGGI il bug. Restituisci TUTTI i file "
    "corretti e COMPLETI (non solo le differenze) nel formato ESATTO, senza testo fuori:\n"
    "=== FILE: nomefile ===\n<contenuto corretto>\n"
    "=== AVVIO: comando ===\n=== NOTE: cosa hai corretto ===\n"
)


def correggi_errore(info, traceback_testo, cfg, log=None):
    """Corregge il codice del progetto in base al traceback. (ok, messaggio, info)."""
    log = log or (lambda s: None)
    provider = agent_llm.provider_predefinito(cfg)
    if not provider:
        return False, "Serve un cervello attivo per correggere.", info
    cartella = info.get("cartella")
    if not cartella or not os.path.isdir(cartella):
        return False, "Progetto non trovato.", info
    correnti = _leggi_progetto(cartella)
    blocco = "\n\n".join(f"=== FILE: {rel} ===\n{c}" for rel, c in correnti)
    log("Leggo l'errore e correggo il codice…")
    try:
        risposta = agent_llm.chiedi(
            cfg, provider, SISTEMA_CORREGGI,
            f"PROGETTO:\n{blocco}\n\nERRORE PRODOTTO:\n{traceback_testo[-1500:]}",
            max_token=3800)
    except Exception as e:
        return False, f"Correzione non riuscita: {e}", info
    files, avvio, note = _parse(risposta)
    if not files:
        return False, "Non sono riuscito a correggere il codice.", info
    for rel, contenuto in files:
        dest = os.path.join(cartella, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(contenuto)
    nuovo = dict(info)
    nuovo["files"] = [r for r, _ in files]
    if avvio:
        nuovo["avvio"] = avvio
    return True, ("🔧 Corretto: " + (note or "sistemato l'errore")), nuovo
