"""L'orchestratore: Mike scompone un obiettivo in compiti, crea un agente per
ciascuno, raccoglie i risultati, li fa verificare da altri agenti, e infine
Mike stesso fa il controllo conclusivo.

Flusso:
  1) PIANIFICAZIONE  -> Mike divide l'obiettivo in sotto-compiti con ruoli.
  2) ESECUZIONE      -> un agente per ogni compito produce il risultato.
  3) VERIFICA        -> per ogni risultato, un altro agente lo controlla.
  4) CONTROLLO FINALE-> Mike unisce tutto e dà il verdetto finale.
"""
from . import llm
from .agente import Agente


class Orchestratore:
    def __init__(self, cfg, log=None):
        self.cfg = cfg
        # log è una funzione che riceve stringhe di avanzamento (per la GUI).
        self.log = log or (lambda s: None)
        self.provider = llm.provider_predefinito(cfg)

    # ---------- 1) pianificazione ----------

    def _pianifica(self, obiettivo):
        """Chiede a Mike di dividere l'obiettivo in compiti. Restituisce una lista
        di dizionari {"nome", "ruolo", "compito"}.
        """
        system = (
            "Sei Mike, il coordinatore di una squadra di agenti AI.\n"
            "Ti viene dato un OBIETTIVO. Dividilo in 2-4 sotto-compiti concreti, "
            "ognuno affidato a un agente con un ruolo adatto.\n"
            "Rispondi SOLO con un array JSON in questo formato:\n"
            '[{"nome": "NomeAgente", "ruolo": "specializzazione breve", '
            '"compito": "cosa deve fare in concreto"}]'
        )
        risposta = llm.chiedi(self.cfg, self.provider, system,
                              f"OBIETTIVO: {obiettivo}", max_token=1000)
        piano = llm.estrai_json(risposta)
        if isinstance(piano, list) and piano:
            # Pulizia dei campi
            valido = []
            for i, p in enumerate(piano, 1):
                if isinstance(p, dict) and p.get("compito"):
                    valido.append({
                        "nome": p.get("nome") or f"Agente{i}",
                        "ruolo": p.get("ruolo") or "esperto generico",
                        "compito": p["compito"],
                    })
            if valido:
                return valido
        # Fallback: un solo agente che fa tutto.
        return [{"nome": "Agente1", "ruolo": "esperto generico", "compito": obiettivo}]

    # ---------- flusso completo ----------

    def esegui(self, obiettivo):
        """Esegue l'intero flusso e restituisce un resoconto testuale formattato."""
        if not self.provider:
            return ("Non posso usare gli agenti: manca una chiave API valida.\n"
                    "Configura Claude o Gemini in config.json.")

        righe = [f"🎯 OBIETTIVO: {obiettivo}\n"]

        # 1) Pianificazione
        self.log("Mike sta pianificando i compiti…")
        piano = self._pianifica(obiettivo)
        righe.append(f"📋 PIANO ({len(piano)} agenti):")
        for p in piano:
            righe.append(f"  • {p['nome']} — {p['ruolo']}: {p['compito']}")
        righe.append("")

        # 2) Esecuzione
        risultati = []
        for p in piano:
            self.log(f"{p['nome']} sta lavorando…")
            agente = Agente(p["nome"], p["ruolo"], self.cfg, self.provider)
            try:
                esito = agente.lavora(p["compito"])
            except Exception as e:
                esito = f"(Errore durante l'esecuzione: {e})"
            risultati.append({"piano": p, "esito": esito})
            righe.append(f"🔧 {p['nome']} ha prodotto:\n{esito}\n")

        # 3) Verifica incrociata (ogni risultato controllato da un altro agente)
        righe.append("🔎 VERIFICA INCROCIATA:")
        for i, r in enumerate(risultati):
            # Il verificatore è l'agente successivo (a rotazione), così non si auto-verifica.
            altro = piano[(i + 1) % len(piano)]
            verificatore = Agente(f"Verificatore-{altro['nome']}",
                                  "controllo qualità e correttezza", self.cfg, self.provider)
            self.log(f"{verificatore.nome} sta verificando il lavoro di {r['piano']['nome']}…")
            try:
                verdetto = verificatore.verifica(r["piano"]["compito"], r["esito"])
            except Exception as e:
                verdetto = {"ok": True, "voto": None, "problemi": [], "suggerimenti": f"(verifica fallita: {e})"}
            r["verdetto"] = verdetto
            stato = "✅ OK" if verdetto.get("ok") else "⚠️ DA RIVEDERE"
            voto = verdetto.get("voto")
            righe.append(f"  • {r['piano']['nome']}: {stato}" + (f" (voto {voto}/10)" if voto is not None else ""))
            for prob in verdetto.get("problemi", []):
                righe.append(f"      - problema: {prob}")
            if verdetto.get("suggerimenti"):
                righe.append(f"      → {verdetto['suggerimenti']}")
        righe.append("")

        # 4) Controllo finale di Mike
        self.log("Mike sta facendo il controllo finale…")
        sintesi = self._controllo_finale(obiettivo, risultati)
        righe.append("🧠 VERDETTO FINALE DI MIKE:")
        righe.append(sintesi)

        return "\n".join(righe)

    def _controllo_finale(self, obiettivo, risultati):
        system = (
            "Sei Mike, il coordinatore. Hai i risultati dei tuoi agenti e le verifiche.\n"
            "Fai una sintesi finale chiara e utile per l'utente: cosa è stato concluso, "
            "cosa è affidabile, cosa resta da fare o controllare. In italiano, conciso."
        )
        blocchi = []
        for r in risultati:
            v = r.get("verdetto", {})
            blocchi.append(
                f"Compito: {r['piano']['compito']}\n"
                f"Risultato: {r['esito']}\n"
                f"Verifica: ok={v.get('ok')} voto={v.get('voto')} "
                f"problemi={v.get('problemi')} note={v.get('suggerimenti')}"
            )
        prompt = f"OBIETTIVO: {obiettivo}\n\n" + "\n\n---\n\n".join(blocchi)
        try:
            return llm.chiedi(self.cfg, self.provider, system, prompt, max_token=1200)
        except Exception as e:
            return f"(Controllo finale non riuscito: {e})"
