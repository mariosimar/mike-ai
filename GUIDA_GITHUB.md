# 🌐 Auto-aggiornamento online di Mike via GitHub (guida in 5 passi)

Con questo, Mike si **aggiorna da solo su ogni PC** prendendo le nuove versioni da
internet. Ho già preparato tutto sul tuo PC (git è inizializzato, le chiavi sono
protette, il manifesto è generato). Ti restano **5 passi facili**, una volta sola.

> 🔒 **Sicurezza già garantita:** il tuo `config.json` con le chiavi API **NON** viene
> mai pubblicato (è nella lista di esclusione). Su GitHub va solo il codice.

---

## 1) Crea un account GitHub (gratis) — se non ce l'hai
Vai su <https://github.com> → **Sign up**. (Devi farlo tu: io non posso creare account.)

## 2) Crea un repository vuoto
- In alto a destra: **+** → **New repository**
- Nome: `mike-ai`
- Scegli **Public** (o Private, ma allora Mike per scaricare avrà bisogno di un token)
- **NON** aggiungere README/gitignore (li abbiamo già)
- Clicca **Create repository**

## 3) Collega il tuo PC al repository (una volta sola)
GitHub ti mostra un indirizzo tipo `https://github.com/TUONOME/mike-ai.git`.
Apri un terminale nella cartella di Mike e scrivi (sostituendo TUONOME):

```
git remote add origin https://github.com/TUONOME/mike-ai.git
git push -u origin main
```

(Ti chiederà di accedere a GitHub la prima volta — è normale.)

## 4) Dì a Mike da dove aggiornarsi
Apri `config.json` e metti (sostituendo TUONOME):

```json
"aggiornamento_sorgente": "https://raw.githubusercontent.com/TUONOME/mike-ai/main/manifesto.json",
```

Salva. Fatto! D'ora in poi, all'avvio Mike controlla se c'è una versione nuova e con
`/aggiorna-mike` la installa (con backup e verifica di sicurezza).

## 5) Come pubblichi un aggiornamento (in futuro)
Ogni volta che migliori Mike, fai **doppio clic su `Pubblica Aggiornamento.bat`**:
scrivi il nuovo numero di versione e lui carica tutto su GitHub. Tutti i PC dove
Mike è installato vedranno l'aggiornamento.

---

### 📦 Per installare Mike su un altro PC da GitHub
Su quel PC (con Python + Ollama installati):
```
git clone https://github.com/TUONOME/mike-ai.git "Mike AI"
```
Poi crea il suo `config.json` (copia da `config.example.json`) e avvia.

---

💡 Se qualcosa non ti torna in uno di questi passi, scrivilo a Mike o a me e ti guido.
