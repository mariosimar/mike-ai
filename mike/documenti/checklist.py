"""Genera un modulo di consenso/intervento stampabile (HTML).

Il tecnico lo stampa, lo compila e lo fa firmare al cliente PRIMA di operare:
serve come autorizzazione scritta e come riepilogo del lavoro svolto.
"""
import os
import time

from .. import config as cfg_mod

CARTELLA = os.path.join(cfg_mod.RADICE, "dati", "Report")

INTERVENTI = [
    "Diagnosi generale del PC",
    "Pulizia file temporanei e spazio disco",
    "Riparazione file di sistema (sfc / DISM)",
    "Scansione antivirus (Windows Defender)",
    "Rimozione programmi indesiderati / malware",
    "Reset / recupero password account",
    "Creazione account di emergenza",
    "Backup / recupero dati",
    "Aggiornamenti di sistema",
    "Sostituzione / aggiunta componenti hardware",
]

MODELLO = """<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8">
<title>Modulo intervento tecnico</title>
<style>
  body {{ font-family: Arial, sans-serif; color:#111; margin:40px; }}
  h1 {{ font-size:20px; border-bottom:2px solid #333; padding-bottom:6px; }}
  .riga {{ margin:8px 0; }}
  .campo {{ display:inline-block; border-bottom:1px solid #888; min-width:280px; }}
  table {{ width:100%; border-collapse:collapse; margin-top:10px; }}
  td {{ padding:6px; border-bottom:1px solid #ddd; }}
  .box {{ width:16px; height:16px; border:1px solid #333; display:inline-block; margin-right:8px; vertical-align:middle; }}
  .consenso {{ background:#f6f6f6; border:1px solid #ccc; padding:12px; margin:18px 0; font-size:13px; }}
  .firme {{ margin-top:40px; display:flex; justify-content:space-between; }}
  .firma {{ width:45%; border-top:1px solid #333; padding-top:6px; text-align:center; font-size:13px; }}
  @media print {{ .nostampa {{ display:none; }} }}
</style></head>
<body>
<h1>🔧 Modulo di intervento tecnico informatico</h1>
<div class="riga">Tecnico / Ditta: <span class="campo">&nbsp;</span></div>
<div class="riga">Cliente: <span class="campo">{cliente}</span></div>
<div class="riga">Data: <span class="campo">{data}</span> &nbsp;&nbsp; PC: <span class="campo">{nome_pc}</span></div>

<div class="consenso">
<b>CONSENSO DEL CLIENTE.</b> Il sottoscritto cliente autorizza il tecnico a operare
sul dispositivo sopra indicato per gli interventi selezionati. Dichiara di essere il
legittimo proprietario/utilizzatore del dispositivo. È informato che alcune operazioni
(reset password, formattazioni, riparazioni) possono comportare la <b>perdita di dati</b>
e che i dati cifrati (BitLocker/EFS) richiedono le relative chiavi. Acconsente al
trattamento dei dati ai soli fini dell'assistenza tecnica.
</div>

<b>Interventi da eseguire / eseguiti:</b>
<table>
{righe_interventi}
</table>

<div class="riga" style="margin-top:16px;">Note: <span class="campo" style="min-width:480px;">&nbsp;</span></div>
<div class="riga">&nbsp;<span class="campo" style="min-width:560px;">&nbsp;</span></div>

<div class="firme">
  <div class="firma">Firma del cliente</div>
  <div class="firma">Firma del tecnico</div>
</div>

<p class="nostampa" style="margin-top:30px;color:#888;font-size:12px;">
Generato da Mike il {data}. Premi Ctrl+P per stampare.</p>
</body></html>
"""


def genera(cliente="", nome_pc=""):
    """Crea il file HTML del modulo e ne restituisce il percorso."""
    os.makedirs(CARTELLA, exist_ok=True)
    righe = "\n".join(
        f'<tr><td><span class="box"></span>{nome}</td></tr>' for nome in INTERVENTI)
    html = MODELLO.format(
        cliente=cliente or "&nbsp;",
        nome_pc=nome_pc or "&nbsp;",
        data=time.strftime("%d/%m/%Y"),
        righe_interventi=righe,
    )
    stamp = time.strftime("%Y%m%d_%H%M%S")
    nome_file = f"modulo_intervento_{stamp}.html"
    percorso = os.path.join(CARTELLA, nome_file)
    with open(percorso, "w", encoding="utf-8") as f:
        f.write(html)
    return percorso
