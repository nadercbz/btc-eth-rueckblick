"""Baut die große Sammlung weiterer Quellen. Jede Richtung steht vorab fest und wird nie am Ergebnis umgedreht.

Aufruf: python quelle_mehr.py <rohdaten mehr> <rohdaten lang> <kurs json> <coin metrics csv> <zielordner>

Reihen: am 1. des Monats zählt die Änderung der 30 Tage davor (7 Tage Schnitt). In REIHEN steht, ob ein Anstieg für den Coin gut sein soll.
  Risikofreude steigt gut, Abwehr und Teuerung steigen schlecht. On Chain Nutzung steigt gut, Börsenzuflüsse und Bewertung steigen schlecht.
Technik: Goldenes Kreuz 50 über 200 Tage, Momentum 12 Monate, Mayer Multiple über 2,4 schlecht und unter 0,8 gut, RSI über 70 schlecht und unter 30 gut,
  70 % unter dem Hoch gut, neues Hoch im Vormonat gut, steigende Schwankung schlecht. MVRV über 3,5 schlecht und unter 1 gut, Puell über 4 schlecht und unter 0,5 gut.
Planeten: Beginn eines Rücklaufs schlecht, Ende gut. Jupiter wechselt das Zeichen gut, Saturn wechselt das Zeichen schlecht. Supermond (Vollmond unter 360.000 km) schlecht.
Natur: Sonnenaktivität F10.7 steigt gut, globale Temperatur steigt schlecht, El Niño schlecht und La Niña gut.
Kalender: 7 Tage vor dem großen Verfall schlecht, Tag danach gut. Monatswechsel gut. Vor dem US Steuertag schlecht, danach gut. Weihnachtsrallye gut, Januareffekt gut.
  Bitcoin Pizza Day und Genesis Tag gut, Black Friday gut. Super Bowl Indikator: NFC Sieg gut, AFC Sieg schlecht.
Religion: Rosh Hashanah schlecht, Yom Kippur gut (Börsenspruch). Pessach, Purim, Chanukka, Schawuot gut. Tischa BeAv schlecht (Trauertag).
  Schmita: jeder Monat des Schmita Jahres schlecht, dazu der 29. Elul am Ende. Aschermittwoch schlecht, Ostern, Pfingsten, Weihnachten gut.
  Ramadan und beide Bajram Feste gut (Bialkowski 2012). Geistermonat schlecht, sein Ende gut, Mondfest gut, Qingming schlecht, Goldene Woche gut.
  Diwali, Holi, Vesak, Nowruz, Yennayer gut. Samhain schlecht, Beltane gut. Wintersonnenwende gut, Sommersonnenwende schlecht.
Symbolik: Freitag der 13. schlecht, 11.11. gut, Jahrestag 11.09. schlecht. Universalmonat der Numerologie: 1, 3, 8, 11, 22 gut, 4, 7, 9 schlecht.
Islamische Daten sind rechnerisch und können einen Tag abweichen. Schlechte Regeln bleiben schlecht, das zeigt die Rangliste.
"""
import csv
import datetime as dt
import json
import math
import sys
from pathlib import Path

import ephem
from convertdate import hebrew, islamic
from lunardate import LunarDate

M, L, KURS, CM, ZIEL = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4], Path(sys.argv[5])
ZIEL.mkdir(parents=True, exist_ok=True)
AB, BIS, HEUTE = dt.date(2010, 6, 1), dt.date(2031, 11, 6), dt.date(2026, 11, 5)
UTC = lambda t: dt.datetime.fromtimestamp(int(t), dt.UTC).date()
kom = lambda v, n=1: f"{v:.{n}f}".replace(".", ",")
TAG = dt.timedelta(days=1)
rang = [100]


def yahoo(p):
    r = json.load(open(p))["chart"]["result"][0]
    return {UTC(t): float(c) for t, c in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]) if c is not None}


kurs = yahoo(KURS)
kurs_tage = sorted(d for d in kurs if d <= HEUTE)


def monate(ende=HEUTE):
    j, m = AB.year, AB.month
    while dt.date(j, m, 1) <= ende:
        yield dt.date(j, m, 1)
        j, m = (j + 1, 1) if m == 12 else (j, m + 1)


