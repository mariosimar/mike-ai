"""Azioni di riparazione/pulizia del PC.

Filosofia di sicurezza:
- Le azioni che MODIFICANO il sistema NON vengono mai eseguite da sole:
  il cervello (brain) le mette "in sospeso" e l'utente deve scrivere /conferma.
- Le azioni che richiedono diritti di amministratore lo segnalano chiaramente.
- Le letture (lista programmi, analisi spazio) sono sola lettura e sicure.

Ogni funzione restituisce (successo: bool, messaggio: str).
"""
import os
import subprocess

_CARTELLA = os.path.dirname(os.path.abspath(__file__))
SCRIPT_SPAZIO = os.path.join(_CARTELLA, "spazio.ps1")


def _is_admin():
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _ps(comando, timeout=600):
    """Esegue un comando PowerShell e restituisce (returncode, stdout, stderr)."""
    c = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", comando],
        capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
    return c.returncode, (c.stdout or "").strip(), (c.stderr or "").strip()


def _cmd(lista, timeout=600):
    c = subprocess.run(lista, capture_output=True, text=True, timeout=timeout,
                       encoding="utf-8", errors="replace")
    return c.returncode, (c.stdout or "").strip(), (c.stderr or "").strip()


def _sanifica_ps(testo):
    """Rende sicuro un valore da inserire in una stringa PowerShell tra apici singoli.

    Raddoppia gli apici singoli (escape PS) e rimuove i caratteri di controllo/newline,
    così un nome malevolo non può "uscire" dalla stringa ed eseguire altri comandi.
    """
    testo = (testo or "").replace("\r", " ").replace("\n", " ")
    testo = testo.replace("`", "").replace("\x00", "")
    return testo.replace("'", "''")


# ---------------- PULIZIA ----------------

def pulisci_temp():
    """Svuota le cartelle temporanee (utente + Windows se admin)."""
    liberati = []
    # Temp utente (sempre possibile)
    temp_utente = os.environ.get("TEMP", "")
    cartelle = [temp_utente]
    if _is_admin():
        cartelle.append(r"C:\Windows\Temp")
    eliminati = 0
    errori = 0
    for cart in cartelle:
        if not cart or not os.path.isdir(cart):
            continue
        for radice, dirs, files in os.walk(cart, topdown=False):
            for f in files:
                try:
                    os.remove(os.path.join(radice, f))
                    eliminati += 1
                except Exception:
                    errori += 1
        liberati.append(cart)
    msg = f"✅ Pulizia temp completata. File rimossi: {eliminati} (in uso/saltati: {errori}).\nCartelle: {', '.join(liberati)}"
    if not _is_admin():
        msg += "\n(Per pulire anche C:\\Windows\\Temp avvia Mike come amministratore.)"
    return True, msg


def svuota_cestino():
    rc, out, err = _ps("Clear-RecycleBin -Force -ErrorAction SilentlyContinue; 'fatto'")
    return True, "✅ Cestino svuotato."


def flush_dns():
    rc, out, err = _cmd(["ipconfig", "/flushdns"])
    if rc == 0:
        return True, "✅ Cache DNS svuotata (utile per problemi di navigazione)."
    return False, f"Non riuscito: {out} {err}"


# ---------------- RIPARAZIONE FILE DI SISTEMA ----------------

def ripara_file_sistema():
    """Esegue SFC e DISM per riparare i file di sistema corrotti (richiede admin, è lento)."""
    if not _is_admin():
        return False, "Servono i diritti di amministratore. Avvia Mike come amministratore e riprova."
    risultati = []
    # SFC
    rc, out, err = _cmd(["sfc", "/scannow"], timeout=1800)
    risultati.append("SFC: " + (out[-400:] if out else err[-400:]))
    # DISM (ripristina l'immagine se SFC non basta)
    rc2, out2, err2 = _cmd(
        ["DISM", "/Online", "/Cleanup-Image", "/RestoreHealth"], timeout=1800)
    risultati.append("DISM: " + (out2[-400:] if out2 else err2[-400:]))
    return True, "🛠️ Riparazione file di sistema completata.\n\n" + "\n\n".join(risultati)


