"""Funzioni di basso livello per parlare con un modello (Claude o Gemini),
usate dagli agenti. Una singola domanda -> una risposta (senza cronologia).
"""
import json
import re

from .. import config as cfg_mod
from ..providers import claude, gemini, ollama


def provider_disponibile(cfg, nome):
    """True se quel provider è utilizzabile adesso."""
    if nome == "ollama":
        return ollama.disponibile()
    if nome == "claude":
        return cfg_mod.chiave_valida(cfg.get("claude_api_key", ""))
    if nome == "gemini":
        return cfg_mod.chiave_valida(cfg.get("gemini_api_key", ""))
    return False


def provider_predefinito(cfg):
    """Sceglie il provider: il principale se disponibile, altrimenti la riserva,
    altrimenti il primo disponibile in assoluto."""
    princ = cfg.get("provider_principale", "ollama")
    ris = cfg.get("provider_riserva", "gemini")
    for nome in (princ, ris, "ollama", "claude", "gemini"):
        if provider_disponibile(cfg, nome):
            return nome
    return None


def chiedi(cfg, provider, system, prompt, max_token=1500, modello_override=None):
    """Una domanda singola al provider indicato. Restituisce il testo."""
    messaggi = [{"ruolo": "utente", "testo": prompt}]
    if provider == "ollama":
        modello = modello_override or cfg.get("modello_ollama", "qwen2.5:3b")
        return ollama.chiedi(modello, messaggi, system=system, max_token=max_token)
    elif provider == "claude":
        modello = modello_override or cfg.get("modello_claude", "claude-sonnet-4-6")
        return claude.chiedi(cfg["claude_api_key"], modello,
                             messaggi, system=system, max_token=max_token)
    elif provider == "gemini":
        modello = modello_override or cfg.get("modello_gemini", "gemini-2.0-flash")
        return gemini.chiedi(cfg["gemini_api_key"], modello,
                             messaggi, system=system, max_token=max_token)
    raise ValueError(f"Provider sconosciuto: {provider}")


def estrai_json(testo):
    """Estrae il primo oggetto/array JSON da un testo, anche se avvolto in ```json.

    Restituisce l'oggetto Python, oppure None se non trova JSON valido.
    """
    if not testo:
        return None
    # Toglie eventuali recinti di codice markdown
    pulito = re.sub(r"```(?:json)?", "", testo).strip()
    # Cerca dal primo [ o { fino all'ultimo ] o }
    for apri, chiudi in (("[", "]"), ("{", "}")):
        inizio = pulito.find(apri)
        fine = pulito.rfind(chiudi)
        if inizio != -1 and fine != -1 and fine > inizio:
            frammento = pulito[inizio:fine + 1]
            try:
                return json.loads(frammento)
            except json.JSONDecodeError:
                continue
    return None