def gleichlauf(s, gut):
    tage, letzt, w, i = sorted(s), None, {}, 0
    for d in kurs_tage:
        while i < len(tage) and tage[i] <= d:
            letzt = s[tage[i]]
            i += 1
        w[d] = letzt
    vor = lambda d: d - dt.timedelta(days=30)
    t = [d for d in kurs_tage if (w.get(d) or 0) > 0 and (w.get(vor(d)) or 0) > 0]
    if len(t) < 100:
        return None
    a, b = [math.log(w[d] / w[vor(d)]) for d in t], [math.log(kurs[d] / kurs[vor(d)]) for d in t]
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    n = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
    return round((1 if gut else -1) * sum((x - ma) * (y - mb) for x, y in zip(a, b)) / n * 100, 1) if n else None


def schreibe(id_, name, gruppe, E, **extra):
    E = sorted((e for e in E if AB.isoformat() <= e["d"] <= BIS.isoformat()), key=lambda e: e["d"])
    if len(E) < 3:
        print("ZU WENIG", id_, len(E))
        return
    rang[0] += 1
    (ZIEL / f"{id_}.json").write_text(json.dumps({"id": id_, "name": name, "rang": rang[0], "gruppe": gruppe, **{k: v for k, v in extra.items() if v is not None}, "ereignisse": E}, ensure_ascii=False, indent=0))
    print(f"{id_}:{len(E)}", end=" ")


ev = lambda d, n, t, k, q: {"d": d.isoformat() if hasattr(d, "isoformat") else d, "n": n, "t": t, "k": k, "quelle": q}


def reihe(id_, name, gruppe, s, gut, wort, quelle):
    tage, E = sorted(s), []
    def schnitt(bis):
        import bisect
        i = bisect.bisect_left(tage, bis)
        w = [s[d] for d in tage[max(i - 7, 0):i]]
        return sum(w) / len(w) if len(w) == 7 else None
    for d in monate():
        neu, alt = schnitt(d), schnitt(d - dt.timedelta(days=30))
        if neu is None or alt is None or neu == alt:
            continue
        E.append(ev(d, f"{wort} {'steigt' if neu > alt else 'fällt'}", name, "up" if (neu > alt) == gut else "down", quelle))
    schreibe(id_, name, gruppe, E, gleichlauf=gleichlauf(s, gut))


Y = "https://finance.yahoo.com/quote/{}/history/"
for gruppe, liste in (
    ("Aktien", (("spx", "S&P 500", "spx", 1), ("russell", "Russell 2000", "russell", 1), ("nikkei", "Nikkei", "nikkei", 1), ("stoxx", "Euro Stoxx 50", "stoxx", 1), ("eem", "Schwellenländer", "eem", 1), ("fxi", "China Aktien", "fxi", 1),
                ("smh", "Halbleiter", "smh", 1), ("tesla", "Tesla", "tesla", 1), ("apple", "Apple", "apple", 1), ("coinbase", "Coinbase Aktie", "coinbase", 1), ("mstr", "MicroStrategy", "mstr", 1), ("riot", "Miner Riot", "riot", 1), ("mara", "Miner Marathon", "mara", 1),
                ("gbtc", "GBTC", "gbtc", 1), ("arkk", "ARK Innovation", "arkk", 1), ("lvmh", "Luxus LVMH", "lvmh", 1), ("ferrari", "Ferrari", "ferrari", 1), ("casino", "Casino Las Vegas Sands", "casino", 1), ("ruestung", "Rüstung Lockheed", "ruestung", 0),
                ("versorger", "Versorger", "versorger", 0), ("walmart", "Walmart", "walmart", 0), ("bau", "Hausbau", "bau", 1))),
    ("Rohstoffe", (("silber", "Silber", "silber", 1), ("platin", "Platin", "platin", 1), ("gas", "Erdgas", "gas", 0), ("weizen", "Weizen", "weizen", 0), ("kaffee", "Kaffee", "kaffee", 0), ("kakao", "Kakao", "kakao", 0), ("lithium", "Lithium", "lithium", 1), ("uran", "Uran", "uran", 1))),
    ("Währungen", (("euro", "Euro", "euro", 1), ("franken", "Dollar gegen Franken", "franken", 1), ("aud", "Australischer Dollar", "aud", 1), ("tuerkei", "Dollar gegen Lira", "tuerkei", 1))),
    ("Zinsen und Liquidität", (("hyg", "Riskante Anleihen", "hyg", 1), ("tlt", "Lange US Anleihen", "tlt", 1), ("zins3m", "US Zins 3 Monate", "zins3m", 0), ("skew", "SKEW Absturzangst", "skew", 0)))):
    for id_, name, datei, gut in liste:
        reihe(id_, name, gruppe, yahoo(M / f"y_{datei}.json"), bool(gut), name, "https://finance.yahoo.com/")

