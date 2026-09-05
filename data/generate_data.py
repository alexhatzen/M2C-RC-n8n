"""
F1 — Synthetischer Datengenerator für den Root-Cause-Klassifizierer.

Erzeugt N synthetische überfällige Forderungsfälle im Meter-to-Cash-Prozess.
Jeder Fall bekommt ein `ground_truth_label` (eine der 5 Root-Cause-Kategorien),
das dem Klassifizierer NICHT übergeben wird — es dient nur der Demo-Validierung
(z. B. um im Dashboard Rule/LLM-Trefferquote gegen die Wahrheit zu zeigen).

Usage:
    python data/generate_data.py [--n 200] [--seed 42] [--out data/synthetic_cases.csv]
"""

import argparse
import random

import pandas as pd

CATEGORIES = [
    "Messdatenerfassung",
    "Messdatenuebertragung",
    "Rechnungserstellung",
    "Mahnverfahren",
    "Zahlungsbuchung",
]

# Freitext-Notizen pro Kategorie (mit etwas Rauschen gemischt), damit sowohl
# die Regel-Engine als auch der LLM-Klassifizierer echtes Signal vorfinden.
NOTES_BY_CATEGORY = {
    "Messdatenerfassung": [
        "Kunde meldet falschen Zaehlerstand seit 3 Wochen",
        "Zaehlerablesung konnte beim letzten Termin nicht durchgefuehrt werden",
        "Kunde bestreitet den abgelesenen Verbrauchswert",
        "Manuelle Ablesung steht seit ueber einem Monat aus",
        "Zaehlerstand wirkt im Vergleich zum Vorjahr unplausibel",
    ],
    "Messdatenuebertragung": [
        "iMSys-Geraet sendet seit Tagen keine Messwerte mehr",
        "Uebertragungsluecke im Smart-Meter-Gateway festgestellt",
        "Messwerte kommen verzoegert beim Messstellenbetreiber an",
        "Datenuebertragung vom intelligenten Messsystem unterbrochen",
        "Gateway-Fehler verhindert automatische Verbrauchsuebermittlung",
    ],
    "Rechnungserstellung": [
        "Rechnung nie erhalten laut Kunde",
        "Rechnung wurde an alte Adresse verschickt",
        "Kunde meldet fehlerhafte Rechnungspositionen",
        "Postversand der Rechnung nicht nachweisbar",
        "Rechnung enthaelt laut Kunde falschen Tarif",
    ],
    "Mahnverfahren": [
        "SEPA-Ruecklastschrift, Grund unbekannt",
        "Kunde reagiert seit mehreren Mahnstufen nicht",
        "Kein dokumentierter Mahnkontakt trotz langer Verzugsdauer",
        "Mahnschreiben kam als unzustellbar zurueck",
        "Kunde bestreitet Erhalt der Mahnung",
    ],
    "Zahlungsbuchung": [
        "Zahlung wurde laut Kunde ueberwiesen, ist aber nicht verbucht",
        "Zahlungseingang auf falsches Kundenkonto zugeordnet",
        "Verzoegerung bei der Zahlungsverbuchung im System",
        "Kunde legt Zahlungsbeleg vor, Buchung fehlt im System",
        "Doppelte Zahlung durch Kunde gemeldet, Buchung ungeklaert",
    ],
}


def make_case(case_id: int, rng: random.Random) -> dict:
    label = rng.choice(CATEGORIES)

    # Strukturierte Felder pro Kategorie so gesetzt, dass GENAU die passende Regel
    # aus F2 zuverlässig greift (Messdatenerfassung/Rechnungserstellung/Mahnverfahren)
    # bzw. GAR KEINE Regel greift (Messdatenuebertragung/Zahlungsbuchung -> LLM-Pfad).
    # Das hält Regel-Engine und LLM-Klassifizierer beide ehrlich nachvollziehbar,
    # statt zufällig überlappende Felder zu erzeugen, die die Regeln verwässern würden.
    if label == "Messdatenerfassung":
        meter_type = "manuell"
        tage_seit_faelligkeit = rng.randint(31, 90)
        rechnungsweg = rng.choice(["Digital", "SEPA"])
        bisherige_verzugstage = rng.randint(0, 55)
        kein_mahnkontakt_dokumentiert = False
    elif label == "Messdatenuebertragung":
        meter_type = "iMSys"
        tage_seit_faelligkeit = rng.randint(15, 60)
        rechnungsweg = rng.choice(["Digital", "SEPA"])
        bisherige_verzugstage = rng.randint(0, 55)
        kein_mahnkontakt_dokumentiert = False
    elif label == "Rechnungserstellung":
        meter_type = "iMSys"
        tage_seit_faelligkeit = rng.randint(5, 90)
        rechnungsweg = "Post"
        bisherige_verzugstage = rng.randint(21, 60)
        kein_mahnkontakt_dokumentiert = False
    elif label == "Mahnverfahren":
        meter_type = "iMSys"
        tage_seit_faelligkeit = rng.randint(5, 90)
        rechnungsweg = rng.choice(["Digital", "SEPA"])
        bisherige_verzugstage = rng.randint(61, 120)
        kein_mahnkontakt_dokumentiert = True
    else:  # Zahlungsbuchung
        meter_type = "iMSys"
        tage_seit_faelligkeit = rng.randint(5, 60)
        rechnungsweg = rng.choice(["Digital", "SEPA"])
        bisherige_verzugstage = rng.randint(0, 55)
        kein_mahnkontakt_dokumentiert = False

    kundensegment = rng.choices(["B2C", "B2B"], weights=[0.75, 0.25])[0]
    betrag_eur = round(rng.uniform(35, 2500) if kundensegment == "B2C" else rng.uniform(500, 15000), 2)

    freitext_notiz = rng.choice(NOTES_BY_CATEGORY[label])

    return {
        "case_id": f"CASE-{case_id:04d}",
        "meter_type": meter_type,
        "tage_seit_faelligkeit": tage_seit_faelligkeit,
        "rechnungsweg": rechnungsweg,
        "kundensegment": kundensegment,
        "betrag_eur": betrag_eur,
        "bisherige_verzugstage": bisherige_verzugstage,
        "kein_mahnkontakt_dokumentiert": kein_mahnkontakt_dokumentiert,
        "freitext_notiz": freitext_notiz,
        "ground_truth_label": label,
    }


def generate(n: int, seed: int) -> pd.DataFrame:
    rng = random.Random(seed)
    rows = [make_case(i + 1, rng) for i in range(n)]
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic M2C receivables cases.")
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default="data/synthetic_cases.csv")
    args = parser.parse_args()

    df = generate(args.n, args.seed)
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df)} synthetic cases to {args.out}")
    print(df["ground_truth_label"].value_counts())


if __name__ == "__main__":
    main()
