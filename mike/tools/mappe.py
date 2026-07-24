"""Ricerca di indirizzi e luoghi sul web (geocoding) via OpenStreetMap/Nominatim.

Trasforma "Colosseo, Roma" o un indirizzo in coordinate (lat/lon) che la mappa
può mostrare con lo zoom. Nessuna chiave richiesta.
"""
import json
import urllib.parse
import urllib.request

URL = "https://nominatim.openstreetmap.org/search"
INTESTAZIONI = {"User-Agent": "MikeAI/0.8 (assistente locale tecnico)"}


def posizione_ip(timeout=10):
    """Posizione APPROSSIMATA dell'utente in base all'indirizzo IP (città/regione/paese).
    Restituisce un dizionario o None. Non è GPS: è la zona della connessione internet."""
    url = ("http://ip-api.com/json/?lang=it&fields=status,country,regionName,city,"
           "lat,lon,isp,query")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8"))
        if d.get("status") != "success":
            return None
        return {
            "citta": d.get("city", ""),
            "regione": d.get("regionName", ""),
            "paese": d.get("country", ""),
            "lat": d.get("lat"),
            "lon": d.get("lon"),
            "provider": d.get("isp", ""),
            "ip": d.get("query", ""),
        }
    except Exception:
        return None


def geocodifica(query, limite=5, timeout=15):
    """Restituisce una lista di luoghi: [{'nome','lat','lon'}]. Lista vuota se nulla."""
    if not query:
        return []
    params = urllib.parse.urlencode({"q": query, "format": "json", "limit": limite,
                                     "addressdetails": 0})
    richiesta = urllib.request.Request(f"{URL}?{params}", headers=INTESTAZIONI)
    try:
        with urllib.request.urlopen(richiesta, timeout=timeout) as r:
            dati = json.loads(r.read().decode("utf-8"))
    except Exception:
        return []
    risultati = []
    for d in dati:
        try:
            risultati.append({
                "nome": d.get("display_name", ""),
                "lat": float(d["lat"]),
                "lon": float(d["lon"]),
            })
        except (KeyError, ValueError):
            continue
    return risultati
