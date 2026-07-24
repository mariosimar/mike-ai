"""Ricerca sul web senza bisogno di chiavi API.

Usa DuckDuckGo (versione HTML leggera) e la libreria standard di Python.
Restituisce alcuni risultati (titolo + breve descrizione) che Mike può
leggere prima di rispondere, così le risposte sono aggiornate da internet.
"""
import gzip
import html
import re
import urllib.parse
import urllib.request
import zlib

URL = "https://html.duckduckgo.com/html/"
INTESTAZIONI = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MikeAI/0.1"}
INTESTAZIONI_WEB = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
}


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


def leggi_pagina(url, timeout=10, max_caratteri=4000):
    """Scarica una pagina web ed estrae il testo leggibile principale senza tag HTML.

    Limita il testo a max_caratteri (~4000) e gestisce errori/timeout senza bloccarsi.
    """
    if not url or not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return f"(URL non valido o mancante: {url})"

    richiesta = urllib.request.Request(url, headers=INTESTAZIONI_WEB)
    try:
        with urllib.request.urlopen(richiesta, timeout=timeout) as risposta:
            content_type = risposta.headers.get("Content-Type", "")
            if content_type and not any(t in content_type.lower() for t in ("text", "html", "xml", "json")):
                return f"(Tipo di contenuto non supportato per la lettura: {content_type})"

            raw_bytes = risposta.read()
            content_encoding = risposta.headers.get("Content-Encoding", "").lower()
            try:
                if "gzip" in content_encoding:
                    raw_bytes = gzip.decompress(raw_bytes)
                elif "deflate" in content_encoding:
                    raw_bytes = zlib.decompress(raw_bytes)
            except Exception:
                pass

            charset = "utf-8"
            if "charset=" in content_type.lower():
                try:
                    charset = content_type.lower().split("charset=")[-1].split(";")[0].strip()
                except Exception:
                    charset = "utf-8"

            try:
                html_testo = raw_bytes.decode(charset, errors="replace")
            except Exception:
                html_testo = raw_bytes.decode("utf-8", errors="replace")
    except Exception as e:
        return f"(Impossibile scaricare la pagina {url}: {e})"

    try:
        # Rimuovi script, stili, nav, header, footer, noscript, svg
        pulito = re.sub(
            r"<(script|style|noscript|svg|iframe|header|footer|nav)[^>]*>.*?</\1>",
            " ",
            html_testo,
            flags=re.DOTALL | re.IGNORECASE,
        )
        # Rimuovi tutti i tag HTML rimanenti
        pulito = re.sub(r"<[^>]+>", " ", pulito)
        # Decodifica entità HTML (&amp;, &nbsp;, ecc.)
        pulito = html.unescape(pulito)
        # Pulisci righe vuote e spazi vuoti multipli
        righe = [riga.strip() for riga in pulito.splitlines() if riga.strip()]
        testo_estratto = "\n".join(righe)

        if len(testo_estratto) > max_caratteri:
            testo_estratto = testo_estratto[:max_caratteri] + "\n... [testo troncato]"

        return testo_estratto if testo_estratto else "(Nessun testo estratto dalla pagina)"
    except Exception as e:
        return f"(Errore nell'estrazione del testo da {url}: {e})"


def ricerca_approfondita(query, numero=3, timeout_pagina=10):
    """Cerca su internet, prende i primi N risultati, scarica e legge le loro pagine,
    e restituisce il testo unito con le fonti (URL).
    """
    try:
        risultati = cerca(query, numero=numero)
    except Exception as e:
        return f"(Ricerca web fallita per «{query}»: {e})"

    if not risultati:
        return f"(Nessun risultato trovato sul web per «{query}».)"

    blocchi = [f"=== RICERCA APPROFONDITA SUL WEB PER: {query} ===\n"]
    for i, r in enumerate(risultati, 1):
        url = r.get("url", "")
        titolo = r.get("titolo", f"Risultato {i}")
        snippet = r.get("testo", "")

        blocchi.append(f"--- Fonte {i}: {titolo} ---")
        blocchi.append(f"URL: {url}")
        if snippet:
            blocchi.append(f"Snippet: {snippet}")

        if url:
            contenuto = leggi_pagina(url, timeout=timeout_pagina)
            blocchi.append("Contenuto pagina:\n" + contenuto)
        else:
            blocchi.append("(URL non disponibile)")
        blocchi.append("\n" + "=" * 40 + "\n")

    return "\n".join(blocchi)

