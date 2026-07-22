"""Ricerca sul web senza bisogno di chiavi API.

Usa DuckDuckGo (versione HTML leggera) e la libreria standard di Python.
Restituisce alcuni risultati (titolo + breve descrizione) che Mike può
leggere prima di rispondere, così le risposte sono aggiornate da internet.
"""
import html
import re
import urllib.parse
import urllib.request

URL = "https://html.duckduckgo.com/html/"
INTESTAZIONI = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MikeAI/0.1"}


def _pulisci(testo):
    """Rimuove i tag HTML e decodifica le entità (&amp; ecc.)."""
    senza_tag = re.sub(r"<[^>]+>", "", testo)
    return html.unescape(senza_tag).strip()


def cerca(query, numero=5, timeout=20):
    """Cerca su internet e restituisce una lista di dizionari:
    {"titolo": ..., "testo": ..., "url": ...}
    """
    dati = urllib.parse.urlencode({"q": query}).encode("utf-8")
    richiesta = urllib.request.Request(URL, data=dati, headers=INTESTAZIONI, method="POST")
    with urllib.request.urlopen(richiesta, timeout=timeout) as risposta:
        pagina = risposta.read().decode("utf-8", errors="replace")

    risultati = []
    # Ogni risultato ha un link con classe "result__a" e uno snippet "result__snippet".
    blocchi = re.findall(
        r'result__a[^>]*href="(.*?)".*?>(.*?)</a>.*?result__snippet[^>]*>(.*?)</a>',
        pagina,
        re.DOTALL,
    )
    for url_grezzo, titolo, snippet in blocchi[:numero]:
        # DuckDuckGo a volte avvolge l'URL in un redirect: estrai quello vero.
        m = re.search(r"uddg=([^&]+)", url_grezzo)
        url_vero = urllib.parse.unquote(m.group(1)) if m else url_grezzo
        risultati.append({
            "titolo": _pulisci(titolo),
            "testo": _pulisci(snippet),
            "url": url_vero,
        })
    return risultati


def cerca_come_testo(query, numero=5):
    """Come cerca(), ma restituisce un unico testo pronto da dare al modello."""
    try:
        risultati = cerca(query, numero=numero)
    except Exception as e:
        return f"(Ricerca web fallita: {e})"
    if not risultati:
        return "(Nessun risultato dalla ricerca web.)"
    righe = [f"Risultati di ricerca per: {query}\n"]
    for i, r in enumerate(risultati, 1):
        righe.append(f"{i}. {r['titolo']}\n   {r['testo']}\n   Fonte: {r['url']}")
    return "\n".join(righe)