kurz, lang10 = yahoo(M / "y_zins3m.json"), yahoo(L / "y_zins10.json")
reihe("zinskurve", "Zinskurve", "Zinsen und Liquidität", {d: lang10[d] - kurz[d] + 20 for d in kurz if d in lang10}, True, "Zinskurve", "https://finance.yahoo.com/quote/%5ETNX/history/")
rrp = {}
for o in json.load(open(M / "rrp.json"))["repo"]["operations"]:
    if o.get("operationType") == "Reverse Repo" and o.get("totalAmtAccepted") is not None:
        d = dt.date.fromisoformat(o["operationDate"])
        rrp[d] = rrp.get(d, 0) + float(o["totalAmtAccepted"])
reihe("rrp", "Reverse Repo der Fed", "Zinsen und Liquidität", {d: v + 1e9 for d, v in rrp.items()}, False, "Reverse Repo", "https://www.newyorkfed.org/markets/desk-operations/reverse-repo")
tga = {}
for z in json.load(open(M / "tga.json"))["data"]:
    if "Federal Reserve Account" in z["account_type"] or "Treasury General Account" in z["account_type"]:
        try:
            tga[dt.date.fromisoformat(z["record_date"])] = float(z["close_today_bal"])
        except ValueError:
            pass
reihe("tga", "US Staatskonto TGA", "Zinsen und Liquidität", tga, False, "Staatskonto", "https://fiscaldata.treasury.gov/datasets/daily-treasury-statement/")

# On Chain
for id_, name, datei, gut in (("difficulty", "Mining Difficulty BTC", "difficulty", 1), ("miner_ertrag", "Miner Einnahmen BTC", "miners-revenue", 1), ("gebuehren", "Gebühren BTC", "transaction-fees-usd", 1), ("transaktionen", "Transaktionen BTC", "n-transactions", 1),
                              ("tx_volumen", "Transaktionswert BTC", "estimated-transaction-volume-usd", 1), ("mempool", "Mempool BTC", "mempool-size", 1)):
    reihe(id_, name, "On Chain", {UTC(x["x"]): float(x["y"]) for x in json.load(open(M / f"bc_{datei}.json"))["values"] if x["y"] > 0}, bool(gut), name, "https://www.blockchain.com/explorer/charts/")
spalten = {}
for z in csv.DictReader(open(CM)):
    d = dt.date.fromisoformat(z["time"][:10])
    for k, v in z.items():
        if v and k != "time":
            try:
                spalten.setdefault(k, {})[d] = float(v)
            except ValueError:
                pass
CMQ = "https://github.com/coinmetrics/data"
for id_, name, sp, gut in (("flow_rein", "Börsen Zuflüsse", "FlowInExUSD", 0), ("flow_raus", "Börsen Abflüsse", "FlowOutExUSD", 1), ("boersenbestand", "Bestand auf Börsen", "SplyExNtv", 0), ("adressen_saldo", "Adressen mit Guthaben", "AdrBalCnt", 1), ("tx_transfers", "Transfers", "TxTfrCnt", 1), ("spot_volumen", "Spot Handelsvolumen", "volume_reported_spot_usd_1d", 1)):
    if sp in spalten and len(spalten[sp]) > 500:
        reihe(id_, name, "On Chain", spalten[sp], bool(gut), name, CMQ)


def monatsstufe(id_, name, gruppe, wert, hoch, tief, wort, quelle):
    """Über hoch schlecht, unter tief gut, dazwischen kein Ereignis. wert(d) nutzt nur Daten vor d."""
    E = []
    for d in monate():
        v = wert(d)
        if v is None:
            continue
        if v > hoch:
            E.append(ev(d, f"{wort} {kom(v)}, sehr hoch", name, "down", quelle))
        elif v < tief:
            E.append(ev(d, f"{wort} {kom(v)}, sehr niedrig", name, "up", quelle))
    schreibe(id_, name, gruppe, E)


