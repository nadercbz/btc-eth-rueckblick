"""Rechnet die Daten fuer btc_astro_rueckblick.html: Ereignisse 2022 bis heute plus echte BTC Tageskurse.

Aufruf: python btc_astro_rueckblick_daten.py <btc.json von Yahoo> <ausgabe.js>
Braucht ephem und numpy. Regeln sind dieselben wie in btc_astro_chart.html und werden nicht an den Kurs angepasst:
  Trigon, Sextil: Anstieg. Neptun Sextil Pluto: leichter Anstieg.
  Quadrat, Opposition: Sprung, dann Ruecksetzer. Konjunktion, Finsternis: Richtung offen.
  Sonnenfinsternis im Wassermann: eher nach oben.
  Mars rueckläufig: Ruecksetzer, Mars direkt: Anstieg. Venus rueckläufig: Ruecksetzer.
Weitere Quellen liegen als JSON in quellen/ und werden automatisch zu Haekchen im Chart.
"""
import datetime as dt
import json
import math
import sys
from pathlib import Path

import ephem
import numpy as np

START = dt.date(2010, 6, 1)  # Vorlauf vor dem ersten Kurs
PFAD, AUS = sys.argv[1], sys.argv[2]
COIN = sys.argv[3] if len(sys.argv) > 3 else "BTC"

r = json.load(open(PFAD))["chart"]["result"][0]
KURS = {}
for t, c in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]):
    if c is not None:
        KURS[dt.datetime.fromtimestamp(t, dt.UTC).date()] = float(c)
ENDE = max(KURS) - dt.timedelta(days=1)  # letzter voller Tag
CHART_START = min(KURS)  # erster Marktpreis
KURS = {d: v for d, v in KURS.items() if d <= ENDE}
ZUKUNFT_ENDE = dt.date(2031, 11, 6)  # alles danach wäre geraten, Termine fehlen
TAGE = [START + dt.timedelta(days=i) for i in range((ZUKUNFT_ENDE - START).days + 1)]


def lon(cls, d):
    b = cls()
    e = ephem.Date(f"{d.year}/{d.month}/{d.day} 12:00")
    b.compute(e, epoch=e)
    return math.degrees(ephem.Ecliptic(b, epoch=e).lon)


LANG = {"Jupiter": ephem.Jupiter, "Saturn": ephem.Saturn, "Uranus": ephem.Uranus,
        "Neptun": ephem.Neptune, "Pluto": ephem.Pluto}
ASP = {"Konjunktion": 0, "Sextil": 60, "Quadrat": 90, "Trigon": 120, "Opposition": 180}
THEMA = {"Konjunktion": "Neuer Zyklus", "Sextil": "Chance", "Trigon": "Aufbau", "Quadrat": "Spannung", "Opposition": "Spannung"}
NAMEN = list(LANG)
L = {n: np.array([lon(LANG[n], d) for d in TAGE]) for n in NAMEN}
E = []
for a in range(len(NAMEN)):
    for b in range(a + 1, len(NAMEN)):
        s = (L[NAMEN[a]] - L[NAMEN[b]] + 180) % 360 - 180
        for asp, grad in ASP.items():
            for ziel in ({grad, -grad} if grad not in (0, 180) else {grad}):
                f = (s - ziel + 180) % 360 - 180
                for i in range(len(f) - 1):
                    if f[i] == 0 or (f[i] * f[i + 1] < 0 and abs(f[i]) < 3):
                        n = f"{NAMEN[a]} {asp} {NAMEN[b]}"
                        if asp in ("Trigon", "Sextil"):
                            k = "mild" if n == "Neptun Sextil Pluto" else "up"
                        elif asp == "Konjunktion":
                            k = "open"
                        else:
                            k = "spike"
                        E.append({"d": TAGE[i], "n": n, "t": THEMA[asp], "k": k, "r": "aspekt" if k != "spike" else "quadrat"})

