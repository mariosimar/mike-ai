"""Esegue scan.ps1 (PowerShell, sola lettura) e restituisce il report come dict.

Lo script raccoglie solo informazioni: non modifica nulla sul sistema.
Per una diagnosi profonda va lanciato come amministratore, ma funziona anche senza.
"""
import json
import os
import subprocess

CARTELLA = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(CARTELLA, "scan.ps1")


def esegui_scansione(timeout=120):
    """Lancia la scansione e restituisce (report_dict, errore_str).

    Se tutto va bene errore_str è None. In caso di problema, report_dict è None.
    """
    if not os.path.exists(SCRIPT):
        return None, f"Script non trovato: {SCRIPT}"

    comando = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", SCRIPT,
    ]
    try:
        completato = subprocess.run(
            comando, capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
    except FileNotFoundError:
        return None, "PowerShell non trovato (sei su Windows?)."
    except subprocess.TimeoutExpired:
        return None, "La scansione ha impiegato troppo tempo ed è stata interrotta."

    uscita = (completato.stdout or "").strip()
    if not uscita:
        return None, f"La scansione non ha prodotto output. Errore: {completato.stderr.strip()}"

    try:
        report = json.loads(uscita)
    except json.JSONDecodeError as e:
        return None, f"Report non leggibile (JSON non valido): {e}"
    return report, None


def riassunto_testo(report):
    """Trasforma il report in un testo leggibile (e adatto da dare a un agente AI)."""
    if not report:
        return "(Nessun report disponibile.)"
    r = []
    sis = report.get("sistema", {})
    r.append(f"PC: {sis.get('nome_pc')} — {sis.get('produttore')} {sis.get('modello')}")
    r.append(f"Sistema: {sis.get('os')} (build {sis.get('build')}, {sis.get('architettura')})")
    r.append(f"Acceso da: {sis.get('uptime_ore')} ore — Amministratore: {report.get('amministratore')}")

    mem = report.get("memoria", {})
    if mem:
        r.append(f"RAM: {mem.get('libera_gb')} GB liberi su {mem.get('totale_gb')} GB ({mem.get('uso_percento')}% in uso)")

    for d in report.get("dischi", []):
        r.append(f"Disco {d.get('unita')}: {d.get('libero_gb')} GB liberi su {d.get('totale_gb')} GB ({d.get('libero_percento')}% libero)")

    for s in report.get("salute_dischi", []):
        r.append(f"Salute disco '{s.get('modello')}' ({s.get('tipo')}): {s.get('salute')}")

    rete = report.get("rete", {})
    if rete:
        r.append(f"Internet: {'sì' if rete.get('internet') else 'NO'}")

    if report.get("riavvio_in_sospeso"):
        r.append("Riavvio in sospeso: SÌ")
    if report.get("temp_mb") is not None:
        r.append(f"Cartella temporanea: {report.get('temp_mb')} MB")

    problemi = report.get("problemi_rilevati", [])
    if problemi:
        r.append("\nProblemi rilevati automaticamente:")
        for p in problemi:
            r.append(f"  [{p.get('gravita')}] {p.get('descrizione')}")
    else:
        r.append("\nNessun problema evidente rilevato dai controlli automatici.")

    r.append(f"\n{report.get('nota_admin', '')}")
    return "\n".join(r)
