"""Testet die These: Wenn YouTuber euphorisch sind, fällt der Kurs danach. Wenn sie Panik machen, steigt er danach.

Aufruf: python3.14 -I test_gegenindikator.py <ordner mit titeln> <fetch_herdenradar.py> <btc json> <eth json>

Regeln, festgelegt vor der ersten Rechnung:
  Zwei Messungen je Kanal und Zeitraum, geteilt durch die Zahl der Titel, Kanäle gewichtet nach Wurzel der Abos:
    Stimmung: Wortliste bullisch minus bärisch aus dem Herdenradar.
    Aufruf: Kaufaufrufe und Gier (KAUF) minus Verkaufsaufrufe und Angst (RAUS). Das ist das "jetzt nochmal einkaufen".
  Zwei Raster: Monat (Rang gegen 24 Monate davor), Woche (Rang gegen 104 Wochen davor).
  Oberste 20 % heißt Euphorie, unterste 20 % heißt Panik. Es zählt erst der Kurs nach Ende des Zeitraums.
  Ergebnis: Kursänderung 30, 90 und 180 Tage danach, verglichen mit allen Zeitpunkten.
  Abstand = Schnitt nach Panik minus Schnitt nach Euphorie. Die These sagt: Abstand größer null.
  Prüfung: die Signale werden auf der Zeitachse kreisförmig verschoben. p = Anteil der Verschiebungen mit mindestens gleichem Abstand.
  Depot: nach Euphorie raus, nach Panik rein, 0,1 % Gebühr, gegen Halten und gegen die verschobenen Signale.
Grenzen: Datum der Titel ist zwischen je 100 Videos gestützt, das Wochenraster ist dadurch unscharf. Nur Titel, nur heute große Kanäle.
"""
import ast
import bisect
import datetime as dt
import json
import math
import re
import statistics as st
import sys
from pathlib import Path

ORDNER, HERD, BTC, ETH = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
listen = {}
for knoten in ast.parse(Path(HERD).read_text()).body:
    if isinstance(knoten, ast.Assign) and getattr(knoten.targets[0], "id", "") in ("BULL", "BEAR", "BULL_DE", "BEAR_DE"):
        listen[knoten.targets[0].id] = ast.literal_eval(knoten.value)
muster = lambda w: re.compile(r"\b(?:" + "|".join(re.escape(x) for x in sorted(set(w), key=len, reverse=True)) + r")\b")

KAUF = muster(["buy now", "buy this", "buy the dip", "time to buy", "buying now", "i'm buying", "im buying", "still time", "load up", "loading up", "accumulate", "last chance", "don't miss", "dont miss",
               "before it's too late", "before its too late", "all in", "going all in", "millionaire", "10x", "20x", "50x", "100x", "1000x", "life changing", "generational", "get rich", "next bull run",
               "jetzt kaufen", "kaufen", "nachkaufen", "einkaufen", "einsteigen", "letzte chance", "millionär", "reich werden", "kaufchance", "kaufsignal", "nicht verpassen"])
RAUS = muster(["sell now", "time to sell", "selling now", "i'm selling", "im selling", "sold my", "get out", "it's over", "its over", "warning", "urgent", "dead", "scam", "collapse", "going to zero", "crash", "capitulation",
               "jetzt verkaufen", "verkaufen", "verkauft", "aussteigen", "warnung", "achtung", "vorsicht", "tot", "absturz", "crash", "zusammenbruch", "es ist vorbei"])
SP = {"en": (muster(listen["BULL"]), muster(listen["BEAR"])), "de": (muster(listen["BULL_DE"] + listen["BULL"]), muster(listen["BEAR_DE"] + listen["BEAR"]))}


def kurse(p):
    r = json.load(open(p))["chart"]["result"][0]
    s = {dt.datetime.fromtimestamp(int(t), dt.UTC).date(): float(c) for t, c in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]) if c}
    tage = sorted(s)
    return tage, [s[d] for d in tage]


def wert_am(tage, w, d):
    i = bisect.bisect_right(tage, d) - 1
    return w[i] if i >= 0 and (d - tage[i]).days <= 5 else None


def woche(d):
    return d - dt.timedelta(days=d.weekday())


kanaele = [json.loads(f.read_text()) for f in ORDNER.glob("UC*.json")]
print("Kanäle", len(kanaele), "Titel", sum(len(k["videos"]) for k in kanaele))