FIN = [("2010-06-26", "Partielle Mondfinsternis"), ("2010-07-11", "Totale Sonnenfinsternis"), ("2010-12-21", "Totale Mondfinsternis"),
       ("2011-01-04", "Partielle Sonnenfinsternis"), ("2011-06-01", "Partielle Sonnenfinsternis"), ("2011-06-15", "Totale Mondfinsternis"),
       ("2011-07-01", "Partielle Sonnenfinsternis"), ("2011-11-25", "Partielle Sonnenfinsternis"), ("2011-12-10", "Totale Mondfinsternis"),
       ("2012-05-20", "Ringförmige Sonnenfinsternis"), ("2012-06-04", "Partielle Mondfinsternis"), ("2012-11-13", "Totale Sonnenfinsternis"),
       ("2012-11-28", "Halbschatten Mondfinsternis"), ("2013-04-25", "Partielle Mondfinsternis"), ("2013-05-10", "Ringförmige Sonnenfinsternis"),
       ("2013-05-25", "Halbschatten Mondfinsternis"), ("2013-10-18", "Halbschatten Mondfinsternis"), ("2013-11-03", "Hybride Sonnenfinsternis"),
       ("2014-04-15", "Totale Mondfinsternis"), ("2014-04-29", "Ringförmige Sonnenfinsternis"), ("2014-10-08", "Totale Mondfinsternis"),
       ("2014-10-23", "Partielle Sonnenfinsternis"), ("2015-03-20", "Totale Sonnenfinsternis"), ("2015-04-04", "Totale Mondfinsternis"),
       ("2015-09-13", "Partielle Sonnenfinsternis"), ("2015-09-28", "Totale Mondfinsternis"), ("2016-03-09", "Totale Sonnenfinsternis"),
       ("2016-03-23", "Halbschatten Mondfinsternis"), ("2016-09-01", "Ringförmige Sonnenfinsternis"), ("2016-09-16", "Halbschatten Mondfinsternis"),
       ("2017-02-11", "Halbschatten Mondfinsternis"), ("2017-02-26", "Ringförmige Sonnenfinsternis"), ("2017-08-07", "Partielle Mondfinsternis"),
       ("2017-08-21", "Totale Sonnenfinsternis"), ("2018-01-31", "Totale Mondfinsternis"), ("2018-02-15", "Partielle Sonnenfinsternis"),
       ("2018-07-13", "Partielle Sonnenfinsternis"), ("2018-07-27", "Totale Mondfinsternis"), ("2018-08-11", "Partielle Sonnenfinsternis"),
       ("2019-01-06", "Partielle Sonnenfinsternis"), ("2019-01-21", "Totale Mondfinsternis"), ("2019-07-02", "Totale Sonnenfinsternis"),
       ("2019-07-16", "Partielle Mondfinsternis"), ("2019-12-26", "Ringförmige Sonnenfinsternis"), ("2020-01-10", "Halbschatten Mondfinsternis"),
       ("2020-06-05", "Halbschatten Mondfinsternis"), ("2020-06-21", "Ringförmige Sonnenfinsternis"), ("2020-07-05", "Halbschatten Mondfinsternis"),
       ("2020-11-30", "Halbschatten Mondfinsternis"), ("2020-12-14", "Totale Sonnenfinsternis"), ("2021-05-26", "Totale Mondfinsternis"),
       ("2021-06-10", "Ringförmige Sonnenfinsternis"), ("2021-11-19", "Partielle Mondfinsternis"), ("2021-12-04", "Totale Sonnenfinsternis"),
       ("2022-04-30", "Partielle Sonnenfinsternis"), ("2022-05-16", "Totale Mondfinsternis"),
       ("2022-10-25", "Partielle Sonnenfinsternis"), ("2022-11-08", "Totale Mondfinsternis"),
       ("2023-04-20", "Hybride Sonnenfinsternis"), ("2023-05-05", "Halbschatten Mondfinsternis"),
       ("2023-10-14", "Ringförmige Sonnenfinsternis"), ("2023-10-28", "Partielle Mondfinsternis"),
       ("2024-03-25", "Halbschatten Mondfinsternis"), ("2024-04-08", "Totale Sonnenfinsternis"),
       ("2024-09-18", "Partielle Mondfinsternis"), ("2024-10-02", "Ringförmige Sonnenfinsternis"),
       ("2025-03-14", "Totale Mondfinsternis"), ("2025-03-29", "Partielle Sonnenfinsternis"),
       ("2025-09-07", "Totale Mondfinsternis"), ("2025-09-21", "Partielle Sonnenfinsternis"),
       ("2026-02-17", "Ringförmige Sonnenfinsternis"), ("2026-03-03", "Totale Mondfinsternis"),
       ("2026-08-12", "Totale Sonnenfinsternis"), ("2026-08-28", "Partielle Mondfinsternis"),
       ("2027-02-06", "Ringförmige Sonnenfinsternis"), ("2027-02-20", "Halbschatten Mondfinsternis"),
       ("2027-07-18", "Halbschatten Mondfinsternis"), ("2027-08-02", "Totale Sonnenfinsternis"),
       ("2027-08-17", "Halbschatten Mondfinsternis"), ("2028-01-12", "Partielle Mondfinsternis"),
       ("2028-01-26", "Ringförmige Sonnenfinsternis"), ("2028-07-06", "Partielle Mondfinsternis"),
       ("2028-07-22", "Totale Sonnenfinsternis"), ("2028-12-31", "Totale Mondfinsternis"),
       ("2029-01-14", "Partielle Sonnenfinsternis"), ("2029-06-12", "Partielle Sonnenfinsternis"),
       ("2029-06-26", "Totale Mondfinsternis"), ("2029-07-11", "Partielle Sonnenfinsternis"),
       ("2029-12-05", "Partielle Sonnenfinsternis"), ("2029-12-20", "Totale Mondfinsternis"),
       ("2030-06-01", "Ringförmige Sonnenfinsternis"), ("2030-06-15", "Partielle Mondfinsternis"),
       ("2030-11-25", "Totale Sonnenfinsternis"), ("2030-12-09", "Halbschatten Mondfinsternis"),
       ("2031-05-07", "Halbschatten Mondfinsternis"), ("2031-05-21", "Ringförmige Sonnenfinsternis"),
       ("2031-06-05", "Halbschatten Mondfinsternis"), ("2031-10-30", "Halbschatten Mondfinsternis")]
