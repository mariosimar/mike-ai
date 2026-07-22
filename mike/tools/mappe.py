"""Ricerca di indirizzi e luoghi sul web (geocoding) via OpenStreetMap/Nominatim.

Trasforma "Colosseo, Roma" o un indirizzo in coordinate (lat/lon) che la mappa
può mostrare con lo zoom. Nessuna chiave richiesta.
"""
import json
import urllib.parse
import urllib.request

URL = "https://nominatim.openstreetmap.org/search"
INTESTAZIONI = {"User-Agent": "MikeAI/0.8 (assistente locale tecnico)"}


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
