"""Cattura dello schermo: Mike "vede" quello che c'è sul monitor.

Fa uno screenshot (via PowerShell/.NET, senza installazioni) e lo restituisce in
base64, pronto per essere analizzato da un modello con visione (Gemini).
Utile per leggere messaggi d'errore, finestre, codici sullo schermo.
"""
import base64
import os
import subprocess
import tempfile

_PS = (
    "Add-Type -AssemblyName System.Windows.Forms,System.Drawing; "
    "$b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
    "$bmp=New-Object System.Drawing.Bitmap $b.Width,$b.Height; "
    "$g=[System.Drawing.Graphics]::FromImage($bmp); "
    "$g.CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size); "
    "$bmp.Save('{percorso}',[System.Drawing.Imaging.ImageFormat]::Png); "
    "$g.Dispose(); $bmp.Dispose()"
)


def cattura_base64(timeout=30):
    """Fa uno screenshot e lo restituisce come (base64, errore)."""
    fd, percorso = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        comando = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                   "-Command", _PS.format(percorso=percorso.replace("\\", "\\\\"))]
        c = subprocess.run(comando, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        if not os.path.exists(percorso) or os.path.getsize(percorso) == 0:
            return None, f"Screenshot non riuscito: {c.stderr.strip()[:200]}"
        with open(percorso, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return b64, None
    except subprocess.TimeoutExpired:
        return None, "Screenshot troppo lento."
    except Exception as e:
        return None, f"Errore screenshot: {e}"
    finally:
        try:
            os.remove(percorso)
        except Exception:
            pass