for s, n in FIN:
    d = dt.date.fromisoformat(s)
    m = ephem.Moon(ephem.Date(f"{d.year}/{d.month}/{d.day} 12:00"))
    assert m.phase < 8 or m.phase > 92, (s, m.phase)
    sonne = lon(ephem.Sun, d)
    wassermann = 300 <= sonne < 330 and "Sonnen" in n
    E.append({"d": d, "n": n + (", Wassermann" if wassermann else ""), "t": "Abschluss" if "Mond" in n else "Neubeginn",
              "k": "upopen" if wassermann else "open", "r": "finsternis"})

PHASEN = []
for name, cls, r_key in (("Mars", ephem.Mars, "mars"), ("Venus", ephem.Venus, "venus")):
    l = np.array([lon(cls, d) for d in TAGE])
    rueck = ((np.diff(l) + 180) % 360 - 180) < 0
    von = None
    for i in range(len(rueck)):
        if rueck[i] and (i == 0 or not rueck[i - 1]):
            von = TAGE[i]
            E.append({"d": von, "n": f"{name} wird rückläufig", "t": "Bremse", "k": "down", "r": r_key})
        if not rueck[i] and i > 0 and rueck[i - 1]:
            PHASEN.append({"von": str(von), "bis": str(TAGE[i]), "n": f"{name} rückläufig"})
            if name == "Mars":
                E.append({"d": TAGE[i], "n": "Mars wird direkt", "t": "Bremse löst sich", "k": "up", "r": r_key})
            von = None
    if von:
        PHASEN.append({"von": str(von), "bis": str(ZUKUNFT_ENDE), "n": f"{name} rückläufig"})

E.sort(key=lambda e: (e["d"], e["n"]))
for e in E:
    e["d"] = str(e["d"])

# Weitere Quellen: jede Datei in quellen/ wird automatisch ein eigenes Häkchen.
# Format: {"id": "...", "name": "...", "rang": 2, "ereignisse": [{"d","n","t","k","quelle"}]}
QUELLEN = [{"id": "astro", "name": "Astrologie", "rang": 0, "ereignisse": E}]
for datei in sorted((Path(__file__).parent / "quellen").glob("*.json")):
    QUELLEN.append(json.loads(datei.read_text()))
