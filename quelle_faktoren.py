"""Baut 24 weitere Quellen. Die Richtung jeder Regel steht vorab aus Theorie oder Studie fest und wird nie umgedreht.

Aufruf: python quelle_faktoren.py <ordner mit den Rohdaten> <kurs für Trend> <kurs für Gleichlauf> [zielordner]

Reihen: am 1. jedes Monats zählt die Änderung der letzten 30 Tage (Schnitt der letzten 7 Werte gegen den Schnitt
der 7 Werte 30 Tage davor), bekannt ist also nur, was vor dem Termin passiert ist.
  Dollar Index fällt: Anstieg. Nasdaq steigt: Anstieg. Gold steigt: Anstieg (digitales Gold). Öl steigt: Rücksetzer (Inflation).
  VIX steigt: Rücksetzer. US 10 Jahres Zins steigt: Rücksetzer. Yen wird stärker: Rücksetzer (Carry Trade läuft aus).
  Kupfer steigt: Anstieg (Konjunktur). Nvidia steigt: Anstieg (KI Boom).
  Stablecoin Menge, Hashrate, aktive Adressen steigen: Anstieg.
  Wikipedia Aufrufe Bitcoin steigen: Anstieg (Kristoufek 2013). Wikipedia Aufrufe Recession steigen: Rücksetzer (Angst).
Trend 200 Tage: am 1. des Monats BTC über dem 200 Tage Schnitt Anstieg, darunter Rücksetzer.
Mondphasen: Neumond Anstieg, Vollmond Rücksetzer (Yuan, Zheng, Zhu 2006). Merkur rückläufig Rücksetzer, direkt Anstieg.
Sonnenflecken: Monatsmittel steigt Anstieg (Tschischewski, Sonnenaktivität und Massenerregung).
Magnetsturm: Kp ab 7, Tag danach Rücksetzer, höchstens einmal je 7 Tage (Krivelyova, Robotti 2003).
Wetter New York: Sonnenstunden des Monats über dem Schnitt 2010 bis 2021 Anstieg, darunter Rücksetzer (Hirshleifer, Shumway 2003).
Erdbeben ab Stärke 7: Tag danach Rücksetzer. Kein Wirkweg bekannt, dient als Gegenprobe.
Sell in May: November bis April Anstieg, Mai bis Oktober Rücksetzer. Chinesisches Neujahr: 30 Tage davor Rücksetzer, am Fest Anstieg.
Zufall: Münzwurf je Monat mit festem Startwert 42. Kontrolle, zeigt was reines Glück schafft.
"""
import csv
import datetime as dt
import json
import math
import random
import sys
from pathlib import Path

import ephem

R, BTC_LANG, BTC5 = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
AB, BIS, HEUTE = dt.date(2010, 6, 1), dt.date(2031, 11, 6), dt.date(2026, 11, 5)
ORDNER = Path(sys.argv[4]) if len(sys.argv) > 4 else Path(__file__).parent / "quellen"  # für ETH: quellen/eth
ORDNER.mkdir(parents=True, exist_ok=True)
UTC = lambda t: dt.datetime.fromtimestamp(int(t), dt.UTC).date()
kom = lambda v, n=1: f"{v:.{n}f}".replace(".", ",")


def monate(ende):
    j, m = AB.year, AB.month
    while dt.date(j, m, 1) <= ende:
        yield dt.date(j, m, 1)
        j, m = (j + 1, 1) if m == 12 else (j, m + 1)


def yahoo(pfad):
    r = json.load(open(pfad))["chart"]["result"][0]
    return {UTC(t): float(c) for t, c in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]) if c is not None}


def schnitt(s, tage, bis):
    w = [s[d] for d in tage if d < bis][-7:]
    return sum(w) / len(w) if len(w) == 7 else None


btc = yahoo(BTC5)
btc_tage = sorted(d for d in btc if d <= HEUTE)


