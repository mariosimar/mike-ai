# 🧠 Mike — il tuo assistente AI locale

Mike è un assistente AI che gira **sul tuo computer**, ti mostra un "cervello"
animato sullo schermo, e risponde alle tue domande usando **Claude** e **Gemini**.
Può anche **cercare su internet** e **ricordare** le cose che gli insegni.

---

## ✅ Cosa fa adesso

- 🪟 **Finestra con cervello animato** + chat dove fai domande.
- 🤖 **Risponde usando Claude e Gemini** (con la tua chiave API).
- 🔁 **Fallback automatico**: se Claude non risponde, prova Gemini (o viceversa).
- 🌐 **Ricerca web automatica** quando la domanda riguarda cose attuali.
- 🧩 **Memoria**: ricorda i fatti che gli insegni con `/ricorda`.
- 💾 **Storico**: salva tutte le conversazioni in `dati/conversazioni.log`.
- 🚫 **Zero installazioni extra**: usa solo Python standard.

---

## 🚀 Come avviarlo

### ✨ Interfaccia WEB (consigliata, fluida e moderna)
Doppio clic su **`Avvia Mike WEB.bat`** → si apre nel browser (usa **Chrome o Edge**).
Include: chat in streaming, **mappe con zoom + ricerca indirizzi**, **camera** (opinione
via Gemini), **voce** parla/ascolta, strumenti e indicatori RAM/Disco live.
La vecchia finestra desktop resta su `Avvia Mike.bat`.

### Funziona SUBITO con il cervello locale (Ollama) — nessuna chiave!

Mike usa **Ollama**, l'AI che gira **in locale sul tuo PC**: gratis, senza chiave
API e anche **senza internet**. Basta che Ollama sia avviato.

