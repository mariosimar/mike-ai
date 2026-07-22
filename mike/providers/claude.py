"""Connettore per l'API di Claude (Anthropic).

Usa solo la libreria standard di Python (urllib): nessuna installazione extra.
"""
import json
import urllib.request
import urllib.error

URL = "https://api.anthropic.com/v1/messages"


class ErroreProvider(Exception):
    """Errore parlante da mostrare all'utente."""


def chiedi(chiave_api, modello, messaggi, system="", max_token=1024, timeout=60):
    """Invia la conversazione a Claude e restituisce il testo della risposta.

    messaggi: lista di {"ruolo": "utente"/"assistente", "testo": "..."}
    """
    if not chiave_api:
        raise ErroreProvider("Manca la chiave API di Claude.")

    # Converte i nostri messaggi nel formato dell'API Anthropic.
    convertiti = []
    for m in messaggi:
        ruolo = "user" if m["ruolo"] == "utente" else "assistant"
        convertiti.append({"role": ruolo, "content": m["testo"]})

    corpo = {
        "model": modello,
        "max_tokens": max_token,
        "messages": convertiti,
    }
    if system:
        corpo["system"] = system

    dati = json.dumps(corpo).encode("utf-8")
    richiesta = urllib.request.Request(
        URL,
        data=dati,
        headers={
            "x-api-key": chiave_api,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(richiesta, timeout=timeout) as risposta:
            risultato = json.loads(risposta.read().decode("utf-8"))
        # La risposta è in risultato["content"][0]["text"]
        parti = risultato.get("content", [])
        testo = "".join(p.get("text", "") for p in parti if p.get("type") == "text")
        return testo.strip() or "(Claude ha risposto vuoto)"
    except urllib.error.HTTPError as e:
        dettaglio = e.read().decode("utf-8", errors="replace")
        raise ErroreProvider(f"Claude ha rifiutato la richiesta (codice {e.code}): {dettaglio}")
    except urllib.error.URLError as e:
        raise ErroreProvider(f"Impossibile contattare Claude (connessione?): {e.reason}")