def gleichlauf(s, vorzeichen):
    """Korrelation der 30 Tage Bewegung im selben Zeitfenster wie BTC. Zeigt Gleichlauf, nicht Vorhersage."""
    tage, letzt, w = sorted(s), None, {}
    i = 0
    for d in btc_tage:
        while i < len(tage) and tage[i] <= d:
            letzt = s[tage[i]]
            i += 1
        w[d] = letzt
    vor = lambda d: d - dt.timedelta(days=30)
    gut = [d for d in btc_tage if (w.get(d) or 0) > 0 and (w.get(vor(d)) or 0) > 0]  # Öl war im April 2020 negativ
    a = [math.log(w[d] / w[vor(d)]) for d in gut]
    b = [math.log(btc[d] / btc[vor(d)]) for d in gut]
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    z = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    return round(vorzeichen * z / math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) * 100, 1)


def schreibe(id_, name, rang, ereignisse, **extra):
    ereignisse = sorted((e for e in ereignisse if AB.isoformat() <= e["d"] <= BIS.isoformat()), key=lambda e: e["d"])
    (ORDNER / f"{id_}.json").write_text(json.dumps({"id": id_, "name": name, "rang": rang, **extra, "ereignisse": ereignisse}, ensure_ascii=False, indent=0))
    z = {}
    for e in ereignisse:
        z[e["k"]] = z.get(e["k"], 0) + 1
    print(f"{id_:16} {len(ereignisse):4} {z} {ereignisse[0]['d']} {ereignisse[-1]['d']}", extra)


def reihe(id_, name, rang, s, steigt_gut, wort, quelle):
    """Monatliches Ereignis aus der 30 Tage Änderung. steigt_gut sagt, ob ein Anstieg der Reihe für BTC gut sein soll."""
    tage, E = sorted(s), []
    for d in monate(HEUTE):
        neu, alt = schnitt(s, tage, d), schnitt(s, tage, d - dt.timedelta(days=30))
        if not neu or not alt or neu == alt:
            continue
        hoch = neu > alt
        E.append({"d": d.isoformat(), "n": f"{wort} {'steigt' if hoch else 'fällt'} {kom(abs(neu / alt - 1) * 100)} % in 30 Tagen", "t": name,
                  "k": "up" if hoch == steigt_gut else "down", "quelle": quelle})
    schreibe(id_, name, rang, E, gleichlauf=gleichlauf(s, 1 if steigt_gut else -1))


Y = "https://finance.yahoo.com/quote/{}/history/"
rang = 10
for id_, name, datei, gut, wort, sym in (
        ("dollar", "Dollar Index", "dxy", False, "Dollar", "DX-Y.NYB"), ("nasdaq", "Nasdaq", "nasdaq", True, "Nasdaq", "%5EIXIC"),
        ("gold", "Gold", "gold", True, "Gold", "GC%3DF"), ("oel", "Ölpreis", "oel", False, "Öl", "CL%3DF"),
        ("vix", "VIX Angstindex", "vix", False, "VIX", "%5EVIX"), ("zins10", "US Zins 10 Jahre", "zins10", False, "Zins 10 Jahre", "%5ETNX"),
        ("yen", "Yen", "yen", True, "Dollar gegen Yen", "JPY%3DX"), ("kupfer", "Kupfer", "kupfer", True, "Kupfer", "HG%3DF"),
        ("nvidia", "Nvidia", "nvidia", True, "Nvidia", "NVDA")):
    reihe(id_, name, rang, yahoo(R / f"y_{datei}.json"), gut, wort, Y.format(sym))
    rang += 1

stable = {UTC(x["date"]): float(x["totalCirculating"]["peggedUSD"]) for x in json.load(open(R / "stable.json"))}
reihe("stablecoins", "Stablecoin Menge", rang, stable, True, "Stablecoin Menge", "https://defillama.com/stablecoins"); rang += 1
for id_, name, datei, wort, url in (("hashrate", "Hashrate", "hash", "Hashrate", "https://www.blockchain.com/explorer/charts/hash-rate"),
                                    ("adressen", "Aktive Adressen", "adressen", "Aktive Adressen", "https://www.blockchain.com/explorer/charts/n-unique-addresses")):
    reihe(id_, name, rang, {UTC(x["x"]): float(x["y"]) for x in json.load(open(R / f"{datei}.json"))["values"]}, True, wort, url)
    rang += 1