1. Assicurati che **Ollama** sia in esecuzione (icona vicino all'orologio). Hai già
   diversi modelli installati (es. `hermes3:8b`, `gpt-oss:20b`).
2. Fai **doppio clic su `Avvia Mike.bat`** (o `python avvia.py`).

Fatto: Mike risponde già. Per vedere/cambiare il cervello: comando `/cervello`.

### (Opzionale) Aggiungere Claude o Gemini come riserva

Se vuoi anche un cervello "in cloud" (più potente per certe cose), metti una chiave
in `config.json`:
- **Gemini (Google):** <https://aistudio.google.com/apikey> (gratuita)
- **Claude (Anthropic):** <https://console.anthropic.com> → *API Keys*

Mike usa il **provider principale** e passa alla **riserva** se serve (vedi
`provider_principale` / `provider_riserva` in `config.json`).
⚠️ **Non condividere `config.json`**: contiene le tue chiavi.

---

## 💬 Comandi nella chat

| Comando               | Cosa fa                                                       |
|-----------------------|---------------------------------------------------------------|
**Diagnosi e log**
| Comando | Cosa fa |
|---|---|
| `/diagnosi` | Scansiona il PC, trova i problemi e **salva un report** |
| `/crash` | Analizza crash, BSOD ed errori recenti |
| `/leggi <percorso>` | Fa leggere e analizzare a Mike un file/log |
| `/spazio` | Mostra dove recuperare spazio (file inutili) |

**Accesso / password**
| Comando | Cosa fa |
|---|---|
| `/account` | Analizza gli account e come recuperare l'accesso |
| `/reset-password <ut> <nuova>` | Azzera la password di un account **locale** (serve admin) |
| `/guida-bloccato` | Guida per PC bloccato (non si entra più) |

**Riparazione** (ognuna chiede `/conferma` prima di agire)
| Comando | Cosa fa |
|---|---|
| `/ripara` | Menù delle riparazioni |
| `/pulisci` | Elimina file temporanei |
| `/svuota-cestino` | Svuota il cestino |
| `/flush-dns` | Ripara problemi di rete (cache DNS) |
| `/ripara-file` | Ripara file di sistema corrotti (sfc + DISM, serve admin) |
| `/antivirus [veloce\|completa]` | Scansione con Windows Defender |
| `/programmi` | Elenco programmi installati |
| `/disinstalla <nome>` | Rimuove un programma |
| `/conferma` · `/annulla` | Conferma o annulla l'azione proposta |

**Documenti / account**
| Comando | Cosa fa |
|---|---|
| `/checklist [cliente]` | Crea il modulo di consenso da far firmare (stampabile) |
| `/crea-account <nome> <pwd>` | Crea un account locale di emergenza (serve admin) |
| `/manutenzione` | Fa tutta la pulizia sicura in un colpo (con conferma) |

**Intelligenza / aggiornamento**
| Comando | Cosa fa |
|---|---|
| `/agenti <obiettivo>` | Squadra di agenti che lavorano e si verificano |
| `/migliora` | Mike riflette sul suo lavoro e si auto-migliora |
| `/aggiorna` | Cerca novità su internet e aggiorna le sue conoscenze |
| `/aggiorna-mike` | Scarica e installa una nuova versione di Mike (con backup) |
| `/revisione` | Crea un report del progetto e lo manda a Gemini per un controllo |
| `/cervello [modello]` | Mostra o cambia il modello AI locale in uso |

**Altro**
| Comando | Cosa fa |
|---|---|
| `/ricorda <fatto>` | Insegna un fatto permanente a Mike |
| `/cerca <testo>` | Cerca su internet |
| `/stato` · `/aiuto` | Stato del sistema · elenco comandi |

Tutto il resto è una normale domanda: scrivi e premi Invio.

---

## 🤖 Squadra di agenti

Con `/agenti <obiettivo>` Mike fa lavorare una **squadra di agenti AI**:

1. **Pianifica** → divide l'obiettivo in compiti, uno per agente.
2. **Esegue** → ogni agente svolge il suo compito.
3. **Verifica incrociata** → ogni risultato viene controllato da *un altro* agente (così nessuno si auto-giudica).
4. **Controllo finale di Mike** → Mike unisce tutto e dà il verdetto.

Esempio: `/agenti prepara un piano per pulire e velocizzare un PC Windows lento`

---

## 🩺 Diagnosi del PC (per il lavoro da tecnico)

Con `/diagnosi` Mike scansiona il PC (**solo lettura, non modifica niente**) e un
agente "Tecnico" analizza i risultati e propone le soluzioni in ordine di priorità.

Controlla: sistema operativo, RAM, spazio e **salute fisica dei dischi (SSD/HDD)**,
processi pesanti, programmi all'avvio, errori recenti del registro eventi, rete e
internet, riavvii in sospeso, file temporanei.

> 🔑 **Diritti di amministratore:** la diagnosi di base funziona normalmente. Per
> l'analisi profonda, avvia **come amministratore** (tasto destro → *Esegui come
> amministratore*). Mike usa i permessi quando glieli dai tu — non aggira mai la
> sicurezza di Windows (sarebbe da malware e verrebbe bloccato dagli antivirus).

---

## 🔌 Kit portatile su chiavetta USB

1. Sul TUO PC, doppio clic su **`Crea chiave USB.bat`** e scrivi la lettera della USB (es. `E`).
2. Sulla chiavetta comparirà la cartella **`Mike AI`**.
3. Su **qualsiasi PC Windows**, dalla USB:
   - **`Diagnosi PC.bat`** → fa la diagnosi e salva un report leggibile nella cartella `Report` (**non serve Python, non installa niente**).
   - **`Avvia Mike.bat`** → apre Mike completo (chat + agenti). *Questo richiede Python sul PC.*

I report di diagnosi restano nella cartella `Report` sulla chiavetta: poi puoi
aprire il file `.json` con Mike e scrivere `/diagnosi` per l'analisi automatica.

---

## 🛠️ Crea e migliora software (Mike sviluppatore)

- **Creare:** `/crea un bot Telegram che…` (o scrivilo a parole) → Mike scrive il codice,
  crea la cartella in `progetti/` e ti offre di avviarlo (con `/conferma`).
- **Migliorare passo passo:** subito dopo, scrivi `/modifica aggiungi un menu` (o
  semplicemente «*aggiungi …*», «*cambia …*») → Mike riscrive i file del progetto.
- **Elenco:** `/progetti`.

