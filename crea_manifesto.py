"""Crea il file 'manifesto.json' per pubblicare un aggiornamento di Mike.

Come usarlo (sul TUO PC, la copia "master" di Mike):
  1. Modifica/migliora Mike come vuoi.
  2. Esegui:   python crea_manifesto.py 0.5.1   (metti la nuova versione)
  3. Copia TUTTA la cartella di Mike (o almeno i file elencati + manifesto.json)
     nella sorgente di aggiornamento: una cartella di rete, una chiavetta, o un
     sito/GitHub.
  4. Sui PC dei clienti, in config.json metti "aggiornamento_sorgente" col percorso
     del manifesto.json, e Mike si aggiornerà da solo (con backup di sicurezza).

Il manifesto elenca tutti i file di Mike (cartella 'mike/' + file principali).
"""
import hashlib
import json
import os
import sys

RADICE = os.path.dirname(os.path.abspath(__file__))

# File principali nella radice da includere nell'aggiornamento
FILE_RADICE = ["avvia.py", "README.md"]


def raccogli_file():
    elenco = []
    # tutti i .py e .ps1 dentro mike/
    for radice, _dirs, files in os.walk(os.path.join(RADICE, "mike")):
        if "__pycache__" in radice:
            continue
        for f in files:
            if f.endswith((".py", ".ps1")):
                completo = os.path.join(radice, f)
                rel = os.path.relpath(completo, RADICE).replace(os.sep, "/")
                elenco.append(rel)
    for f in FILE_RADICE:
        if os.path.exists(os.path.join(RADICE, f)):
            elenco.append(f)
    return sorted(elenco)


def main():
    if len(sys.argv) < 2:
        print("Uso: python crea_manifesto.py <nuova_versione> [note]")
        print("Esempio: python crea_manifesto.py 0.5.1 \"Aggiunto comando X\"")
        return
    versione = sys.argv[1]
    note = sys.argv[2] if len(sys.argv) > 2 else ""

    file_inclusi = raccogli_file()
    # Calcola l'impronta SHA-256 di ogni file (per verificare che non venga alterato).
    impronte = {}
    for rel in file_inclusi:
        with open(os.path.join(RADICE, rel.replace("/", os.sep)), "rb") as fh:
            impronte[rel] = hashlib.sha256(fh.read()).hexdigest()

    manifesto = {"versione": versione, "note": note,
                 "file": file_inclusi, "hash": impronte}
    percorso = os.path.join(RADICE, "manifesto.json")
    with open(percorso, "w", encoding="utf-8") as f:
        json.dump(manifesto, f, ensure_ascii=False, indent=2)

    # aggiorna anche version.json locale
    with open(os.path.join(RADICE, "version.json"), "w", encoding="utf-8") as f:
        json.dump({"versione": versione, "note": note}, f, ensure_ascii=False, indent=2)

    print(f"[OK] Creato manifesto.json (versione {versione}) con {len(manifesto['file'])} file.")
    print("Ora copia la cartella di Mike nella sorgente di aggiornamento.")


if __name__ == "__main__":
    main()