# Wikipedia und Sonnenflecken sind Monatswerte, bekannt ab dem 1. des Folgemonats
for id_, name, art, gut in (("wiki_bitcoin", "Wikipedia Bitcoin", "Bitcoin", True), ("wiki_rezession", "Wikipedia Rezession", "Recession", False)):
    v = [(dt.date(int(x["timestamp"][:4]), int(x["timestamp"][4:6]), 1), x["views"]) for x in json.load(open(R / f"wiki_{art}.json"))["items"]][:-1]
    E, tag = [], {}
    for (m0, a), (m1, b) in zip(v, v[1:]):
        fertig = dt.date(m1.year + (m1.month == 12), m1.month % 12 + 1, 1)
        tag[m1] = b
        if a != b:
            E.append({"d": fertig.isoformat(), "n": f"Aufrufe {art} {'steigen' if b > a else 'fallen'} {kom(abs(b / a - 1) * 100, 0)} %", "t": "Aufmerksamkeit",
                      "k": "up" if (b > a) == gut else "down", "quelle": f"https://en.wikipedia.org/wiki/{art}"})
    schreibe(id_, name, rang, E, gleichlauf=gleichlauf(tag, 1 if gut else -1))
    rang += 1

# Trend
lang = yahoo(BTC_LANG)
tage = sorted(lang)
E = []
for d in monate(HEUTE):
    w = [lang[t] for t in tage if t < d][-200:]
    if len(w) < 200:
        continue
    E.append({"d": d.isoformat(), "n": f"BTC {'über' if w[-1] > sum(w) / 200 else 'unter'} dem 200 Tage Schnitt", "t": "Trend",
              "k": "up" if w[-1] > sum(w) / 200 else "down", "quelle": "https://finance.yahoo.com/quote/BTC-USD/history/"})
schreibe("trend200", "Trend 200 Tage", rang, E); rang += 1

# Mond, bis 2031 berechenbar
E, d = [], ephem.Date("2010/6/1")
while (n := ephem.next_new_moon(d)).datetime().date() <= BIS:
    E.append({"d": n.datetime().date().isoformat(), "n": "Neumond", "t": "Mond", "k": "up", "quelle": "https://doi.org/10.1016/j.jempfin.2005.06.001"})
    d = n + 1
d = ephem.Date("2010/6/1")
while (n := ephem.next_full_moon(d)).datetime().date() <= BIS:
    E.append({"d": n.datetime().date().isoformat(), "n": "Vollmond", "t": "Mond", "k": "down", "quelle": "https://doi.org/10.1016/j.jempfin.2005.06.001"})
    d = n + 1
schreibe("mond", "Mondphasen", rang, E); rang += 1


# Merkur
def lon(d):
    b = ephem.Mercury()
    e = ephem.Date(f"{d.year}/{d.month}/{d.day} 12:00")
    b.compute(e, epoch=e)
    return math.degrees(ephem.Ecliptic(b, epoch=e).lon)


E, vor, rueck = [], lon(AB), False
for i in range(1, (BIS - AB).days + 1):
    d = AB + dt.timedelta(days=i)
    v = lon(d)
    jetzt = ((v - vor + 180) % 360 - 180) < 0
    if jetzt != rueck:
        E.append({"d": d.isoformat(), "n": "Merkur wird rückläufig" if jetzt else "Merkur wird direkt", "t": "Merkur", "k": "down" if jetzt else "up",
                  "quelle": "https://en.wikipedia.org/wiki/Apparent_retrograde_motion"})
    vor, rueck = v, jetzt
schreibe("merkur", "Merkur rückläufig", rang, E); rang += 1

# Sonnenflecken
sonne = {}
for z in csv.reader(open(R / "sonne.csv"), delimiter=";"):
    if float(z[3]) >= 0:
        sonne[dt.date(int(z[0]), int(z[1]), 1)] = float(z[3])
E = []
for m in sorted(sonne):
    a = sonne.get(dt.date(m.year - (m.month == 1), (m.month - 2) % 12 + 1, 1))
    if a is None or a == sonne[m]:
        continue
    fertig = dt.date(m.year + (m.month == 12), m.month % 12 + 1, 1)
    E.append({"d": fertig.isoformat(), "n": f"Sonnenflecken {'steigen' if sonne[m] > a else 'fallen'} auf {kom(sonne[m])}", "t": "Sonne", "k": "up" if sonne[m] > a else "down",
              "quelle": "https://www.sidc.be/SILSO/datafiles"})