if COIN == "ETH":  # quellen/eth überschreibt gleichnamige Quellen und bringt eigene mit
    je_id = {q["id"]: q for q in QUELLEN}
    for datei in sorted((Path(__file__).parent / "quellen" / "eth").glob("*.json")):
        q = json.loads(datei.read_text())
        je_id[q["id"]] = q
    QUELLEN = list(je_id.values())
    NAMEN_ETH = {"adressen": "Aktive Adressen BTC", "hashrate": "Hashrate BTC", "stablecoins": "Stablecoin Menge gesamt", "halving": "Halving Zyklus BTC"}
    for q in QUELLEN:
        q["name"] = NAMEN_ETH.get(q["id"], q["name"])
QUELLEN.sort(key=lambda q: q.get("rang", 99))
GRUPPEN = {"Kosmos": "astro mond merkur sonnenflecken", "Märkte": "nasdaq nvidia gold kupfer oel dollar yen vix zins10",
           "Wirtschaft und Politik": "wirtschaft geldmenge krieg_politik wahlzyklus", "Krypto": "halving trend200 stablecoins hashrate adressen stimmung krypto_ereignisse eth_ereignisse tvl_eth stable_eth adressen_eth eth_btc btc_takt",
           "Aufmerksamkeit": "influencer popkultur wiki_bitcoin wiki_ethereum wiki_rezession", "Natur": "magnetsturm wetter_ny erdbeben", "Kalender": "saison sell_in_may neujahr", "Kontrolle": "zufall"}
for q in QUELLEN:
    q["gruppe"] = q.get("gruppe") or next((g for g, ids in GRUPPEN.items() if q["id"] in ids.split()), "Weitere")

DEUT = {"up": "Anstieg", "mild": "Leichter Anstieg", "down": "Rücksetzer", "spike": "Sprung, dann Rücksetzer",
        "open": "Sprung, Richtung offen", "upopen": "Sprung, eher nach oben"}
RICHTUNG = {"up": 1, "mild": 1, "upopen": 1, "down": -1, "spike": -1}
sortiert = sorted(KURS)
for q in QUELLEN:
    behalten = []
    for e in q["ereignisse"]:
        assert e["k"] in DEUT and "<" not in e["n"] and e.get("quelle", "https://").startswith("https://"), e
        d = dt.date.fromisoformat(e["d"])
        if d > ZUKUNFT_ENDE or d < CHART_START - dt.timedelta(days=31):
            continue
        e["deut"], e["echt"] = DEUT[e["k"]], None
        e["zukunft"] = d > ENDE
        z = d + dt.timedelta(days=30)
        if d in KURS and z in KURS:
            e["echt"] = round((KURS[z] / KURS[d] - 1) * 100, 1)
        e["treffer"] = None if e["echt"] is None or e["k"] not in RICHTUNG else (e["echt"] > 0) == (RICHTUNG[e["k"]] > 0)
        behalten.append(e)
    q["ereignisse"] = sorted(behalten, key=lambda e: (e["d"], e["n"]))
    # Zukunft zählt nur, wenn vorab Termine mit Richtung feststehen
    # Ein Datenpunkt, der nur in den nächsten Wochen erscheint, zählt nicht als Blick nach vorn
    q["zukunft"] = any(e["k"] in RICHTUNG and e["d"] > str(ENDE + dt.timedelta(days=45)) for e in q["ereignisse"])

KURSE = [[str(d), round(KURS[d], 4) if KURS[d] < 100 else round(KURS[d])] for d in sortiert if d >= CHART_START]
with open(AUS, "w") as f:
    f.write(f"const COIN = {json.dumps(COIN)};\n")
    f.write("const QUELLEN = " + json.dumps(QUELLEN, ensure_ascii=False) + ";\n")
    f.write("const RUECKLAEUFE = " + json.dumps(PHASEN, ensure_ascii=False) + ";\n")
    f.write("const KURSE = " + json.dumps(KURSE, separators=(",", ":")) + ";\n")


def beitrag(k, t):
    if t <= 0:
        return 0
    x = min(1, t / 30)
    if k == "up":
        return 8 * x
    if k in ("mild", "upopen"):
        return 4 * x
    if k == "down":
        return -8 * x
    if k == "spike":
        return 8 * t / 7 if t < 7 else 8 - 12 * min(1, (t - 7) / 23)
    return 0


