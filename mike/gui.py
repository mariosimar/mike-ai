"""Interfaccia grafica di Mike — «COGNITIVE NEURAL LINK» (HUD olografico).

Dashboard sci-fi con:
- HEADER HUD animato: reattore ad anelli rotanti (stile Jarvis), strumenti radiali
  LIVE che mostrano RAM e Disco reali del PC, titolo con glow e scanline;
- risposte in STREAMING in tempo reale (token per token);
- rete neurale animata a fisica vettoriale nel pannello destro;
- stato provider e warm-up del modello in BACKGROUND (la GUI non si blocca mai);
- comunicazione thread→GUI solo tramite coda thread-safe (Tkinter-safe).
"""
import ctypes
import json
import math
import os
import queue
import random
import shutil
import sys
import threading
import tkinter as tk
from tkinter import scrolledtext, simpledialog, filedialog, messagebox

from .brain import Mike
from .voce import voce
from .config import RADICE

# --- Palette olografica ---
SFONDO = "#05070f"        # Quasi nero spaziale
PANNELLO = "#070b16"      # CRT black
HEADER_BG = "#080d1c"
TESTO = "#cdd6e6"
ACCENTO = "#00e5ff"       # Cyan
VIOLA = "#c850ff"         # Magenta
VERDE = "#39ff14"
ROSSO = "#ff2d6e"
GIALLO = "#ffc400"
GRIGIO = "#16203a"
PULSANTE = "#0e1730"

MONO = "Consolas" if sys.platform.startswith("win") else ("Menlo" if sys.platform == "darwin" else "DejaVu Sans Mono")


# ---------- lettura statistiche di sistema (veloce, senza subprocess) ----------

class _MEMSTAT(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


def ram_percento():
    try:
        s = _MEMSTAT()
        s.dwLength = ctypes.sizeof(s)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))
        return float(s.dwMemoryLoad)
    except Exception:
        return 0.0


def disco_percento():
    try:
        drive = os.environ.get("SystemDrive", "C:") + "\\"
        u = shutil.disk_usage(drive)
        return u.used / u.total * 100.0
    except Exception:
        return 0.0