def letzter(s):
    tage = sorted(s)
    import bisect
    def f(d):
        i = bisect.bisect_left(tage, d)
        return s[tage[i - 1]] if i else None
    return f


if "CapMVRVCur" in spalten:
    monatsstufe("mvrv", "MVRV", "On Chain", letzter(spalten["CapMVRVCur"]), 3.5, 1, "MVRV", CMQ)
if "IssTotUSD" in spalten:
    iss, t = spalten["IssTotUSD"], sorted(spalten["IssTotUSD"])
    puell = {t[i]: iss[t[i]] / (sum(iss[x] for x in t[i - 365:i]) / 365) for i in range(365, len(t))}
    monatsstufe("puell", "Puell Multiple", "On Chain", letzter(puell), 4, .5, "Puell", CMQ)
if "CapMrktCurUSD" in spalten and "TxTfrValAdjUSD" in spalten:
    pass

# Technik aus dem eigenen Kurs, immer nur mit Tagen vor dem Termin
T, P = kurs_tage, [kurs[d] for d in kurs_tage]
import bisect
def bis(d):
    return P[:bisect.bisect_left(T, d)]
QK = "https://finance.yahoo.com/"
G, Mo, Ma, Hoch, Tiefst = [], [], [], [], []
for d in monate():
    w = bis(d)
    if len(w) >= 200:
        a, b = sum(w[-50:]) / 50, sum(w[-200:]) / 200
        G.append(ev(d, "50 Tage Schnitt über 200 Tage" if a > b else "50 Tage Schnitt unter 200 Tage", "Technik", "up" if a > b else "down", QK))
    if len(w) >= 366:
        Mo.append(ev(d, f"12 Monate {'im Plus' if w[-1] > w[-366] else 'im Minus'}", "Technik", "up" if w[-1] > w[-366] else "down", QK))
    if w and w[-1] < .3 * max(w):
        Tiefst.append(ev(d, "Über 70 % unter dem Hoch", "Technik", "up", QK))
    if len(w) > 31 and max(w[-30:]) >= max(w[:-30]):
        Hoch.append(ev(d, "Neues Allzeithoch im Vormonat", "Technik", "up", QK))
schreibe("goldkreuz", "Goldenes Kreuz", "Technik", G)
schreibe("momentum12", "Momentum 12 Monate", "Technik", Mo)
schreibe("tief70", "70 % unter dem Hoch", "Technik", Tiefst)
schreibe("neues_hoch", "Neues Allzeithoch", "Technik", Hoch)
monatsstufe("mayer", "Mayer Multiple", "Technik", lambda d: (lambda w: w[-1] / (sum(w[-200:]) / 200) if len(w) >= 200 else None)(bis(d)), 2.4, .8, "Mayer", QK)
def rsi(d):
    w = bis(d)[-15:]
    if len(w) < 15:
        return None
    a = sum(max(y - x, 0) for x, y in zip(w, w[1:])); b = sum(max(x - y, 0) for x, y in zip(w, w[1:]))
    return 100 if b == 0 else 100 - 100 / (1 + a / b)
monatsstufe("rsi", "RSI 14 Tage", "Technik", rsi, 70, 30, "RSI", QK)
vola = {T[i]: 1e-6 + math.sqrt(sum(math.log(P[j] / P[j - 1]) ** 2 for j in range(i - 29, i + 1)) / 30) for i in range(31, len(T))}
reihe("schwankung", "Schwankung 30 Tage", "Technik", vola, False, "Schwankung", QK)

