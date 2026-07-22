"""Un singolo agente di Mike: ha un nome, un ruolo, ed esegue un compito."""
from . import llm


class Agente:
    def __init__(self, nome, ruolo, cfg, provider=None):
        self.nome = nome
        self.ruolo = ruolo
        self.cfg = cfg
        self.provider = provider or llm.provider_predefinito(cfg)

    def lavora(self, compito, contesto=""):
        """Esegue il compito assegnato e restituisce il risultato (testo)."""
        system = (
            f"Sei «{self.nome}», un agente AI specializzato che lavora per Mike.\n"
            f"Il tuo ruolo: {self.ruolo}.\n"
            "Esegui il compito che ti viene dato in modo concreto, preciso e conciso. "
            "Se ti servono informazioni che non hai, dichiaralo chiaramente invece di inventare. "
            "Rispondi in italiano."
        )
        prompt = compito
        if contesto:
            prompt += f"\n\n--- Contesto / dati a disposizione ---\n{contesto}"
        return llm.chiedi(self.cfg, self.provider, system, prompt)

    def verifica(self, compito, risultato, contesto=""):
        """Controlla il lavoro di un altro agente. Restituisce un dizionario:
        {"ok": bool, "voto": 0-10, "problemi": [...], "suggerimenti": "..."}
        """
        system = (
            f"Sei «{self.nome}», un agente VERIFICATORE severo ma giusto.\n"
            f"Ruolo: {self.ruolo}.\n"
            "Devi controllare il lavoro di un altro agente: è corretto? completo? "
            "ci sono errori, rischi o cose mancanti?\n"
            "Rispondi SOLO con un oggetto JSON in questo formato esatto:\n"
            '{"ok": true/false, "voto": numero 0-10, "problemi": ["..."], "suggerimenti": "testo"}'
        )
        prompt = (
            f"COMPITO ASSEGNATO:\n{compito}\n\n"
            f"RISULTATO PRODOTTO DALL'ALTRO AGENTE:\n{risultato}"
        )
        if contesto:
            prompt += f"\n\n--- Dati di riferimento ---\n{contesto}"
        risposta = llm.chiedi(self.cfg, self.provider, system, prompt)
        dati = llm.estrai_json(risposta)
        if isinstance(dati, dict):
            dati.setdefault("ok", True)
            dati.setdefault("voto", None)
            dati.setdefault("problemi", [])
            dati.setdefault("suggerimenti", "")
            return dati
        # Se non ha risposto in JSON, conserviamo il testo grezzo.
        return {"ok": True, "voto": None, "problemi": [], "suggerimenti": risposta}
