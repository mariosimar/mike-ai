"""Istantanea in tempo reale del PC (processi attivi, RAM): permette a Mike di
"vedere" davvero cosa sta facendo il computer quando glielo chiedi.
"""
import ctypes
import os
import shutil
import subprocess

CARTELLA = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(CARTELLA, "live.ps1")


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
        return round(float(s.dwMemoryLoad), 1)
    except Exception:
        return 0.0


def disco_percento():
    try:
        u = shutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\")
        return round(u.used / u.total * 100.0, 1)
    except Exception:
        return 0.0


def istantanea(timeout=30):
    """Restituisce (testo, errore). Sola lettura: legge solo lo stato del sistema."""
    if not os.path.exists(SCRIPT):
        return None, "Script live non trovato."
    comando = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", SCRIPT]
    try:
        c = subprocess.run(comando, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return None, "PowerShell non trovato (sei su Windows?)."
    except subprocess.TimeoutExpired:
        return None, "Lettura stato troppo lunga."
    out = (c.stdout or "").strip()
    if not out:
        return None, f"Nessun dato. {c.stderr.strip()}"
    return out, None