class FinestraMike:
    def __init__(self):
        self.mike = Mike()
        self.coda = queue.Queue()
        self.fase = 0.0
        self.scan_x = 0
        self.sta_pensando = False
        self.tick = 0

        # Valori strumenti (animati verso il target reale)
        self.gauge = {"ram": 0.0, "disk": 0.0, "neural": 0.0}
        self.gauge_target = {"ram": 0.0, "disk": 0.0, "neural": 12.0}
        self.onda = [0.0] * 40  # waveform

        # Rete neurale (pannello destro)
        self.nodi = []
        for _ in range(15):
            self.nodi.append({
                "x": random.randint(20, 300), "y": random.randint(20, 110),
                "vx": random.uniform(-0.8, 0.8), "vy": random.uniform(-0.8, 0.8),
                "colore": random.choice([ACCENTO, VIOLA, VERDE]),
            })

        self.mike.progresso = lambda s: self.coda.put(("progresso", s))

        self.root = tk.Tk()
        self.root.title(f"{self.mike.cfg['nome_assistente']} — COGNITIVE NEURAL LINK v{self._versione()}")
        self.root.geometry("1000x740")
        self.root.minsize(860, 620)
        self.root.configure(bg=SFONDO)

        self._costruisci_menu()
        self._costruisci_interfaccia()

        self._anima()
        self.root.after(60, self._controlla_coda)

        self._scrivi_chat(self.mike.cfg["nome_assistente"],
                          "SISTEMA OPERATIVO COGNITIVO AVVIATO.\n"
                          "Benvenuto operatore. Cervello locale Ollama + riserva cloud.\n"
                          "Usa i pannelli a destra o digita una domanda. Le risposte arrivano in tempo reale.",
                          ACCENTO)

        self._refresh_stato_async()
        threading.Thread(target=self.mike.warmup, daemon=True).start()
        self.root.after(300, self._controllo_aggiornamento)

    # ---------- util ----------

    def _versione(self):
        try:
            p = os.path.join(RADICE, "version.json")
            if os.path.exists(p):
                with open(p, encoding="utf-8") as f:
                    return json.load(f).get("versione", "1.0.0")
        except Exception:
            pass
        return "1.0.0"

    def _controllo_aggiornamento(self):
        def lavora():
            try:
                avviso = self.mike.controllo_aggiornamento_avvio()
            except Exception:
                avviso = None
            if avviso:
                self.coda.put(("sistema", avviso))
        threading.Thread(target=lavora, daemon=True).start()

    # ---------- menu ----------

    def _menu(self, parent):
        return tk.Menu(parent, tearoff=0, bg=SFONDO, fg=ACCENTO,
                       activebackground=ACCENTO, activeforeground="black", bd=0)

    def _costruisci_menu(self):
        menubar = tk.Menu(self.root, bg=SFONDO, fg=ACCENTO,
                          activebackground=ACCENTO, activeforeground="black", bd=0)

        m = self._menu(menubar)
        m.add_command(label="Apri cartella Report", command=self._apri_cartella_report)
        m.add_command(label="Azzera sessione (log)", command=self._reset_chat)
        m.add_separator()
        m.add_command(label="Esci", command=self.root.quit)
        menubar.add_cascade(label="Connessione", menu=m)

        m = self._menu(menubar)
        m.add_command(label="Scansione diagnostica PC", command=lambda: self._comando("/diagnosi"))
        m.add_command(label="Analizza crash & BSOD", command=lambda: self._comando("/crash"))
        m.add_command(label="Mappa spazio disco", command=lambda: self._comando("/spazio"))
        m.add_command(label="Checklist consenso…", command=self._click_checklist)
        m.add_separator()
        m.add_command(label="Pulizia file temp", command=lambda: self._comando("/pulisci"))
        m.add_command(label="Flush DNS", command=lambda: self._comando("/flush-dns"))
        m.add_command(label="Scansione antivirus", command=lambda: self._comando("/antivirus veloce"))
        menubar.add_cascade(label="Scansioni & Pulizia", menu=m)

        m = self._menu(menubar)
        m.add_command(label="Auto-miglioramento", command=lambda: self._comando("/migliora"))
        m.add_command(label="Aggiorna conoscenze (web)", command=lambda: self._comando("/aggiorna"))
        m.add_command(label="Report revisione", command=lambda: self._comando("/revisione"))
        m.add_command(label="Cambia modello locale…", command=self._click_cambia_cervello)
        m.add_command(label="Aggiorna Mike (firmware)", command=lambda: self._comando("/aggiorna-mike"))
        menubar.add_cascade(label="Neural Core", menu=m)

        m = self._menu(menubar)
        m.add_command(label="Comandi (/aiuto)", command=lambda: self._comando("/aiuto"))
        m.add_command(label="Guida PC bloccato", command=lambda: self._comando("/guida-bloccato"))
        m.add_separator()
        m.add_command(label="Informazioni", command=self._click_informazioni)
        menubar.add_cascade(label="Info", menu=m)

        self.root.config(menu=menubar)

    # ---------- interfaccia ----------

    def _costruisci_interfaccia(self):
        # === HEADER HUD animato (a tutta larghezza) ===
        self.header = tk.Canvas(self.root, height=132, bg=HEADER_BG, highlightthickness=0)
        self.header.pack(fill="x", side="top")

        cont = tk.Frame(self.root, bg=SFONDO)
        cont.pack(fill="both", expand=True, padx=8, pady=(6, 0))

        # --- sinistra: chat + input ---
        left = tk.Frame(cont, bg=SFONDO)
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        bv = tk.Frame(left, bg=SFONDO)
        bv.pack(fill="x", pady=(0, 6))
        self.voce_attiva = tk.BooleanVar(value=False)
        tk.Checkbutton(bv, text="🔊 SINTESI VOCALE (Mike legge le risposte)",
                       variable=self.voce_attiva, bg=SFONDO, fg=ACCENTO,
                       activebackground=SFONDO, activeforeground=TESTO, selectcolor=PANNELLO,
                       font=(MONO, 9, "bold"), bd=0, highlightthickness=0).pack(side="left")

        cf = tk.Frame(left, bg=ACCENTO)  # bordo glow
        cf.pack(fill="both", expand=True)
        inner = tk.Frame(cf, bg=ACCENTO)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        self.chat = scrolledtext.ScrolledText(
            inner, bg=PANNELLO, fg=TESTO, wrap="word", state="disabled",
            font=(MONO, 11), bd=0, padx=14, pady=12, insertbackground=ACCENTO)
        self.chat.pack(fill="both", expand=True)
        self.chat.tag_configure("corpo", foreground=TESTO, font=(MONO, 11))

        riga = tk.Frame(left, bg=SFONDO)
        riga.pack(fill="x", pady=(8, 8))
        ib = tk.Frame(riga, bg=ACCENTO)
        ib.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.input = tk.Entry(ib, bg=PANNELLO, fg="white", font=(MONO, 11, "bold"),
                              insertbackground=ACCENTO, bd=0)
        self.input.pack(fill="x", ipady=9, padx=1, pady=1)
        self.input.bind("<Return>", lambda e: self._invia())
        self.input.focus()

        self.bottone_mic = self._bottone(riga, "🎤 VOICE", self._ascolta, GRIGIO, ACCENTO)
        self.bottone_mic.pack(side="left", padx=(0, 6))
        self.bottone = self._bottone(riga, "  EXECUTE ▸ ", self._invia, VIOLA, "white", ACCENTO)
        self.bottone.pack(side="right")

        # --- destra: core neurale + toolkit ---
        right = tk.Frame(cont, bg=SFONDO, width=352)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        core = tk.LabelFrame(right, text=" ◢ NEURAL NETWORK ◣ ", bg=SFONDO, fg=VIOLA,
                             relief="flat", bd=0, highlightbackground=VIOLA, highlightthickness=1,
                             font=(MONO, 9, "bold"))
        core.pack(fill="x", pady=(0, 8), ipady=3)
        self.tela = tk.Canvas(core, width=332, height=128, bg="black", highlightthickness=0)
        self.tela.pack(padx=6, pady=4)

        tools = tk.LabelFrame(right, text=" ◢ QUANTUM TOOLKIT ◣ ", bg=SFONDO, fg=ACCENTO,
                              relief="flat", bd=0, highlightbackground=ACCENTO, highlightthickness=1,
                              font=(MONO, 9, "bold"))
        tools.pack(fill="both", expand=True)

        tabs = tk.Frame(tools, bg=SFONDO)
        tabs.pack(fill="x", pady=4, padx=4)
        self.tab_container = tk.Frame(tools, bg=SFONDO)
        self.tab_container.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        self.tab_diagnosi = tk.Frame(self.tab_container, bg=SFONDO)
        self.tab_ripara = tk.Frame(self.tab_container, bg=SFONDO)
        self.tab_ai = tk.Frame(self.tab_container, bg=SFONDO)
        self.tab_frames = [self.tab_diagnosi, self.tab_ripara, self.tab_ai]
        self.tab_buttons = []
        for idx, nome in enumerate(["🩺 DIAGNOSI", "🛠️ RIPARA", "🧠 NEURAL"]):
            b = tk.Button(tabs, text=nome, command=lambda i=idx: self._mostra_tab(i),
                          bg=GRIGIO, fg=ACCENTO, font=(MONO, 8, "bold"), bd=0,
                          activebackground=ACCENTO, activeforeground="black", cursor="hand2", pady=4)
            b.pack(side="left", fill="x", expand=True, padx=1)
            self.tab_buttons.append(b)

        D = self.tab_diagnosi
        self._tool(D, "🩺 Scansione diagnostica PC", lambda: self._comando("/diagnosi"))
        self._tool(D, "📑 Analizza crash & BSOD", lambda: self._comando("/crash"))
        self._tool(D, "💾 Mappa storage & spazio", lambda: self._comando("/spazio"))
        self._tool(D, "👥 Account & privilegi", lambda: self._comando("/account"))
        self._tool(D, "📂 Analizza file/log esterno…", self._click_leggi_file)

        R = self.tab_ripara
        self._tool(R, "✨ Manutenzione completa", lambda: self._comando("/manutenzione"))
        self._tool(R, "🧹 Pulisci file temporanei", lambda: self._comando("/pulisci"))
        self._tool(R, "🗑️ Svuota cestino", lambda: self._comando("/svuota-cestino"))
        self._tool(R, "🌐 Flush DNS (rete)", lambda: self._comando("/flush-dns"))
        self._tool(R, "🛡️ Antivirus (Defender)", lambda: self._comando("/antivirus veloce"))
        self._tool(R, "⚙️ Ripara file sistema (SFC)", lambda: self._comando("/ripara-file"))
        self._tool(R, "❌ Disinstalla programma…", self._click_disinstalla)

        A = self.tab_ai
        self._tool(A, "🌱 Auto-miglioramento", lambda: self._comando("/migliora"))
        self._tool(A, "🌐 Aggiorna conoscenze (web)", lambda: self._comando("/aggiorna"))
        self._tool(A, "📋 Report per revisione", lambda: self._comando("/revisione"))
        self._tool(A, "📝 Checklist consenso…", self._click_checklist)
        self._tool(A, "🆕 Crea admin emergenza…", self._click_crea_account)
        self._tool(A, "🔑 Reset password locale…", self._click_reset_password)
        self._tool(A, "💿 Aggiorna Mike (firmware)", lambda: self._comando("/aggiorna-mike"))
        self._tool(A, "🆘 Guida PC bloccato", lambda: self._comando("/guida-bloccato"))

        self._mostra_tab(0)

        # --- barra di stato ---
        barra = tk.Frame(self.root, bg=SFONDO, highlightbackground=ACCENTO, highlightthickness=1)
        barra.pack(side="bottom", fill="x")
        self.stato_msg = tk.Label(barra, text=" 📡 CORE READY | LINK STABLE", bg=SFONDO, fg=ACCENTO,
                                  font=(MONO, 8, "bold"), anchor="w")
        self.stato_msg.pack(side="left", fill="x", expand=True, padx=2, pady=2)
        self.stato_ai = tk.Label(barra, text="OLLAMA: …  CLAUDE: …  GEMINI: …", bg=SFONDO, fg=VIOLA,
                                 font=(MONO, 8, "bold"), anchor="e")
        self.stato_ai.pack(side="right", padx=8, pady=2)

    def _bottone(self, parent, testo, comando, bg, fg, hover=ACCENTO):
        b = tk.Button(parent, text=testo, command=comando, bg=bg, fg=fg, font=(MONO, 9, "bold"),
                      bd=0, highlightthickness=1, highlightbackground=bg,
                      activebackground=hover, activeforeground="black", padx=16, pady=5, cursor="hand2")
        b.bind("<Enter>", lambda e: b.config(bg=hover, fg="black"))
        b.bind("<Leave>", lambda e: b.config(bg=bg, fg=fg))
        return b

    def _tool(self, parent, testo, comando):
        b = tk.Button(parent, text=testo, command=comando, bg=PULSANTE, fg=ACCENTO, relief="flat",
                      bd=0, highlightbackground=ACCENTO, highlightthickness=1,
                      activebackground=ACCENTO, activeforeground="black",
                      font=(MONO, 9, "bold"), anchor="w", padx=12, pady=6, cursor="hand2")
        b.bind("<Enter>", lambda e: b.config(bg=ACCENTO, fg="black"))
        b.bind("<Leave>", lambda e: b.config(bg=PULSANTE, fg=ACCENTO))
        b.pack(fill="x", pady=3, padx=4)
        return b

    def _mostra_tab(self, indice):
        for i, b in enumerate(self.tab_buttons):
            b.config(bg=ACCENTO if i == indice else GRIGIO, fg="black" if i == indice else ACCENTO)
        for i, f in enumerate(self.tab_frames):
            (f.pack(fill="both", expand=True) if i == indice else f.pack_forget())

    # ---------- disegno HUD ----------

    def _arc_gauge(self, c, cx, cy, r, perc, etichetta, colore):
        """Strumento radiale: anello di sfondo + arco proporzionale + valore."""
        x0, y0, x1, y1 = cx - r, cy - r, cx + r, cy + r
        c.create_oval(x0, y0, x1, y1, outline="#13203a", width=7)
        estensione = -(270.0 * max(0.0, min(100.0, perc)) / 100.0)
        if estensione < 0:
            c.create_arc(x0, y0, x1, y1, start=225, extent=estensione,
                         style="arc", outline=colore, width=7)
        # puntino luminoso alla fine dell'arco
        ang = math.radians(225 + estensione)
        px, py = cx + math.cos(ang) * r, cy - math.sin(ang) * r
        c.create_oval(px-4, py-4, px+4, py+4, fill="white", outline=colore)
        c.create_text(cx, cy-4, text=f"{int(perc)}%", fill="white", font=(MONO, 12, "bold"))
        c.create_text(cx, cy+12, text=etichetta, fill=colore, font=(MONO, 7, "bold"))

    def _reattore(self, c, cx, cy):
        """Reattore ad anelli rotanti (stile arc-reactor)."""
        attivo = self.sta_pensando
        for k in range(3):
            r = 20 + k * 9
            estensione = 90 + k * 40
            start = (self.fase * (40 + k * 25) * (2.2 if attivo else 1.0)) % 360
            col = ACCENTO if k % 2 == 0 else VIOLA
            c.create_arc(cx-r, cy-r, cx+r, cy+r, start=start, extent=estensione,
                         style="arc", outline=col, width=3)
            c.create_arc(cx-r, cy-r, cx+r, cy+r, start=start+180, extent=estensione,
                         style="arc", outline=col, width=3)
        battito = math.sin(self.fase * (3.0 if attivo else 1.2))
        rc = 12 + battito * (4 if attivo else 2)
        for g in range(3):
            rr = rc + g * 4
            c.create_oval(cx-rr, cy-rr, cx+rr, cy+rr, outline=ACCENTO, width=1)
        c.create_oval(cx-rc, cy-rc, cx+rc, cy+rc, fill=ACCENTO if attivo else VIOLA, outline="white", width=2)

    def _glow_text(self, c, x, y, testo, colore, font, anchor="w"):
        """Testo con alone (neon) disegnandolo più volte sfumato."""
        for dx, dy, col in ((1, 1, "#0a3b52"), (-1, 0, "#0a3b52"), (0, -1, "#0a3b52")):
            c.create_text(x+dx, y+dy, text=testo, fill=col, font=font, anchor=anchor)
        c.create_text(x, y, text=testo, fill=colore, font=font, anchor=anchor)

    def _anima(self):
        # --- HEADER HUD ---
        h = self.header
        h.delete("all")
        W = h.winfo_width() or 1000
        H = 132
        self.fase += 0.06
        self.tick += 1

        # griglia di sfondo
        for x in range(0, W, 26):
            h.create_line(x, 0, x, H, fill="#0b1426", width=1)
        for y in range(0, H, 26):
            h.create_line(0, y, W, y, fill="#0b1426", width=1)

        # reattore a sinistra
        self._reattore(h, 66, H // 2)

        # titolo con glow
        self._glow_text(h, 130, 44, "M . I . K . E .", ACCENTO, (MONO, 26, "bold"))
        self._glow_text(h, 132, 78, f"COGNITIVE NEURAL LINK  ·  v{self._versione()}", VIOLA, (MONO, 10, "bold"))
        stato = "◉ ELABORAZIONE COGNITIVA…" if self.sta_pensando else "◉ SISTEMA ONLINE · PRONTO"
        h.create_text(132, 100, text=stato, fill=GIALLO if self.sta_pensando else VERDE,
                      font=(MONO, 9, "bold"), anchor="w")

        # aggiorna i target degli strumenti ogni ~1s
        if self.tick % 18 == 0:
            self.gauge_target["ram"] = ram_percento()
            self.gauge_target["disk"] = disco_percento()
            self.gauge_target["neural"] = 92.0 if self.sta_pensando else 10.0 + (self.fase * 7) % 12
        for k in self.gauge:
            self.gauge[k] += (self.gauge_target[k] - self.gauge[k]) * 0.12

        # tre strumenti radiali a destra (se c'è spazio)
        if W > 560:
            base = W - 250
            self._arc_gauge(h, base, H // 2, 34, self.gauge["ram"], "RAM", ACCENTO)
            self._arc_gauge(h, base + 90, H // 2, 34, self.gauge["disk"], "DISCO", VIOLA)
            self._arc_gauge(h, base + 180, H // 2, 34, self.gauge["neural"], "NEURAL", VERDE)

        # scanline orizzontale
        self.scan_x = (self.scan_x + 6) % W
        h.create_line(self.scan_x, 0, self.scan_x, H, fill="#10406a", width=2)
        h.create_line(0, H-1, W, H-1, fill=ACCENTO, width=1)

        # --- rete neurale (pannello destro) ---
        self._anima_rete()

        self.root.after(40, self._anima)

    def _anima_rete(self):
        c = self.tela
        c.delete("all")
        W, H = 332, 128
        for x in range(0, W, 22):
            c.create_line(x, 0, x, H, fill="#0a1830", width=1)
        for y in range(0, H, 22):
            c.create_line(0, y, W, y, fill="#0a1830", width=1)
        mult = 2.3 if self.sta_pensando else 1.0
        for i, n1 in enumerate(self.nodi):
            n1["x"] += n1["vx"] * mult
            n1["y"] += n1["vy"] * mult
            if n1["x"] < 10 or n1["x"] > W-10:
                n1["vx"] *= -1
            if n1["y"] < 10 or n1["y"] > H-10:
                n1["vy"] *= -1
            for n2 in self.nodi[i+1:]:
                d = math.hypot(n1["x"]-n2["x"], n1["y"]-n2["y"])
                if d < 66:
                    v = int(255 * (1.0 - d/66))
                    c.create_line(n1["x"], n1["y"], n2["x"], n2["y"],
                                  fill=f"#00{int(v*0.8):02x}{int(v*0.9):02x}", width=1)
        for n in self.nodi:
            c.create_oval(n["x"]-4, n["y"]-4, n["x"]+4, n["y"]+4, fill=n["colore"], outline="#ffffff")

    # ---------- chat / streaming ----------

    def _scrivi_chat(self, chi, testo, colore):
        self.chat.configure(state="normal")
        tag = f"tag_{chi}"
        self.chat.tag_configure(tag, foreground=colore, font=(MONO, 10, "bold"))
        self.chat.insert("end", f"[{chi.upper()}] ▸ ", tag)
        self.chat.insert("end", f"{testo}\n\n", "corpo")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def _prefisso_risposta(self):
        self.chat.configure(state="normal")
        tag = f"tag_{self.mike.cfg['nome_assistente']}"
        self.chat.tag_configure(tag, foreground=VIOLA, font=(MONO, 10, "bold"))
        self.chat.insert("end", f"[{self.mike.cfg['nome_assistente'].upper()}] ▸ ", tag)
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def _aggiungi_token(self, frammento):
        self.chat.configure(state="normal")
        self.chat.insert("end", frammento, "corpo")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def _fine_risposta(self):
        self.chat.configure(state="normal")
        self.chat.insert("end", "\n\n", "corpo")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    # ---------- invio / lavoro ----------

    def _invia(self):
        testo = self.input.get().strip()
        if not testo or self.sta_pensando:
            return
        self.input.delete(0, "end")
        self._avvia_lavoro(testo, testo)

    def _comando(self, comando):
        if self.sta_pensando:
            return
        self._avvia_lavoro(comando, comando)

    def _avvia_lavoro(self, testo, mostra):
        self._scrivi_chat("Tu", mostra, VERDE)
        self.sta_pensando = True
        self.bottone.config(state="disabled")
        self.bottone_mic.config(state="disabled")
        self.stato_msg.config(text=" ⚡ CORE PROCESSING…", fg=GIALLO)
        threading.Thread(target=self._lavora, args=(testo,), daemon=True).start()

    def _lavora(self, testo):
        self.coda.put(("inizio_risposta", None))
        try:
            full = self.mike.chiedi_stream(testo, lambda fr: self.coda.put(("token", fr)))
        except Exception as e:
            self.coda.put(("token", f"Errore imprevisto: {e}"))
            full = ""
        self.coda.put(("fine_risposta", full))

    # ---------- voce ----------

    def _ascolta(self):
        if self.sta_pensando:
            return
        self.stato_msg.config(text=" 🎤 PARLA ORA…", fg=VERDE)
        self.bottone_mic.config(state="disabled")
        threading.Thread(target=self._ascolta_lavora, daemon=True).start()

    def _ascolta_lavora(self):
        testo, errore = voce.ascolta()
        self.coda.put(("vocale_err", errore) if errore else ("vocale_ok", testo))

    # ---------- stato provider (background) ----------

    def _refresh_stato_async(self):
        def lavora():
            try:
                d = self.mike.diagnostica_provider()
            except Exception:
                d = None
            self.coda.put(("stato_provider", d))
        threading.Thread(target=lavora, daemon=True).start()

    # ---------- coda (unico punto che tocca la GUI) ----------

    def _controlla_coda(self):
        try:
            while True:
                tipo, dato = self.coda.get_nowait()
                if tipo == "progresso":
                    self.stato_msg.config(text=f" ⏳ {dato}", fg=ACCENTO)
                elif tipo == "sistema":
                    self._scrivi_chat("Sistema", dato, ROSSO)
                elif tipo == "stato_provider":
                    self._mostra_stato_provider(dato)
                elif tipo == "inizio_risposta":
                    self._prefisso_risposta()
                elif tipo == "token":
                    self._aggiungi_token(dato)
                elif tipo == "fine_risposta":
                    self._fine_risposta()
                    self.sta_pensando = False
                    self.bottone.config(state="normal")
                    self.bottone_mic.config(state="normal")
                    self.stato_msg.config(text=" 📡 CORE READY | LINK STABLE", fg=ACCENTO)
                    self._refresh_stato_async()
                    if self.voce_attiva.get() and dato:
                        leggi = dato if len(dato) <= 800 else dato[:800] + ". Continua sullo schermo."
                        voce.parla(leggi)
                elif tipo == "vocale_ok":
                    self.bottone_mic.config(state="normal")
                    self.stato_msg.config(text=" 📡 CORE READY | LINK STABLE", fg=ACCENTO)
                    self.input.delete(0, "end")
                    self.input.insert(0, dato)
                    self._invia()
                elif tipo == "vocale_err":
                    self.bottone_mic.config(state="normal")
                    self.stato_msg.config(text=" 📡 CORE READY | LINK STABLE", fg=ACCENTO)
                    self._scrivi_chat("Sistema", dato, ROSSO)
        except queue.Empty:
            pass
        self.root.after(60, self._controlla_coda)

    def _mostra_stato_provider(self, d):
        if not d:
            self.stato_ai.config(text="STATO: n/d")
            return
        def led(v):
            return "✅" if v else "❌"
        self.stato_ai.config(
            text=f"OLLAMA {led(d['ollama'])} ({d.get('modello','')})  CLAUDE {led(d['claude'])}  GEMINI {led(d['gemini'])}",
            fg=ACCENTO if d["ollama"] else ROSSO)

    # ---------- azioni / dialoghi ----------

    def _apri_cartella_report(self):
        import subprocess
        cartella = os.path.join(RADICE, "dati", "Report")
        os.makedirs(cartella, exist_ok=True)
        try:
            if sys.platform.startswith("win"):
                os.startfile(cartella)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", cartella])
            else:
                subprocess.Popen(["xdg-open", cartella])
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire la cartella: {e}")

    def _reset_chat(self):
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.configure(state="disabled")
        self.mike.cronologia = []
        self._scrivi_chat("Sistema", "Sessione azzerata. Memoria conversazione svuotata.", VIOLA)

    def _click_leggi_file(self):
        p = filedialog.askopenfilename(
            title="Analizza file/log esterno",
            filetypes=[("Log/Testo", "*.log *.txt *.ini *.json *.xml *.jsonl"), ("Tutti i file", "*.*")])
        if p:
            self._comando(f"/leggi {p}")

    def _click_disinstalla(self):
        nome = simpledialog.askstring("Disinstalla", "Nome (anche parziale) del programma da rimuovere:")
        if nome:
            self._comando(f"/disinstalla {nome}")

    def _click_checklist(self):
        cliente = simpledialog.askstring("Checklist consenso", "Nome del cliente (apparirà nel modulo):")
        if cliente is not None:
            self._comando(f"/checklist {cliente}")

    def _click_crea_account(self):
        u = simpledialog.askstring("Account di emergenza", "Nome del nuovo account locale:")
        if u:
            p = simpledialog.askstring("Account di emergenza", f"Password per «{u}»:", show="*")
            if p:
                self._comando(f"/crea-account {u} {p}")

    def _click_reset_password(self):
        u = simpledialog.askstring("Reset password", "Account Windows LOCALE da resettare:")
        if u:
            p = simpledialog.askstring("Reset password", f"NUOVA password per «{u}»:", show="*")
            if p:
                self._comando(f"/reset-password {u} {p}")

    def _click_cambia_cervello(self):
        attuale = self.mike.cfg.get("modello_ollama", "")
        nome = simpledialog.askstring("Cambia modello locale",
                                      f"Modello attuale: {attuale}\n\nNome del modello Ollama "
                                      "(es. hermes3:8b, gpt-oss:20b, qwen2.5:3b):")
        if nome:
            self._comando(f"/cervello {nome}")

    def _click_informazioni(self):
        messagebox.showinfo(
            "COGNITIVE NEURAL LINK",
            "🧠 M.I.K.E. — Machine Intelligent Knowledge Engine\n"
            f"Firmware core: v{self._versione()}\n\n"
            "Assistente neurale e diagnostico per tecnici PC Windows.\n"
            "Cervello locale (Ollama) + riserva cloud, agenti, diagnostica,\n"
            "recupero accesso, riparazione e auto-aggiornamento sicuro.")

    # ---------- avvio ----------

    def avvia(self):
        self.root.mainloop()


def main():
    FinestraMike().avvia()


if __name__ == "__main__":
    main()