tage = [d for d in sortiert if d >= CHART_START]
btc = np.array([KURS[d] for d in tage])
linie = {}
for q in QUELLEN:
    # Jedes Ereignis wirkt 30 Tage als Rampe, danach bleibt sein Endwert stehen
    tl, rest = np.zeros(len(tage)), np.zeros(len(tage))
    for e in q["ereignisse"]:
        i0 = (dt.date.fromisoformat(e["d"]) - tage[0]).days
        for t in range(1, 31):
            if 0 <= i0 + t < len(tage):
                tl[i0 + t] += beitrag(e["k"], t)
        if i0 + 31 < len(tage):
            rest[max(i0 + 31, 0)] += beitrag(e["k"], 31)
    tl += np.cumsum(rest)
    linie[q["id"]] = tl - tl[0]
sig = lambda l: float(np.std(l[30:] - l[:-30]))
basis = sig(linie["astro"])
faktor = {q["id"]: basis / sig(linie[q["id"]]) for q in QUELLEN}
db = np.log(btc[30:] / btc[:-30])  # logarithmisch, sonst bestimmen die Monate mit +500 % aus 2010 bis 2013 alles


I22 = next(i for i, d in enumerate(tage) if str(d) >= "2022-01-01")


def bewerte(name, l, ev, ab=0):
    # ab: erst rechnen, wenn die Quelle Daten hat
    dg, bb = (l[30:] - l[:-30])[ab:], db[ab:]
    kor = [np.corrcoef(np.roll(dg, o), bb)[0, 1] for o in range(0, len(dg), 3)]
    ger = [e for e in ev if e["treffer"] is not None]
    p = float(np.mean(np.array(kor) >= kor[0]))
    print(f"{name:26} Ereignisse {len(ev):3}, Treffer {sum(e['treffer'] for e in ger):3}/{len(ger):3}, Korr30 {kor[0] * 100:+6.1f}%, p {p:.3f}, gleiche Richtung {np.mean((dg > 0) == (bb > 0)) * 100:.1f}%")
    return {"korr": round(float(kor[0]) * 100, 1), "p": round(p, 3)}


print("Zeitraum", tage[0], tage[-1], "BTC im Plus", round(float(np.mean(db > 0)) * 100, 1))
RANG = {}
for q in QUELLEN:
    ev = [e for e in q["ereignisse"] if str(CHART_START) <= e["d"] <= str(ENDE)]
    ab = max((dt.date.fromisoformat(ev[0]["d"]) - tage[0]).days, 0)
    l = faktor[q["id"]] * linie[q["id"]]
    RANG[q["id"]] = bewerte(q["name"], l, ev, ab)
    RANG[q["id"]]["seit"] = ev[0]["d"][:4]
    d22 = (l[30:] - l[:-30])[I22:]
    RANG[q["id"]]["korr22"] = round(float(np.corrcoef(d22, db[I22:])[0, 1]) * 100, 1)
bewerte("Alle gleich", sum(faktor[q["id"]] * linie[q["id"]] for q in QUELLEN) / len(QUELLEN), [e for q in QUELLEN for e in q["ereignisse"] if str(CHART_START) <= e["d"] <= str(ENDE)])


# Maßstab: reine Münzwürfe je Monat. So hoch kommt eine Linie und die beste von allen allein durch Glück.
wuerfel = np.random.default_rng(7)
monat = np.array([(d.year - 2010) * 12 + d.month - 1 for d in tage])
glueck = []
for _ in range(3000):
    l = np.cumsum(wuerfel.choice((-1.0, 1.0), monat.max() + 1)[monat])
    glueck.append(float(np.corrcoef(l[30:] - l[:-30], db)[0, 1]) * 100)
