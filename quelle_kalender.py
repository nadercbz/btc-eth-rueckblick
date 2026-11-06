"""Baut die Quellen, die allein aus festen Regeln entstehen. Keine Regel schaut auf Kurse ab 2022.

Aufruf: python quelle_kalender.py <btc_lang.json von Yahoo> <fng.json von alternative.me> <hoehe des letzten Blocks> <m2.csv der Fed, H.6>

Halving Zyklus (halving.json), abgeleitet nur aus den Zyklen 2012, 2016, 2020:
  Hochs lagen 12, 17, 18 Monate nach dem Halving (Schnitt rund 16), Tiefs 26 und 29 Monate danach (rund 28).
  Monat 0 bis 15 Anstieg, Monat 16 bis 27 Rücksetzer, ab Monat 28 Anstieg bis zum nächsten Halving.
  Nächstes Halving: Block 1.050.000, Datum aus der Blockhöhe bei 10 Minuten je Block geschätzt.
Saisonalität (saison.json): Median je Kalendermonat nur aus BTC Kursen bis Ende 2021. Plus Anstieg, Minus Rücksetzer.
US Wahlzyklus (wahlzyklus.json), Regel aus der Aktienmarkt Literatur (Hirsch, Stock Trader's Almanac):
  Oktober des Zwischenwahljahrs bis Dezember des Wahljahrs Anstieg, sonst Rücksetzer.
Stimmung (stimmung.json), gegen die Herde: Fear & Greed bis 20 Anstieg, ab 80 Rücksetzer,
  höchstens ein Ereignis je 30 Tage, solange der Wert im Bereich bleibt. Keine Zukunft, der Wert ist nicht vorab bekannt.
Geldmenge M2 (geldmenge.json): Jahreswachstum steigt um mindestens 0,1 Punkte Anstieg, fällt Rücksetzer. Keine Zukunft.
"""
import csv
import datetime as dt
import json
import statistics
import sys
from pathlib import Path

BTC, FNG, HOEHE, M2 = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
AB, BIS = dt.date(2010, 6, 1), dt.date(2031, 11, 6)
HEUTE = dt.date(2026, 11, 6)
ORDNER = Path(__file__).parent / "quellen"
ORDNER.mkdir(exist_ok=True)
MONAT = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]


def monate(start, ende):
    j, m = start.year, start.month
    while dt.date(j, m, 1) <= ende:
        yield dt.date(j, m, 1)
        j, m = (j + 1, 1) if m == 12 else (j, m + 1)


def plus_monate(d, n):
    m = d.month - 1 + n
    return dt.date(d.year + m // 12, m % 12 + 1, min(d.day, 28))


def schreibe(id_, name, rang, ereignisse):
    ereignisse = [e for e in ereignisse if AB.isoformat() <= e["d"] <= BIS.isoformat()]
    (ORDNER / f"{id_}.json").write_text(json.dumps({"id": id_, "name": name, "rang": rang, "ereignisse": ereignisse}, ensure_ascii=False, indent=0))
    z = {}
    for e in ereignisse:
        z[e["k"]] = z.get(e["k"], 0) + 1
    print(id_, len(ereignisse), z, ereignisse[0]["d"], ereignisse[-1]["d"])


# Halving
naechstes = HEUTE + dt.timedelta(minutes=10 * (1_050_000 - HOEHE))
print("Nächstes Halving geschätzt", naechstes)
HALVINGS = [dt.date(2012, 11, 28), dt.date(2016, 7, 9), dt.date(2020, 5, 11), dt.date(2024, 4, 20), naechstes]
E = []
for i, h in enumerate(HALVINGS):
    schluss = HALVINGS[i + 1] if i + 1 < len(HALVINGS) else BIS
    n = 0
    while (d := plus_monate(h, n)) < schluss:
        k = "up" if n <= 15 or n >= 28 else "down"
        geschaetzt = ", Termin geschätzt" if h == naechstes else ""
        E.append({"d": d.isoformat(), "n": f"Monat {n} nach Halving {h.year}{geschaetzt}", "t": "Halving", "k": k,
                  "quelle": "https://en.bitcoin.it/wiki/Controlled_supply"})
        n += 1
schreibe("halving", "Halving Zyklus", 5, E)

# Saisonalität, nur Kurse bis Ende 2021
r = json.load(open(BTC))["chart"]["result"][0]
kurs = {}
for t, c in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]):
    if c is not None:
        kurs[dt.datetime.fromtimestamp(t, dt.UTC).date()] = float(c)
