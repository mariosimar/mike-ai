"""Controllo rapido dello stato di salute del PC, con soglie di allarme.

Legge RAM e disco (veloce, senza subprocess) e segnala i problemi.
"""
import os
import shutil

from ..diagnostica import live

SOGLIE = {
    "ram": 90.0,        # % RAM usata oltre cui allarme
    "disco": 90.0,      # % disco usato oltre cui allarme
    "disco_gb_liberi": 10.0,  # GB liberi sotto cui allarme
}


def controlla(soglie=None):
    """Restituisce (testo_stato, lista_allarmi)."""
    s = dict(SOGLIE)
    if soglie:
        s.update(soglie)

    ram = live.ram_percento()
    disco = live.disco_percento()
    try:
        u = shutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\")
        gb_liberi = u.free / (1024 ** 3)
    except Exception:
        gb_liberi = 0.0

    allarmi = []
    if ram >= s["ram"]:
        allarmi.append(f"RAM quasi piena: {ram:.0f}% usata")
    if disco >= s["disco"]:
        allarmi.append(f"Disco quasi pieno: {disco:.0f}% usato")
    if gb_liberi and gb_liberi < s["disco_gb_liberi"]:
        allarmi.append(f"Poco spazio: solo {gb_liberi:.0f} GB liberi")

    testo = f"RAM {ram:.0f}% usata · Disco {disco:.0f}% usato ({gb_liberi:.0f} GB liberi)"
    return testo, allarmi