- **Librerie automatiche:** se il progetto usa pacchetti extra (es. `requests`,
  `python-telegram-bot`), Mike li **rileva e li installa con pip** da solo (con
  `/conferma`), poi avvia. Non devi installare niente a mano.

I file sono scritti solo dentro `progetti/`; installazione ed esecuzione richiedono
sempre `/conferma`. Qualità: per progetti seri usa `/cervello gpt-oss:20b` o una
chiave Claude/Gemini.

---

## 🔄 Auto-aggiornamento online (GitHub)

Mike può aggiornarsi da solo da internet. È già tutto pronto sul tuo PC (git
inizializzato, chiavi protette). Segui **`GUIDA_GITHUB.md`** (5 passi, una volta sola)
e poi pubblichi gli aggiornamenti con **`Pubblica Aggiornamento.bat`**. Le tue chiavi
API non vengono mai pubblicate.

---

## 🤖 Modalità agentica (Mike ragiona come Claude)

Non devi più conoscere i comandi `/`. Scrivi (o parla) in **linguaggio naturale** e
Mike **decide da solo** quali strumenti usare, li esegue e poi ti risponde con i dati
raccolti — esattamente come fa un assistente AI avanzato.

Strumenti che può usare in autonomia (solo lettura, sicuri): ricerca **web**, **mappe**
e indirizzi, **stato del PC** (processi/RAM), **diagnosi**, **crash/log**, **spazio
disco**, **account**, **lettura file**. Le azioni che *modificano* il PC restano dietro
`/conferma`.

Esempi: «*dov'è il Duomo di Milano?*», «*cosa sta rallentando il pc?*», «*ci sono stati
crash ultimamente?*», «*quanto spazio posso liberare?*» → Mike sceglie lo strumento giusto.

- Si attiva/disattiva da `config.json` → `"modalita_agente": true`.
- 💡 Per il massimo dell'intelligenza (scelta strumenti più precisa): `/cervello gpt-oss:20b`.

---

## 🧠 Cervello locale + auto-miglioramento

- **Cervello locale (Ollama):** Mike pensa con un modello che gira sul tuo PC, gratis
  e offline. Cambia modello al volo con `/cervello gpt-oss:20b` (più potente) o
  `/cervello qwen2.5:3b` (più veloce).
- **Auto-miglioramento (`/migliora`):** Mike rilegge le conversazioni recenti, capisce
  cosa può fare meglio e si scrive delle "lezioni" che applica nelle risposte
  successive. È l'auto-miglioramento **vero ma sicuro**: Mike migliora il proprio
  *comportamento*, **non riscrive il proprio codice da solo** (sarebbe pericoloso).
- **Aggiornamento (`/aggiorna`):** cerca novità su internet (es. nuovi modelli AI) e
  aggiorna le sue conoscenze.

> 💡 Perché non lascio che Mike riscriva da solo il suo programma? Perché un software
> che si auto-modifica senza controllo può rompersi o comportarsi in modi imprevisti
> — anche i laboratori AI più avanzati lo fanno solo in ambienti isolati. La via giusta
> è quella di Mike: impara e si aggiorna, sotto il tuo controllo.

---

## 🔄 Auto-aggiornamento del codice (`/aggiorna-mike`)

Mike può **scaricare e installarsi da solo** una nuova versione, in modo **sicuro**:
fa un **backup** prima di toccare i file, e se il nuovo codice ha un errore **ripristina
automaticamente** la versione precedente (rollback). Niente viene rotto.

**Da dove prende gli aggiornamenti?** Da una sorgente che decidi tu, in `config.json`
→ `"aggiornamento_sorgente"`:
- 📁 una **cartella / chiavetta / cartella di rete** (es. `D:\\MikeMaster\\manifesto.json`) — funziona anche **offline**
- 🌐 un **link internet** (es. GitHub o un tuo sito) → `https://.../manifesto.json`

**Come pubblichi un aggiornamento** (dalla tua copia "master" di Mike):
1. Modifichi/migliori Mike.
2. Esegui: `python crea_manifesto.py 0.5.1 "cosa hai cambiato"`
3. Copi la cartella di Mike (con `manifesto.json`) nella sorgente.
4. Sui PC dei clienti, Mike all'avvio **avvisa** se c'è una versione nuova; con
   `/aggiorna-mike` la installa (con backup).

