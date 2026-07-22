"""Auto-aggiornamento del codice di Mike, in modo SICURO.

Come funziona:
  1. Mike legge la versione locale (version.json).
  2. Controlla la sorgente di aggiornamento (una cartella o un link) cercando un
     file 'manifesto.json' con la nuova versione e l'elenco dei file aggiornati.
  3. Se la versione remota è più recente:
       - fa un BACKUP dei file che verranno sostituiti (in dati/backup_...),
       - scarica/copia i nuovi file,
       - VERIFICA che i file Python siano validi (compilabili),
       - se la verifica fallisce, RIPRISTINA tutto dal backup (rollback).
  4. Chiede di riavviare Mike per usare la nuova versione.

Mike NON esegue codice nuovo da solo: si limita a sostituire i file e poi tu
riavvii. Niente auto-esecuzione incontrollata.

La sorgente si imposta in config.json -> "aggiornamento_sorgente":
  - cartella/USB/rete:  "D:\\MikeMaster\\manifesto.json"
  - link internet:      "https://.../manifesto.json"
"""
import hashlib
import json
import os
import shutil
import time
import urllib.request

from .. import config as cfg_mod

RADICE = cfg_mod.RADICE
PERCORSO_VERSIONE = os.path.join(RADICE, "version.json")
CARTELLA_BACKUP = os.path.join(RADICE, "dati", "backup")


# ---------- versioni ----------

def versione_locale():
    try:
        with open(PERCORSO_VERSIONE, "r", encoding="utf-8") as f:
            return json.load(f).get("versione", "0.0.0")
    except Exception:
        return "0.0.0"


def _tupla(v):
    """Trasforma '1.2.10' in (1,2,10) per confrontare le versioni."""
    parti = []
    for p in str(v).split("."):
        try:
            parti.append(int(p))
        except ValueError:
            parti.append(0)
    return tuple(parti)


def piu_recente(remota, locale):
    return _tupla(remota) > _tupla(locale)


# ---------- lettura sorgente (cartella o URL) ----------

def _e_url(sorgente):
    return str(sorgente).lower().startswith(("http://", "https://"))


def _leggi_testo(percorso_o_url, timeout=30):
    """Legge un file (da disco o da internet) come testo."""
    if _e_url(percorso_o_url):
        with urllib.request.urlopen(percorso_o_url, timeout=timeout) as r:
            return r.read().decode("utf-8")
    with open(percorso_o_url, "r", encoding="utf-8") as f:
        return f.read()


def _leggi_bytes(percorso_o_url, timeout=60):
    """Legge un file (da disco o da internet) come byte."""
    if _e_url(percorso_o_url):
        with urllib.request.urlopen(percorso_o_url, timeout=timeout) as r:
            return r.read()
    with open(percorso_o_url, "rb") as f:
        return f.read()


def _base_di(sorgente):
    """Restituisce il 'prefisso' da cui risolvere i file del manifesto."""
    if _e_url(sorgente):
        return sorgente.rsplit("/", 1)[0] + "/"
    return os.path.dirname(sorgente)


def _unisci(base, relativo):
    if _e_url(base):
        return base + relativo.replace("\\", "/")
    return os.path.join(base, relativo.replace("/", os.sep))


# ---------- controllo ----------

def controlla(cfg):
    """Verifica se c'è un aggiornamento. Restituisce un dizionario informativo."""
    sorgente = (cfg.get("aggiornamento_sorgente") or "").strip()
    locale = versione_locale()
    if not sorgente:
        return {"ok": False, "motivo": "nessuna_sorgente", "locale": locale,
                "messaggio": ("Nessuna sorgente di aggiornamento impostata.\n"
                              "Apri config.json e metti in \"aggiornamento_sorgente\" il percorso del "
                              "manifesto (una cartella/USB o un link), es. "
                              "\"D:\\\\MikeMaster\\\\manifesto.json\".")}
    try:
        manifesto = json.loads(_leggi_testo(sorgente))
    except Exception as e:
        return {"ok": False, "motivo": "sorgente_irraggiungibile", "locale": locale,
                "messaggio": f"Non riesco a leggere la sorgente di aggiornamento: {e}"}

    remota = manifesto.get("versione", "0.0.0")
    if not piu_recente(remota, locale):
        return {"ok": False, "motivo": "gia_aggiornato", "locale": locale, "remota": remota,
                "messaggio": f"Mike è già aggiornato (versione {locale})."}

    return {"ok": True, "locale": locale, "remota": remota,
            "note": manifesto.get("note", ""),
            "file": manifesto.get("file", []),
            "sorgente": sorgente, "manifesto": manifesto,
            "messaggio": (f"Aggiornamento disponibile: {locale} → {remota}\n"
                          f"Novità: {manifesto.get('note', '(nessuna nota)')}\n"
                          f"File da aggiornare: {len(manifesto.get('file', []))}")}


# ---------- applicazione (con backup e rollback) ----------

