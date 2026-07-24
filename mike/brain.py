"""Il cervello di Mike: decide quale provider usare, cerca sul web se serve,
ricorda le cose e costruisce le risposte.
"""
import os
from . import config as cfg_mod
from .providers import claude, gemini, ollama
from .tools import web
from .memory import store
from .agents.orchestratore import Orchestratore
from .agents.agente import Agente
from .agents import llm as agent_llm
from .agents.ragionatore import Ragionatore
from .tools import mappe, schermo
from .costruttore import builder
from .pianificatore import scheduler
from .conoscenza import base as conoscenza
from .monitor import watch
from .clienti import registro as clienti
from .diagnostica import scanner, logs, live
from .recupero import recupero
from .riparazione import azioni
from .aggiornamento import updater

# Per velocità: quanti messaggi della conversazione inviare al modello (prompt più
# corto = risposta più veloce) e quanti tenerne in memoria.
MAX_STORIA = 14
MAX_CRONOLOGIA = 40


class Mike:
    def __init__(self):
        self.cfg = cfg_mod.carica()
        # Storico della conversazione corrente (in memoria, per il contesto).
        self.cronologia = []
        # Funzione opzionale per mostrare l'avanzamento (impostata dalla GUI).
        self.progresso = None
        # Azione di riparazione in attesa di conferma (sicurezza).
        self.azione_in_sospeso = None
        # Ultimo progetto software creato (per poterlo modificare).
        self.ultimo_progetto = None

    def _log(self, messaggio):
        if self.progresso:
            try:
                self.progresso(messaggio)
            except Exception:
                pass

    # ---------- stato / diagnostica ----------

    def stato(self):
        """Riepilogo di cosa è pronto e cosa manca (mostrato nella GUI)."""
        righe = []
        o_ok = ollama.disponibile()
        c_ok = cfg_mod.chiave_valida(self.cfg["claude_api_key"])
        g_ok = cfg_mod.chiave_valida(self.cfg["gemini_api_key"])
        if o_ok:
            righe.append(f"🧠 Ollama (locale): ✅ attivo — modello {self.cfg['modello_ollama']}")
        else:
            righe.append("🧠 Ollama (locale): ❌ non avviato (apri l'app Ollama)")
        righe.append(f"Claude: {'✅ pronto' if c_ok else '❌ manca la chiave'}")
        righe.append(f"Gemini: {'✅ pronto' if g_ok else '❌ manca la chiave'}")
        righe.append(f"Ricerca web: {'✅ attiva' if self.cfg['abilita_ricerca_web'] else '⏸ disattivata'}")
        righe.append(f"Memoria: {'✅ attiva' if self.cfg['abilita_memoria'] else '⏸ disattivata'}")
        return "\n".join(righe)

    def pronto(self):
        """True se almeno un provider (locale o con chiave) è utilizzabile."""
        return (ollama.disponibile()
                or cfg_mod.chiave_valida(self.cfg["claude_api_key"])
                or cfg_mod.chiave_valida(self.cfg["gemini_api_key"]))

    # ---------- prompt di sistema ----------

    def _prompt_sistema(self, contesto_web="", contesto_sistema="", query=""):
        nome = self.cfg["nome_assistente"]
        parti = [
            f"Tu sei {nome}, un assistente AI che VIVE ed AGISCE su questo computer Windows.",
            f"Rispondi sempre in {self.cfg['lingua']}, in modo chiaro, amichevole e diretto.",
            "COSA SAI FARE DAVVERO su questo PC (NON dire mai «non posso» o «sono solo un "
            "assistente»): analizzare lo spazio del disco compresi i FILE NASCOSTI di sistema, "
            "liberare memoria, vedere i processi attivi, fare la diagnosi, leggere crash e log, "
            "resettare password di account locali, creare account, creare/riparare programmi, "
            "leggere lo schermo, cercare su internet, trovare indirizzi e mappe. "
            "Se l'utente chiede una di queste cose, conferma che PUOI farlo e digli il comando "
            "(es. «libera spazio», «/diagnosi»). Sei uno strumento che ESEGUE, non solo consiglia.",
        ]
        if query:
            try:
                manuale = conoscenza.cerca(query)
                if manuale:
                    parti.append("Materiale dai manuali che hai studiato (usalo se pertinente "
                                 "e cita il manuale):\n" + manuale)
            except Exception:
                pass
        if self.cfg["abilita_memoria"]:
            profilo = store.profilo_come_testo()
            if profilo:
                parti.append(profilo)
            fatti = store.fatti_come_testo()
            if fatti:
                parti.append(fatti)
            auto = store.auto_istruzioni_come_testo()
            if auto:
                parti.append(auto)
        if contesto_sistema:
            parti.append("STATO REALE DEL PC IN QUESTO MOMENTO (dati veri appena letti dal "
                         "sistema: basati SU QUESTI per rispondere su processi/prestazioni):\n"
                         + contesto_sistema)
        if contesto_web:
            parti.append("Informazioni aggiornate dal web (usale se utili e cita le fonti):\n" + contesto_web)
        return "\n\n".join(parti)

    # ---------- comandi speciali ----------

    def _gestisci_comando(self, testo, su_token=None):
        """Comandi che iniziano con '/'. Restituisce una risposta o None."""
        t = testo.strip()
        if t.lower() in ("/aiuto", "/help"):
            return (
                "🔍 DIAGNOSI E LOG\n"
                "/diagnosi                     → analizza il PC, trova problemi, salva un report\n"
                "/crash                        → analizza crash, BSOD ed errori recenti\n"
                "/leggi <percorso>             → fa leggere e analizzare a Mike un file/log\n"
                "/spazio                       → mostra dove recuperare spazio (file inutili)\n"
                "/processi                     → mostra cosa sta facendo il PC adesso (live)\n"
                "/check-tp                     → verifica le affiliazioni su Travelpayouts\n"
                "\n🌐 RICERCA WEB ED ANALISI\n"
                "/ricerca <domanda>            → ricerca approfondita sul web (legge i siti e cita le fonti)\n"
                "\n🔐 ACCESSO / PASSWORD\n"
                "/account                      → analizza gli account e come recuperare l'accesso\n"
                "/reset-password <ut> <nuova>  → azzera la password di un account LOCALE (serve admin)\n"
                "/guida-bloccato               → guida per PC bloccato (non si entra più)\n"
                "\n🛠️ RIPARAZIONE (chiedono /conferma prima di agire)\n"
                "/ripara                       → menù delle riparazioni\n"
                "/pulisci                      → elimina file temporanei\n"
                "/svuota-cestino               → svuota il cestino\n"
                "/flush-dns                    → svuota la cache DNS (problemi di rete)\n"
                "/ripara-file                  → ripara i file di sistema (sfc + DISM, serve admin)\n"
                "/antivirus [veloce|completa]  → scansione con Windows Defender\n"
                "/programmi                    → elenco programmi installati\n"
                "/disinstalla <nome>           → disinstalla un programma\n"
                "/conferma  |  /annulla        → conferma o annulla l'azione proposta\n"
                "\n📋 DOCUMENTI / ACCOUNT\n"
                "/checklist [cliente]          → crea il modulo di consenso da far firmare (stampabile)\n"
                "/crea-account <nome> <pwd>    → crea un account locale di emergenza (serve admin)\n"
                "\n🧠 INTELLIGENZA / CREAZIONE\n"
                "/crea <cosa>                  → crea un programma/bot completo (scrive il codice)\n"
                "/modifica <cosa cambiare>     → migliora il progetto appena creato\n"
                "/progetti                     → elenco dei progetti creati\n"
                "/riprendi <nome>              → riapre un progetto vecchio (per modificarlo/avviarlo)\n"
                "/template [tipo]              → crea un progetto da un modello pronto\n"
                "/esperto on|off               → esegue le azioni senza chiedere /conferma\n"
                "\n👁️ STRUMENTI AVANZATI\n"
                "/schermo [domanda]            → Mike guarda lo schermo e ti aiuta (legge errori/finestre)\n"
                "/impara <file>                → studia un manuale/PDF; poi rispondo su quello\n"
                "/conoscenza  |  /dimentica    → manuali studiati · cancellali\n"
                "/pianifica <n>|<cmd>|<quando> → attività automatica (es. pulizia settimanale)\n"
                "/attivita  |  /rimuovi-attivita <n> → attività pianificate · rimuovi\n"
                "/monitor                      → stato del PC e avvisi (RAM/disco)\n"
                "/clienti                      → elenco clienti\n"
                "/cliente <nome>               → scheda del cliente (o la crea)\n"
                "/intervento <cliente> | <cosa> → registra un intervento fatto\n"
                "/agenti <obiettivo>           → squadra di agenti che lavorano e si verificano\n"
                "/migliora                     → Mike riflette sul suo lavoro e si auto-migliora\n"
                "/aggiorna                     → cerca novità su internet e aggiorna le sue conoscenze\n"
                "/aggiorna-mike                → scarica e installa una nuova versione di Mike (con backup)\n"
                "/revisione                    → crea un report del progetto e lo manda a Gemini per un controllo\n"
                "/cervello [modello]           → mostra/cambia il modello AI in uso\n"
                "\n💬 ALTRO\n"
                "/ricorda <fatto>  /cerca <testo>  /ricerca <domanda>  /stato  /aiuto")
        # --- conferma / annulla azioni di riparazione ---
        if t.lower() in ("/conferma", "/conferma!", "/si", "/sì"):
            return self._esegui_azione_in_sospeso()
        if t.lower() in ("/annulla", "/no"):
            self.azione_in_sospeso = None
            return "Azione annullata. Non ho toccato niente."
        if t.lower().startswith("/esperto"):
            arg = t[len("/esperto"):].strip().lower()
            if arg in ("on", "si", "sì", "attiva", "1"):
                self.cfg["modalita_esperto"] = True
                return ("⚙️ MODALITÀ ESPERTO ATTIVA: eseguo le azioni subito, senza chiederti "
                        "/conferma ogni volta. (Per renderla permanente: \"modalita_esperto\": true "
                        "in config.json.) Le azioni restano quelle legittime.")
            if arg in ("off", "no", "disattiva", "0"):
                self.cfg["modalita_esperto"] = False
                return "Modalità esperto disattivata: tornerò a chiederti /conferma prima di agire."
            return (f"Modalità esperto: {'ATTIVA' if self.cfg.get('modalita_esperto') else 'disattivata'}. "
                    "Usa /esperto on  oppure  /esperto off.")
        if t.lower().startswith("/cerca-sempre") or t.lower().startswith("/cerca sempre"):
            arg = t.split("sempre", 1)[1].strip().lower() if "sempre" in t.lower() else ""
            if arg in ("on", "si", "sì", "attiva", "1"):
                self.cfg["cerca_sempre"] = True
                return ("🌐 CERCA SEMPRE ATTIVA: cercherò sul web per ogni domanda. "
                        "(Ci vogliono ~30s a domanda.) Per spegnerla: /cerca-sempre off.")
            if arg in ("off", "no", "disattiva", "0"):
                self.cfg["cerca_sempre"] = False
                return "Cerca-sempre disattivata: cerco sul web solo quando serve (meteo, notizie…)."
            return (f"Cerca sempre: {'ATTIVA' if self.cfg.get('cerca_sempre') else 'disattivata'}. "
                    "Usa /cerca-sempre on  oppure  /cerca-sempre off.")
        # --- diagnosi / log ---
        if t.lower() in ("/diagnosi", "/diagnostica"):
            return self.diagnosi_pc()
        if t.lower() in ("/crash", "/log", "/logs"):
            return self.analizza_crash()
        if t.lower().startswith("/leggi "):
            return self.leggi_e_analizza(t[len("/leggi "):].strip())
        if t.lower() == "/spazio":
            ok, msg = azioni.analizza_spazio()
            return msg
        if t.lower() in ("/analizza-spazio", "/spazio-profondo"):
            self._log("Analizzo lo spazio (anche i file nascosti)…")
            ok, msg = azioni.analizza_spazio_profondo()
            return msg
        if t.lower() in ("/libera-spazio", "/libera"):
            return self._proponi(
                "Eliminare le cache di sistema nascoste e recuperabili (temp, cestino, "
                "cache aggiornamenti Windows, miniature, component store). I file personali "
                "NON vengono toccati",
                azioni.libera_spazio_profondo)
        if t.lower() in ("/processi", "/attivita", "/attività", "/task"):
            return self.vedi_processi()
        # --- riparazioni ---
        if t.lower() == "/ripara":
            return self._menu_riparazioni()
        if t.lower() == "/pulisci":
            return self._proponi("Eliminare i file temporanei (cache, file di installazione vecchi)",
                                  azioni.pulisci_temp)
        if t.lower() == "/svuota-cestino":
            return self._proponi("Svuotare definitivamente il Cestino", azioni.svuota_cestino)
        if t.lower() == "/flush-dns":
            ok, msg = azioni.flush_dns()  # azione innocua: eseguita subito
            return msg
        if t.lower() in ("/ripara-file", "/sfc"):
            return self._proponi("Riparare i file di sistema con SFC e DISM (può durare 10-30 min, serve admin)",
                                  azioni.ripara_file_sistema)
        if t.lower().startswith("/antivirus"):
            tipo = "completa" if "complet" in t.lower() else "veloce"
            return self._proponi(f"Avviare una scansione antivirus {tipo} con Windows Defender",
                                 lambda: azioni.scansione_antivirus(tipo))
        if t.lower() in ("/programmi", "/software"):
            ok, msg = azioni.lista_programmi()
            return msg
        if t.lower().startswith("/disinstalla "):
            nome = t[len("/disinstalla "):].strip()
            return self._proponi(f"Disinstallare il programma «{nome}»",
                                 lambda: azioni.disinstalla(nome))
        if t.lower() in ("/manutenzione", "/manutenzione-sicura"):
            return self._proponi(
                "Eseguire la manutenzione sicura (svuota temp + cestino + cache DNS, "
                "e se sei admin anche la riparazione file di sistema sfc/DISM)",
                azioni.manutenzione_sicura)
        # --- documenti / account ---
        if t.lower().startswith("/checklist"):
            cliente = t[len("/checklist"):].strip()
            return self.crea_checklist(cliente)
        if t.lower().startswith("/crea-account "):
            parti = t[len("/crea-account "):].split()
            if len(parti) < 2:
                return "Uso: /crea-account <nome> <password>"
            nome, pwd = parti[0], " ".join(parti[1:])
            return self._proponi(
                f"Creare un account LOCALE amministratore di emergenza «{nome}»",
                lambda: azioni.crea_account_emergenza(nome, pwd))
        # --- intelligenza / aggiornamento ---
        if t.lower() == "/migliora":
            return self.auto_migliora()
        if t.lower() == "/aggiorna":
            return self.aggiorna_conoscenze()
        if t.lower() in ("/aggiorna-mike", "/aggiornamento"):
            return self.aggiorna_mike()
        if t.lower().startswith("/cervello"):
            return self.gestisci_cervello(t[len("/cervello"):].strip())
        if t.lower() in ("/revisione", "/revisione-gemini", "/revisione-claude", "/report"):
            return self.revisione_esterna()
        if t.lower().startswith("/crea ") or t.lower().startswith("/costruisci "):
            desc = t.split(" ", 1)[1].strip() if " " in t else ""
            return self.crea_software(desc)
        if t.lower().startswith("/modifica "):
            return self.modifica_software(t[len("/modifica "):].strip())
        if t.lower().startswith("/riprendi ") or t.lower().startswith("/riapri "):
            return self.riapri_progetto(t.split(" ", 1)[1].strip())
        if t.lower().startswith("/schermo") or t.lower().startswith("/schermata"):
            domanda = t.split(" ", 1)[1].strip() if " " in t else ""
            return self.leggi_schermo(domanda)
        if t.lower().startswith("/template"):
            arg = t[len("/template"):].strip()
            if not arg:
                tpl = builder.elenca_template()
                return ("🧩 Template pronti (crea in un secondo):\n"
                        + "\n".join(f"  • {k} — {v}" for k, v in tpl.items())
                        + "\nUsa: /template <nome>")
            ok, msg, info = builder.crea_da_template(arg)
            if ok:
                self.ultimo_progetto = info
                store.registra_progetto(info["nome"], info["cartella"], info["descrizione"], info["avvio"])
                msg += self._proponi_prossimo_passo(info)
            return msg
        if t.lower().startswith("/impara "):
            percorso = t[len("/impara "):].strip()
            n, err = conoscenza.impara(percorso)
            if err:
                return f"Non sono riuscito a studiarlo: {err}"
            return (f"📚 Ho studiato «{os.path.basename(percorso)}» ({n} sezioni). "
                    "Ora puoi farmi domande su quel materiale.")
        if t.lower() in ("/conoscenza", "/manuali"):
            fonti = conoscenza.elenca()
            if not fonti:
                return "Non ho ancora studiato nessun manuale. Usa: /impara <percorso file>"
            return "📚 Manuali studiati:\n" + "\n".join(f"  • {f} ({n} sezioni)" for f, n in fonti.items())
        if t.lower() in ("/dimentica", "/dimentica-manuali"):
            conoscenza.dimentica()
            return "Ho dimenticato tutti i manuali studiati."
        if t.lower().startswith("/pianifica "):
            return self._pianifica_da_comando(t[len("/pianifica "):].strip())
        if t.lower() in ("/attivita", "/attività", "/pianificate"):
            voci = scheduler.elenca()
            if not voci:
                return "Nessuna attività pianificata. Crea con: /pianifica nome | comando | giornaliera 09:00"
            return "📅 Attività pianificate:\n" + "\n".join(f"  • {n} → prossima: {p}" for n, p in voci)
        if t.lower().startswith("/rimuovi-attivita "):
            ok, msg = scheduler.rimuovi(t[len("/rimuovi-attivita "):].strip())
            return msg
        if t.lower() in ("/monitor", "/monitoraggio", "/salute"):
            testo, allarmi = watch.controlla()
            r = f"🔎 STATO PC: {testo}"
            if allarmi:
                r += "\n\n🔔 ATTENZIONE:\n" + "\n".join(f"  • {a}" for a in allarmi)
                if any("spazio" in a.lower() or "disco" in a.lower() for a in allarmi):
                    r += "\n\n💡 Posso liberare spazio: scrivi /libera-spazio"
            else:
                r += "\n✅ Tutto nella norma."
            return r
        # --- storico clienti ---
        if t.lower() in ("/clienti", "/clientela"):
            elenco = clienti.elenca()
            if not elenco:
                return ("Nessun cliente registrato. Crea con: /cliente <nome>\n"
                        "Registra un intervento con: /intervento <cliente> | <cosa hai fatto>")
            righe = ["👥 CLIENTI:"]
            for nome, n_int, pc in elenco:
                righe.append(f"  • {nome}" + (f" [{pc}]" if pc else "") + f" — {n_int} interventi")
            return "\n".join(righe)
        if t.lower().startswith("/cliente "):
            nome = t[len("/cliente "):].strip()
            s = clienti.scheda(nome)
            if s:
                return s
            clienti.aggiungi_o_prendi(nome)
            return f"👤 Scheda creata per «{nome}». Registra gli interventi con:\n/intervento {nome} | <cosa hai fatto>"
        if t.lower().startswith("/intervento "):
            resto = t[len("/intervento "):]
            if "|" not in resto:
                return "Formato: /intervento <cliente> | <cosa hai fatto>"
            nome, cosa = [p.strip() for p in resto.split("|", 1)]
            n = clienti.registra_intervento(nome, cosa)
            return f"✅ Intervento #{n} registrato per «{nome}»: {cosa}"
        if t.lower() in ("/progetti", "/progetto"):
            reg = store.progetti()
            if not reg:
                return "Non hai ancora creato progetti. Prova: /crea un programma che…"
            righe = ["📁 I tuoi progetti (dal più recente):"]
            for p in reversed(reg[-15:]):
                d = f" — {p['descrizione'][:60]}" if p.get("descrizione") else ""
                righe.append(f"  • {p['nome']}{d}  ({p.get('quando','')})")
            righe.append("\nPer riprenderne uno: /riprendi <nome o parola chiave>")
            if self.ultimo_progetto:
                righe.append(f"(Attivo ora: {self.ultimo_progetto.get('nome','') or os.path.basename(self.ultimo_progetto.get('cartella',''))})")
            return "\n".join(righe)
        if t.lower().startswith("/agenti "):
            obiettivo = t[len("/agenti "):].strip()
            return self.esegui_squadra(obiettivo)
        if t.lower() in ("/account", "/utenti"):
            return self.analizza_accessi()
        if t.lower() in ("/guida-bloccato", "/bloccato"):
            return recupero.GUIDA_BLOCCATO
        if t.lower().startswith("/reset-password "):
            parti = t[len("/reset-password "):].split()
            if len(parti) < 2:
                return "Uso: /reset-password <nomeutente> <nuovapassword>"
            utente, nuova = parti[0], " ".join(parti[1:])
            ok, messaggio = recupero.reset_password(utente, nuova)
            return messaggio
        if t.lower().startswith("/ricorda "):
            fatto = t[len("/ricorda "):].strip()
            store.aggiungi_fatto(fatto)
            return f"Memorizzato! D'ora in poi ricorderò: «{fatto}»"
        if t.lower().startswith("/chiamami "):
            nome = t[len("/chiamami "):].strip()
            store.imposta_nome(nome)
            return f"Piacere, {nome}! D'ora in poi mi ricorderò di te. 🙂"
        if t.lower().startswith("/io "):
            store.aggiungi_nota_profilo(t[len("/io "):].strip())
            return "Fatto, l'ho aggiunto al tuo profilo. Ti conosco un po' meglio ora."
        if t.lower() in ("/profilo", "/chi-sono"):
            p = store.profilo_come_testo()
            return p if p else "Non so ancora molto di te. Dimmi: /chiamami <nome>  e  /io <qualcosa su di te>."
        if t.lower().startswith("/ricerca ") or t.lower() in ("/ricerca", "/approfondisci"):
            query = t.split(" ", 1)[1].strip() if " " in t else ""
            if not query:
                return ("🔍 USO DEL COMANDO /ricerca:\n"
                        "/ricerca <domanda o argomento>\n\n"
                        "Esempio: /ricerca ultime notizie su Windows 11\n"
                        "Mike cercherà su internet, leggerà le pagine web dei siti e risponderà con informazioni aggiornate citando le fonti.")
            return self.ricerca_autonoma(query, su_token=su_token)
        if t.lower().startswith("/cerca "):
            query = t[len("/cerca "):].strip()
            return web.cerca_come_testo(query)
        if t.lower() == "/stato":
            return self.stato()
        return None

    def ricerca_autonoma(self, query, su_token=None):
        """Esegue una ricerca approfondita sul web, scarica e legge il contenuto delle pagine,
        e genera una sintesi citando le fonti reali (URL).
        """
        self._log(f"🔎 Cerco sul web: «{query}»…")
        # Su un PC senza GPU, scaricare pagine intere è troppo lento. Usiamo i risultati
        # di ricerca (titolo + riassunto + URL): veloci e citano già le fonti.
        dati_web = web.cerca_come_testo(query, numero=5)
        if dati_web and len(dati_web) > 2500:
            dati_web = dati_web[:2500] + "\n…(estratto)"

        sistema = (
            "Sei Mike. Rispondi alla domanda dell'utente USANDO i dati estratti dal web qui "
            "sotto. Sii chiaro e conciso. Cita le FONTI (URL) che hai usato. In italiano."
        )
        prompt = f"Domanda: {query}\n\nDati dal web:\n{dati_web}"

        prov = agent_llm.provider_predefinito(self.cfg)
        self._log("Scrivo la risposta…")
        storia = [{"ruolo": "utente", "testo": prompt}]
        if su_token and prov == "ollama":
            # Usa il modello configurato (veloce). NIENTE gpt-oss:20b qui: su CPU si pianta.
            mod = self.cfg.get("modello_ollama", "qwen2.5:3b")
            risposta = ollama.chiedi_stream(mod, storia, system=sistema, su_token=su_token)
        else:
            risposta = agent_llm.chiedi(self.cfg, prov, sistema, prompt, max_token=900)
            if su_token:
                su_token(risposta)

        self.cronologia.append({"ruolo": "utente", "testo": f"/ricerca {query}"})
        self.cronologia.append({"ruolo": "assistente", "testo": risposta})
        self.cronologia = self.cronologia[-MAX_CRONOLOGIA:]
        if self.cfg.get("abilita_memoria", True):
            try:
                store.registra_conversazione(query, risposta, f"{prov}_ricerca")
            except Exception:
                pass
        return risposta

    # ---------- domanda principale ----------

    def _serve_sistema(self, testo):
        """La domanda riguarda lo stato/i processi del PC? Allora Mike deve GUARDARLO."""
        spie = ["processo", "processi", "gira", "girando", "aperto", "aperti", "task",
                "rallenta", "lento", "lenta", "veloce", "cpu", "ram", "memoria",
                "cosa sta facendo", "che sta facendo", "consuma", "bot", "programma",
                "programmi", "applicazion", "in esecuzione", "carico", "pesante",
                "blocca", "freeze", "rallentamenti", "antivirus sta", "windows sta"]
        t = testo.lower()
        return any(s in t for s in spie)

    def _serve_web(self, testo):
        """Euristica semplice: la domanda riguarda cose attuali/aggiornate?"""
        if not self.cfg["abilita_ricerca_web"]:
            return False
        spie = ["oggi", "adesso", "attuale", "ultim", "notizi", "prezzo", "quotazione",
                "meteo", "2024", "2025", "2026", "novità", "appena", "ieri", "domani",
                "chi ha vinto", "risultato", "in tempo reale"]
        t = testo.lower()
        return any(s in t for s in spie)

    def _serve_ricerca(self, testo):
        """La domanda richiede informazioni ATTUALI dal web? (meteo, notizie, prezzi…)
        In tal caso Mike deve CERCARE davvero, non rispondere a memoria."""
        t = " " + testo.lower() + " "
        chiavi = [
            # meteo
            "meteo", "che tempo", "tempo fa", "tempo fara", "tempo farà", "previsioni",
            "pioggia", "pioverà", "piovera", "piove", "neve", "nevica", "temperatura",
            "gradi", "che tempo fa", "farà bello", "fara bello", "sole domani",
            # notizie / attualità
            "notizie", "ultime notizie", "cosa è successo", "cosa e successo",
            "chi ha vinto", "risultato", "risultati", "partita", "classifica",
            # prezzi / mercati
            "prezzo", "quanto costa", "quotazione", "cambio euro", "bitcoin", "borsa",
            "benzina", "carburante",
            # orari / info aggiornate
            "orari", "a che ora", "quando esce", "quando gioca", "in tempo reale",
        ]
        # giorni della settimana insieme a "tempo/meteo" (es. "domenica a Fiano")
        giorni = ("lunedì", "lunedi", "martedì", "martedi", "mercoledì", "mercoledi",
                  "giovedì", "giovedi", "venerdì", "venerdi", "sabato", "domenica")
        if any(k in t for k in chiavi):
            return True
        if any(g in t for g in giorni) and any(w in t for w in ("tempo", "meteo", "pioggia", "sole")):
            return True
        return False

    def _rileva_apri(self, testo):
        """Se l'utente chiede di APRIRE un sito, restituisce l'URL. Altrimenti None."""
        import re
        t = testo.lower()
        m = re.search(r"(?:apri(?:mi)?|apre|vai su|portami su|vai sul sito|mostrami il sito)\s+"
                      r"(?:il sito |la pagina |su |sul )?([a-zà-ÿ0-9.\-/ ]{2,60})", t)
        if not m:
            return None
        target = m.group(1).strip(" ?.!,")
        if not target:
            return None
        comuni = [
            ("goog", "https://www.google.com"), ("you", "https://www.youtube.com"),
            ("face", "https://www.facebook.com"), ("insta", "https://www.instagram.com"),
            ("whats", "https://web.whatsapp.com"), ("gmail", "https://mail.google.com"),
            ("posta", "https://mail.google.com"), ("mapp", "https://www.google.com/maps"),
            ("maps", "https://www.google.com/maps"), ("meteo", "https://www.ilmeteo.it"),
            ("amazon", "https://www.amazon.it"), ("wiki", "https://it.wikipedia.org"),
            ("ebay", "https://www.ebay.it"), ("subito", "https://www.subito.it"),
            ("netflix", "https://www.netflix.com"), ("chatgpt", "https://chat.openai.com"),
        ]
        for pref, url in comuni:
            if target.startswith(pref) or pref in target:
                return url
        # è già un dominio (es. "repubblica.it")?
        if re.match(r"^[a-z0-9][a-z0-9.\-]*\.[a-z]{2,}(/.*)?$", target):
            return "https://" + target
        # altrimenti prova www.<nome>.com
        slug = re.sub(r"[^a-z0-9]", "", target.split()[0]) if target.split() else ""
        return f"https://www.{slug}.com" if len(slug) >= 2 else None

    def apri_sito(self, url):
        """Apre un sito nel browser predefinito del PC."""
        import webbrowser
        try:
            webbrowser.open(url)
            return (f"🌐 Ho aperto {url} nel tuo browser.\n"
                    "(I siti come Google non si possono mostrare dentro Mike perché lo vietano; "
                    "li apro in una scheda. Mappe e indirizzi invece li vedi nel pannello a destra.)")
        except Exception as e:
            return f"Non sono riuscito ad aprire {url}: {e}"

    def _e_saluto(self, testo):
        """True se è solo un saluto/ringraziamento (non vale la pena cercare sul web)."""
        t = testo.lower().strip(" .!?")
        saluti = ("ciao", "salve", "buongiorno", "buonasera", "buonanotte", "ehi", "hey",
                  "grazie", "ok", "perfetto", "va bene", "come stai", "chi sei", "aiuto")
        return t in saluti or len(t) <= 2

    def chiedi(self, testo):
        """Punto d'ingresso: l'utente fa una domanda, Mike risponde (stringa)."""
        # 1) Comandi speciali
        speciale = self._gestisci_comando(testo)
        if speciale is not None:
            return speciale

        # 2) Rilevamento linguaggio naturale per Travelpayouts
        accumulo = []
        def acc(fr): accumulo.append(fr)
        naturale = self._rileva_e_gestisci_naturale(testo, acc)
        if naturale is not None:
            return "".join(accumulo)

        if not self.pronto():
            return ("Non ho ancora nessuna chiave API configurata.\n"
                    "Apri il file config.json e incolla almeno una chiave (Claude o Gemini).\n"
                    "Guarda il README.md per le istruzioni passo-passo.")

        # 2) Eventuale ricerca web e/o lettura live del PC
        contesto_web = ""
        if self._serve_web(testo):
            contesto_web = web.cerca_come_testo(testo, numero=5)
        contesto_sistema = ""
        if self._serve_sistema(testo):
            self._log("Guardo cosa sta facendo il PC adesso…")
            istant, _err = live.istantanea()
            if istant:
                contesto_sistema = istant

        # 3) Aggiunge la domanda alla cronologia
        self.cronologia.append({"ruolo": "utente", "testo": testo})

        sistema = self._prompt_sistema(contesto_web, contesto_sistema)

        # 4) Prova il provider principale, poi quello di riserva
        ordine = [self.cfg["provider_principale"], self.cfg["provider_riserva"]]
        ultimo_errore = None
        for nome_provider in ordine:
            try:
                risposta = self._invoca(nome_provider, sistema)
                self.cronologia.append({"ruolo": "assistente", "testo": risposta})
                if self.cfg["abilita_memoria"]:
                    store.registra_conversazione(testo, risposta, nome_provider)
                return risposta
            except Exception as e:
                ultimo_errore = e
                continue

        return f"Ho avuto un problema con tutti i provider.\nUltimo errore: {ultimo_errore}"

    # ---------- multi-agente ----------

    def esegui_squadra(self, obiettivo):
        """Crea una squadra di agenti che eseguono e si verificano a vicenda."""
        if not obiettivo:
            return "Scrivi cosa devono fare gli agenti. Esempio: /agenti analizza i rischi di sicurezza di questo PC"
        orch = Orchestratore(self.cfg, log=self._log)
        return orch.esegui(obiettivo)

    # ---------- diagnostica del PC ----------

    def diagnosi_pc(self):
        """Scansiona il PC (sola lettura) e fa analizzare i risultati a un agente."""
        self._log("Sto scansionando il sistema (sola lettura)…")
        report, errore = scanner.esegui_scansione()
        if errore:
            return f"Diagnosi non riuscita: {errore}"

        riassunto = scanner.riassunto_testo(report)

        # Se c'è un provider, un agente "Tecnico" analizza e propone soluzioni.
        provider = agent_llm.provider_predefinito(self.cfg)
        if not provider:
            return ("DIAGNOSI DEL PC (dati grezzi — aggiungi una chiave API per l'analisi automatica):\n\n"
                    + riassunto)

        self._log("L'agente Tecnico sta analizzando i risultati…")
        tecnico = Agente(
            "Tecnico", "tecnico informatico esperto in diagnostica Windows e risoluzione problemi",
            self.cfg, provider)
        try:
            analisi = tecnico.lavora(
                "Analizza questo report di diagnostica di un PC Windows. Elenca i problemi in ordine "
                "di priorità e per ognuno proponi una soluzione concreta e i passi da fare. "
                "Distingui ciò che richiede i diritti di amministratore. Sii pratico, da tecnico.",
                contesto=riassunto)
        except Exception as e:
            testo = (f"📊 DIAGNOSTICA DEL PC (dati reali):\n{riassunto}\n\n"
                     f"(L'analisi AI non è disponibile ora: {e})")
            self._salva_report("diagnosi", testo)
            return testo

        testo = f"📊 RIASSUNTO DIAGNOSTICA:\n{riassunto}\n\n🩺 ANALISI DEL TECNICO:\n{analisi}"
        percorso = self._salva_report("diagnosi", testo)
        if percorso:
            testo += f"\n\n💾 Report salvato in: {percorso}"
        return testo

    # ---------- visione live del PC ----------

    def vedi_processi(self):
        """Mostra cosa sta facendo il PC adesso e lo fa commentare a un agente."""
        self._log("Leggo i processi attivi…")
        istant, errore = live.istantanea()
        if errore:
            return f"Non riesco a leggere lo stato del PC: {errore}"
        provider = agent_llm.provider_predefinito(self.cfg)
        if not provider:
            return "🖥️ " + istant
        self._log("Analizzo cosa sta girando…")
        tecnico = Agente("Tecnico", "monitoraggio processi e prestazioni Windows",
                         self.cfg, provider)
        try:
            analisi = tecnico.lavora(
                "Questo è lo stato REALE del PC adesso. Dimmi in modo semplice cosa sta "
                "girando, se c'è qualcosa di anomalo o che consuma troppo, e cosa eventualmente "
                "chiudere. Sii concreto.", contesto=istant)
        except Exception:
            return f"🖥️ COSA STA FACENDO IL PC ORA (dati reali):\n{istant}"
        return f"🖥️ COSA STA FACENDO IL PC ORA:\n{istant}\n\n🩺 ANALISI:\n{analisi}"

    # ---------- analisi crash e file ----------

    def analizza_crash(self):
        """Legge i log di crash/errore e li fa analizzare a un agente Tecnico."""
        self._log("Sto leggendo i log di sistema (crash, errori)…")
        report, errore = logs.leggi_log_crash()
        if errore:
            return f"Lettura log non riuscita: {errore}"
        riassunto = logs.riassunto_log(report)
        provider = agent_llm.provider_predefinito(self.cfg)
        if not provider:
            testo = "LOG DI CRASH/ERRORE (dati grezzi):\n" + riassunto
        else:
            self._log("L'agente Tecnico sta analizzando i crash…")
            tecnico = Agente("Tecnico", "esperto di crash, BSOD ed errori di Windows",
                             self.cfg, provider)
            try:
                analisi = tecnico.lavora(
                    "Analizza questi log di un PC Windows. Individua le cause probabili di crash/errori, "
                    "raggruppa i problemi ricorrenti e proponi soluzioni concrete in ordine di priorità. "
                    "Spiega in modo pratico, da tecnico.", contesto=riassunto)
                testo = f"📑 LOG RACCOLTI:\n{riassunto}\n\n🩺 ANALISI DEL TECNICO:\n{analisi}"
            except Exception:
                testo = f"📑 LOG DI CRASH/ERRORE (dati reali):\n{riassunto}"
        percorso = self._salva_report("crash", testo)
        if percorso:
            testo += f"\n\n💾 Report salvato in: {percorso}"
        return testo

    def leggi_e_analizza(self, percorso):
        """Legge un file indicato dall'utente e lo fa analizzare a Mike."""
        if not percorso:
            return "Indica il percorso del file. Esempio: /leggi C:\\percorso\\errore.log"
        contenuto, errore = logs.leggi_file(percorso)
        if errore:
            return errore
        provider = agent_llm.provider_predefinito(self.cfg)
        if not provider:
            return f"CONTENUTO DI {percorso}:\n\n{contenuto}"
        self._log("Mike sta analizzando il file…")
        tecnico = Agente("Tecnico", "analisi di log e file di configurazione", self.cfg, provider)
        analisi = tecnico.lavora(
            f"Analizza il contenuto di questo file ({percorso}). Spiega cosa contiene, "
            "evidenzia errori/anomalie e cosa fare. In italiano.", contesto=contenuto)
        return f"📄 {percorso}\n\n🩺 ANALISI:\n{analisi}"

    # ---------- riparazioni (con conferma) ----------

    def _menu_riparazioni(self):
        return ("🛠️ RIPARAZIONI DISPONIBILI (ognuna chiede conferma prima di agire):\n"
                "  /pulisci          → elimina file temporanei\n"
                "  /svuota-cestino   → svuota il cestino\n"
                "  /flush-dns        → ripara problemi di rete (cache DNS)\n"
                "  /ripara-file      → ripara file di sistema corrotti (sfc + DISM)\n"
                "  /antivirus veloce → scansione rapida Windows Defender\n"
                "  /antivirus completa → scansione completa (lenta)\n"
                "  /programmi        → elenco programmi installati\n"
                "  /disinstalla <nome> → rimuove un programma\n"
                "  /manutenzione     → fa tutta la pulizia sicura in un colpo\n"
                "  /analizza-spazio  → dove finisce lo spazio (anche i file NASCOSTI)\n"
                "  /libera-spazio    → elimina le cache nascoste che riempiono il disco\n"
                "  /spazio           → quanto spazio si può recuperare (veloce)")

    def _proponi(self, descrizione, funzione):
        """Propone un'azione. Con la modalità esperto la esegue subito, senza conferma."""
        if self.cfg.get("modalita_esperto"):
            self._log(f"[esperto] Eseguo: {descrizione}")
            try:
                ok, msg = funzione()
            except Exception as e:
                return f"Errore durante l'esecuzione: {e}"
            return f"⚙️ (esperto) {descrizione}:\n{msg}"
        self.azione_in_sospeso = {"descrizione": descrizione, "esegui": funzione}
        return (f"⚠️ Sto per: {descrizione}.\n"
                "Scrivi /conferma per procedere, oppure /annulla per fermarti.")

    def _esegui_azione_in_sospeso(self):
        if not self.azione_in_sospeso:
            return "Non c'è nessuna azione in attesa di conferma."
        azione = self.azione_in_sospeso
        self.azione_in_sospeso = None
        self._log(f"Eseguo: {azione['descrizione']}…")
        try:
            ok, messaggio = azione["esegui"]()
        except Exception as e:
            return f"Errore durante l'esecuzione: {e}"
        return messaggio

    # ---------- recupero accesso ----------

    def analizza_accessi(self):
        """Analizza gli account (sola lettura) e mostra la guida al recupero."""
        self._log("Sto leggendo gli account del PC…")
        report, errore = recupero.analizza_account()
        if errore:
            return f"Analisi account non riuscita: {errore}"
        situazione = recupero.riassunto_account(report)
        guida = recupero.guida_recupero(report)
        testo = f"👥 SITUAZIONE ACCOUNT:\n{situazione}\n\n{guida}"
        percorso = self._salva_report("account", testo)
        if percorso:
            testo += f"\n\n💾 Report salvato in: {percorso}"
        return testo

    # ---------- salvataggio report ----------

    def _salva_report(self, prefisso, contenuto):
        """Salva un report in dati/Report/ con data e nome PC. Restituisce il percorso."""
        import os, time, socket
        try:
            cartella = os.path.join(cfg_mod.RADICE, "dati", "Report")
            os.makedirs(cartella, exist_ok=True)
            stamp = time.strftime("%Y%m%d_%H%M%S")
            nome = f"{prefisso}_{socket.gethostname()}_{stamp}.txt"
            percorso = os.path.join(cartella, nome)
            with open(percorso, "w", encoding="utf-8") as f:
                f.write(f"Report '{prefisso}' generato da Mike — {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                f.write(contenuto)
            return percorso
        except Exception:
            return None

    # ---------- intelligenza: auto-miglioramento e aggiornamento ----------

    def auto_migliora(self):
        """Mike riflette sulle conversazioni recenti e migliora le PROPRIE istruzioni.

        È l'auto-miglioramento SICURO: Mike non riscrive il suo codice, ma affina
        le proprie istruzioni di comportamento, che userà nelle risposte future.
        """
        provider = agent_llm.provider_predefinito(self.cfg)
        if not provider:
            return "Per auto-migliorarmi mi serve un cervello attivo (Ollama acceso o una chiave API)."

        conversazioni = store.leggi_conversazioni()
        diario = store.carica().get("diario", [])
        attuali = store.auto_istruzioni_come_testo() or "(nessuna ancora)"
        if not conversazioni:
            return ("Non ho ancora abbastanza conversazioni per imparare. "
                    "Usami un po', poi riprova con /migliora.")

        self._log("Sto riflettendo sul mio lavoro per migliorarmi…")
        system = (
            "Sei Mike che riflette su sé stesso per lavorare meglio. "
            "Dalle conversazioni recenti, individua 3-6 LEZIONI pratiche su come "
            "migliorare le tue risposte future (cosa hai sbagliato, cosa apprezza "
            "l'utente, scorciatoie utili). "
            "Rispondi SOLO con un array JSON di stringhe brevi e azionabili."
        )
        prompt = (f"ISTRUZIONI ATTUALI:\n{attuali}\n\n"
                  f"CONVERSAZIONI RECENTI:\n{conversazioni}\n\n"
                  f"NOTE DIARIO: {diario[-5:]}")
        risposta = agent_llm.chiedi(self.cfg, provider, system, prompt, max_token=600)
        nuove = agent_llm.estrai_json(risposta)
        if not isinstance(nuove, list) or not nuove:
            return "Ho riflettuto ma non sono riuscito a estrarre lezioni chiare. Riprovo la prossima volta."

        # Unisce le vecchie con le nuove (senza duplicati), max 12
        esistenti = store.carica().get("auto_istruzioni", [])
        unite = esistenti + [str(x) for x in nuove if str(x) not in esistenti]
        unite = unite[-12:]
        store.imposta_auto_istruzioni(unite)
        store.aggiungi_diario(f"Auto-miglioramento: {len(nuove)} nuove lezioni apprese.")
        elenco = "\n".join(f"  • {x}" for x in nuove)
        return f"🌱 Mi sono auto-migliorato. Nuove lezioni che applicherò:\n{elenco}"

    def aggiorna_conoscenze(self):
        """Cerca novità su internet e aggiorna le conoscenze di Mike (es. modelli AI)."""
        if not self.cfg["abilita_ricerca_web"]:
            return "La ricerca web è disattivata in config.json (abilita_ricerca_web)."
        self._log("Cerco aggiornamenti su internet…")
        notizie = web.cerca_come_testo("novità ultimi modelli AI Claude Gemini 2026", numero=5)
        provider = agent_llm.provider_predefinito(self.cfg)
        modelli_locali = ollama.modelli()
        info = (f"Modelli locali installati (Ollama): {', '.join(modelli_locali) or 'nessuno'}\n\n"
                f"Dal web:\n{notizie}")
        if not provider:
            return "🔄 Aggiornamento (dati grezzi):\n\n" + info
        self._log("Riassumo le novità…")
        agente = Agente("Aggiornatore", "tieni Mike al passo con le novità AI", self.cfg, provider)
        riassunto = agente.lavora(
            "Riassumi le novità rilevanti e dimmi se conviene cambiare modello. Conciso, in italiano.",
            contesto=info)
        store.aggiungi_diario("Aggiornamento conoscenze dal web eseguito.")
        return f"🔄 AGGIORNAMENTO CONOSCENZE:\n{riassunto}"

    def revisione_esterna(self):
        """Genera i report del progetto per Gemini e Claude, e manda quello Gemini per la revisione se la chiave c'è.

        Se la chiave Gemini non c'è, salva i report pronti da incollare nelle rispettive AI.
        """
        from .documenti import report
        self._log("Genero i report completi per Gemini e Claude…")
        percorso_gemini, testo_gemini = report.genera()
        percorso_claude, testo_claude = report.genera_claude()

        msg_chiave = ""
        # Se c'è la chiave Gemini, glielo mandiamo per la revisione
        if cfg_mod.chiave_valida(self.cfg.get("gemini_api_key", "")):
            self._log("Mando il report a Gemini per il controllo…")
            try:
                recensione = gemini.chiedi(
                    self.cfg["gemini_api_key"], self.cfg["modello_gemini"],
                    [{"ruolo": "utente", "testo": report.PROMPT_REVISIONE + testo_gemini}],
                    system="Sei un revisore software esperto di sicurezza e qualità.",
                    max_token=2500)
                store.aggiungi_diario("Revisione esterna di Gemini ricevuta.")
                return (f"✅ Report generati con successo!\n\n"
                        f"🤖 Report per Gemini:\n{percorso_gemini}\n\n"
                        f"🧡 Report per Claude:\n{percorso_claude}\n\n"
                        f"🔎 REVISIONE DI GEMINI:\n{recensione}")
            except Exception as e:
                msg_chiave = f"⚠️ Invio a Gemini non riuscito ({e}).\n"

        return (f"✅ Report generati con successo!\n\n"
                f"🤖 Per Gemini:\n{percorso_gemini}\n"
                f"• Incollalo in Gemini/Antigravity per la revisione.\n\n"
                f"🧡 Per Claude:\n{percorso_claude}\n"
                f"• Incollalo in Claude per una revisione super dettagliata!\n\n"
                f"{msg_chiave}I file sono pronti nella cartella dei report. Copiane il contenuto e incollalo nelle rispettive chat delle AI.")

    def aggiorna_mike(self):
        """Controlla e (con conferma) installa una nuova versione di Mike."""
        self._log("Controllo se c'è una nuova versione di Mike…")
        info = updater.controlla(self.cfg)
        if not info["ok"]:
            return info["messaggio"]
        # C'è un aggiornamento: lo proponiamo con conferma
        return self._proponi(
            f"Aggiornare Mike dalla versione {info['locale']} alla {info['remota']} "
            f"(con backup automatico). Novità: {info['note'] or 'n/d'}",
            lambda: updater.applica(self.cfg, log=self._log))

    def controllo_aggiornamento_avvio(self):
        """All'avvio: se attivo e c'è una sorgente, avvisa se esiste un aggiornamento.
        NON installa nulla da solo: ritorna un avviso o None."""
        if not self.cfg.get("aggiornamento_auto", True):
            return None
        if not (self.cfg.get("aggiornamento_sorgente") or "").strip():
            return None
        try:
            info = updater.controlla(self.cfg)
        except Exception:
            return None
        if info.get("ok"):
            return (f"🔔 È disponibile una nuova versione di Mike "
                    f"({info['locale']} → {info['remota']}). Scrivi /aggiorna-mike per installarla.")
        return None

    def gestisci_cervello(self, argomento):
        """Mostra o cambia il modello AI in uso."""
        if not argomento:
            disponibili = ollama.modelli()
            attuale = self.cfg["modello_ollama"]
            elenco = "\n".join(f"  • {m}{' (in uso)' if m == attuale else ''}" for m in disponibili)
            return (f"🧠 Cervello attuale (locale): {attuale}\n"
                    f"Provider principale: {self.cfg['provider_principale']}\n\n"
                    f"Modelli locali disponibili:\n{elenco}\n\n"
                    "Per cambiare: /cervello <nome-modello>  (es. /cervello gpt-oss:20b)")
        disponibili = ollama.modelli()
        if argomento not in disponibili:
            return f"«{argomento}» non è tra i modelli installati: {', '.join(disponibili)}"
        self.cfg["modello_ollama"] = argomento
        self.cfg["provider_principale"] = "ollama"
        return f"✅ Cervello cambiato in «{argomento}». (Per renderlo permanente, mettilo in config.json → modello_ollama)"

    # ---------- documenti ----------

    def crea_checklist(self, cliente):
        """Genera il modulo di consenso/intervento stampabile (HTML) e lo apre."""
        from .documenti import checklist
        percorso = checklist.genera(cliente, nome_pc=__import__("socket").gethostname())
        # Apertura multipiattaforma (Windows / Mac / Linux)
        try:
            import sys, subprocess
            if sys.platform.startswith("win"):
                os.startfile(percorso)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", percorso])
            else:
                subprocess.Popen(["xdg-open", percorso])
        except Exception:
            pass
        return (f"🗂️ Modulo creato e aperto per la stampa:\n{percorso}\n"
                "Stampalo, compilalo e fallo firmare al cliente prima dell'intervento.")

    def _invoca(self, nome_provider, sistema):
        """Chiama il provider richiesto con la cronologia (limitata, per velocità)."""
        storia = self.cronologia[-MAX_STORIA:]
        if nome_provider == "ollama":
            return ollama.chiedi(self.cfg["modello_ollama"], storia, system=sistema)
        elif nome_provider == "claude":
            return claude.chiedi(
                self.cfg["claude_api_key"], self.cfg["modello_claude"],
                storia, system=sistema)
        elif nome_provider == "gemini":
            return gemini.chiedi(
                self.cfg["gemini_api_key"], self.cfg["modello_gemini"],
                storia, system=sistema)
        raise ValueError(f"Provider sconosciuto: {nome_provider}")

    def _is_edge_window_visible(self):
        import ctypes
        EnumWindows = ctypes.windll.user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
        GetWindowText = ctypes.windll.user32.GetWindowTextW
        GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
        IsWindowVisible = ctypes.windll.user32.IsWindowVisible
        
        titles = []
        def foreach_window(hwnd, lParam):
            if IsWindowVisible(hwnd):
                length = GetWindowTextLength(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    GetWindowText(hwnd, buff, length + 1)
                    titles.append(buff.value)
            return True
            
        try:
            EnumWindows(EnumWindowsProc(foreach_window), 0)
        except Exception:
            return True
            
        for t in titles:
            t_low = t.lower()
            if "microsoft edge" in t_low:
                return True
        return False

    def _rileva_e_gestisci_naturale(self, testo, su_token):
        t_low = testo.lower().strip()
        # Comando esplicito: scatta sempre.
        if t_low in ("/check-tp", "/verifica-affiliati"):
            return self._esegui_verifica_live_stream(su_token)
        # Altrimenti scatta SOLO su messaggi BREVI che chiedono esplicitamente di
        # verificare le affiliazioni. Così un testo lungo incollato (report, link, ecc.)
        # viene letto/risposto normalmente e NON fa partire la scansione per sbaglio.
        if len(t_low) > 80:
            return None
        parla_di_affiliati = any(w in t_low for w in ["affiliat", "affiliazion", "travelpayout", "programmi affil"])
        chiede_verifica = any(w in t_low for w in ["verif", "control", "check", "stato", "attiv"])
        if parla_di_affiliati and chiede_verifica:
            return self._esegui_verifica_live_stream(su_token)
        return None

    def _esegui_verifica_live_stream(self, su_token):
        su_token("🤖 Avvio il controllo dei programmi di affiliazione su Travelpayouts...\n\n")
        try:
            import subprocess
            su_token("✓ Inizio la scansione in background...\n")
            
            # Start the check script and stream stdout line-by-line
            process = subprocess.Popen(
                ["python", "-u", r"C:\Users\mario\Software travel\TripTotale\check_and_notify.py", "--interactive"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                bufsize=1
            )
            
            # Read stdout and stream to chat
            for line in iter(process.stdout.readline, ""):
                line_str = line.strip()
                if line_str:
                    clean_line = line_str
                    # Remove timestamp for clean formatting in chat
                    if "]" in line_str:
                        clean_line = line_str.split("]", 1)[1].strip()
                    su_token(f"{clean_line}\n")
            
            process.stdout.close()
            process.wait()
            
            # Read full log summary to show at the end
            log_file = r"C:\Users\mario\Software travel\TripTotale\check_notify.log"
            last_run = ""
            if os.path.exists(log_file):
                with open(log_file, "r", encoding="utf-8") as f:
                    log_lines = f.readlines()
                last_run = "".join(log_lines[-15:])
            
            su_token(f"\n✅ Verifica completata con successo!\n\nResoconto finale:\n```\n{last_run}\n```")
            return "Verifica completata."
        except Exception as e:
            err_msg = f"\n❌ Errore durante l'esecuzione del controllo: {e}\n"
            su_token(err_msg)
            return err_msg

    # ---------- streaming (risposte in tempo reale) e warm-up ----------

    def chiedi_stream(self, testo, su_token):
        """Come chiedi(), ma trasmette la risposta in tempo reale via su_token(frammento).

        Per i comandi e per i provider cloud, su_token riceve il testo completo in
        una volta. Per Ollama, riceve i token man mano. Restituisce il testo completo.
        """
        speciale = self._gestisci_comando(testo, su_token=su_token)
        if speciale is not None:
            if speciale:
                su_token(speciale)
            return speciale

        # Impara automaticamente qualcosa sull'utente (nome), così ti conosce.
        self._impara_su_utente(testo)

        # Richiesta di CREARE software/bot in linguaggio naturale → generatore
        if self._e_richiesta_software(testo):
            risposta = self.crea_software(testo)
            su_token(risposta)
            return risposta

        # Riaprire un progetto salvato in linguaggio naturale ("riapri il bot di ieri")
        tl = testo.lower().strip()
        if tl.startswith(("riapri ", "riprendi ", "riprendiamo ")):
            risposta = self.riapri_progetto(testo.split(" ", 1)[1].strip())
            su_token(risposta)
            return risposta
        # Avviare il progetto attivo con una frase semplice
        if self.ultimo_progetto and tl in ("avvialo", "avvia", "avvia il progetto",
                                           "fallo partire", "eseguilo", "esegui", "lancialo"):
            _ok, risposta = self._esegui_con_autofix(self.ultimo_progetto)
            su_token(risposta)
            return risposta

        # Se c'è un progetto attivo e l'utente chiede una modifica → aggiorna il progetto
        if self.ultimo_progetto and self._e_richiesta_modifica(testo):
            risposta = self.modifica_software(testo)
            su_token(risposta)
            return risposta

        # INTENTI DIRETTI: richieste concrete sul PC → esegui lo strumento vero,
        # senza lasciar "decidere" al modello (che tende a chiacchierare).
        diretto = self._intento_diretto(testo)
        if diretto is not None:
            su_token(diretto)
            return diretto

        # "APRI <sito>" → apre il sito nel browser (non lo cerca).
        url_apri = self._rileva_apri(testo)
        if url_apri:
            risposta = self.apri_sito(url_apri)
            su_token(risposta)
            return risposta

        # Modalità "CERCA SEMPRE": Mike cerca sul web per QUALSIASI domanda (tranne i saluti).
        if (self.cfg.get("cerca_sempre", False) and self.cfg.get("abilita_ricerca_web", True)
                and not self._e_saluto(testo)):
            return self.ricerca_autonoma(testo, su_token=su_token)

        # Domande che richiedono INFO ATTUALI dal web (meteo, notizie, prezzi, risultati…)
        # → cerca davvero sul web invece di far rispondere il modello a vuoto.
        if self.cfg.get("abilita_ricerca_web", True) and self._serve_ricerca(testo):
            return self.ricerca_autonoma(testo, su_token=su_token)

        # 2) Rilevamento linguaggio naturale per Travelpayouts
        naturale = self._rileva_e_gestisci_naturale(testo, su_token)
        if naturale is not None:
            return naturale

        if not self.pronto():
            msg = ("Nessun cervello attivo: avvia Ollama (gratis, locale) "
                   "oppure metti una chiave Claude/Gemini in config.json.")
            su_token(msg)
            return msg

        # Modalità agentica (stile Claude/ReAct): il modello sceglie ed usa gli strumenti da solo.
        if self.cfg.get("modalita_agente", True):
            try:
                return self._ragiona(testo, su_token)
            except Exception as e:
                self._log(f"(modalità agente non riuscita, uso quella base: {e})")
                # Evita di duplicare il turno utente aggiunto da _ragiona
                if self.cronologia and self.cronologia[-1].get("testo") == testo:
                    self.cronologia.pop()

        contesto_web = ""
        if self._serve_web(testo):
            self._log("Cerco informazioni aggiornate sul web…")
            # Ricerca leggera (snippet) per le chat: veloce. La lettura completa
            # delle pagine è nel comando /ricerca.
            contesto_web = web.cerca_come_testo(testo, numero=4)
        contesto_sistema = ""
        if self._serve_sistema(testo):
            self._log("Guardo cosa sta facendo il PC adesso…")
            istant, _err = live.istantanea()
            if istant:
                contesto_sistema = istant

        self.cronologia.append({"ruolo": "utente", "testo": testo})
        sistema = self._prompt_sistema(contesto_web, contesto_sistema, query=testo)
        storia = self.cronologia[-MAX_STORIA:]

        ordine = [self.cfg["provider_principale"], self.cfg["provider_riserva"]]
        ultimo_errore = None
        for nome in ordine:
            try:
                if nome == "ollama":
                    risposta = ollama.chiedi_stream(
                        self.cfg["modello_ollama"], storia, system=sistema, su_token=su_token)
                else:
                    risposta = self._invoca(nome, sistema)
                    su_token(risposta)  # provider cloud: mostra tutto insieme
                self.cronologia.append({"ruolo": "assistente", "testo": risposta})
                self.cronologia = self.cronologia[-MAX_CRONOLOGIA:]
                if self.cfg["abilita_memoria"]:
                    store.registra_conversazione(testo, risposta, nome)
                return risposta
            except Exception as e:
                ultimo_errore = e
                continue
        msg = f"Ho avuto un problema con tutti i provider. Ultimo errore: {ultimo_errore}"
        su_token(msg)
        return msg

    # ---------- ragionamento agentico (stile Claude) ----------

    def _strumenti_agente(self):
        """Strumenti di SOLA LETTURA che il ragionatore può usare da solo.

        Le azioni che modificano il PC NON sono qui: restano dietro conferma esplicita.
        """
        def _mappa(luogo):
            ris = mappe.geocodifica(luogo, limite=3)
            if not ris:
                return f"Nessun luogo trovato per «{luogo}»."
            r = ris[0]
            return f"{r['nome']}\nCoordinate: {r['lat']}, {r['lon']}"

        def _leggi(percorso):
            testo, err = logs.leggi_file(percorso)
            return testo if testo else (err or "File non leggibile.")

        def _diagnosi():
            rep, err = scanner.esegui_scansione()
            return scanner.riassunto_testo(rep) if rep else (err or "Diagnosi non riuscita.")

        def _crash():
            rep, err = logs.leggi_log_crash()
            return logs.riassunto_log(rep) if rep else (err or "Log non leggibili.")

        def _account():
            rep, err = recupero.analizza_account()
            return recupero.riassunto_account(rep) if rep else (err or "Account non leggibili.")

        return {
            "cerca_web": {"desc": "Cerca informazioni aggiornate su INTERNET (titoli e snippet). argomento=cosa cercare",
                          "param": True, "fn": lambda q: web.cerca_come_testo(q, numero=4)},
            "leggi_pagina": {"desc": "Scarica e legge il contenuto completo di una pagina web da un URL. argomento=URL della pagina",
                             "param": True, "fn": lambda u: web.leggi_pagina(u)},
            "approfondisci": {"desc": "Ricerca approfondita sul web: trova e legge direttamente le pagine dei primi 3 risultati. argomento=query di ricerca",
                              "param": True, "fn": lambda q: web.ricerca_approfondita(q, numero=3)},
            "mappa": {"desc": "Trova un indirizzo o luogo e le sue coordinate. argomento=indirizzo o luogo",
                      "param": True, "fn": _mappa},
            "stato_pc": {"desc": "Legge cosa sta facendo il PC ADESSO (processi attivi, RAM, CPU).",
                         "param": False, "fn": lambda: (live.istantanea()[0] or "Stato non disponibile.")},
            "diagnosi_pc": {"desc": "Scansione diagnostica del PC (dischi, memoria, salute, problemi).",
                            "param": False, "fn": _diagnosi},
            "crash_log": {"desc": "Legge crash, BSOD ed errori recenti di Windows.",
                          "param": False, "fn": _crash},
            "spazio_disco": {"desc": "Analizza dove finisce lo spazio del disco, inclusi i file "
                             "NASCOSTI di sistema (cache aggiornamenti, temp, cestino, component store) "
                             "che non si vedono e non si cancellano a mano. Usalo se il disco è pieno.",
                             "param": False, "fn": lambda: azioni.analizza_spazio_profondo()[1]},
            "account_pc": {"desc": "Analizza gli account Windows e come recuperare l'accesso.",
                           "param": False, "fn": _account},
            "leggi_file": {"desc": "Legge il contenuto di un file o log. argomento=percorso del file",
                           "param": True, "fn": _leggi},
        }

    def _ragiona(self, testo, su_token):
        """Percorso agentico: il modello sceglie ed esegue strumenti, poi risponde."""
        self.cronologia.append({"ruolo": "utente", "testo": testo})
        sistema_base = self._prompt_sistema(query=testo)
        storia = self.cronologia[-MAX_STORIA:]
        rag = Ragionatore(self.cfg, self._strumenti_agente(), log=self._log)
        risposta = rag.esegui(testo, storia, sistema_base, su_token)
        self.cronologia.append({"ruolo": "assistente", "testo": risposta})
        self.cronologia = self.cronologia[-MAX_CRONOLOGIA:]
        if self.cfg["abilita_memoria"]:
            store.registra_conversazione(testo, risposta, "agente")
        return risposta

    # ---------- generatore di software ----------

    def crea_software(self, descrizione):
        """Genera un programma/bot completo e lo scrive su file (avvio con conferma)."""
        if not descrizione:
            return ("Dimmi cosa creare. Esempio:\n"
                    "/crea un bot Telegram che risponde 'ciao' ai messaggi\n"
                    "/crea un programma che rinomina in massa i file di una cartella")
        ok, messaggio, info = builder.crea_progetto(descrizione, self.cfg, log=self._log)
        if not ok:
            return messaggio
        self.ultimo_progetto = info
        try:
            store.registra_progetto(info.get("nome", ""), info.get("cartella", ""),
                                    descrizione, info.get("avvio", ""))
        except Exception:
            pass
        messaggio += "\n\n💡 Puoi migliorarlo: scrivi /modifica <cosa cambiare> (o «aggiungi …»)."
        return messaggio + self._proponi_prossimo_passo(info)

    def leggi_schermo(self, domanda=""):
        """Fa uno screenshot e lo fa "leggere" a Gemini (messaggi d'errore, finestre…)."""
        if not cfg_mod.chiave_valida(self.cfg.get("gemini_api_key", "")):
            return ("Per leggere lo schermo serve la chiave Gemini in config.json "
                    "(gratuita su https://aistudio.google.com/apikey).")
        self._log("Catturo lo schermo…")
        b64, err = schermo.cattura_base64()
        if err:
            return f"Non riesco a catturare lo schermo: {err}"
        prompt = (domanda or "Guarda questo screenshot dello schermo. Dimmi cosa c'è, se ci "
                  "sono errori o problemi, e come risolverli.") + " Rispondi in italiano."
        self._log("Gemini sta leggendo lo schermo…")
        try:
            return "👁️ " + gemini.descrivi_immagine(
                self.cfg["gemini_api_key"], self.cfg["modello_gemini"], b64, prompt, mime="image/png")
        except Exception as e:
            return f"Lettura schermo non riuscita: {e}"

    def _pianifica_da_comando(self, testo):
        """Formato: nome | comando | quando  (es. 'pulizia | Libera Spazio.bat | settimanale lun 09:00')."""
        import re
        parti = [p.strip() for p in testo.split("|")]
        if len(parti) < 2:
            return ("Formato: /pianifica <nome> | <comando o file> | <quando>\n"
                    "Esempi di 'quando': 'giornaliera 09:00', 'settimanale lun 08:00', 'oraria'.\n"
                    "Es.: /pianifica pulizia | \"C:\\Mike AI\\Libera Spazio.bat\" | settimanale lun 09:00")
        nome, comando = parti[0], parti[1]
        quando = parti[2].lower() if len(parti) > 2 else "giornaliera 09:00"
        ora_m = re.search(r"(\d{1,2}:\d{2})", quando)
        ora = ora_m.group(1) if ora_m else "09:00"
        giorni = {"lun": "MON", "mar": "TUE", "mer": "WED", "gio": "THU",
                  "ven": "FRI", "sab": "SAT", "dom": "SUN"}
        giorno = next((v for k, v in giorni.items() if k in quando), None)
        if "orari" in quando:
            freq = "oraria"
        elif "settiman" in quando or giorno:
            freq = "settimanale"
        else:
            freq = "giornaliera"
        ok, msg = scheduler.crea(nome, comando, frequenza=freq, ora=ora, giorno=giorno)
        return msg

    def riapri_progetto(self, termine):
        """Riapre un progetto creato in passato, così puoi modificarlo/avviarlo."""
        p = store.trova_progetto(termine)
        if not p:
            return f"Non trovo un progetto simile a «{termine}». Vedi /progetti per l'elenco."
        cartella = p.get("cartella", "")
        if not os.path.isdir(cartella):
            return f"Il progetto «{p['nome']}» risulta in memoria ma la cartella non c'è più."
        files = []
        for radice, _dirs, fs in os.walk(cartella):
            for f in fs:
                files.append(os.path.relpath(os.path.join(radice, f), cartella).replace(os.sep, "/"))
        self.ultimo_progetto = {"cartella": cartella, "avvio": p.get("avvio", ""),
                                "files": files, "nome": p.get("nome", ""),
                                "descrizione": p.get("descrizione", "")}
        return (f"📂 Riaperto «{p['nome']}»"
                + (f" — {p['descrizione']}" if p.get("descrizione") else "")
                + ".\nOra puoi: /modifica <cosa cambiare>  oppure  «avvialo».")

    def modifica_software(self, richiesta):
        """Modifica/migliora l'ultimo progetto creato."""
        if not richiesta:
            return "Dimmi cosa cambiare. Esempio: /modifica aggiungi un menu iniziale"
        if not self.ultimo_progetto:
            return ("Non c'è un progetto attivo da modificare. Prima crealo con /crea, "
                    "oppure vedi /progetti.")
        ok, messaggio, info = builder.modifica_progetto(
            self.ultimo_progetto, richiesta, self.cfg, log=self._log)
        if ok:
            self.ultimo_progetto = info
            messaggio += self._proponi_prossimo_passo(info)
        return messaggio

    def _proponi_prossimo_passo(self, info):
        """Dopo aver creato/modificato: se servono librerie propone di installarle
        (poi avviare); altrimenti propone direttamente l'avvio. Restituisce testo extra."""
        try:
            libs = builder.dipendenze(info.get("cartella", ""))
        except Exception:
            libs = []
        if libs:
            self.azione_in_sospeso = {
                "descrizione": f"Installare le librerie necessarie ({', '.join(libs)}) e poi avviare",
                "esegui": lambda: self._installa_e_poi_avvia(info),
            }
            return (f"\n\n📦 Questo progetto usa librerie extra: {', '.join(libs)}.\n"
                    "▶️ Vuoi che le installi io (e poi avvii)? Scrivi /conferma  (o /annulla).")
        if info.get("avvio") or any(f.endswith(".py") for f in info.get("files", [])):
            self.azione_in_sospeso = {
                "descrizione": f"Avviare il programma ({info.get('avvio','')})",
                "esegui": lambda: self._esegui_con_autofix(info),
            }
            return "\n\n▶️ Vuoi che lo avvii ora? (se dà errore, lo correggo da solo) /conferma  (o /annulla)."
        return ""

    def _installa_e_poi_avvia(self, info):
        """Installa le librerie (con auto-riparazione) e poi ripropone l'avvio."""
        self._log("Installo le librerie con pip…")
        ok, msg, errore = builder.installa_dipendenze(info.get("cartella", ""), log=self._log)
        if ok:
            return True, self._prepara_avvio(info, msg)

        # I rimedi fissi non sono bastati: Mike LEGGE l'errore e prova una soluzione alternativa.
        ok2, msg2 = self._riparazione_intelligente_pip(errore)
        if ok2:
            return True, self._prepara_avvio(info, msg + "\n\n" + msg2)

        # Non risolvibile in automatico: spiega all'utente cosa fare.
        spiegazione = msg2 or self._spiega_errore_pip(errore)
        if spiegazione:
            msg += "\n\n🩺 " + spiegazione
        return True, msg

    def _prepara_avvio(self, info, msg):
        """Se il progetto è avviabile, imposta l'azione di avvio con auto-correzione."""
        if info.get("avvio") or any(f.endswith(".py") for f in info.get("files", [])):
            self.azione_in_sospeso = {
                "descrizione": f"Avviare il programma ({info.get('avvio','')})",
                "esegui": lambda: self._esegui_con_autofix(info),
            }
            msg += "\n\n▶️ Ora posso avviarlo (e se dà errore lo correggo da solo): /conferma  (o /annulla)."
        return msg

    def _esegui_con_autofix(self, info, tentativi=2):
        """Esegue il programma; se va in errore, legge il traceback, corregge e riprova."""
        for i in range(tentativi + 1):
            self._log("Eseguo il programma…")
            stato, out = builder.esegui_con_diagnostica(info)
            if stato == "ok":
                testo = "✅ Eseguito senza errori."
                if out:
                    testo += f"\n\nOutput:\n{out[:1500]}"
                self.ultimo_progetto = info
                return True, testo
            if stato == "running":
                builder.avvia_progetto(info)  # sembra un programma che gira: lo lancio davvero
                self.ultimo_progetto = info
                return True, "✅ Il programma parte correttamente ed è ora in esecuzione."
            # stato == "errore"
            if i >= tentativi:
                self.ultimo_progetto = info
                return True, ("⚠️ Il programma dà un errore che non sono riuscito a correggere "
                              f"da solo dopo {tentativi} tentativi. Ecco il dettaglio:\n"
                              f"{out[-700:]}\n\nPuoi dirmi tu cosa fare, o /modifica <istruzione>.")
            self._log(f"Errore rilevato: correggo il codice (tentativo {i+1}/{tentativi})…")
            ok, _msg, info = builder.correggi_errore(info, out, self.cfg, log=self._log)
            self.ultimo_progetto = info
            if not ok:
                return True, f"⚠️ Non sono riuscito a correggere l'errore:\n{out[-600:]}"
        return True, "⚠️ Non sono riuscito a farlo funzionare."

    def _riparazione_intelligente_pip(self, errore):
        """Legge l'errore di pip, chiede al modello UNA soluzione alternativa e la prova.

        Sicurezza: esegue SOLO 'pip install <pacchetti>' con nomi validati (nessun
        comando arbitrario, nessun flag di shell).
        """
        import re
        if not errore:
            return False, ""
        valido = re.compile(r"^[A-Za-z0-9_.\-]+([=<>!~]=?[0-9A-Za-z.\-]+)?$")

        # LIVELLO 1 (deterministico, affidabile): se pip elenca le versioni disponibili
        # ("from versions: 1.2, 1.3, …"), riprova con la più recente.
        m_ver = re.search(r"from versions:\s*([0-9][0-9.,\s]*)\)", errore)
        m_pkg = re.search(r"requirement\s+([A-Za-z0-9_.\-]+)", errore)
        if m_ver and m_pkg:
            versioni = [v.strip() for v in m_ver.group(1).split(",") if v.strip()]
            if versioni:
                pkg = f"{m_pkg.group(1)}=={versioni[-1]}"
                if valido.match(pkg):
                    self._log(f"Provo con una versione disponibile: {pkg}…")
                    ok, _o = builder._pip(["install", pkg])
                    if ok:
                        return True, f"✅ Risolto usando una versione compatibile: {pkg}"

        # LIVELLO 2: chiedo al modello un'alternativa
        provider = agent_llm.provider_predefinito(self.cfg)
        if not provider:
            return False, ""
        system = (
            "Sei un esperto di packaging Python. Ti do l'errore di un 'pip install' fallito. "
            "Proponi UN tentativo alternativo per installare la libreria: una VERSIONE diversa, "
            "una libreria EQUIVALENTE, o una wheel precompilata.\n"
            "Rispondi SOLO in JSON:\n"
            '{\"pacchetti\": [\"nome\" o \"nome==versione\"], \"motivo\": \"breve spiegazione\"}\n'
            "Se il problema NON si risolve con pip (serve un compilatore, un pacchetto di sistema "
            "o un'altra versione di Python), rispondi con pacchetti vuoti e spiega nel motivo cosa "
            "deve fare l'utente. Solo nomi pip reali. Nessun testo fuori dal JSON, niente markdown."
        )
        try:
            out = agent_llm.chiedi(self.cfg, provider, system, f"Errore:\n{errore}", max_token=500)
        except Exception:
            return False, ""
        dati = agent_llm.estrai_json(out)
        if not isinstance(dati, dict):
            return False, ""
        motivo = str(dati.get("motivo", "")).strip()
        grezzi = dati.get("pacchetti") or []
        # Validazione severa: solo nomi pacchetto/versione, niente metacaratteri o flag.
        puliti = [p.strip() for p in grezzi if isinstance(p, str) and valido.match(p.strip())]
        if not puliti:
            return False, motivo
        self._log(f"Provo una soluzione alternativa: {', '.join(puliti)}…")
        ok, _out = builder._pip(["install"] + puliti)
        if ok:
            testo = "✅ Risolto con un'alternativa: " + ", ".join(puliti)
            if motivo:
                testo += f"\n({motivo})"
            return True, testo
        return False, motivo

    def _spiega_errore_pip(self, errore):
        """Chiede al modello di spiegare l'errore di pip e cosa fare (in italiano)."""
        if not errore:
            return ""
        provider = agent_llm.provider_predefinito(self.cfg)
        if not provider:
            return ""
        try:
            return agent_llm.chiedi(
                self.cfg, provider,
                "Sei un tecnico Python. Spiega in 2-3 frasi semplici perché questa "
                "installazione pip è fallita e cosa deve fare l'utente per risolvere "
                "(es. installare un compilatore, cambiare versione di Python, un pacchetto "
                "di sistema). In italiano, concreto.",
                f"Errore di pip:\n{errore}", max_token=250)
        except Exception:
            return ""

    def _e_richiesta_software(self, testo):
        """True se l'utente sta chiedendo di CREARE un programma/bot/script."""
        t = testo.lower()
        verbi = ("crea", "creami", "fammi", "fai", "costruisci", "sviluppa", "scrivimi",
                 "scrivi un", "programma", "generami")
        oggetti = ("bot", "programma", "software", "script", "applicazione", "app ",
                   "gioco", "sito ", "tool", "automazione")
        return any(v in t for v in verbi) and any(o in t for o in oggetti)

    def _rileva_intento(self, testo):
        """Riconosce (per parole chiave) cosa vuole l'utente sul PC. Restituisce una
        stringa-intento o None. Solo rilevamento, nessuna azione (così è testabile)."""
        t = " " + testo.lower() + " "

        def a(*chiavi):
            return any(k in t for k in chiavi)

        # domanda teorica ("cos'è la memoria RAM?") → non è un comando, lascia al modello
        if a("cos'è", "cos e", "cosè", "cosa è", "che cos", "come funziona", "differenza tra",
              "significa", "spiegami", "spiega ", "a cosa serve", "che cos'è"):
            return None

        # PULIZIA (azione che modifica)
        if a("libera spazio", "liberare spazio", "libera la memoria", "libera memoria",
              "fai spazio", "pulisci il disco", "pulisci disco", "svuota il disco",
              "pulizia disco", "pulisci la memoria", "pulisci la cache", "libera il disco",
              "pulisci i temp", "pulisci temp", "recupera spazio", "elimina i file inutili"):
            return "pulisci"
        if a("svuota il cestino", "svuota cestino", "pulisci il cestino"):
            return "cestino"

        # PROBLEMI / DIAGNOSI (parole chiave larghe)
        if a("problem", "diagnos", "cosa non va", "non va il pc", "non funziona",
              "è lento", "e lento", "va lento", "lentissimo", "rallenta tutto",
              "check up", "checkup", "controlla il pc", "controlla il computer",
              "controlla il sistema", "verifica il pc", "verifica il computer",
              "verifica pc", "controlla pc", "scansiona il pc", "analizza il pc",
              "stato di salute", "cosa c'è che non va"):
            return "diagnosi"

        # CRASH / BLOCCHI
        if a("crash", "bsod", "schermata blu", "si è bloccato", "si e bloccato",
              "si blocca", "freeze", "si riavvia da solo", "si spegne da solo", "impallato"):
            return "crash"

        # PROCESSI / cosa gira
        if a("cosa gira", "cosa sta girando", "process", "cosa rallenta", "programmi attivi",
              "cosa consuma", "cosa sta facendo il pc", "programmi aperti", "cosa è aperto"):
            return "processi"

        # SCHERMO
        if a("leggi lo schermo", "guarda lo schermo", "leggi schermo", "sullo schermo",
              "cosa vedi", "guarda la schermata", "guarda il monitor", "cosa c'è a schermo"):
            return "schermo"

        # MEMORIA / SPAZIO / DISCO / FILE NASCOSTI
        if a("memoria", "spazio", "disco", "gb liber", "quanto spazio", "occupazione",
              "hard disk", "hd pieno", "ssd", "file nascost", "file inutili", "file grossi",
              "file grandi", "file che occupano", "vedi i file", "mostra i file",
              "trova i file", "trovi i file", "quali file", "file di sistema"):
            return "spazio"

        # STATO veloce
        if a("come va il pc", "come sta il pc", "salute del pc", "stato del pc",
              "stato pc", "va bene il pc", "monitora"):
            return "stato"

        # POSIZIONE (dove mi trovo) — via IP
        if a("dove mi trovo", "dove sono", "la mia posizione", "dove sto",
              "posizione attuale", "in che città sono", "in che citta sono",
              "qual è la mia posizione", "dove siamo", "che città è questa"):
            return "posizione"
        return None

    def _intento_diretto(self, testo):
        """Esegue lo strumento reale per l'intento rilevato (o None)."""
        intento = self._rileva_intento(testo)
        if intento is None:
            return None
        if intento == "pulisci":
            return self._proponi(
                "Eliminare le cache di sistema nascoste e recuperabili (temp, cestino, "
                "cache aggiornamenti, miniature, component store)", azioni.libera_spazio_profondo)
        if intento == "cestino":
            return self._proponi("Svuotare il cestino", azioni.svuota_cestino)
        if intento == "posizione":
            self._log("Rilevo la posizione dall'indirizzo IP…")
            p = mappe.posizione_ip()
            if not p:
                return "Non riesco a rilevare la posizione ora (controlla la connessione internet)."
            return (f"📍 Ti trovi (circa) a: {p['citta']}, {p['regione']}, {p['paese']}\n"
                    f"Coordinate: {p['lat']}, {p['lon']}\n"
                    f"Connessione: {p['provider']}\n"
                    "(È la zona della tua connessione internet, non un GPS preciso.)")
        if intento == "diagnosi":
            return self.diagnosi_pc()
        if intento == "crash":
            return self.analizza_crash()
        if intento == "processi":
            return self.vedi_processi()
        if intento == "schermo":
            return self.leggi_schermo()
        if intento == "spazio":
            self._log("Analizzo la memoria/disco del PC…")
            ok, msg = azioni.analizza_spazio_profondo()
            return msg + "\n\n💡 Per liberarla scrivi: «libera spazio»."
        if intento == "stato":
            testo_s, allarmi = watch.controlla()
            r = f"🔎 STATO PC: {testo_s}"
            r += ("\n\n🔔 " + "\n".join(allarmi)) if allarmi else "\n✅ Tutto nella norma."
            return r
        return None

    def _e_richiesta_modifica(self, testo):
        """True se l'utente chiede di modificare il progetto attivo."""
        t = testo.lower().strip()
        avvii = ("aggiungi", "aggiungici", "modifica", "cambia", "cambiami", "migliora",
                 "correggi", "rendi", "fai in modo", "togli", "rimuovi", "sostituisci",
                 "metti", "fai che")
        return t.startswith(avvii)

    def _impara_su_utente(self, testo):
        """Rileva automaticamente il nome dell'utente da frasi tipo 'mi chiamo X'."""
        import re
        if not self.cfg.get("abilita_memoria", True):
            return
        try:
            if store.carica().get("profilo", {}).get("nome"):
                return  # nome già noto, non insistere
            m = re.search(r"\b(?:mi chiamo|sono|il mio nome (?:è|e))\s+([A-ZÀ-Ýa-zà-ÿ]{2,20})",
                          testo, re.IGNORECASE)
            if m:
                nome = m.group(1).strip().capitalize()
                # evita falsi positivi ("sono stanco", "sono qui"…)
                if nome.lower() not in ("stanco", "qui", "un", "una", "il", "lo", "in", "molto", "sicuro", "pronto", "d"):
                    store.imposta_nome(nome)
                    self._log(f"(mi ricorderò che ti chiami {nome})")
        except Exception:
            pass

    def warmup(self):
        """Carica il modello locale in RAM in anticipo, così la prima risposta è veloce."""
        try:
            if self.cfg.get("provider_principale") == "ollama" and ollama.disponibile():
                ollama.precarica(self.cfg["modello_ollama"])
                return True
        except Exception:
            pass
        return False

    def diagnostica_provider(self):
        """Stato dei provider (per la GUI). Restituisce un dizionario."""
        try:
            import ctypes
            admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            admin = False
        return {
            "ollama": ollama.disponibile(),
            "claude": cfg_mod.chiave_valida(self.cfg.get("claude_api_key", "")),
            "gemini": cfg_mod.chiave_valida(self.cfg.get("gemini_api_key", "")),
            "modello": self.cfg.get("modello_ollama", ""),
            "amministratore": admin,
        }
