"""Holt die Videotitel der Herdenradar Kanäle samt Datum, kostenlos per yt_dlp ohne Schlüssel.

Aufruf: python3.14 quelle_influencer_holen.py <herdenradar_kanaele.json> <zielordner>

Die Kanalliste liefert alle Titel in zeitlicher Reihenfolge, aber ohne Datum. Das echte Upload Datum wird nur für jedes
100. Video geholt, die Tage dazwischen werden linear aufgeteilt. Pausen, weil YouTube sonst drosselt. Abgebrochene Läufe
machen dort weiter, wo sie aufgehört haben.
"""
import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

KANAELE, ZIEL = json.load(open(sys.argv[1])), Path(sys.argv[2])
ZIEL.mkdir(parents=True, exist_ok=True)
SCHRITT = 100


def yt(*argumente):
    try:
        return subprocess.run([sys.executable, "-m", "yt_dlp", "--no-warnings", *argumente], capture_output=True, text=True, timeout=900).stdout
    except subprocess.TimeoutExpired:  # ein hängender Abruf darf den Lauf nicht beenden, der Kanal kommt im nächsten Lauf dran
        return ""


def datum(video):
    for versuch in range(3):
        aus = yt("--skip-download", "--print", "%(upload_date)s", f"https://www.youtube.com/watch?v={video}").strip()
        if len(aus) == 8 and aus.isdigit():
            return dt.date(int(aus[:4]), int(aus[4:6]), int(aus[6:]))
        time.sleep(20 * (versuch + 1))
    return None


for sprache, feld in (("en", "englisch"), ("de", "deutsch")):
    for k in KANAELE[feld]:
        ziel = ZIEL / f"{k['id']}.json"
        if ziel.exists():
            continue
        zeilen = [z.split("\t", 1) for z in yt("--flat-playlist", "--print", "%(id)s\t%(title)s", f"https://www.youtube.com/channel/{k['id']}/videos").splitlines() if "\t" in z]
        if not zeilen:
            print("LEER", k["name"], flush=True)
            continue
        zeilen.reverse()  # ältestes zuerst
        stuetzen = sorted(set(range(0, len(zeilen), SCHRITT)) | {len(zeilen) - 1})
        tage = {}
        for i in stuetzen:
            d = datum(zeilen[i][0])
            if d:
                tage[i] = d
            time.sleep(1)
        punkte = sorted(tage)
        videos = []
        for a, b in zip(punkte, punkte[1:]):
            for i in range(a, b):
                videos.append([(tage[a] + (tage[b] - tage[a]) * (i - a) / (b - a)).isoformat(), zeilen[i][1]])
        if punkte:
            videos.append([tage[punkte[-1]].isoformat(), zeilen[punkte[-1]][1]])
        ziel.write_text(json.dumps({"name": k["name"], "sprache": sprache, "abos": k["abos"], "videos": videos}, ensure_ascii=False))
        print(k["name"], len(zeilen), "Videos,", len(punkte), "Stützen,", videos[0][0] if videos else "", flush=True)
        time.sleep(3)
print("FERTIG", flush=True)
