"""Baut die ETH eigenen Quellen in quellen/eth/. Sie überschreiben dort gleichnamige Quellen oder kommen dazu.

Aufruf: python quelle_eth.py <ordner mit ETH Rohdaten> <eth_ab_start.json> <btc_ab_2010.json>

Regeln vorab festgelegt, nie am Kurs angepasst, Reihen wie in quelle_faktoren.py (am 1. des Monats, Änderung der 30 Tage davor):
  Ethereum TVL, Stablecoins auf Ethereum, aktive ETH Adressen steigen: Anstieg.
  ETH gegen BTC steigt: Anstieg. BTC steigt: Anstieg (BTC als Taktgeber). Wikipedia Aufrufe Ethereum steigen: Anstieg.
Saisonalität: wie bei BTC der Median je Kalendermonat, hier aus ETH Kursen bis Ende 2021.
Ethereum Ereignisse: große Upgrades, ETF und Futures Starts Anstieg, Hacks und Sanktionen Rücksetzer. Daten aus dem Gedächtnis
  ohne Blick auf Kurse, keine fest terminierten Zukunftstermine.
"""
import csv
import datetime as dt
import json
import math
import statistics
import sys
from pathlib import Path

R, ETH, BTC = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
AB, HEUTE = dt.date(2015, 7, 1), dt.date(2026, 11, 5)
ZIEL = Path(__file__).parent / "quellen" / "eth"
ZIEL.mkdir(parents=True, exist_ok=True)
MONAT = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
UTC = lambda t: dt.datetime.fromtimestamp(int(t), dt.UTC).date()
kom = lambda v, n=1: f"{v:.{n}f}".replace(".", ",")


def yahoo(p):
    r = json.load(open(p))["chart"]["result"][0]
    return {UTC(t): float(c) for t, c in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]) if c is not None}


eth, btc = yahoo(ETH), yahoo(BTC)
eth_tage = sorted(d for d in eth if d <= HEUTE)


def monate(ende):
    j, m = AB.year, AB.month
    while dt.date(j, m, 1) <= ende:
        yield dt.date(j, m, 1)
        j, m = (j + 1, 1) if m == 12 else (j, m + 1)


def schnitt(s, tage, bis):
    w = [s[d] for d in tage if d < bis][-7:]
    return sum(w) / len(w) if len(w) == 7 else None


def gleichlauf(s):
    tage, letzt, w, i = sorted(s), None, {}, 0
    for d in eth_tage:
        while i < len(tage) and tage[i] <= d:
            letzt = s[tage[i]]
            i += 1
        w[d] = letzt
    vor = lambda d: d - dt.timedelta(days=30)
    gut = [d for d in eth_tage if (w.get(d) or 0) > 0 and (w.get(vor(d)) or 0) > 0]
    a, b = [math.log(w[d] / w[vor(d)]) for d in gut], [math.log(eth[d] / eth[vor(d)]) for d in gut]
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    return round(sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) * 100, 1)


def schreibe(id_, name, rang, ereignisse, **extra):
    ereignisse = sorted((e for e in ereignisse if e["d"] >= AB.isoformat()), key=lambda e: e["d"])
    (ZIEL / f"{id_}.json").write_text(json.dumps({"id": id_, "name": name, "rang": rang, **extra, "ereignisse": ereignisse}, ensure_ascii=False, indent=0))
    z = {}
    for e in ereignisse:
        z[e["k"]] = z.get(e["k"], 0) + 1
    print(f"{id_:16} {len(ereignisse):4} {z} {ereignisse[0]['d']} {ereignisse[-1]['d']}", extra)


def reihe(id_, name, rang, s, wort, quelle):
    tage, E = sorted(s), []
    for d in monate(HEUTE):
        neu, alt = schnitt(s, tage, d), schnitt(s, tage, d - dt.timedelta(days=30))
        if not neu or not alt or neu == alt:
            continue
        E.append({"d": d.isoformat(), "n": f"{wort} {'steigt' if neu > alt else 'fällt'} {kom(abs(neu / alt - 1) * 100)} % in 30 Tagen", "t": name, "k": "up" if neu > alt else "down", "quelle": quelle})
    schreibe(id_, name, rang, E, gleichlauf=gleichlauf(s))


reihe("tvl_eth", "Ethereum TVL", 40, {UTC(x["date"]): float(x["tvl"]) for x in json.load(open(R / "tvl.json")) if x["tvl"] > 0}, "TVL", "https://defillama.com/chain/Ethereum")
reihe("stable_eth", "Stablecoins auf Ethereum", 41, {UTC(x["date"]): float(x["totalCirculating"]["peggedUSD"]) for x in json.load(open(R / "stable_eth.json")) if x["totalCirculating"].get("peggedUSD")}, "Stablecoins auf Ethereum", "https://defillama.com/stablecoins/Ethereum")
reihe("adressen_eth", "Aktive Adressen ETH", 42, {dt.date.fromisoformat(k): v for k, v in json.load(open(R / "adr.json")).items()}, "Aktive ETH Adressen", "https://github.com/coinmetrics/data")
reihe("eth_btc", "ETH gegen BTC", 43, {d: eth[d] / btc[d] for d in eth if d in btc}, "ETH gegen BTC", "https://finance.yahoo.com/quote/ETH-BTC/history/")
reihe("btc_takt", "BTC als Taktgeber", 44, btc, "BTC", "https://finance.yahoo.com/quote/BTC-USD/history/")

