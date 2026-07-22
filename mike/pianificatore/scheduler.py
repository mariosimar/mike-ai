"""Crea/elenca/rimuove attività automatiche usando schtasks di Windows.

Le attività di Mike hanno il prefisso 'Mike_' così si riconoscono e non si mischiano
con quelle di sistema. Non serve amministratore per le attività dell'utente.
"""
import re
import subprocess

PREFISSO = "Mike_"


def _safe(nome):
    return re.sub(r"[^A-Za-z0-9_]+", "_", nome).strip("_") or "attivita"


def _run(args, timeout=30):
    try:
        c = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return c.returncode == 0, ((c.stdout or "") + (c.stderr or "")).strip()
    except Exception as e:
        return False, str(e)


def crea(nome, comando, frequenza="giornaliera", ora="09:00", giorno=None):
    """Crea un'attività pianificata. frequenza: giornaliera|settimanale|oraria.
    Restituisce (ok, messaggio)."""
    if not nome or not comando:
        return False, "Servono un nome e un comando da eseguire."
    tn = PREFISSO + _safe(nome)
    args = ["schtasks", "/Create", "/TN", tn, "/TR", comando, "/F"]
    f = frequenza.lower()
    if f.startswith("orari"):
        args += ["/SC", "HOURLY"]
    elif f.startswith("settiman"):
        args += ["/SC", "WEEKLY", "/ST", ora]
        if giorno:
            args += ["/D", giorno.upper()[:3]]  # MON, TUE, …
    else:
        args += ["/SC", "DAILY", "/ST", ora]
    ok, out = _run(args)
    if ok:
        quando = {"orari": "ogni ora", "settiman": f"ogni settimana alle {ora}"}.get(
            f[:7], f"ogni giorno alle {ora}")
        return True, f"✅ Attività «{nome}» pianificata ({quando}).\nEseguirà: {comando}"
    return False, f"Non riuscita: {out[:250]}"


def elenca():
    """Elenca le attività create da Mike. Restituisce lista di (nome, prossima_esecuzione)."""
    ok, out = _run(["schtasks", "/Query", "/FO", "CSV", "/NH"])
    if not ok:
        return []
    voci = []
    for riga in out.splitlines():
        campi = [c.strip('"') for c in riga.split('","')]
        if not campi:
            continue
        tn = campi[0].strip('"').lstrip("\\")
        if tn.startswith(PREFISSO):
            prossima = campi[1] if len(campi) > 1 else ""
            voci.append((tn[len(PREFISSO):], prossima))
    # deduplica mantenendo l'ordine
    viste, uniche = set(), []
    for n, p in voci:
        if n not in viste:
            viste.add(n)
            uniche.append((n, p))
    return uniche


def rimuovi(nome):
    ok, out = _run(["schtasks", "/Delete", "/TN", PREFISSO + _safe(nome), "/F"])
    return (True, f"🗑️ Attività «{nome}» rimossa.") if ok else (False, f"Non riuscita: {out[:200]}")
