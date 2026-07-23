"""Caricamento della configurazione di Mike (chiavi API, modelli, opzioni)."""
import json
import os

# Cartella radice del progetto (la cartella "Mike AI")
RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERCORSO_CONFIG = os.path.join(RADICE, "config.json")
PERCORSO_ESEMPIO = os.path.join(RADICE, "config.example.json")

# Valori predefiniti: usati se manca config.json o se manca una voce.
PREDEFINITI = {
    "claude_api_key": "",
    "gemini_api_key": "",
    "modello_claude": "claude-sonnet-4-6",
    "modello_gemini": "gemini-2.0-flash",
    "modello_ollama": "hermes3:8b",
    "provider_principale": "ollama",
    "provider_riserva": "gemini",
    "nome_assistente": "Mike",
    "lingua": "italiano",
    "abilita_ricerca_web": True,
    "abilita_memoria": True,
    "aggiornamento_sorgente": "",
    "aggiornamento_auto": True,
    "modalita_agente": True,    # si attiva SOLO con Claude (veloce); sul locale resta diretta
    "modalita_esperto": False,
}


def carica():
    """Restituisce un dizionario con la configurazione completa.

    Cerca prima in config.json. Le chiavi API possono anche essere messe
    in variabili d'ambiente (CLAUDE_API_KEY / GEMINI_API_KEY), utili se non
    vuoi salvarle in un file.
    """
    cfg = dict(PREDEFINITI)

    if os.path.exists(PERCORSO_CONFIG):
        try:
            with open(PERCORSO_CONFIG, "r", encoding="utf-8") as f:
                dati = json.load(f)
            for chiave, valore in dati.items():
                if not chiave.startswith("_"):  # ignora le note tipo "_nota"
                    cfg[chiave] = valore
        except (json.JSONDecodeError, OSError) as e:
            print(f"[config] Attenzione: impossibile leggere config.json ({e}). Uso i valori predefiniti.")

    # Le variabili d'ambiente hanno la precedenza, se presenti.
    cfg["claude_api_key"] = os.environ.get("CLAUDE_API_KEY") or cfg["claude_api_key"]
    cfg["gemini_api_key"] = os.environ.get("GEMINI_API_KEY") or cfg["gemini_api_key"]

    return cfg


def chiave_valida(valore):
    """True se la chiave sembra reale (non vuota e non il segnaposto)."""
    return bool(valore) and "INCOLLA" not in valore.upper()
