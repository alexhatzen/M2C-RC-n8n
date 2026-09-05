"""
F2 — Rule Engine.

Deterministische Regeln für eindeutige Fälle. Jede Regel, die greift, liefert
sofort Label + source="rule" + confidence=1.0 zurück (kein LLM-Call nötig —
Kostenkontrolle). Greift keine Regel, geht der Fall an den LLM-Klassifizierer (F3).
"""

from typing import Optional


def apply_rules(case: dict) -> Optional[dict]:
    """Wendet die Regeln aus PRD F2 der Reihe nach an.

    `case` enthält die strukturierten Felder eines synthetischen Falls
    (siehe data/generate_data.py) — NICHT das ground_truth_label.
    """

    # Regel 1: manuelle Zählerablesung, seit über 30 Tagen überfällig
    if case["meter_type"] == "manuell" and case["tage_seit_faelligkeit"] > 30:
        return {
            "label": "Messdatenerfassung",
            "source": "rule",
            "confidence": 1.0,
            "reasoning": "Regel: meter_type=manuell und tage_seit_faelligkeit>30",
        }

    # Regel 2: Papierrechnung, lange in Verzug -> Rechnung könnte nie angekommen sein
    if case["rechnungsweg"] == "Post" and case["bisherige_verzugstage"] > 20:
        return {
            "label": "Rechnungserstellung",
            "source": "rule",
            "confidence": 1.0,
            "reasoning": "Regel: rechnungsweg=Post und bisherige_verzugstage>20",
        }

    # Regel 3: sehr langer Verzug ohne dokumentierten Mahnkontakt
    if case["bisherige_verzugstage"] > 60 and case["kein_mahnkontakt_dokumentiert"]:
        return {
            "label": "Mahnverfahren",
            "source": "rule",
            "confidence": 1.0,
            "reasoning": "Regel: bisherige_verzugstage>60 und kein_mahnkontakt_dokumentiert",
        }

    return None
