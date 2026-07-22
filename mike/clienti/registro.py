"""Registro clienti e loro PC, con lo storico degli interventi.

Per un tecnico: tieni una scheda per ogni cliente/PC (dati, note, cosa hai fatto e
quando, problemi ricorrenti). Salvato in dati/clienti.json.
"""
import json
import os
import time

from .. import config as cfg_mod

PERCORSO = os.path.join(cfg_mod.RADICE, "dati", "clienti.json")


def _carica():
    if not os.path.exists(PERCORSO):
        return []
    try:
        with open(PERCORSO, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _salva(dati):
    os.makedirs(os.path.dirname(PERCORSO), exist_ok=True)
    with open(PERCORSO, "w", encoding="utf-8") as f:
        json.dump(dati, f, ensure_ascii=False, indent=2)


def trova(nome):
    nome = (nome or "").lower().strip()
    for c in _carica():
        if c.get("nome", "").lower() == nome:
            return c
    # ricerca parziale
    for c in _carica():
        if nome and nome in c.get("nome", "").lower():
            return c
    return None


def aggiungi_o_prendi(nome, note="", pc=""):
    """Crea la scheda cliente se non esiste, o la restituisce."""
    dati = _carica()
    esistente = next((c for c in dati if c.get("nome", "").lower() == nome.lower()), None)
    if esistente:
        if note:
            esistente["note"] = note
        if pc:
            esistente["pc"] = pc
        _salva(dati)
        return esistente
    nuovo = {"nome": nome, "note": note, "pc": pc,
             "creato": time.strftime("%Y-%m-%d"), "interventi": []}
    dati.append(nuovo)
    _salva(dati)
    return nuovo


def registra_intervento(nome, descrizione):
    """Aggiunge un intervento alla scheda del cliente (crea la scheda se manca)."""
    dati = _carica()
    cliente = next((c for c in dati if c.get("nome", "").lower() == nome.lower()), None)
    if not cliente:
        cliente = {"nome": nome, "note": "", "pc": "",
                   "creato": time.strftime("%Y-%m-%d"), "interventi": []}
        dati.append(cliente)
    cliente.setdefault("interventi", []).append(
        {"quando": time.strftime("%Y-%m-%d %H:%M"), "cosa": descrizione})
    _salva(dati)
    return len(cliente["interventi"])


def elenca():
    return [(c["nome"], len(c.get("interventi", [])), c.get("pc", "")) for c in _carica()]


def scheda(nome):
    c = trova(nome)
    if not c:
        return None
    righe = [f"👤 CLIENTE: {c['nome']}"]
    if c.get("pc"):
        righe.append(f"PC: {c['pc']}")
    if c.get("note"):
        righe.append(f"Note: {c['note']}")
    righe.append(f"Cliente dal: {c.get('creato', '?')}")
    interventi = c.get("interventi", [])
    righe.append(f"\nInterventi ({len(interventi)}):")
    for i in interventi[-15:]:
        righe.append(f"  • {i['quando']} — {i['cosa']}")
    if not interventi:
        righe.append("  (nessun intervento registrato)")
    return "\n".join(righe)