def reihe(art, raster):
    je = {}
    for k in kanaele:
        bull, bear = (KAUF, RAUS) if art == "Aufruf" else SP[k["sprache"]]
        z = {}
        for d, titel in k["videos"]:
            t = titel.lower()
            tag = dt.date.fromisoformat(d)
            sch = tag.replace(day=1) if raster == "Monat" else woche(tag)
            e = z.setdefault(sch, [0, 0])
            e[0] += 1
            e[1] += len(bull.findall(t)) - len(bear.findall(t))
        for sch, (n, s) in z.items():
            if n >= (3 if raster == "Monat" else 1):
                je.setdefault(sch, []).append((s / n, math.sqrt(k["abos"])))
    return {s: sum(a * g for a, g in v) / sum(g for _, g in v) for s, v in je.items() if len(v) >= 5}


def ende(s, raster):
    if raster == "Monat":
        return dt.date(s.year + (s.month == 12), s.month % 12 + 1, 1)
    return s + dt.timedelta(days=7)


def zeitpunkte(w, raster):
    fenster = 24 if raster == "Monat" else 104
    sch = sorted(w)
    aus = []
    for i, s in enumerate(sch):
        if i < fenster:
            continue
        davor = [w[x] for x in sch[i - fenster:i]]
        aus.append((ende(s, raster), sum(v < w[s] for v in davor) / fenster))
    return aus


def schnitt(x):
    return sum(x) / len(x) if x else float("nan")


def auswertung(zeit, tage, preis, h, von=None, bis=None):
    z = []
    for d, rang in zeit:
        if (von and d < von) or (bis and d >= bis):
            continue
        a, b = wert_am(tage, preis, d), wert_am(tage, preis, d + dt.timedelta(days=h))
        if a and b:
            z.append((rang, math.log(b / a)))
    if len(z) < 12:
        return None
    r = [x[1] for x in z]
    abst = lambda rg: schnitt([y for x, y in zip(rg, r) if x <= .2]) - schnitt([y for x, y in zip(rg, r) if x >= .8])
    rg = [x[0] for x in z]
    echt = abst(rg)
    versch = [abst(rg[i:] + rg[:i]) for i in range(1, len(rg))]
    versch = [v for v in versch if v == v]
    p = sum(v >= echt for v in versch) / len(versch)
    pz = lambda l: (math.exp(l) - 1) * 100
    eu = [y for x, y in zip(rg, r) if x >= .8]
    pa = [y for x, y in zip(rg, r) if x <= .2]
    return {"n": len(z), "alle": pz(schnitt(r)), "eu": pz(schnitt(eu)), "pa": pz(schnitt(pa)), "neu": len(eu), "npa": len(pa), "eu_fall": sum(y < 0 for y in eu) / max(len(eu), 1) * 100,
            "pa_steig": sum(y > 0 for y in pa) / max(len(pa), 1) * 100, "alle_fall": sum(y < 0 for y in r) / len(r) * 100, "p": p}


def depot(zeit, tage, preis):
    start = zeit[0][0]
    t0 = bisect.bisect_left(tage, start)
    signale = {}
    for d, rang in zeit:
        if rang >= .8:
            signale[d] = 0
        elif rang <= .2:
            signale[d] = 1

    def lauf(sig):
        drin, wert, wechsel = 1, 1.0, 0
        for i in range(t0 + 1, len(tage)):
            if drin:
                wert *= preis[i] / preis[i - 1]
            if tage[i] in sig and sig[tage[i]] != drin:
                drin = sig[tage[i]]
                wert *= .999
                wechsel += 1
        return wert, wechsel
    echt, wechsel = lauf(signale)
    halten = preis[-1] / preis[t0]
    tg = tage[t0:]
    idx = {d: bisect.bisect_left(tg, d) for d in signale}
    versch = []
    for sh in range(30, len(tg), 30):
        versch.append(lauf({tg[(idx[d] + sh) % len(tg)]: v for d, v in signale.items() if idx[d] < len(tg)})[0])
    return echt, halten, wechsel, sum(v >= echt for v in versch) / len(versch)