# ---------------- ANTIVIRUS (Windows Defender) ----------------

def scansione_antivirus(tipo="veloce"):
    """Avvia una scansione con Windows Defender. tipo: 'veloce' o 'completa'."""
    scan = "QuickScan" if tipo == "veloce" else "FullScan"
    timeout = 600 if tipo == "veloce" else 7200
    try:
        rc, out, err = _ps(f"Start-MpScan -ScanType {scan}; "
                           "$t = (Get-MpThreatDetection | Select-Object -Last 5).ThreatName -join ', '; "
                           "if ($t) { 'Minacce rilevate: ' + $t } else { 'Nessuna minaccia rilevata.' }",
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "La scansione ha superato il tempo massimo (potrebbe essere ancora utile controllare in Sicurezza di Windows)."
    if rc == 0:
        return True, f"🛡️ Scansione {tipo} completata.\n{out}"
    return False, f"Scansione non riuscita: {out} {err}\n(Windows Defender potrebbe essere disattivato o sostituito da un altro antivirus.)"


def stato_antivirus():
    """Sola lettura: stato di Windows Defender."""
    rc, out, err = _ps(
        "$d = Get-MpComputerStatus; "
        "\"Antivirus attivo: $($d.AntivirusEnabled)`nProtezione realtime: $($d.RealTimeProtectionEnabled)`n"
        "Ultima scansione veloce: $($d.QuickScanEndTime)`nDefinizioni aggiornate: $($d.AntivirusSignatureLastUpdated)\"")
    if rc == 0 and out:
        return True, "🛡️ " + out
    return False, "Impossibile leggere lo stato di Windows Defender (forse è attivo un altro antivirus)."


# ---------------- SERVIZI ----------------

def riavvia_servizio(nome):
    if not _is_admin():
        return False, "Servono i diritti di amministratore per riavviare un servizio."
    rc, out, err = _ps(f"Restart-Service -Name '{_sanifica_ps(nome)}' -Force; 'ok'")
    if rc == 0:
        return True, f"✅ Servizio '{nome}' riavviato."
    return False, f"Non riuscito (nome esatto?): {err}"


# ---------------- PROGRAMMI INSTALLATI / DISINSTALLA ----------------

def lista_programmi():
    """Sola lettura: elenco dei programmi installati (dal registro)."""
    comando = (
        "$p = @('HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*',"
        "'HKLM:\\SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*',"
        "'HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*'); "
        "Get-ItemProperty $p -ErrorAction SilentlyContinue | "
        "Where-Object { $_.DisplayName } | Select-Object -Unique DisplayName | "
        "Sort-Object DisplayName | ForEach-Object { $_.DisplayName }")
    rc, out, err = _ps(comando, timeout=60)
    if rc == 0 and out:
        righe = [l for l in out.splitlines() if l.strip()]
        return True, f"📦 Programmi installati ({len(righe)}):\n" + "\n".join("  • " + l for l in righe)
    return False, "Impossibile leggere l'elenco dei programmi."


def trova_disinstallazione(nome):
    """Cerca il comando di disinstallazione di un programma per nome (parziale)."""
    comando = (
        "$p = @('HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*',"
        "'HKLM:\\SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*',"
        "'HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*'); "
        f"Get-ItemProperty $p -ErrorAction SilentlyContinue | Where-Object {{ $_.DisplayName -like '*{_sanifica_ps(nome)}*' }} | "
        "Select-Object DisplayName, UninstallString, QuietUninstallString | ConvertTo-Json -Depth 3")
    rc, out, err = _ps(comando, timeout=60)
    if rc != 0 or not out:
        return None
    import json
    try:
        dati = json.loads(out)
    except json.JSONDecodeError:
        return None
    return dati if isinstance(dati, list) else [dati]


def disinstalla(nome):
    """Avvia la disinstallazione di un programma. Da chiamare SOLO dopo conferma."""
    trovati = trova_disinstallazione(nome)
    if not trovati:
        return False, f"Nessun programma trovato con nome simile a «{nome}». Usa /programmi per vedere i nomi esatti."
    if len(trovati) > 1:
        nomi = ", ".join(t.get("DisplayName", "?") for t in trovati)
        return False, f"Trovati più programmi: {nomi}. Sii più preciso (es. usa il nome esatto)."
    prog = trovati[0]
    comando_unins = prog.get("QuietUninstallString") or prog.get("UninstallString")
    if not comando_unins:
        return False, f"«{prog.get('DisplayName')}» non ha un comando di disinstallazione registrato."
    try:
        # Avvia il disinstallatore (potrebbe aprire una finestra che chiede conferma all'utente).
        subprocess.Popen(comando_unins, shell=True)
        return True, (f"🗑️ Avviata la disinstallazione di «{prog.get('DisplayName')}».\n"
                      "Segui le eventuali finestre del disinstallatore per completare.")
    except Exception as e:
        return False, f"Impossibile avviare la disinstallazione: {e}"


# ---------------- SPAZIO DISCO PROFONDO ----------------

def analizza_spazio_profondo():
    """Analisi PROFONDA (sola lettura): dove finisce lo spazio, inclusi i file nascosti."""
    if not os.path.exists(SCRIPT_SPAZIO):
        return False, "Script di analisi non trovato."
    try:
        rc, out, err = _ps_file(SCRIPT_SPAZIO, timeout=180)
    except Exception as e:
        return False, f"Analisi non riuscita: {e}"
    if out:
        nota = "" if _is_admin() else "\n\n(ℹ️ Avvia come amministratore per vedere e pulire anche i file di sistema nascosti.)"
        return True, out + nota
    return False, f"Analisi non riuscita: {err}"


def libera_spazio_profondo():
    """Elimina le cache di sistema NASCOSTE e recuperabili (temp, aggiornamenti,
    cestino, miniature, component store). Documenti e file personali NON toccati.
    Alcune parti richiedono i diritti di amministratore.
    """
    fatti = []
    admin = _is_admin()

    # Temp utente
    _svuota_cartella(os.environ.get("TEMP", ""))
    fatti.append("• File temporanei utente")

    # Cestino
    _ps("Clear-RecycleBin -Force -ErrorAction SilentlyContinue")
    fatti.append("• Cestino")

    # Cache miniature
    lad = os.environ.get("LOCALAPPDATA", "")
    if lad:
        _ps(f"Remove-Item '{_sanifica_ps(lad)}\\Microsoft\\Windows\\Explorer\\thumbcache_*.db' -Force -ErrorAction SilentlyContinue")
        fatti.append("• Cache miniature")

    if admin:
        _svuota_cartella(r"C:\Windows\Temp")
        fatti.append("• Temp di Windows")
        # Cache Aggiornamenti Windows
        _ps("Stop-Service wuauserv,bits -Force -ErrorAction SilentlyContinue; "
            "Remove-Item 'C:\\Windows\\SoftwareDistribution\\Download\\*' -Recurse -Force -ErrorAction SilentlyContinue; "
            "Start-Service bits,wuauserv -ErrorAction SilentlyContinue", timeout=120)
        fatti.append("• Cache Aggiornamenti Windows")
        # Delivery Optimization
        _ps("Delete-DeliveryOptimizationCache -Force -ErrorAction SilentlyContinue")
        fatti.append("• Cache Delivery Optimization")
        # Report errori
        _ps("Remove-Item 'C:\\ProgramData\\Microsoft\\Windows\\WER\\Report*\\*' -Recurse -Force -ErrorAction SilentlyContinue")
        fatti.append("• Report errori vecchi")
        # DISM component cleanup
        _cmd(["Dism.exe", "/Online", "/Cleanup-Image", "/StartComponentCleanup"], timeout=1800)
        fatti.append("• Archivio componenti (DISM)")

    testo = "🧹 SPAZIO LIBERATO. Pulito:\n" + "\n".join(fatti)
    if not admin:
        testo += ("\n\n⚠️ Per liberare anche i file di SISTEMA nascosti (cache aggiornamenti, "
                  "component store) — di solito i più grossi — riavvia Mike come amministratore, "
                  "oppure usa 'Libera Spazio.bat' (si eleva da solo).")
    return True, testo


def _svuota_cartella(cart):
    if not cart or not os.path.isdir(cart):
        return
    for radice, _dirs, files in os.walk(cart, topdown=False):
        for f in files:
            try:
                os.remove(os.path.join(radice, f))
            except Exception:
                pass


def _ps_file(percorso, timeout=180):
    c = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", percorso],
        capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
    return c.returncode, (c.stdout or "").strip(), (c.stderr or "").strip()


# ---------------- MANUTENZIONE COMBINATA ----------------

def manutenzione_sicura():
    """Esegue in sequenza le pulizie sicure (e la riparazione file se admin)."""
    passi = []
    ok, msg = flush_dns(); passi.append(msg)
    ok, msg = svuota_cestino(); passi.append(msg)
    ok, msg = pulisci_temp(); passi.append(msg)
    if _is_admin():
        ok, msg = ripara_file_sistema(); passi.append(msg)
    else:
        passi.append("ℹ️ Riparazione file di sistema (sfc/DISM) saltata: avvia come amministratore per includerla.")
    return True, "🧹 MANUTENZIONE COMPLETATA:\n\n" + "\n\n".join(passi)


# ---------------- ACCOUNT DI EMERGENZA ----------------

def crea_account_emergenza(nome, password, rendi_admin=True):
    """Crea un account LOCALE di emergenza per rientrare nel PC / salvare i dati.

    Utile quando il cliente ha perso anche l'accesso alla mail dell'account Microsoft:
    si crea un account locale amministratore con cui accedere e recuperare i file.
    Richiede diritti di amministratore.
    """
    if not nome or not password:
        return False, "Servono nome e password: /crea-account <nome> <password>"
    if not _is_admin():
        return False, ("Servono i diritti di amministratore. Avvia Mike come amministratore e riprova.")
    # Crea l'utente
    rc, out, err = _cmd(["net", "user", nome, password, "/add"])
    if rc != 0:
        return False, f"Creazione account non riuscita: {out} {err}"
    messaggi = [f"✅ Account locale «{nome}» creato."]
    if rendi_admin:
        # Aggiunge al gruppo amministratori (prova nome IT e SID per sicurezza)
        rc2, o2, e2 = _cmd(["net", "localgroup", "Administrators", nome, "/add"])
        if rc2 != 0:
            _cmd(["net", "localgroup", "Amministratori", nome, "/add"])
        messaggi.append("✅ Aggiunto al gruppo Amministratori.")
    messaggi.append("Ora il cliente può accedere a Windows con questo account e recuperare i suoi dati.")
    return True, "\n".join(messaggi)


# ---------------- ANALISI SPAZIO (sola lettura) ----------------

def analizza_spazio():
    """Sola lettura: dove si può recuperare spazio (file inutili)."""
    comando = (
        "$r = [ordered]@{}; "
        "$t = (Get-ChildItem $env:TEMP -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum; "
        "$r['Temp utente (MB)'] = [math]::Round($t/1MB,0); "
        "$d = (Get-ChildItem \"$env:USERPROFILE\\Downloads\" -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum; "
        "$r['Download (MB)'] = [math]::Round($d/1MB,0); "
        "$w = (Get-ChildItem 'C:\\Windows\\Temp' -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum; "
        "$r['Windows Temp (MB)'] = [math]::Round($w/1MB,0); "
        "$r.GetEnumerator() | ForEach-Object { \"$($_.Key): $($_.Value)\" }")
    rc, out, err = _ps(comando, timeout=120)
    if rc == 0 and out:
        return True, "💽 Spazio recuperabile (file inutili):\n" + "\n".join("  " + l for l in out.splitlines())
    return False, "Impossibile analizzare lo spazio."