def applica(cfg, log=None):
    """Applica l'aggiornamento in modo sicuro. Restituisce (ok, messaggio)."""
    log = log or (lambda s: None)
    info = controlla(cfg)
    if not info["ok"]:
        return False, info["messaggio"]

    sorgente = info["sorgente"]
    base = _base_di(sorgente)
    file_da_agg = info["file"]
    if not file_da_agg:
        return False, "Il manifesto non elenca nessun file da aggiornare."

    # 1) Backup dei file esistenti che verranno toccati
    stamp = time.strftime("%Y%m%d_%H%M%S")
    cartella_bk = os.path.join(CARTELLA_BACKUP, f"v{info['locale']}_{stamp}")
    os.makedirs(cartella_bk, exist_ok=True)
    log("Faccio il backup della versione attuale…")
    backup_fatti = []
    for rel in file_da_agg + ["version.json"]:
        sorg = os.path.join(RADICE, rel.replace("/", os.sep))
        if os.path.exists(sorg):
            dest = os.path.join(cartella_bk, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(sorg, dest)
            backup_fatti.append(rel)

    # 2) Scarica/copia i nuovi file in un'area di staging, VERIFICANDO l'impronta
    log("Scarico i nuovi file…")
    impronte = info["manifesto"].get("hash", {})
    staging = os.path.join(CARTELLA_BACKUP, f"staging_{stamp}")
    os.makedirs(staging, exist_ok=True)
    try:
        for rel in file_da_agg:
            contenuto = _leggi_bytes(_unisci(base, rel))
            # Controllo di sicurezza: l'impronta del file scaricato deve combaciare
            atteso = impronte.get(rel)
            if atteso:
                calcolato = hashlib.sha256(contenuto).hexdigest()
                if calcolato != atteso:
                    shutil.rmtree(staging, ignore_errors=True)
                    return False, (f"⛔ AGGIORNAMENTO RIFIUTATO: il file «{rel}» è stato "
                                   "alterato durante il download (impronta non corrispondente).\n"
                                   "Non ho toccato niente. Possibile file corrotto o manomesso.")
            dest = os.path.join(staging, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(contenuto)
        # aggiorna anche version.json dal manifesto
        with open(os.path.join(staging, "version.json"), "w", encoding="utf-8") as f:
            json.dump({"versione": info["remota"], "data": stamp[:8],
                       "note": info["note"]}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        shutil.rmtree(staging, ignore_errors=True)
        return False, f"Download non riuscito, non ho toccato niente: {e}"

    # 3) Applica i file dallo staging alla cartella vera
    log("Applico l'aggiornamento…")
    applicati = []
    nuovi = []  # file che prima non esistevano (da rimuovere in caso di rollback)
    try:
        for rel in file_da_agg + ["version.json"]:
            sorg = os.path.join(staging, rel.replace("/", os.sep))
            if not os.path.exists(sorg):
                continue
            dest = os.path.join(RADICE, rel.replace("/", os.sep))
            if not os.path.exists(dest):
                nuovi.append(rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(sorg, dest)
            applicati.append(rel)
    except Exception as e:
        _rollback(cartella_bk, backup_fatti, nuovi)
        shutil.rmtree(staging, ignore_errors=True)
        return False, f"Errore durante l'applicazione: RIPRISTINATA la versione precedente. ({e})"

    # 4) Verifica che i file Python siano validi (compilabili)
    log("Verifico che il nuovo codice sia valido…")
    errore_compilazione = _verifica_python(applicati)
    if errore_compilazione:
        _rollback(cartella_bk, backup_fatti, nuovi)
        shutil.rmtree(staging, ignore_errors=True)
        return False, ("Il nuovo codice non è valido (errore di sintassi): "
                       f"RIPRISTINATA la versione precedente.\n{errore_compilazione}")

    shutil.rmtree(staging, ignore_errors=True)
    return True, (f"✅ Aggiornato alla versione {info['remota']}!\n"
                  f"File aggiornati: {len(applicati)}. Backup in: {cartella_bk}\n"
                  "🔄 Chiudi e riapri Mike per usare la nuova versione.")


def _verifica_python(file_relativi):
    """Compila i file .py aggiornati. Restituisce None se ok, o il messaggio d'errore."""
    import py_compile
    for rel in file_relativi:
        if rel.endswith(".py"):
            percorso = os.path.join(RADICE, rel.replace("/", os.sep))
            try:
                py_compile.compile(percorso, doraise=True)
            except py_compile.PyCompileError as e:
                return f"{rel}: {e}"
    return None


def _rollback(cartella_bk, file_esistenti, file_nuovi):
    """Ripristina i file dal backup e rimuove quelli appena creati."""
    for rel in file_esistenti:
        sorg = os.path.join(cartella_bk, rel.replace("/", os.sep))
        if os.path.exists(sorg):
            dest = os.path.join(RADICE, rel.replace("/", os.sep))
            try:
                shutil.copy2(sorg, dest)
            except Exception:
                pass
    for rel in file_nuovi:
        dest = os.path.join(RADICE, rel.replace("/", os.sep))
        try:
            if os.path.exists(dest):
                os.remove(dest)
        except Exception:
            pass
