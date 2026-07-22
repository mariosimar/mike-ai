"""Recupero dell'accesso a Windows in modo LEGALE (reset, non cracking).

- analizza_account(): legge gli account e la situazione (sola lettura).
- guida_recupero(): genera la guida giusta in base al tipo di account.
- reset_password(): su un PC acceso, azzera la password di un account LOCALE
  (richiede diritti di amministratore). Non serve conoscere la vecchia password.

NB: per gli account Microsoft il reset si fa SOLO online (account.microsoft.com),
non localmente. BitLocker/EFS: resettare la password senza la chiave puo' rendere
i dati illeggibili — Mike avvisa sempre prima.
"""
import json
import os
import subprocess

CARTELLA = os.path.dirname(os.path.abspath(__file__))
SCRIPT_ACCOUNT = os.path.join(CARTELLA, "account.ps1")

URL_RESET_MICROSOFT = "https://account.live.com/password/reset"


def analizza_account(timeout=60):
    """Esegue account.ps1 (sola lettura) e restituisce (report_dict, errore)."""
    if not os.path.exists(SCRIPT_ACCOUNT):
        return None, f"Script non trovato: {SCRIPT_ACCOUNT}"
    comando = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
               "-File", SCRIPT_ACCOUNT]
    try:
        c = subprocess.run(comando, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return None, "PowerShell non trovato (sei su Windows?)."
    except subprocess.TimeoutExpired:
        return None, "Analisi troppo lunga, interrotta."
    uscita = (c.stdout or "").strip()
    if not uscita:
        return None, f"Nessun output. Errore: {c.stderr.strip()}"
    try:
        return json.loads(uscita), None
    except json.JSONDecodeError as e:
        return None, f"Report account non leggibile: {e}"


def riassunto_account(report):
    """Testo leggibile della situazione account."""
    if not report:
        return "(Nessun dato.)"
    r = [f"Sei amministratore adesso: {'SÌ' if report.get('amministratore') else 'NO'}"]
    r.append(f"Account 'Administrator' integrato: {'ATTIVO' if report.get('administrator_integrato_abilitato') else 'disattivato'}")
    if report.get("bitlocker_leggibile"):
        attivi = [b for b in report.get("bitlocker", []) if "On" in b.get("protezione", "")]
        if attivi:
            unita = ", ".join(b["unita"] for b in attivi)
            r.append(f"⚠️ BitLocker ATTIVO su: {unita} — serve la chiave di ripristino prima di resettare!")
        else:
            r.append("BitLocker: non attivo.")
    else:
        r.append("BitLocker: stato non leggibile (lancia come amministratore per saperlo).")

    r.append("\nAccount trovati:")
    for a in report.get("account", []):
        flag = []
        if a.get("amministratore"):
            flag.append("admin")
        if not a.get("abilitato"):
            flag.append("disabilitato")
        etichetta = f" [{', '.join(flag)}]" if flag else ""
        r.append(f"  • {a['nome']} — tipo: {a['tipo']}{etichetta} (ultimo accesso: {a['ultimo_accesso']})")
    return "\n".join(r)


def guida_recupero(report):
    """Genera la guida di recupero giusta in base agli account presenti."""
    if not report:
        return "(Nessun dato per generare la guida.)"

    account = report.get("account", [])
    attivi = [a for a in account if a.get("abilitato")]
    ha_microsoft = any(a.get("tipo") == "MicrosoftAccount" for a in attivi)
    ha_locale = any(a.get("tipo") == "Local" for a in attivi)
    sono_admin = report.get("amministratore")

    g = ["📋 GUIDA AL RECUPERO ACCESSO\n"]

    # Avviso BitLocker
    if report.get("bitlocker_leggibile"):
        if any("On" in b.get("protezione", "") for b in report.get("bitlocker", [])):
            g.append("⚠️ ATTENZIONE: BitLocker è ATTIVO. Prima di qualsiasi reset, procurati la "
                     "CHIAVE DI RIPRISTINO BitLocker (su https://account.microsoft.com/devices "
                     "del cliente). Senza, i dati possono diventare illeggibili.\n")

    # Caso account Microsoft
    if ha_microsoft:
        g.append("🔵 C'è un ACCOUNT MICROSOFT (online). Questo NON si resetta sul PC:")
        g.append(f"   1. Da un altro dispositivo vai su: {URL_RESET_MICROSOFT}")
        g.append("   2. Il cliente reimposta la password (serve accesso alla sua email/telefono di recupero).")
        g.append("   3. Poi accede al PC con la nuova password (serve internet la prima volta).")
        g.append("   → Se il cliente non ha più accesso all'email di recupero, può creare un account")
        g.append("     LOCALE di emergenza (vedi sotto) per salvare i dati.\n")

    # Caso account locale
    if ha_locale or not ha_microsoft:
        g.append("🟢 ACCOUNT LOCALE — due situazioni:")
        g.append("   A) PC ACCESO e tu sei amministratore"
                 + (" (✅ è il tuo caso ora):" if sono_admin else " (ora NON lo sei):"))
        g.append("      → Comando Mike:  /reset-password <nomeutente> <nuovapassword>")
        g.append("      → Oppure manuale (da Prompt come admin):  net user <nomeutente> <nuovapassword>")
        g.append("   B) PC BLOCCATO (non si entra):")
        g.append("      → Avvia il PC da una chiavetta di installazione/ripristino di Windows,")
        g.append("        apri il Prompt dei comandi del ripristino e reimposta la password del-")
        g.append("        l'account locale. Mike ti dà i passi esatti con:  /guida-bloccato\n")

    g.append("ℹ️ Nota legale: fai questo solo su PC del cliente, con il suo consenso. "
             "Il reset cambia la password: i file cifrati con EFS o protetti da BitLocker "
             "richiedono la rispettiva chiave, altrimenti restano illeggibili.")
    return "\n".join(g)


GUIDA_BLOCCATO = """🔧 RECUPERO SU PC BLOCCATO (account LOCALE) — solo con consenso del cliente

PREMESSA: se c'è BitLocker, procurati prima la chiave di ripristino
(https://account.microsoft.com/devices), altrimenti il disco resta cifrato.

Se l'account è MICROSOFT: NON usare questo metodo, reimposta online su
https://account.live.com/password/reset

PASSI (account locale, con supporto di installazione Windows su USB/DVD):
 1. Avvia il PC dalla chiavetta di Windows (tasto Boot Menu: di solito F12/F9/Esc).
 2. Alla schermata di installazione premi MAIUSC+F10 per aprire il Prompt dei comandi.
 3. Trova la lettera del disco di Windows (di solito C: o D:):  dir C:\\Windows
 4. Reimposta la password dell'account locale con lo strumento di gestione utenti
    del sistema riavviato in modalità provvisoria, OPPURE abilita l'account
    Administrator integrato e poi cambia la password dell'utente da lì.
 5. Riavvia, rimuovi la USB, accedi e imposta una nuova password.

Suggerimento pratico più sicuro e supportato da Microsoft quando possibile:
 • Se esiste un disco di reimpostazione password creato in precedenza, usalo.
 • Per i PC aziendali (account AzureAD/dominio), il reset si fa dall'amministratore
   del dominio / portale, NON localmente.

Mike può prepararti il report completo del PC e la checklist da consegnare al cliente.
"""


def _is_admin():
    """True se il processo Python corrente ha i diritti di amministratore."""
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def reset_password(nome_utente, nuova_password):
    """Su un PC ACCESO, azzera la password di un account LOCALE.

    Restituisce (successo: bool, messaggio: str). Richiede diritti di admin.
    Non serve la vecchia password. Funziona solo per account locali.
    """
    if not nome_utente or not nuova_password:
        return False, "Servono nome utente e nuova password: /reset-password <utente> <password>"

    if not _is_admin():
        return False, ("Per resettare la password servono i diritti di amministratore.\n"
                       "Chiudi Mike e riavvialo con tasto destro → «Esegui come amministratore», "
                       "poi riprova. (Hai già la password admin di questo PC perché lo stai riparando.)")

    # Verifica che l'account esista e sia LOCALE (non Microsoft)
    report, errore = analizza_account()
    if report:
        trovato = next((a for a in report.get("account", []) if a["nome"].lower() == nome_utente.lower()), None)
        if trovato and trovato.get("tipo") == "MicrosoftAccount":
            return False, (f"«{nome_utente}» è un ACCOUNT MICROSOFT: non si resetta sul PC.\n"
                           f"Reimposta la password online su {URL_RESET_MICROSOFT}")
        if not trovato:
            disponibili = ", ".join(a["nome"] for a in report.get("account", []))
            return False, f"Account «{nome_utente}» non trovato. Account presenti: {disponibili}"

    # Esegue il reset con il comando di sistema 'net user' (non mostra la password nei log)
    try:
        c = subprocess.run(["net", "user", nome_utente, nuova_password],
                           capture_output=True, text=True, timeout=30,
                           encoding="utf-8", errors="replace")
    except Exception as e:
        return False, f"Errore durante il reset: {e}"

    if c.returncode == 0:
        return True, (f"✅ Password di «{nome_utente}» reimpostata.\n"
                      "Il cliente può accedere subito con la nuova password.\n"
                      "⚠️ Se aveva file cifrati con EFS, potrebbero non aprirsi più (è normale dopo un reset).")
    return False, f"Reset non riuscito: {c.stdout.strip()} {c.stderr.strip()}"
