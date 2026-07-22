"""Server web locale di Mike.

Serve l'interfaccia (app.html) e offre alcune API al browser:
  GET  /                 -> la pagina dell'app
  GET  /api/stato        -> stato provider + RAM/disco (per gli strumenti)
  GET  /api/geocode?q=   -> ricerca indirizzi/luoghi (mappe)
  POST /api/chat         -> risposta in STREAMING (testo che arriva man mano)
  POST /api/camera       -> analisi immagine webcam tramite Gemini

Gira solo in locale (127.0.0.1): non è esposto sulla rete.
Usa solo la libreria standard di Python.
"""
import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from ..brain import Mike
from ..providers import gemini
from ..tools import mappe
from ..diagnostica import live
from .. import config as cfg_mod

CARTELLA = os.path.dirname(os.path.abspath(__file__))
APP_HTML = os.path.join(CARTELLA, "app.html")

# Un'unica istanza del cervello, condivisa. Un lucchetto serializza le chat.
mike = Mike()
_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # niente log rumorosi in console

    # ---------- helper ----------

    def _invia(self, codice, contenuto, tipo="application/json; charset=utf-8"):
        if isinstance(contenuto, (dict, list)):
            contenuto = json.dumps(contenuto, ensure_ascii=False)
        if isinstance(contenuto, str):
            contenuto = contenuto.encode("utf-8")
        self.send_response(codice)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(contenuto)))
        self.end_headers()
        self.wfile.write(contenuto)

    def _corpo(self):
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return {}

    # ---------- GET ----------

    def do_GET(self):
        rotta = urlparse(self.path)
        if rotta.path in ("/", "/index.html"):
            try:
                with open(APP_HTML, "rb") as f:
                    self._invia(200, f.read(), "text/html; charset=utf-8")
            except Exception as e:
                self._invia(500, f"Errore caricamento UI: {e}", "text/plain; charset=utf-8")
            return
        if rotta.path == "/api/stato":
            d = {}
            try:
                d = mike.diagnostica_provider()
            except Exception:
                d = {"ollama": False, "claude": False, "gemini": False, "modello": ""}
            d["ram"] = live.ram_percento()
            d["disco"] = live.disco_percento()
            d["versione"] = self._versione()
            self._invia(200, d)
            return
        if rotta.path == "/api/geocode":
            q = parse_qs(rotta.query).get("q", [""])[0]
            self._invia(200, {"risultati": mappe.geocodifica(q)})
            return
        self._invia(404, {"errore": "non trovato"})

    def _versione(self):
        try:
            with open(os.path.join(cfg_mod.RADICE, "version.json"), encoding="utf-8") as f:
                return json.load(f).get("versione", "")
        except Exception:
            return ""

    # ---------- POST ----------

    def do_POST(self):
        rotta = urlparse(self.path)
        if rotta.path == "/api/chat":
            self._chat(self._corpo())
            return
        if rotta.path == "/api/camera":
            self._camera(self._corpo())
            return
        self._invia(404, {"errore": "non trovato"})

    def _chat(self, corpo):
        testo = (corpo.get("testo") or "").strip()
        if not testo:
            self._invia(400, {"errore": "testo vuoto"})
            return
        # Streaming: scriviamo i token man mano (testo semplice, chunked)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        def su_token(frammento):
            try:
                self.wfile.write(frammento.encode("utf-8"))
                self.wfile.flush()
            except Exception:
                pass

        with _lock:
            try:
                mike.chiedi_stream(testo, su_token)
            except Exception as e:
                su_token(f"\n[Errore: {e}]")

    def _camera(self, corpo):
        data_url = corpo.get("immagine", "")
        domanda = (corpo.get("prompt") or
                   "Guarda questa persona dalla webcam e dimmi in modo gentile e sincero "
                   "come appare: aspetto generale, espressione, abbigliamento, e un consiglio "
                   "amichevole. Rispondi in italiano, breve.")
        if "," in data_url:
            b64 = data_url.split(",", 1)[1]
        else:
            b64 = data_url
        if not b64:
            self._invia(400, {"errore": "nessuna immagine"})
            return
        chiave = mike.cfg.get("gemini_api_key", "")
        if not cfg_mod.chiave_valida(chiave):
            self._invia(200, {"opinione": "Per usare la telecamera serve la chiave Gemini in "
                                          "config.json (gratuita su https://aistudio.google.com/apikey)."})
            return
        try:
            op = gemini.descrivi_immagine(chiave, mike.cfg["modello_gemini"], b64, domanda)
            self._invia(200, {"opinione": op})
        except Exception as e:
            self._invia(200, {"opinione": f"Analisi non riuscita: {e}"})


def main(porta=8765, apri=True):
    server = ThreadingHTTPServer(("127.0.0.1", porta), Handler)
    url = f"http://127.0.0.1:{porta}"
    print("=" * 50)
    print(f"  MIKE — interfaccia web attiva su: {url}")
    print("  (Chiudi questa finestra per spegnere Mike.)")
    print("=" * 50)
    # warm-up del modello in background
    threading.Thread(target=mike.warmup, daemon=True).start()
    if apri:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
