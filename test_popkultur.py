"""Prüft, ob große Filmstarts und Spiele BTC bewegen. Aufruf: python test_popkultur.py <btc.json von Yahoo>

Vergleicht Starttage mit allen normalen Tagen: Tagesbewegung, Betrag der Bewegung, 7 und 30 Tage danach.
p Wert aus dem zirkulären Verschiebetest, der die Abstände zwischen den Starts erhält.
"""
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

r = json.load(open(sys.argv[1]))["chart"]["result"][0]
kurs = {}
for t, c in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]):
    if c is not None:
        kurs[dt.datetime.fromtimestamp(t, dt.UTC).date()] = float(c)
tage = sorted(kurs)[:-1]
p = np.array([kurs[d] for d in tage])
idx = {d: i for i, d in enumerate(tage)}
n = len(tage)
tag = np.r_[np.nan, p[1:] / p[:-1] - 1]
vor = lambda k: np.r_[p[k:] / p[:-k] - 1, np.full(k, np.nan)]
d7, d30 = vor(7), vor(30)
ev = json.loads((Path(__file__).parent / "quellen" / "popkultur.json").read_text())["ereignisse"]
ev = [e for e in ev if dt.date.fromisoformat(e["d"]) in idx]


def p_wert(werte, pos, richtung):
    """Anteil der Verschiebungen, die mindestens so stark in Richtung der Regel ausfallen."""
    echt = np.nanmean(werte[pos])
    v = [np.nanmean(werte[(pos + o) % n]) for o in range(1, n, 3)]
    return float(np.mean(np.array(v) * richtung >= echt * richtung))


print(f"Normal: Tag {np.nanmean(tag) * 100:+.2f} %, Betrag {np.nanmean(abs(tag)) * 100:.2f} %, 7 Tage {np.nanmean(d7) * 100:+.1f} %, 30 Tage {np.nanmean(d30) * 100:+.1f} %, Minus Tage {np.nanmean(tag[1:] < 0) * 100:.1f} %")
for name, auswahl, richtung in (("Alle Starts", ev, 0), ("Thema dunkel, Regel Rücksetzer", [e for e in ev if e["k"] == "down"], -1),
                                ("Thema hell, Regel Anstieg", [e for e in ev if e["k"] == "up"], 1), ("Film", [e for e in ev if e["t"] == "Film"], 0),
                                ("Spiel", [e for e in ev if e["t"] == "Spiel"], 0)):
    if not auswahl:
        continue
    pos = np.array(sorted({idx[dt.date.fromisoformat(e["d"])] for e in auswahl}))
    pos = pos[pos > 0]
    zeile = f"{name}: {len(pos)} Tage, Tag {np.nanmean(tag[pos]) * 100:+.2f} %, Betrag {np.nanmean(abs(tag[pos])) * 100:.2f} % (p {p_wert(abs(tag), pos, 1):.2f}), Minus Tage {np.mean(tag[pos] < 0) * 100:.0f} %, 7 Tage {np.nanmean(d7[pos]) * 100:+.1f} %, 30 Tage {np.nanmean(d30[pos]) * 100:+.1f} %"
    if richtung:
        zeile += f", p Tag {p_wert(tag, pos, richtung):.2f}, p 30 Tage {p_wert(d30, pos, richtung):.2f}"
    print(zeile)

print("Größte Tagesverluste auf Starttagen:")
for e in sorted(ev, key=lambda e: tag[idx[dt.date.fromisoformat(e["d"])]] if idx[dt.date.fromisoformat(e["d"])] else 0)[:8]:
    print(" ", e["d"], f"{tag[idx[dt.date.fromisoformat(e['d'])]] * 100:+.1f} %", e["k"], e["n"])
for e in ev:
    if "Tron" in e["n"]:
        i = idx[dt.date.fromisoformat(e["d"])]
        print("TRON", e["d"], e["k"], f"Tag {tag[i] * 100:+.1f} %, Rang {int(np.sum(tag[1:] < tag[i])) + 1} von {n - 1}, 7 Tage {d7[i] * 100:+.1f} %, 30 Tage {d30[i] * 100:+.1f} %, Kurs {p[i - 1]:.0f} auf {p[i]:.0f}")
