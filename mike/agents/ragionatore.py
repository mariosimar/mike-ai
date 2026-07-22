"""Ragionatore agentico di Mike (stile Claude/ReAct).

Data una richiesta in linguaggio naturale, il modello DECIDE da solo se e quali
strumenti usare (ricerca web, mappe, stato del PC, diagnosi, log…), li esegue,
osserva i risultati e infine risponde in streaming usando i dati raccolti.

È ciò che trasforma Mike da "chatbot con comandi /" in un assistente che ragiona
e agisce da solo. Gli strumenti esposti qui sono SOLO di lettura/sicuri: le azioni
che modificano il sistema restano dietro conferma esplicita (/conferma).
"""
from . import llm as agent_llm
from ..providers import ollama


class Ragionatore:
    def __init__(self, cfg, strumenti, log=None):
        self.cfg = cfg
        self.strumenti = strumenti          # {nome: {"desc","param":bool,"fn"}}
        self.log = log or (lambda s: None)
        self.provider = agent_llm.provider_predefinito(cfg)

    def _descrizioni(self):
        righe = []
        for nome, s in self.strumenti.items():
            arg = "(argomento)" if s.get("param") else "()"
            righe.append(f"- {nome}{arg}: {s['desc']}")
        return "\n".join(righe)

    def _storia_breve(self, storia, n=3):
        pezzi = []
        for m in storia[-n:]:
            chi = "Utente" if m["ruolo"] == "utente" else "Mike"
            pezzi.append(f"{chi}: {m['testo'][:300]}")
        return "\n".join(pezzi)

    # ---------- decisione: quale strumento usare ----------

    def _decidi(self, testo, storia, osservazioni):
        sistema = (
            "Sei il modulo di RAGIONAMENTO di Mike. Il tuo compito è decidere se usare "
            "uno STRUMENTO per rispondere all'utente.\n\n"
            "Strumenti disponibili:\n" + self._descrizioni() + "\n\n"
            "REGOLE:\n"
            "• Se ti serve un dato che solo uno strumento può darti, rispondi SOLO con:\n"
            '  {\"strumento\": \"nome\", \"argomento\": \"testo\"}\n'
            "• Se è una domanda generica, di conversazione, o hai già i dati per rispondere, "
            "rispondi SOLO con:\n  {\"strumento\": \"nessuno\"}\n"
            "Rispondi SOLO con il JSON, niente altro."
        )
        oss = "\n\n".join(f"[{n} {a}] → {r[:600]}" for n, a, r in osservazioni) or "(nessuna)"
        prompt = (
            f"Conversazione recente:\n{self._storia_breve(storia)}\n\n"
            f"Osservazioni già raccolte dagli strumenti:\n{oss}\n\n"
            f"Ultima richiesta dell'utente: {testo}"
        )
        try:
            out = agent_llm.chiedi(self.cfg, self.provider, sistema, prompt, max_token=150)
        except Exception:
            return None
        return agent_llm.estrai_json(out)

    # ---------- ciclo agentico ----------

    def esegui(self, testo, storia, sistema_base, su_token, max_passi=3):
        osservazioni = []
        gia_usati = set()
        for _ in range(max_passi):
            dec = self._decidi(testo, storia, osservazioni)
            if not isinstance(dec, dict):
                break
            nome = (dec.get("strumento") or "").strip()
            if nome in ("", "nessuno", "none", "nessun"):
                break
            s = self.strumenti.get(nome)
            if not s:
                break
            arg = str(dec.get("argomento", "")).strip()
            firma = f"{nome}|{arg}"
            if firma in gia_usati:  # evita loop sullo stesso strumento
                break
            gia_usati.add(firma)
            self.log(f"🔧 Uso lo strumento «{nome}»…")
            try:
                risultato = s["fn"](arg) if s.get("param") else s["fn"]()
            except Exception as e:
                risultato = f"(errore nello strumento {nome}: {e})"
            osservazioni.append((nome, arg, (risultato or "")[:2500]))

        return self._rispondi(testo, storia, sistema_base, osservazioni, su_token)

    # ---------- risposta finale (in streaming) ----------

    def _rispondi(self, testo, storia, sistema_base, osservazioni, su_token):
        sistema = sistema_base
        if osservazioni:
            blocco = "\n\n".join(f"[Strumento {n} {a}]\n{r}" for n, a, r in osservazioni)
            sistema += (
                "\n\nDATI REALI RACCOLTI DAGLI STRUMENTI. La tua risposta DEVE basarsi su questi "
                "dati e riportarli all'utente (indirizzi, coordinate, valori, risultati). "
                "NON dire all'utente di cercare altrove o su Google: il dato è già qui sotto, "
                "usalo direttamente.\n" + blocco)
        if self.provider == "ollama":
            return ollama.chiedi_stream(self.cfg["modello_ollama"], storia,
                                        system=sistema, su_token=su_token)
        risposta = agent_llm.chiedi(self.cfg, self.provider, sistema, testo, max_token=1200)
        su_token(risposta)
        return risposta