monatsende = {}
for d in sorted(kurs):
    monatsende[(d.year, d.month)] = kurs[d]
je = {m: [] for m in range(1, 13)}
for (j, m), v in monatsende.items():
    vor = monatsende.get((j - 1, 12) if m == 1 else (j, m - 1))
    if vor and j <= 2021:
        je[m].append(v / vor - 1)
RICHTUNG = {m: statistics.median(w) > 0 for m, w in je.items()}
print("Saison bis 2021:", {MONAT[m - 1][:3]: f"{statistics.median(w) * 100:+.1f}%/{len(w)}" for m, w in je.items()})
schreibe("saison", "Saisonalität", 6, [
    {"d": d.isoformat(), "n": f"{MONAT[d.month - 1]} war bis 2021 im Median {'positiv' if RICHTUNG[d.month] else 'negativ'}", "t": "Saison",
     "k": "up" if RICHTUNG[d.month] else "down", "quelle": "https://finance.yahoo.com/quote/BTC-USD/history/"}
    for d in monate(AB, BIS)])

# US Wahlzyklus. Wahljahre 2020, 2024, 2028, 2032, Zwischenwahljahre 2022, 2026, 2030
def wahl_k(d):
    rest = d.year % 4
    if rest == 2:
        return "up" if d.month >= 10 else "down"
    return "up" if rest in (3, 0) else "down"


schreibe("wahlzyklus", "US Wahlzyklus", 7, [
    {"d": d.isoformat(), "n": f"Wahlzyklus: {['Wahljahr', 'Jahr nach der Wahl', 'Zwischenwahljahr', 'Jahr vor der Wahl'][d.year % 4]}", "t": "Wahlzyklus",
     "k": wahl_k(d), "quelle": "https://www.investopedia.com/terms/p/presidentialelection.asp"}
    for d in monate(AB, BIS)])

# Stimmung
werte = sorted(((dt.datetime.fromtimestamp(int(x["timestamp"]), dt.UTC).date(), int(x["value"])) for x in json.load(open(FNG))["data"]))
E, letzt = [], {"up": dt.date(2000, 1, 1), "down": dt.date(2000, 1, 1)}
for d, v in werte:
    k = "up" if v <= 20 else "down" if v >= 80 else None
    if k and (d - letzt[k]).days >= 30:
        letzt[k] = d
        E.append({"d": d.isoformat(), "n": f"Fear & Greed bei {v}, {'extreme Angst' if k == 'up' else 'extreme Gier'}", "t": "Stimmung", "k": k,
                  "quelle": "https://alternative.me/crypto/fear-and-greed-index/"})
schreibe("stimmung", "Stimmung", 8, E)

# Geldmenge: Jahreswachstum von M2, saisonbereinigt. Veröffentlichung vorsichtig am 28. des Folgemonats
zeilen = list(csv.reader(open(M2)))
spalte = next(z for z in zeilen if z[0] == "Time Period").index("M2.M")
m2 = {tuple(map(int, z[0].split("-"))): float(z[spalte]) for z in zeilen if z[0][:2] == "20" and z[spalte] not in ("", "ND")}
rate = {(j, m): (v / m2[(j - 1, m)] - 1) * 100 for (j, m), v in m2.items() if (j - 1, m) in m2}
E = []
for (j, m), v in sorted(rate.items()):
    vor = rate.get((j - 1, 12) if m == 1 else (j, m - 1))
    if vor is None or abs(v - vor) < 0.1:
        continue
    fj, fm = (j + 1, 1) if m == 12 else (j, m + 1)
    E.append({"d": f"{fj}-{fm:02d}-28", "n": f"M2 Jahreswachstum {'steigt' if v > vor else 'fällt'} auf {v:.1f} % ({MONAT[m - 1]})".replace(".", ","), "t": "Geldmenge",
              "k": "up" if v > vor else "down", "quelle": "https://www.federalreserve.gov/releases/h6/"})
schreibe("geldmenge", "Geldmenge M2", 9, E)