GRENZE = dt.date(2023, 1, 1)
ergebnis = {}
for coin, pfad in (("BTC", BTC), ("ETH", ETH)):
    tage, preis = kurse(pfad)
    for art in ("Stimmung", "Aufruf"):
        for raster in ("Monat", "Woche"):
            zeit = zeitpunkte(reihe(art, raster), raster)
            print(f"\n{coin} {art} {raster}, Zeitpunkte {len(zeit)}, ab {zeit[0][0]}")
            for h in (30, 90, 180):
                for name, von, bis in (("alle", None, None), ("bis 2022", None, GRENZE), ("ab 2023", GRENZE, None)):
                    e = auswertung(zeit, tage, preis, h, von, bis)
                    if not e:
                        continue
                    ergebnis[f"{coin}|{art}|{raster}|{h}|{name}"] = e
                    print(f"  {h:3}T {name:9} n{e['n']:4} alle {e['alle']:+6.1f}%  nach Euphorie {e['eu']:+6.1f}% ({e['neu']}, fällt {e['eu_fall']:.0f}%, sonst {e['alle_fall']:.0f}%)  nach Panik {e['pa']:+6.1f}% ({e['npa']}, steigt {e['pa_steig']:.0f}%)  p {e['p']:.2f}")
            d = depot(zeit, tage, preis)
            ergebnis[f"{coin}|{art}|{raster}|depot"] = {"regel": d[0], "halten": d[1], "wechsel": d[2], "p": d[3]}
            print(f"  Depot Regel x{d[0]:.2f}, Halten x{d[1]:.2f}, Wechsel {d[2]}, verschoben besser oder gleich {d[3] * 100:.0f}%")

    # Laufen die Titel dem Kurs hinterher? Rang gegen Kursänderung der 30 Tage davor
    zeit = zeitpunkte(reihe("Stimmung", "Monat"), "Monat")
    pa = []
    for d, rang in zeit:
        a, b = wert_am(tage, preis, d - dt.timedelta(days=30)), wert_am(tage, preis, d)
        if a and b:
            pa.append((rang, math.log(b / a)))
    mx, my = schnitt([x for x, _ in pa]), schnitt([y for _, y in pa])
    korr = sum((x - mx) * (y - my) for x, y in pa) / math.sqrt(sum((x - mx) ** 2 for x, _ in pa) * sum((y - my) ** 2 for _, y in pa))
    print(f"\n{coin} Stimmung gegen Kurs der 30 Tage DAVOR: Korrelation {korr * 100:+.1f} %")
    ergebnis[f"{coin}|hinterher"] = korr

    # Gegenprobe zugunsten der These. Hoch: höchster Monatsschluss im Umkreis von 6 Monaten, Tief: niedrigster.
    schluss = {}
    for d, w in zip(tage, preis):
        schluss[d.replace(day=1)] = w
    mon = sorted(schluss)
    hochs, tiefs = [], []
    for i, m in enumerate(mon):
        um = [schluss[x] for x in mon[max(0, i - 6):i + 7]]
        if i >= 6 and i + 6 < len(mon):
            if schluss[m] == max(um):
                hochs.append(m)
            elif schluss[m] == min(um):
                tiefs.append(m)
    for art in ("Stimmung", "Aufruf"):
        zeit = zeitpunkte(reihe(art, "Monat"), "Monat")
        rang = {dt.date(d.year - (d.month == 1), (d.month - 2) % 12 + 1, 1): r for d, r in zeit}  # zurück auf den gemessenen Monat
        h, t = [(m, rang[m]) for m in hochs if m in rang], [(m, rang[m]) for m in tiefs if m in rang]
        print(f"\n{coin} {art}, Rang im Monat der echten Hochs:", [(m.isoformat()[:7], round(r * 100)) for m, r in h])
        print(f"{coin} {art}, Rang im Monat der echten Tiefs:", [(m.isoformat()[:7], round(r * 100)) for m, r in t])
        eu = [m for m, r in rang.items() if r >= .8]
        pa = [m for m, r in rang.items() if r <= .2]
        nah = lambda m, ziele: any(abs((m.year - z.year) * 12 + m.month - z.month) <= 2 for z in ziele)
        print(f"  Euphorie Monate {len(eu)}, davon höchstens 2 Monate neben einem Hoch {sum(nah(m, hochs) for m in eu)}. Panik Monate {len(pa)}, davon neben einem Tief {sum(nah(m, tiefs) for m in pa)}.")
        print(f"  Zum Vergleich alle Monate {len(rang)}: neben einem Hoch {sum(nah(m, hochs) for m in rang)}, neben einem Tief {sum(nah(m, tiefs) for m in rang)}.")
        for obere in (.9, 1.0):
            streng = [(d, 1.0 if r >= obere else 0.0 if r <= 1 - obere else .5) for d, r in zeit]
            for h_tage in (30, 90):
                e = auswertung(streng, tage, preis, h_tage)
                print(f"  Nur die extremsten, Grenze {obere * 100:.0f} %, {h_tage}T: alle {e['alle']:+.1f}%, nach Euphorie {e['eu']:+.1f}% ({e['neu']}), nach Panik {e['pa']:+.1f}% ({e['npa']}), p {e['p']:.2f}")
        spaeter = [(d + dt.timedelta(days=30), r) for d, r in zeit]
        e = auswertung(spaeter, tage, preis, 90)
        print(f"  Signal 30 Tage später, 90T: nach Euphorie {e['eu']:+.1f}%, nach Panik {e['pa']:+.1f}%, p {e['p']:.2f}")

Path(__file__).with_name("test_gegenindikator_ergebnis.json").write_text(json.dumps(ergebnis, ensure_ascii=False, indent=0))
