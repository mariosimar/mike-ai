"""Base di conoscenza di Mike.

Gli dai un file o un manuale (txt, md, log, csv, pdf, docx) e Mike lo "studia":
ne salva il contenuto a pezzetti e, quando fai una domanda, richiama i pezzi più
pertinenti per risponderti su quel materiale.

Semplice e locale: nessun database, solo un indice JSON in dati/conoscenza.
"""
import json
import os
import re

from .. import config as cfg_mod

CARTELLA = os.path.join(cfg_mod.RADICE, "dati", "conoscenza")
INDICE = os.path.join(CARTELLA, "indice.json")
MAX_CHUNK = 900


def _carica():
    if not os.path.exists(INDICE):
        return []
    try:
        with open(INDICE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _salva(dati):
    os.makedirs(CARTELLA, exist_ok=True)
    with open(INDICE, "w", encoding="utf-8") as f:
        json.dump(dati, f, ensure_ascii=False)


def _testo_da_file(percorso):
    """Estrae il testo da un file. Restituisce (testo, errore)."""
    ext = os.path.splitext(percorso)[1].lower()
    if ext in (".txt", ".md", ".log", ".csv", ".json", ".ini", ".py", ".xml", ".html"):
        try:
            with open(percorso, encoding="utf-8", errors="replace") as f:
                return f.read(), None
        except Exception as e:
            return None, str(e)
    if ext == ".pdf":
        try:
            import pypdf
        except ImportError:
            try:
                from ..costruttore import builder
                builder._pip(["install", "pypdf"])
                import pypdf
            except Exception:
                return None, "Per i PDF serve la libreria 'pypdf' (non sono riuscito a installarla)."
        try:
            lettore = pypdf.PdfReader(percorso)
            return "\n".join((p.extract_text() or "") for p in lettore.pages), None
        except Exception as e:
            return None, f"PDF non leggibile: {e}"
    if ext == ".docx":
        try:
            import docx
        except ImportError:
            try:
                from ..costruttore import builder
                builder._pip(["install", "python-docx"])
                import docx
            except Exception:
                return None, "Per i .docx serve la libreria 'python-docx'."
        try:
            d = docx.Document(percorso)
            return "\n".join(p.text for p in d.paragraphs), None
        except Exception as e:
            return None, f"Docx non leggibile: {e}"
    return None, f"Tipo di file non supportato: {ext}"


def _spezza(testo):
    pezzi, corrente = [], ""
    for para in re.split(r"\n\s*\n", testo):
        para = para.strip()
        if not para:
            continue
        if len(corrente) + len(para) < MAX_CHUNK:
            corrente += ("\n" + para) if corrente else para
        else:
            if corrente:
                pezzi.append(corrente)
            corrente = para[:MAX_CHUNK]
    if corrente:
        pezzi.append(corrente)
    return pezzi


def impara(percorso):
    """Studia un file. Restituisce (numero_pezzi, errore)."""
    percorso = percorso.strip().strip('"')
    if not os.path.isfile(percorso):
        return 0, f"File non trovato: {percorso}"
    testo, err = _testo_da_file(percorso)
    if err:
        return 0, err
    if not (testo or "").strip():
        return 0, "Il file sembra vuoto o senza testo estraibile."
    fonte = os.path.basename(percorso)
    dati = [d for d in _carica() if d.get("fonte") != fonte]  # rimpiazza se già presente
    for pezzo in _spezza(testo):
        dati.append({"fonte": fonte, "testo": pezzo})
    _salva(dati)
    return sum(1 for d in dati if d["fonte"] == fonte), None


def cerca(query, k=3):
    """Restituisce i pezzi più pertinenti alla domanda (per il prompt)."""
    dati = _carica()
    if not dati:
        return ""
    parole = set(w for w in re.findall(r"[a-zà-ÿ0-9]+", query.lower()) if len(w) > 2)
    if not parole:
        return ""
    valutati = []
    for d in dati:
        blob = d["testo"].lower()
        score = sum(1 for w in parole if w in blob)
        if score:
            valutati.append((score, d))
    valutati.sort(key=lambda x: x[0], reverse=True)
    scelti = valutati[:k]
    if not scelti:
        return ""
    return "\n\n".join(f"[dal manuale «{d['fonte']}»]\n{d['testo']}" for _s, d in scelti)


def elenca():
    dati = _carica()
    fonti = {}
    for d in dati:
        fonti[d["fonte"]] = fonti.get(d["fonte"], 0) + 1
    return fonti


def dimentica():
    _salva([])