glueck = np.array(glueck)
beste = glueck[:len(glueck) // len(QUELLEN) * len(QUELLEN)].reshape(-1, len(QUELLEN)).max(1)
MASS = {"q95": round(float(np.quantile(glueck, .95)), 1), "beste": round(float(np.mean(beste)), 1), "n": len(QUELLEN)}
print("Münzwürfe:", MASS)


# Optimierte Anteile: höchste Korrelation der 30 Tage Bewegungen, jeder Anteil ab 0, Summe 100 %.
# Die Anteile sind nachträglich an den Kurs angepasst. Darum zählt der Test auf Daten, die sie nicht gesehen haben.
def anteile(X, y, runden=3000):
    X, y = X - X.mean(0), y - y.mean()
    G, c = X.T @ X, X.T @ y
    w = np.zeros(X.shape[1])
    for _ in range(runden):
        for j in range(len(w)):
            w[j] = max(0.0, w[j] + (c[j] - G[j] @ w) / G[j, j])
    return w / w.sum() if w.sum() > 0 else np.full(len(w), 1 / len(w))


def nach_korr(X, y):
    """Anteil im Verhältnis zur eigenen Korrelation, Quellen mit negativer Korrelation bekommen 0."""
    c = np.array([max(0.0, np.corrcoef(X[:, j], y)[0, 1]) for j in range(X.shape[1])])
    return c / c.sum() if c.sum() > 0 else np.full(len(c), 1 / len(c))


kor = lambda a, b: float(np.corrcoef(a, b)[0, 1])
X = np.column_stack([(lambda l: l[30:] - l[:-30])(faktor[q["id"]] * linie[q["id"]]) for q in QUELLEN])
gleich = np.full(X.shape[1], 1 / X.shape[1])
w, wk = anteile(X, db), nach_korr(X, db)
zeige = lambda v: {q["name"]: round(float(a) * 100, 1) for q, a in sorted(zip(QUELLEN, v), key=lambda x: -x[1]) if a > .0005}
print("\nOptimale Anteile:", zeige(w))
print("Nach Korrelation:", zeige(wk))
print(f"Korrelation gleich {kor(X @ gleich, db) * 100:+.1f} %, nach Korrelation {kor(X @ wk, db) * 100:+.1f} %, optimiert {kor(X @ w, db) * 100:+.1f} %")
r = np.linalg.lstsq(np.c_[X, np.ones(len(X))], db, rcond=None)[0][:-1]
print(f"Mit negativen Anteilen (Quelle umgedreht) {kor(X @ r, db) * 100:+.1f} %")
# Kurs verschoben, Anteile jedes Mal neu bestimmt. So hoch kommt das Verfahren auch ohne echten Zusammenhang.
verschoben = [(o, np.roll(db, o)) for o in range(30, len(db) - 30, 60)]
zufall = [kor(X @ anteile(X, y, 300), y) for _, y in verschoben]
zufall_k = [kor(X @ nach_korr(X, y), y) for _, y in verschoben]
p_opt, p_k = float(np.mean(np.array(zufall) >= kor(X @ w, db))), float(np.mean(np.array(zufall_k) >= kor(X @ wk, db)))
print(f"Verschobener Kurs: optimiert Schnitt {np.mean(zufall) * 100:+.1f} %, p {p_opt:.2f}; nach Korrelation Schnitt {np.mean(zufall_k) * 100:+.1f} %, p {p_k:.2f}")
TEST = []
for grenze in ("2018-01-01", "2022-01-01", "2025-01-01"):
    n = sum(1 for d in tage[:len(db)] if str(d) < grenze) - 30  # letztes Fenster endet vor der Grenze, kein Vorgriff
    v, vk = anteile(X[:n], db[:n]), nach_korr(X[:n], db[:n])
    t = n + 30
    TEST.append({"bis": grenze, "lern": round(kor(X[:n] @ v, db[:n]) * 100, 1), "test": round(kor(X[t:] @ v, db[t:]) * 100, 1), "korr": round(kor(X[t:] @ vk, db[t:]) * 100, 1),
                 "gleich": round(kor(X[t:] @ gleich, db[t:]) * 100, 1), "anteile": zeige(v)})
    print(TEST[-1])
with open(AUS, "a") as f:
    f.write("const RANG = " + json.dumps(RANG, ensure_ascii=False) + ";\n")
    f.write("const OPT_TEST = " + json.dumps({"p": round(p_opt, 2), "p_korr": round(p_k, 2), "zufall": round(float(np.mean(zufall)) * 100, 1), "zufall_korr": round(float(np.mean(zufall_k)) * 100, 1),
                                               "mass": MASS, "tests": TEST}, ensure_ascii=False) + ";\n")