> 🔒 Perché è sicuro: Mike **non esegue** il codice nuovo da solo — sostituisce i
> file, verifica che siano validi, e poi **tu riavvii**. Con backup e ripristino
> automatico, nel peggiore dei casi torni com'eri.

**🔐 Protezione anti-manomissione (hash SHA-256):** il manifesto contiene l'"impronta
digitale" di ogni file. Durante il download Mike ricalcola l'impronta e, se anche un
solo byte è diverso (file corrotto o manomesso), **rifiuta l'aggiornamento senza
toccare niente**. Così nessuno può infilare codice malevolo al posto di un file.

---

## 🗂️ Modulo di consenso cliente (`/checklist`)

Crea un **modulo stampabile** (si apre nel browser, premi Ctrl+P) con: dati cliente,
testo di **consenso**, lista degli **interventi** con caselle, e spazi per le **firme**.
Da far firmare al cliente *prima* di operare — ti tutela legalmente e fa ordine.

---

## 🆘 Account locale di emergenza (`/crea-account`)

Quando il cliente ha dimenticato la password **e** ha perso anche l'accesso alla mail
dell'account Microsoft, puoi creare al volo un **account locale amministratore** per
rientrare in Windows e recuperare i dati:

```
/crea-account TecnicoTemp PasswordForte123
```

(Richiede di avviare Mike come amministratore. Sempre con `/conferma`.)

---

## 🎤 Comando vocale