# Aufmerksamkeit
for art, name, gut in (("Cryptocurrency", "Wikipedia Kryptowährung", 1), ("Blockchain", "Wikipedia Blockchain", 1), ("Dogecoin", "Wikipedia Dogecoin", 1), ("Elon_Musk", "Wikipedia Elon Musk", 1), ("Lamborghini", "Wikipedia Lamborghini", 1), ("Satoshi_Nakamoto", "Wikipedia Satoshi", 1),
                       ("Non-fungible_token", "Wikipedia NFT", 1), ("Gold", "Wikipedia Gold", 1), ("Inflation", "Wikipedia Inflation", 1), ("Bankruptcy", "Wikipedia Insolvenz", 0), ("Ponzi_scheme", "Wikipedia Schneeballsystem", 0),
                       ("Tulip_mania", "Wikipedia Tulpenmanie", 0), ("Unemployment", "Wikipedia Arbeitslosigkeit", 0), ("World_War_III", "Wikipedia Dritter Weltkrieg", 0), ("Stock_market_crash", "Wikipedia Börsencrash", 0)):
    try:
        items = json.load(open(M / f"wiki_{art}.json"))["items"][:-1]
    except Exception:
        print("FEHLT", art)
        continue
    v = [(dt.date(int(x["timestamp"][:4]), int(x["timestamp"][4:6]), 1), x["views"]) for x in items]
    E = []
    for (m0, a), (m1, b) in zip(v, v[1:]):
        if a != b:
            E.append(ev(dt.date(m1.year + (m1.month == 12), m1.month % 12 + 1, 1), f"Aufrufe {name[10:]} {'steigen' if b > a else 'fallen'}", "Aufmerksamkeit", "up" if (b > a) == bool(gut) else "down", f"https://en.wikipedia.org/wiki/{art}"))
    schreibe("w_" + art.lower().replace("-", "_"), name, "Aufmerksamkeit", E, gleichlauf=gleichlauf(dict(v), bool(gut)))


# Planeten, alles bis 2031 berechenbar
def laenge(cls, d):
    b = cls()
    e = ephem.Date(f"{d.year}/{d.month}/{d.day} 12:00")
    b.compute(e, epoch=e)
    return math.degrees(ephem.Ecliptic(b, epoch=e).lon)


