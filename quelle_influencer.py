"""Baut quellen/influencer.json: wie bullisch die großen YouTube Krypto Kanäle waren, als Gegenindikator.

Aufruf: python quelle_influencer.py <ordner mit den Titeln> <fetch_herdenradar.py wegen der Wortlisten>

Regel, festgelegt bevor Ergebnisse da waren:
  Je Monat und Kanal: bullische minus bärische Treffer in den Titeln, geteilt durch alle Titel des Monats.
  Monatswert: Schnitt der Kanäle mit mindestens 3 Titeln, gewichtet nach Wurzel der heutigen Abos. Mindestens 5 Kanäle.
  Am 1. des Folgemonats Vergleich mit den 24 Monaten davor:
    oberste 20 %, extrem bullisch: Rücksetzer. Unterste 20 %, extrem bärisch: Anstieg. Dazwischen kein Ereignis.
Grenzen: nur Titel und grobe Wortliste. Titel klingen fast immer bullisch, deshalb zählt nur der Vergleich mit der eigenen Vergangenheit.
Die Kanäle sind die größten von heute, wer früher groß war und aufgegeben hat, fehlt also. Keine Zukunft.
"""
import ast
import json
import math
import re
import sys
from pathlib import Path

ORDNER, HERD = Path(sys.argv[1]), sys.argv[2]
listen = {}
for knoten in ast.parse(Path(HERD).read_text()).body:
    if isinstance(knoten, ast.Assign) and getattr(knoten.targets[0], "id", "") in ("BULL", "BEAR", "BULL_DE", "BEAR_DE"):
        listen[knoten.targets[0].id] = ast.literal_eval(knoten.value)
muster = lambda w: re.compile(r"\b(?:" + "|".join(re.escape(x) for x in sorted(set(w), key=len, reverse=True)) + r")\b")
P = {"en": (muster(listen["BULL"]), muster(listen["BEAR"])), "de": (muster(listen["BULL_DE"] + listen["BULL"]), muster(listen["BEAR_DE"] + listen["BEAR"]))}

kanal_monat = {}
gesamt = 0
for datei in ORDNER.glob("UC*.json"):
    k = json.loads(datei.read_text())
    bull, bear = P[k["sprache"]]
    je = {}
    for d, titel in k["videos"]:
        t = titel.lower()
        m = je.setdefault(d[:7], [0, 0])
        m[0] += 1
        m[1] += len(bull.findall(t)) - len(bear.findall(t))
        gesamt += 1
    for monat, (n, s) in je.items():
        if n >= 3:
            kanal_monat.setdefault(monat, []).append((s / n, math.sqrt(k["abos"])))
wert = {m: sum(a * g for a, g in v) / sum(g for _, g in v) for m, v in kanal_monat.items() if len(v) >= 5}
monate = sorted(wert)
print("Titel", gesamt, "Kanäle", len(list(ORDNER.glob('UC*.json'))), "Monate", len(monate), monate[0], monate[-1])

E = []
for i, m in enumerate(monate):
    davor = [wert[x] for x in monate[max(0, i - 24):i]]
    if len(davor) < 24 or m >= "2026-11":
        continue
    rang = sum(v < wert[m] for v in davor) / len(davor)
    k = "down" if rang >= .8 else "up" if rang <= .2 else None
    if not k:
        continue
    j, mo = int(m[:4]), int(m[5:])
    j, mo = (j + 1, 1) if mo == 12 else (j, mo + 1)
    E.append({"d": f"{j}-{mo:02d}-01", "n": f"YouTuber {'extrem bullisch' if k == 'down' else 'extrem bärisch'} im Vergleich zu 24 Monaten", "t": "Influencer", "k": k,
              "quelle": "https://www.youtube.com/results?search_query=bitcoin"})
(Path(__file__).parent / "quellen" / "influencer.json").write_text(json.dumps({"id": "influencer", "name": "YouTube Influencer", "rang": 35, "ereignisse": E}, ensure_ascii=False, indent=0))
print(len(E), "Ereignisse", E[0]["d"], E[-1]["d"], {x: sum(e["k"] == x for e in E) for x in ("up", "down")})
