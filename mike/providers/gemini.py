"""Connettore per l'API di Gemini (Google).

Usa solo la libreria standard di Python (urllib): nessuna installazione extra.
"""
import json
import urllib.request
import urllib.error

URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models/{modello}:generateContent?key={chiave}"


class ErroreProvider(Exception):
    """Errore parlante da mostrare all'utente."""


def chiedi(chiave_api, modello, messaggi, system="", max_token=1024, timeout=60):
    """Invia la conversazione a Gemini e restituisce il testo della risposta."""
    if not chiave_api:
        raise ErroreProvider("Manca la chiave API di Gemini.")

    # Converte i messaggi nel formato di Gemini.
    contenuti = []
    for m in messaggi:
        ruolo = "user" if m["ruolo"] == "utente" else "model"
        contenuti.append({"role": ruolo, "parts": [{"text": m["testo"]}]})

    corpo = {
        "contents": contenuti,
        "generationConfig": {"maxOutputTokens": max_token},
    }
    if system:
        corpo["systemInstruction"] = {"parts": [{"text": system}]}

    url = URL_BASE.format(modello=modello, chiave=chiave_api)
    dati = json.dumps(corpo).encode("utf-8")
    richiesta = urllib.request.Request(
        url,
        data=dati,
        headers={"content-type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(richiesta, timeout=timeout) as risposta:
            risultato = json.loads(risposta.read().decode("utf-8"))
        candidati = risultato.get("candidates", [])
        if not candidati:
            return "(Gemini non ha prodotto una risposta)"
        parti = candidati[0].get("content", {}).get("parts", [])
        testo = "".join(p.get("text", "") for p in parti)
        return testo.strip() or "(Gemini ha risposto vuoto)"
    except urllib.error.HTTPError as e:
        dettaglio = e.read().decode("utf-8", errors="replace")
        raise ErroreProvider(f"Gemini ha rifiutato la richiesta (codice {e.code}): {dettaglio}")
    except urllib.error.URLError as e:
        raise ErroreProvider(f"Impossibile contattare Gemini (connessione?): {e.reason}")


def descrivi_immagine(chiave_api, modello, immagine_b64, prompt, mime="image/jpeg", timeout=60):
    """Manda un'immagine (base64) a Gemini e restituisce la descrizione/opinione."""
    if not chiave_api:
        raise ErroreProvider("Manca la chiave API di Gemini.")
    corpo = {
        "contents": [{
            "role": "user",
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": mime, "data": immagine_b64}},
            ],
        }],
        "generationConfig": {"maxOutputTokens": 800},
    }
    url = URL_BASE.format(modello=modello, chiave=chiave_api)
    dati = json.dumps(corpo).encode("utf-8")
    richiesta = urllib.request.Request(
        url, data=dati, headers={"content-type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(richiesta, timeout=timeout) as risposta:
            risultato = json.loads(risposta.read().decode("utf-8"))
        candidati = risultato.get("candidates", [])
        if not candidati:
            return "(Gemini non ha saputo descrivere l'immagine)"
        parti = candidati[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parti).strip() or "(vuoto)"
    except urllib.error.HTTPError as e:
        dettaglio = e.read().decode("utf-8", errors="replace")
        raise ErroreProvider(f"Gemini errore {e.code}: {dettaglio}")
    except urllib.error.URLError as e:
        raise ErroreProvider(f"Impossibile contattare Gemini: {e.reason}")