TAGE = [AB + TAG * i for i in range((BIS - AB).days + 1)]
ZEICHEN = ["Widder", "Stier", "Zwillinge", "Krebs", "Löwe", "Jungfrau", "Waage", "Skorpion", "Schütze", "Steinbock", "Wassermann", "Fische"]
QP = "https://en.wikipedia.org/wiki/Apparent_retrograde_motion"
for name, cls in (("Venus", ephem.Venus), ("Mars", ephem.Mars), ("Jupiter", ephem.Jupiter), ("Saturn", ephem.Saturn), ("Uranus", ephem.Uranus), ("Neptun", ephem.Neptune), ("Pluto", ephem.Pluto)):
    l = [laenge(cls, d) for d in TAGE]
    E, r = [], False
    for i in range(1, len(l)):
        jetzt = ((l[i] - l[i - 1] + 180) % 360 - 180) < 0
        if jetzt != r:
            E.append(ev(TAGE[i], f"{name} wird {'rückläufig' if jetzt else 'direkt'}", "Planet", "down" if jetzt else "up", QP))
        r = jetzt
    schreibe(f"rueck_{name.lower()}", f"{name} rückläufig", "Planeten", E)
    if name in ("Jupiter", "Saturn"):
        E = [ev(TAGE[i], f"{name} geht in {ZEICHEN[int(l[i] // 30)]}", "Planet", "up" if name == "Jupiter" else "down", QP) for i in range(1, len(l)) if int(l[i] // 30) != int(l[i - 1] // 30)]
        schreibe(f"zeichen_{name.lower()}", f"{name} wechselt das Zeichen", "Planeten", E)
E, d = [], ephem.Date("2010/6/1")
while (n := ephem.next_full_moon(d)).datetime().date() <= BIS:
    m = ephem.Moon(n)
    km = m.earth_distance * ephem.meters_per_au / 1000
    if km < 360000:
        E.append(ev(n.datetime().date(), f"Supermond, {round(km):,} km".replace(",", "."), "Mond", "down", "https://en.wikipedia.org/wiki/Supermoon"))
    d = n + 1
schreibe("supermond", "Supermond", "Planeten", E)

# Natur
F = {}
for z in open(M / "sonnenfluss.txt"):
    if z[:1] != "#" and z[:4].isdigit() and int(z[:4]) >= 2009:
        t = z.split()
        try:
            if float(t[25]) > 0:
                F[dt.date(int(t[0]), int(t[1]), int(t[2]))] = float(t[25])
        except (IndexError, ValueError):
            pass
if F:
    reihe("f107", "Sonnenaktivität F10.7", "Natur", F, True, "Sonnenaktivität", "https://kp.gfz-potsdam.de/en/data")
temp, E = {}, []
for z in csv.reader(open(M / "giss.csv")):
    if z and z[0].isdigit():
        for m, v in enumerate(z[1:13], 1):
            if v.strip() not in ("***", ""):
                temp[(int(z[0]), m)] = float(v)
for (j, m), v in sorted(temp.items()):
    a = temp.get((j - 1, 12) if m == 1 else (j, m - 1))
    if a is not None and a != v:
        E.append(ev(dt.date(j + (m == 12), m % 12 + 1, 15), f"Weltweite Temperatur {'steigt' if v > a else 'fällt'}", "Klima", "down" if v > a else "up", "https://data.giss.nasa.gov/gistemp/"))
schreibe("temperatur", "Weltweite Temperatur", "Natur", E)
E = []
for z in open(M / "oni.txt"):
    t = z.split()
    if len(t) == 4 and t[1].isdigit() and t[0] in ("DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"):
        m = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"].index(t[0]) + 1
        v = float(t[3])
        j, mo = int(t[1]) + (m + 2 > 12), (m + 1) % 12 + 1
        if abs(v) >= .5:
            E.append(ev(dt.date(j, mo, 1), "El Niño" if v > 0 else "La Niña", "Klima", "down" if v > 0 else "up", "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ONI_v5.php"))
schreibe("enso", "El Niño und La Niña", "Natur", E)


# Kalender
JAHRE = range(2010, 2032)
def letzter_freitag(j, m):
    d = dt.date(j + (m == 12), m % 12 + 1, 1) - TAG
    while d.weekday() != 4:
        d -= TAG
    return d
E = []
for j in JAHRE:
    for m in (3, 6, 9, 12):
        f = letzter_freitag(j, m)
        E += [ev(f - TAG * 7, "7 Tage vor dem großen Verfall", "Kalender", "down", "https://www.cmegroup.com/markets/cryptocurrencies/bitcoin/bitcoin.html"), ev(f + TAG, "Tag nach dem großen Verfall", "Kalender", "up", "https://www.cmegroup.com/markets/cryptocurrencies/bitcoin/bitcoin.html")]
schreibe("verfall", "Großer Optionsverfall", "Kalender", E)
schreibe("monatswechsel", "Monatswechsel", "Kalender", [ev(dt.date(d.year + (d.month == 12), d.month % 12 + 1, 1) - TAG * 2, "Monatswechsel", "Kalender", "up", "https://en.wikipedia.org/wiki/Calendar_effect") for d in monate(BIS)])
WIKI = "https://en.wikipedia.org/wiki/"
schreibe("steuertag", "US Steuertag", "Kalender", [x for j in JAHRE for x in (ev(dt.date(j, 3, 15), "Vor dem US Steuertag", "Kalender", "down", WIKI + "Tax_Day"), ev(dt.date(j, 4, 16), "Nach dem US Steuertag", "Kalender", "up", WIKI + "Tax_Day"))])
schreibe("santa", "Weihnachtsrallye", "Kalender", [ev(dt.date(j, 12, 20), "Weihnachtsrallye", "Kalender", "up", WIKI + "Santa_Claus_rally") for j in JAHRE])
schreibe("januar", "Januareffekt", "Kalender", [ev(dt.date(j, 1, 2), "Januareffekt", "Kalender", "up", WIKI + "January_effect") for j in JAHRE])
schreibe("pizza", "Bitcoin Pizza Day", "Symbolik", [ev(dt.date(j, 5, 22), "Bitcoin Pizza Day", "Symbolik", "up", WIKI + "Bitcoin") for j in JAHRE])
schreibe("genesis", "Genesis Tag", "Symbolik", [ev(dt.date(j, 1, 3), "Jahrestag Genesis Block", "Symbolik", "up", WIKI + "Bitcoin") for j in JAHRE])
def schwarz(j):
    d = dt.date(j, 11, 1)
    while d.weekday() != 3:
        d += TAG
    return d + TAG * 22
schreibe("black_friday", "Black Friday", "Kalender", [ev(schwarz(j), "Black Friday", "Kalender", "up", WIKI + "Black_Friday_(shopping)") for j in JAHRE])
SB = [("2011-02-06", 1), ("2012-02-05", 1), ("2013-02-03", 0), ("2014-02-02", 1), ("2015-02-01", 0), ("2016-02-07", 0), ("2017-02-05", 0), ("2018-02-04", 1), ("2019-02-03", 0), ("2020-02-02", 0), ("2021-02-07", 1), ("2022-02-13", 1), ("2023-02-12", 0), ("2024-02-11", 0), ("2025-02-09", 1), ("2026-02-08", 1)]
schreibe("super_bowl", "Super Bowl Indikator", "Kalender", [ev(d, f"Super Bowl, {'NFC' if n else 'AFC'} gewinnt", "Kalender", "up" if n else "down", WIKI + "Super_Bowl_indicator") for d, n in SB])


# Religion und Tradition
RELI = "Religion und Tradition"
hj = lambda j, m, t: dt.date(*hebrew.to_gregorian(j, m, t))
HEB = range(5770, 5793)
Q_J = WIKI + "Jewish_holidays"
schreibe("rosh_yom", "Rosh Hashanah und Yom Kippur", RELI, [x for j in HEB for x in (ev(hj(j, 7, 1), "Rosh Hashanah", "Jüdisch", "down", Q_J), ev(hj(j, 7, 10), "Yom Kippur", "Jüdisch", "up", Q_J))])
schreibe("pessach", "Pessach", RELI, [ev(hj(j, 1, 15), "Pessach", "Jüdisch", "up", WIKI + "Passover") for j in HEB])
def adar(j):
    return 13 if hebrew.leap(j) else 12
schreibe("purim", "Purim", RELI, [ev(hj(j, adar(j), 14), "Purim", "Jüdisch", "up", WIKI + "Purim") for j in HEB])
schreibe("chanukka", "Chanukka", RELI, [ev(hj(j, 9, 25), "Chanukka", "Jüdisch", "up", WIKI + "Hanukkah") for j in HEB])
schreibe("schawuot", "Schawuot", RELI, [ev(hj(j, 3, 6), "Schawuot", "Jüdisch", "up", WIKI + "Shavuot") for j in HEB])
schreibe("tischa", "Tischa BeAv", RELI, [ev(hj(j, 5, 9), "Tischa BeAv, Trauertag", "Jüdisch", "down", WIKI + "Tisha_B%27Av") for j in HEB])
E = []
for s in (5768, 5775, 5782, 5789):  # Schmita Jahre
    a, b = hj(s, 7, 1), hj(s, 6, 29)
    d = a
    while d < b:
        E.append(ev(d, f"Schmita Jahr {s}", "Jüdisch", "down", WIKI + "Shmita"))
        d += TAG * 30
    E.append(ev(b, f"29. Elul, Ende Schmita {s}", "Jüdisch", "down", WIKI + "Shmita"))
schreibe("schmita", "Schmita Jahr", RELI, E)
def ostern(j):
    a, b, c = j % 19, j // 100, j % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    return dt.date(j, (h + l - 7 * m + 114) // 31, ((h + l - 7 * m + 114) % 31) + 1)
Q_C = WIKI + "Easter"
schreibe("fasten_ostern", "Fastenzeit und Ostern", RELI, [x for j in JAHRE for x in (ev(ostern(j) - TAG * 46, "Aschermittwoch", "Christlich", "down", Q_C), ev(ostern(j), "Ostern", "Christlich", "up", Q_C))])
schreibe("pfingsten", "Pfingsten", RELI, [ev(ostern(j) + TAG * 49, "Pfingsten", "Christlich", "up", WIKI + "Pentecost") for j in JAHRE])
schreibe("weihnachten", "Weihnachten", RELI, [ev(dt.date(j, 12, 25), "Weihnachten", "Christlich", "up", WIKI + "Christmas") for j in JAHRE])
ij = lambda j, m, t: dt.date(*islamic.to_gregorian(j, m, t))
HIJ = range(1431, 1454)
schreibe("ramadan", "Ramadan", RELI, [ev(ij(j, 9, 1), "Beginn Ramadan", "Islamisch", "up", "https://doi.org/10.1016/j.jempfin.2012.04.006") for j in HIJ])
schreibe("zuckerfest", "Zuckerfest", RELI, [ev(ij(j, 10, 1), "Eid al Fitr", "Islamisch", "up", WIKI + "Eid_al-Fitr") for j in HIJ])
schreibe("opferfest", "Opferfest", RELI, [ev(ij(j, 12, 10), "Eid al Adha", "Islamisch", "up", WIKI + "Eid_al-Adha") for j in HIJ])
lj = lambda j, m, t: LunarDate(j, m, t).to_solar_date()
schreibe("geistermonat", "Chinesischer Geistermonat", RELI, [x for j in JAHRE for x in (ev(lj(j, 7, 1), "Beginn Geistermonat", "Chinesisch", "down", WIKI + "Ghost_Festival"), ev(lj(j, 8, 1), "Ende Geistermonat", "Chinesisch", "up", WIKI + "Ghost_Festival"))])
schreibe("mondfest", "Chinesisches Mondfest", RELI, [ev(lj(j, 8, 15), "Mondfest", "Chinesisch", "up", WIKI + "Mid-Autumn_Festival") for j in JAHRE])
schreibe("qingming", "Qingming Totenfest", RELI, [ev(dt.date(j, 4, 5), "Qingming", "Chinesisch", "down", WIKI + "Qingming_Festival") for j in JAHRE])
schreibe("goldene_woche", "Chinesische Goldene Woche", RELI, [ev(dt.date(j, 10, 1), "Goldene Woche", "Chinesisch", "up", WIKI + "Golden_Week_(China)") for j in JAHRE])
def mond_im_fenster(j, von, bis_, voll):
    f = ephem.next_full_moon if voll else ephem.next_new_moon
    return f(ephem.Date(f"{j}/{von[0]}/{von[1]}")).datetime().date()
schreibe("diwali", "Diwali", RELI, [ev(mond_im_fenster(j, (10, 13), None, False), "Diwali", "Hinduistisch", "up", WIKI + "Diwali") for j in JAHRE])
schreibe("holi", "Holi", RELI, [ev(mond_im_fenster(j, (2, 25), None, True), "Holi", "Hinduistisch", "up", WIKI + "Holi") for j in JAHRE])
schreibe("vesak", "Vesak", RELI, [ev(mond_im_fenster(j, (4, 28), None, True), "Vesak", "Buddhistisch", "up", WIKI + "Vesak") for j in JAHRE])
schreibe("nowruz", "Nowruz", RELI, [ev(dt.date(j, 3, 20), "Nowruz", "Persisch", "up", WIKI + "Nowruz") for j in JAHRE])
schreibe("yennayer", "Yennayer, Neujahr der Imazighen", RELI, [ev(dt.date(j, 1, 14), "Yennayer", "Amazigh", "up", WIKI + "Yennayer") for j in JAHRE])
schreibe("samhain_beltane", "Samhain und Beltane", RELI, [x for j in JAHRE for x in (ev(dt.date(j, 5, 1), "Beltane", "Keltisch", "up", WIKI + "Beltane"), ev(dt.date(j, 11, 1), "Samhain", "Keltisch", "down", WIKI + "Samhain"))])
schreibe("sonnenwende", "Sonnenwenden", RELI, [x for j in JAHRE for x in (ev(ephem.next_summer_solstice(f"{j}/1/1").datetime().date(), "Sommersonnenwende", "Sonne", "down", WIKI + "Solstice"), ev(ephem.next_winter_solstice(f"{j}/1/1").datetime().date(), "Wintersonnenwende", "Sonne", "up", WIKI + "Solstice"))])

# Symbolik
schreibe("freitag13", "Freitag der 13.", "Symbolik", [ev(d, "Freitag der 13.", "Symbolik", "down", WIKI + "Friday_the_13th") for d in TAGE if d.day == 13 and d.weekday() == 4])
schreibe("elf_elf", "11.11.", "Symbolik", [ev(dt.date(j, 11, 11), "11.11.", "Symbolik", "up", WIKI + "11:11_(numerology)") for j in JAHRE])
schreibe("neun_elf", "Jahrestag 11.09.", "Symbolik", [ev(dt.date(j, 9, 11), "Jahrestag 11.09.", "Symbolik", "down", WIKI + "September_11_attacks") for j in JAHRE])
def quer(n):
    while n > 9 and n not in (11, 22):
        n = sum(int(c) for c in str(n))
    return n
E = []
for d in monate(BIS):
    z = quer(sum(int(c) for c in f"{d.year}{d.month}"))
    if z in (1, 3, 8, 11, 22, 4, 7, 9):
        E.append(ev(d, f"Universalmonat {z}", "Numerologie", "up" if z in (1, 3, 8, 11, 22) else "down", WIKI + "Numerology"))
schreibe("numerologie", "Numerologie Universalmonat", "Symbolik", E)
print("\nFERTIG", rang[0] - 100)
