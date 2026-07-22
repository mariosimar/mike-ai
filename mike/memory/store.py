"""Memoria persistente di Mike, salvata in dati/memoria.json.

Contiene:
- "fatti": cose che hai insegnato a Mike o che ha imparato (lista di stringhe).
- "diario": annotazioni di auto-miglioramento (cosa è andato bene/male).

Le conversazioni complete vengono salvate a parte in dati/conversazioni.log.
Questo è il modo *sicuro* in cui Mike "impara": accumula memoria, non riscrive
il proprio codice da solo.
"""
import json
import os
import time

RADICE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CARTELLA_DATI = os.path.join(RADICE, "dati")
PERCORSO_MEMORIA = os.path.join(CARTELLA_DATI, "memoria.json")
PERCORSO_LOG = os.path.join(CARTELLA_DATI, "conversazioni.log")

VUOTA = {"fatti": [], "diario": [], "auto_istruzioni": [], "profilo": {"nome": "", "note": []}}


def _assicura_cartella():
    os.makedirs(CARTELLA_DATI, exist_ok=True)


def carica():
    _assicura_cartella()
    if not os.path.exists(PERCORSO_MEMORIA):
        return {"fatti": [], "diario": [], "auto_istruzioni": [], "profilo": {"nome": "", "note": []}}
    try:
        with open(PERCORSO_MEMORIA, "r", encoding="utf-8") as f:
            dati = json.load(f)
        dati.setdefault("fatti", [])
        dati.setdefault("diario", [])
        dati.setdefault("auto_istruzioni", [])
        dati.setdefault("profilo", {"nome": "", "note": []})
        return dati
    except (json.JSONDecodeError, OSError):
        return {"fatti": [], "diario": [], "auto_istruzioni": [], "profilo": {"nome": "", "note": []}}


# ---------- profilo dell'utente (così Mike ti conosce) ----------

def imposta_nome(nome):
    m = carica()
    m["profilo"]["nome"] = nome.strip()
    salva(m)


def aggiungi_nota_profilo(nota):
    m = carica()
    nota = nota.strip()
    if nota and nota not in m["profilo"]["note"]:
        m["profilo"]["note"].append(nota)
        m["profilo"]["note"] = m["profilo"]["note"][-30:]
        salva(m)


def profilo_come_testo():
    m = carica()
    p = m.get("profilo", {})
    if not p.get("nome") and not p.get("note"):
        return ""
    righe = ["Chi è l'utente con cui stai parlando (ricordalo e trattalo di conseguenza):"]
    if p.get("nome"):
        righe.append(f"- Si chiama {p['nome']}.")
    for n in p.get("note", []):
        righe.append(f"- {n}")
    return "\n".join(righe)


def salva(memoria):
    _assicura_cartella()
    with open(PERCORSO_MEMORIA, "w", encoding="utf-8") as f:
        json.dump(memoria, f, ensure_ascii=False, indent=2)


def aggiungi_fatto(testo):
    """Insegna un fatto permanente a Mike."""
    memoria = carica()
    testo = testo.strip()
    if testo and testo not in memoria["fatti"]:
        memoria["fatti"].append(testo)
        salva(memoria)
    return memoria["fatti"]


def aggiungi_diario(nota):
    """Annota nel diario di apprendimento."""
    memoria = carica()
    memoria["diario"].append({"quando": time.strftime("%Y-%m-%d %H:%M:%S"), "nota": nota})
    salva(memoria)


def imposta_auto_istruzioni(lista):
    """Sostituisce le auto-istruzioni che Mike ha imparato su sé stesso."""
    memoria = carica()
    memoria["auto_istruzioni"] = [str(x).strip() for x in lista if str(x).strip()]
    salva(memoria)
    return memoria["auto_istruzioni"]


def auto_istruzioni_come_testo():
    """Restituisce le auto-istruzioni apprese, pronte per il prompt di sistema."""
    memoria = carica()
    voci = memoria.get("auto_istruzioni", [])
    if not voci:
        return ""
    righe = ["Lezioni che hai imparato su come lavorare meglio (applicale):"]
    for v in voci:
        righe.append(f"- {v}")
    return "\n".join(righe)


def leggi_conversazioni(ultimi_caratteri=6000):
    """Legge la coda del log conversazioni (per l'auto-miglioramento)."""
    if not os.path.exists(PERCORSO_LOG):
        return ""
    try:
        with open(PERCORSO_LOG, "r", encoding="utf-8") as f:
            testo = f.read()
        return testo[-ultimi_caratteri:]
    except OSError:
        return ""


def fatti_come_testo():
    """Restituisce i fatti imparati pronti da inserire nel prompt di sistema."""
    memoria = carica()
    if not memoria["fatti"]:
        return ""
    righe = ["Cose che l'utente ti ha insegnato e devi ricordare:"]
    for f in memoria["fatti"]:
        righe.append(f"- {f}")
    return "\n".join(righe)


def registra_conversazione(domanda, risposta, provider):
    """Salva un turno di conversazione nel log (per storico e miglioramento)."""
    _assicura_cartella()
    with open(PERCORSO_LOG, "a", encoding="utf-8") as f:
        f.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} [{provider}] ---\n")
        f.write(f"TU: {domanda}\n")
        f.write(f"MIKE: {risposta}\n\n")
