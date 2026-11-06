"""Baut quellen/wirtschaft.json aus offiziellen Daten. Regeln stehen fest und schauen nie auf BTC.

Aufruf: python quelle_wirtschaft.py <ordner mit effr.json, bls.json, spf_rgdp.xlsx>
  effr.json     markets.newyorkfed.org/api/rates/unsecured/effr/search.json?startDate=2021-12-01&endDate=...
  bls.json      api.bls.gov/publicAPI/v2/timeseries/data/ mit LNS14000000 und CUUR0000SA0, 2020 bis heute
  spf_rgdp.xlsx philadelphiafed.org, Survey of Professional Forecasters, Median_RGDP_Growth.xlsx

Regeln:
  Leitzins: Senkung Anstieg, Erhöhung Rücksetzer. Datum ist der erste Tag der neuen Spanne.
  Inflation (Jahresrate, nicht saisonbereinigt): sinkt um mindestens 0,1 Punkte Anstieg, steigt Rücksetzer.
  Arbeitslosigkeit: sinkt um mindestens 0,1 Punkte Anstieg, steigt Rücksetzer.
  Prognosen: Mittel der Wachstumsprognose für dieselben 3 Quartale gegen die Umfrage davor, ab 0,1 Punkten Änderung.
Veröffentlichungstage sind vorsichtig genähert, damit nichts früher zählt als es bekannt war:
  Arbeitslosigkeit am 8., Inflation am 15. des Folgemonats, Prognosen am 20. des mittleren Quartalsmonats.
"""
import json
import sys
from pathlib import Path

import openpyxl

ORDNER = Path(sys.argv[1])
AB = "2010-06-01"
FED = "https://markets.newyorkfed.org/api/rates/unsecured/effr/search.json"
BLS_ARBEIT = "https://data.bls.gov/timeseries/LNS14000000"
BLS_CPI = "https://data.bls.gov/timeseries/CUUR0000SA0"
SPF = "https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/survey-of-professional-forecasters"
MONAT = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
kom = lambda v, n=1: f"{v:.{n}f}".replace(".", ",")
E = []


def folgemonat(j, m, tag):
    j, m = (j + 1, 1) if m == 12 else (j, m + 1)
    return f"{j}-{m:02d}-{tag:02d}"


# Leitzins
zins = sorted(json.load(open(ORDNER / "effr.json"))["refRates"], key=lambda r: r["effectiveDate"])
for a, b in zip(zins, zins[1:]):
    if b["targetRateTo"] != a["targetRateTo"]:
        runter = b["targetRateTo"] < a["targetRateTo"]
        E.append({"d": b["effectiveDate"], "n": f"Fed {'senkt' if runter else 'erhöht'} Leitzins auf {kom(b['targetRateFrom'], 2)} bis {kom(b['targetRateTo'], 2)} %",
                  "t": "Zinsen", "k": "up" if runter else "down", "quelle": FED})

# BLS Reihen
reihen = {}
for s in json.load(open(ORDNER / "bls.json"))["Results"]["series"]:
    reihen[s["seriesID"]] = {(int(x["year"]), int(x["period"][1:])): float(x["value"]) for x in s["data"]
                             if x["period"].startswith("M") and x["value"] not in ("", "-")}

alo = reihen["LNS14000000"]
for (j, m), v in sorted(alo.items()):
    vor = alo.get((j - 1, 12) if m == 1 else (j, m - 1))
    d = folgemonat(j, m, 8)
    if vor is None or d < AB or abs(v - vor) < 0.05:
        continue
    E.append({"d": d, "n": f"Arbeitslosigkeit {'sinkt' if v < vor else 'steigt'} auf {kom(v)} % ({MONAT[m - 1]})",
              "t": "Arbeitsmarkt", "k": "up" if v < vor else "down", "quelle": BLS_ARBEIT})

cpi = reihen["CUUR0000SA0"]
jahresrate = {(j, m): round((v / cpi[(j - 1, m)] - 1) * 100, 1) for (j, m), v in cpi.items() if (j - 1, m) in cpi}
for (j, m), v in sorted(jahresrate.items()):
    vor = jahresrate.get((j - 1, 12) if m == 1 else (j, m - 1))
    d = folgemonat(j, m, 15)
    if vor is None or d < AB or abs(v - vor) < 0.05:
        continue
    E.append({"d": d, "n": f"Inflation {'sinkt' if v < vor else 'steigt'} auf {kom(v)} % ({MONAT[m - 1]})",
              "t": "Inflation", "k": "up" if v < vor else "down", "quelle": BLS_CPI})

# Prognosen: DRGDP3 bis 5 jetzt gegen DRGDP4 bis 6 der Umfrage davor, das sind dieselben Zielquartale
zeilen = list(openpyxl.load_workbook(ORDNER / "spf_rgdp.xlsx", data_only=True).worksheets[0].values)
kopf = zeilen[0]
spf = [dict(zip(kopf, z)) for z in zeilen[1:] if z[0]]
for a, b in zip(spf, spf[1:]):
    try:
        alt = (float(a["DRGDP4"]) + float(a["DRGDP5"]) + float(a["DRGDP6"])) / 3
        neu = (float(b["DRGDP3"]) + float(b["DRGDP4"]) + float(b["DRGDP5"])) / 3
    except (TypeError, ValueError):
        continue
    j, q = int(b["YEAR"]), int(b["QUARTER"])
    d = f"{j}-{q * 3 - 1:02d}-20"
    if d < AB or abs(neu - alt) < 0.1:
        continue
    E.append({"d": d, "n": f"Ökonomen {'heben' if neu > alt else 'senken'} Wachstumsprognose ({kom(alt)} auf {kom(neu)} %)",
              "t": "Prognosen", "k": "up" if neu > alt else "down", "quelle": SPF})

E.sort(key=lambda e: e["d"])
Path(__file__).parent.joinpath("quellen").mkdir(exist_ok=True)
aus = {"id": "wirtschaft", "name": "Wirtschaft", "rang": 1, "ereignisse": E}
Path(__file__).parent.joinpath("quellen", "wirtschaft.json").write_text(json.dumps(aus, ensure_ascii=False, indent=0))
zaehl = {}
for e in E:
    zaehl[(e["t"], e["k"])] = zaehl.get((e["t"], e["k"]), 0) + 1
print(len(E), zaehl, E[0]["d"], E[-1]["d"])
print(*[f"{e['d']} {e['k']:5} {e['n']}" for e in E if e["t"] in ("Zinsen", "Prognosen")], sep="\n")