schreibe("sonnenflecken", "Sonnenflecken", rang, E); rang += 1

# Magnetstürme
k = json.load(open(R / "kp.json"))
tag_max = {}
for t, v in zip(k["datetime"], k["Kp"]):
    d = dt.date.fromisoformat(t[:10])
    tag_max[d] = max(tag_max.get(d, 0), v)
E, letzt = [], dt.date(2000, 1, 1)
for d in sorted(tag_max):
    if tag_max[d] >= 7 and (d - letzt).days >= 7:
        letzt = d
        E.append({"d": (d + dt.timedelta(days=1)).isoformat(), "n": f"Magnetsturm, Kp {kom(tag_max[d])}", "t": "Magnetsturm", "k": "down", "quelle": "https://kp.gfz-potsdam.de/en/"})
schreibe("magnetsturm", "Magnetstürme", rang, E); rang += 1

# Wetter New York
w = json.load(open(R / "wetter.json"))["daily"]
je = {}
for t, v in zip(w["time"], w["sunshine_duration"]):
    if v is not None:
        d = dt.date.fromisoformat(t)
        je.setdefault((d.year, d.month), []).append(v / 3600)
monat = {a: sum(v) for a, v in je.items() if len(v) >= 28}
norm = {m: sum(v for (j, mm), v in monat.items() if mm == m and j <= 2021) / 12 for m in range(1, 13)}
E = []
for (j, m), v in sorted(monat.items()):
    fertig = dt.date(j + (m == 12), m % 12 + 1, 1)
    E.append({"d": fertig.isoformat(), "n": f"New York {kom(v, 0)} Sonnenstunden, Schnitt {kom(norm[m], 0)}", "t": "Wetter", "k": "up" if v > norm[m] else "down",
              "quelle": "https://open-meteo.com/en/docs/historical-weather-api"})
schreibe("wetter_ny", "Wetter New York", rang, E); rang += 1

# Erdbeben
E = []
for f in json.load(open(R / "beben.json"))["features"]:
    d = dt.datetime.fromtimestamp(f["properties"]["time"] / 1000, dt.UTC).date() + dt.timedelta(days=1)
    E.append({"d": d.isoformat(), "n": f"Erdbeben Stärke {kom(f['properties']['mag'])}", "t": "Erdbeben", "k": "down", "quelle": "https://earthquake.usgs.gov/earthquakes/search/"})
schreibe("erdbeben", "Erdbeben", rang, E); rang += 1

# Kalender
schreibe("sell_in_may", "Sell in May", rang, [
    {"d": d.isoformat(), "n": "Mai bis Oktober" if 5 <= d.month <= 10 else "November bis April", "t": "Kalender", "k": "down" if 5 <= d.month <= 10 else "up",
     "quelle": "https://www.investopedia.com/terms/s/sell-in-may-and-go-away.asp"} for d in monate(BIS)]); rang += 1
E = []
for s in ("2011-02-03", "2012-01-23", "2013-02-10", "2014-01-31", "2015-02-19", "2016-02-08", "2017-01-28", "2018-02-16", "2019-02-05", "2020-01-25", "2021-02-12", "2022-02-01", "2023-01-22", "2024-02-10", "2025-01-29", "2026-02-17", "2027-02-06", "2028-01-26", "2029-02-13", "2030-02-03", "2031-01-23"):
    d = dt.date.fromisoformat(s)
    url = "https://en.wikipedia.org/wiki/Chinese_New_Year"
    E.append({"d": (d - dt.timedelta(days=30)).isoformat(), "n": "30 Tage vor Chinesisch Neujahr", "t": "Kalender", "k": "down", "quelle": url})
    E.append({"d": s, "n": "Chinesisch Neujahr", "t": "Kalender", "k": "up", "quelle": url})
schreibe("neujahr", "Chinesisch Neujahr", rang, E); rang += 1

# Zufall, fester Startwert, damit die Linie nie nachträglich ausgesucht werden kann
muenze = random.Random(42)
schreibe("zufall", "Zufall (Kontrolle)", 99, [
    {"d": d.isoformat(), "n": "Münzwurf", "t": "Kontrolle", "k": muenze.choice(("up", "down")), "quelle": "https://en.wikipedia.org/wiki/Coin_flipping"} for d in monate(HEUTE)])