v = [(dt.date(int(x["timestamp"][:4]), int(x["timestamp"][4:6]), 1), x["views"]) for x in json.load(open(R / "wiki_Ethereum.json"))["items"]][:-1]
E, tag = [], {}
for (m0, a), (m1, b) in zip(v, v[1:]):
    tag[m1] = b
    if a != b:
        fertig = dt.date(m1.year + (m1.month == 12), m1.month % 12 + 1, 1)
        E.append({"d": fertig.isoformat(), "n": f"Aufrufe Ethereum {'steigen' if b > a else 'fallen'} {kom(abs(b / a - 1) * 100, 0)} %", "t": "Aufmerksamkeit", "k": "up" if b > a else "down", "quelle": "https://en.wikipedia.org/wiki/Ethereum"})
schreibe("wiki_ethereum", "Wikipedia Ethereum", 45, E, gleichlauf=gleichlauf(tag))

# Saisonalität aus ETH Kursen bis Ende 2021, Regel wie bei BTC
monatsende = {}
for d in sorted(eth):
    monatsende[(d.year, d.month)] = eth[d]
je = {m: [] for m in range(1, 13)}
for (j, m), w in monatsende.items():
    vor = monatsende.get((j - 1, 12) if m == 1 else (j, m - 1))
    if vor and j <= 2021:
        je[m].append(w / vor - 1)
GUT = {m: statistics.median(w) > 0 for m, w in je.items()}
print("Saison ETH bis 2021:", {MONAT[m - 1][:3]: f"{statistics.median(w) * 100:+.1f}%/{len(w)}" for m, w in je.items()})
schreibe("saison", "Saisonalität", 6, [{"d": d.isoformat(), "n": f"{MONAT[d.month - 1]} war bei ETH bis 2021 im Median {'positiv' if GUT[d.month] else 'negativ'}", "t": "Saison", "k": "up" if GUT[d.month] else "down",
                                        "quelle": "https://finance.yahoo.com/quote/ETH-USD/history/"} for d in monate(dt.date(2031, 11, 6))])

GESCHICHTE, HACK = "https://ethereum.org/en/history/", "https://en.wikipedia.org/wiki/Ethereum"
schreibe("eth_ereignisse", "Ethereum Ereignisse", 46, [{"d": d, "n": n, "t": t, "k": k, "quelle": q} for d, n, t, k, q in (
    ("2016-06-17", "The DAO Hack", "Hack", "down", HACK),
    ("2016-07-20", "Hard Fork nach The DAO", "Upgrade", "up", GESCHICHTE),
    ("2017-07-19", "Parity Wallet Hack", "Hack", "down", HACK),
    ("2017-10-16", "Upgrade Byzantium", "Upgrade", "up", GESCHICHTE),
    ("2017-11-06", "Parity Fehler friert Wallets ein", "Hack", "down", HACK),
    ("2019-02-28", "Upgrade Constantinople", "Upgrade", "up", GESCHICHTE),
    ("2019-12-08", "Upgrade Istanbul", "Upgrade", "up", GESCHICHTE),
    ("2020-12-01", "Start Beacon Chain, Staking", "Upgrade", "up", GESCHICHTE),
    ("2021-02-08", "CME startet ETH Futures", "ETF", "up", HACK),
    ("2021-08-05", "Upgrade London, EIP 1559 verbrennt Gebühren", "Upgrade", "up", GESCHICHTE),
    ("2022-08-08", "US Sanktionen gegen Tornado Cash", "Hack", "down", HACK),
    ("2022-09-15", "The Merge, Proof of Stake", "Upgrade", "up", GESCHICHTE),
    ("2023-04-12", "Upgrade Shapella, Staking Auszahlungen", "Upgrade", "up", GESCHICHTE),
    ("2024-03-13", "Upgrade Dencun", "Upgrade", "up", GESCHICHTE),
    ("2024-05-23", "SEC genehmigt ETH Spot ETFs", "ETF", "up", HACK),
    ("2024-07-23", "ETH Spot ETFs starten in den USA", "ETF", "up", HACK),
    ("2025-02-21", "Bybit Hack, rund 1,5 Mrd Dollar in ETH", "Hack", "down", HACK),
    ("2025-05-07", "Upgrade Pectra", "Upgrade", "up", GESCHICHTE),
    ("2025-12-03", "Upgrade Fusaka", "Upgrade", "up", GESCHICHTE))])