- **🎤 (pulsante)**: premi e parla — Mike trascrive e risponde.
- **🔊 Mike parla**: attiva l'interruttore e Mike legge le risposte ad alta voce
  (con la voce italiana di Windows, se installata — su questo PC c'è "Elsa").

> Il parlato (Mike che legge) funziona quasi sempre. L'ascolto (tu che parli)
> richiede il **riconoscimento vocale** della lingua installato in Windows
> (*Impostazioni → Ora e lingua → Voce*). Se non c'è, scrivi pure la domanda.

---

## 🩺 Analisi crash e file

- `/crash` → Mike legge gli eventi di crash, i BSOD, gli errori di sistema e delle
  applicazioni degli ultimi 7 giorni, i dump e le segnalazioni, poi un agente
  "Tecnico" individua le cause e propone le soluzioni.
- `/leggi C:\percorso\file.log` → Mike legge un file che gli indichi (log, config,
  ecc.) e te lo analizza.

---

## 🛠️ Riparazione e pulizia (sempre con conferma)

Ogni azione che **modifica** il PC viene prima *proposta*: Mike spiega cosa farà e
tu scrivi **`/conferma`** (o **`/annulla`**). Niente viene toccato senza il tuo OK.

Incluso: pulizia file temporanei, svuota cestino, flush DNS, riparazione file di
sistema (`sfc` + `DISM`), scansione **Windows Defender**, elenco e **disinstallazione**
programmi. Le azioni che richiedono privilegi di amministratore te lo dicono (avvia
Mike come amministratore quando serve).

---

## 🔐 Recupero accesso / password dimenticata (per il tecnico)

Quando un cliente **non ricorda la password di Windows**, l'approccio giusto è
**azzerarla** (reset), non "scoprirla". Non serve la vecchia password.

Comando `/account` → Mike legge gli account (sola lettura) e ti dice **esattamente
cosa fare**, perché il metodo cambia a seconda del tipo di account:

- 🔵 **Account Microsoft** (email): si reimposta SOLO online su
  <https://account.live.com/password/reset> (serve la mail/telefono di recupero del cliente). *Non si resetta sul PC.*
- 🟢 **Account locale**, PC **acceso** e tu admin: `/reset-password <utente> <nuova>`
  (o a mano: `net user <utente> <nuova>`).
- 🟢 **Account locale**, PC **bloccato**: `/guida-bloccato` → passi per il reset
  da chiavetta di ripristino di Windows.

> ⚠️ **BitLocker / EFS:** se il disco è cifrato con BitLocker, **procurati prima la
> chiave di ripristino** (su <https://account.microsoft.com/devices> del cliente),
> altrimenti dopo il reset i dati restano illeggibili. Mike ti avvisa se rileva BitLocker.

> ⚖️ **Solo con consenso:** usa queste funzioni solo sui PC del cliente, con la sua
> autorizzazione. Mike **non estrae e non cracca** password (sarebbe illegale e
> inutile): fa solo il **reset** per far rientrare il legittimo proprietario.

I report di `/diagnosi` e `/account` vengono salvati automaticamente in
`dati/Report/` (un file di testo per ogni cliente, con data e nome del PC), così
puoi consegnarli o archiviarli.

---

## 🍎 Funziona su Mac?

**In parte.** Mike è nato su Windows, quindi:

✅ **Funziona su Mac** (serve Python + Ollama installati):
- il cervello AI (Ollama locale, Claude, Gemini), la chat e la **finestra**
- gli **agenti** e la verifica incrociata
- **memoria**, **auto-miglioramento** (`/migliora`), ricerca web
- **auto-aggiornamento** del codice (con hash di sicurezza)

❌ **Non funziona su Mac (per ora)** — usano comandi di **Windows**:
- diagnosi PC, analisi crash/log, riparazione (`sfc`/DISM), antivirus Defender
- recupero/reset password, account di emergenza
- la voce (usa il sistema vocale di Windows; il Mac ha `say`)
- i file `.bat`

In pratica: su Mac hai **l'assistente AI completo**, ma non gli **strumenti da tecnico
Windows**. Quelli sono legati ai comandi di Windows.

> 👉 Se lavori anche su **Mac come tecnico**, posso aggiungere le versioni macOS degli
> strumenti (diagnosi con `system_profiler`/`diskutil`, log con `log show`, voce con
> `say`, gestione utenti con `dscl`). Dimmelo e li costruisco.

---

## ⚙️ Personalizzazione (`config.json`)

- `provider_principale` / `provider_riserva`: `"claude"` o `"gemini"`.
- `modello_claude`: es. `claude-sonnet-4-6` (più economico) o `claude-opus-4-8` (più potente).
- `modello_gemini`: es. `gemini-2.0-flash`.
- `nome_assistente`: cambia "Mike" con il nome che preferisci.
- `lingua`: la lingua in cui Mike risponde.
- `abilita_ricerca_web` / `abilita_memoria`: `true` o `false`.

---

## 🧱 Com'è fatto (struttura)

```
Mike AI/
├─ Avvia Mike.bat        ← doppio clic per partire
├─ avvia.py              ← avvio da terminale
├─ config.json           ← le TUE chiavi e impostazioni
├─ README.md             ← questo file
├─ mike/
│  ├─ brain.py           ← il cervello: decide e orchestra
│  ├─ gui.py             ← la finestra con il cervello animato
│  ├─ config.py          ← legge la configurazione
│  ├─ providers/         ← connettori a Claude e Gemini
│  ├─ tools/web.py       ← ricerca su internet
│  └─ memory/store.py    ← memoria e diario
└─ dati/                 ← memoria salvata + storico conversazioni
```

---

## 🌱 Sull'"auto-miglioramento"

Mike **impara in modo sicuro**: accumula in memoria i fatti che gli insegni e
tiene uno storico delle conversazioni. Questa è la forma realistica e sicura di
"migliorarsi".

L'idea di un'AI che **riscrive il proprio codice da sola, senza controllo**
(auto-miglioramento ricorsivo) è affascinante ma **rischiosa**: un programma che
si modifica da solo può rompersi o comportarsi in modi imprevisti. Per questo qui
non è attiva. Se vorrai, in futuro possiamo aggiungere — passo dopo passo e sotto
il tuo controllo — funzioni più avanzate (compiti automatici programmati, lettura
di documenti, comando vocale, ecc.).

---

## ❓ Problemi comuni

- **"Non ho nessuna chiave configurata"** → non hai ancora incollato la chiave in `config.json`.
- **La finestra non si apre** → assicurati di avviare con `python avvia.py` dalla cartella `Mike AI`.
- **Errore "codice 401" da Claude/Gemini** → la chiave è sbagliata o scaduta.
- **Errore di connessione** → controlla internet / firewall.
```
