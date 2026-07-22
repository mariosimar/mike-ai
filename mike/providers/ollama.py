"""Connettore per Ollama: modelli AI che girano IN LOCALE sul tuo PC.

Nessuna chiave API, nessun costo, funziona anche senza internet.
Ollama espone un server su http://localhost:11434.
Usa solo la libreria standard di Python (urllib).
"""
import json
import urllib.request
import urllib.error

BASE = "http://localhost:11434"


class ErroreProvider(Exception):
    pass


def disponibile(timeout=3):
    """True se il server Ollama è attivo e raggiungibile."""
    try:
        with urllib.request.urlopen(f"{BASE}/api/tags", timeout=timeout):
            return True
    except Exception:
        return False


def modelli(timeout=5):
    """Elenco dei modelli locali installati."""
    try:
        with urllib.request.urlopen(f"{BASE}/api/tags", timeout=timeout) as r:
            dati = json.loads(r.read().decode("utf-8"))
        return [m["name"] for m in dati.get("models", [])]
    except Exception:
        return []


def _converti(messaggi, system):
    convertiti = []
    if system:
        convertiti.append({"role": "system", "content": system})
    for m in messaggi:
        ruolo = "user" if m["ruolo"] == "utente" else "assistant"
        convertiti.append({"role": ruolo, "content": m["testo"]})
    return convertiti


def chiedi(modello, messaggi, system="", max_token=1024, timeout=300, keep_alive="30m"):
    """Invia la conversazione al modello locale e restituisce il testo.

    messaggi: lista di {"ruolo": "utente"/"assistente", "testo": "..."}
    keep_alive: per quanto tempo il modello resta in RAM (velocizza le chiamate successive).
    """
    corpo = {
        "model": modello,
        "messages": _converti(messaggi, system),
        "stream": False,
        "keep_alive": keep_alive,
        "options": {"num_predict": max_token},
    }
    dati = json.dumps(corpo).encode("utf-8")
    richiesta = urllib.request.Request(
        f"{BASE}/api/chat", data=dati,
        headers={"content-type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(richiesta, timeout=timeout) as r:
            risultato = json.loads(r.read().decode("utf-8"))
        testo = risultato.get("message", {}).get("content", "")
        return testo.strip() or "(Il modello locale ha risposto vuoto)"
    except urllib.error.HTTPError as e:
        dettaglio = e.read().decode("utf-8", errors="replace")
        raise ErroreProvider(f"Ollama errore {e.code}: {dettaglio}")
    except urllib.error.URLError as e:
        raise ErroreProvider(f"Ollama non raggiungibile (è avviato?): {e.reason}")


def chiedi_stream(modello, messaggi, system="", max_token=1024, su_token=None,
                  timeout=300, keep_alive="30m"):
    """Come chiedi(), ma trasmette la risposta token-per-token.

    Per ogni pezzo di testo generato chiama su_token(frammento), così la GUI può
    mostrarlo in tempo reale (latenza percepita quasi nulla). Restituisce il testo completo.
    """
    corpo = {
        "model": modello,
        "messages": _converti(messaggi, system),
        "stream": True,
        "keep_alive": keep_alive,
        "options": {"num_predict": max_token},
    }
    dati = json.dumps(corpo).encode("utf-8")
    richiesta = urllib.request.Request(
        f"{BASE}/api/chat", data=dati,
        headers={"content-type": "application/json"}, method="POST")
    pezzi = []
    try:
        with urllib.request.urlopen(richiesta, timeout=timeout) as r:
            for linea in r:  # Ollama invia un oggetto JSON per riga
                linea = linea.decode("utf-8", errors="replace").strip()
                if not linea:
                    continue
                try:
                    obj = json.loads(linea)
                except json.JSONDecodeError:
                    continue
                frammento = obj.get("message", {}).get("content", "")
                if frammento:
                    pezzi.append(frammento)
                    if su_token:
                        su_token(frammento)
                if obj.get("done"):
                    break
    except urllib.error.HTTPError as e:
        dettaglio = e.read().decode("utf-8", errors="replace")
        raise ErroreProvider(f"Ollama errore {e.code}: {dettaglio}")
    except urllib.error.URLError as e:
        raise ErroreProvider(f"Ollama non raggiungibile (è avviato?): {e.reason}")
    return "".join(pezzi).strip() or "(Il modello locale ha risposto vuoto)"


def precarica(modello, timeout=120):
    """Carica il modello in RAM in anticipo (warm-up), così la prima risposta è veloce."""
    try:
        chiedi(modello, [{"ruolo": "utente", "testo": "ok"}], max_token=1, timeout=timeout)
        return True
    except Exception:
        return False
