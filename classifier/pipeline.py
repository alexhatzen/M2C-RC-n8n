"""
F4 — Confidence-Gate & Pipeline-Orchestrierung.

Für jeden Fall: Rule Engine zuerst (F2). Kein Treffer -> LLM-Klassifizierer (F3).
Danach Confidence-Gate: >=THRESHOLD -> POST an n8n-Webhook (F5),
sonst -> Zeile in manual_review_log.csv.

Schreibt für jeden Fall einen vollständigen Ergebnis-Datensatz nach results.json
(inkl. ground_truth_label, ausschließlich zur Demo-Validierung) — das ist die
Datenquelle für das Dashboard (F6).

Usage:
    python -m classifier.pipeline --n 200
    python -m classifier.pipeline --live 3 --sample curated
"""

import argparse
import csv
import json
import os
import random
import time
from datetime import datetime, timezone

import pandas as pd
import requests

from classifier.config import (
    CONFIDENCE_THRESHOLD,
    MANUAL_REVIEW_LOG_PATH,
    N8N_WEBHOOK_URL,
    N8N_WORKFLOW_URL,
    RESULTS_PATH,
)
from classifier.llm_classifier import classify_with_llm
from classifier.rules import apply_rules

CASE_FIELDS = [
    "case_id",
    "meter_type",
    "tage_seit_faelligkeit",
    "rechnungsweg",
    "kundensegment",
    "betrag_eur",
    "bisherige_verzugstage",
    "kein_mahnkontakt_dokumentiert",
    "freitext_notiz",
]


def classify_case(case: dict) -> dict:
    """Rule-first, LLM-fallback. Gibt {label, source, confidence, reasoning} zurück."""
    result = apply_rules(case)
    if result is not None:
        return result
    return classify_with_llm(case)


def send_to_n8n(payload: dict) -> tuple[bool, str | None]:
    """POSTet an n8n. Gibt (erfolgreich, execution_id) zurück — die execution_id
    kommt aus der Respond-to-Webhook-Node (`$execution.id`) und erlaubt einen
    Deep-Link direkt auf die Ausführung dieses Falls im n8n-Editor (Demo-Feature)."""
    try:
        resp = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=10)
        execution_id = None
        if resp.ok:
            try:
                execution_id = resp.json().get("execution_id")
            except ValueError:
                pass
        return resp.ok, execution_id
    except requests.RequestException as exc:
        print(f"  [WARN] Webhook-POST fehlgeschlagen für {payload.get('case_id')}: {exc}")
        return False, None


def n8n_execution_link(execution_id: str | None) -> str | None:
    if not execution_id:
        return None
    return f"{N8N_WORKFLOW_URL}/executions/{execution_id}"


def append_manual_review(case: dict, classification: dict) -> None:
    file_exists = os.path.exists(MANUAL_REVIEW_LOG_PATH)
    row = {**{k: case[k] for k in CASE_FIELDS}, **classification}
    with open(MANUAL_REVIEW_LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def run_pipeline(cases: list, verbose: bool = True) -> list:
    results = []
    for case in cases:
        classification = classify_case(case)
        gate_action = "webhook_sent" if classification["confidence"] >= CONFIDENCE_THRESHOLD else "manual_review"

        payload = {
            **{k: case[k] for k in CASE_FIELDS},
            "label": classification["label"],
            "source": classification["source"],
            "confidence": classification["confidence"],
            "reasoning": classification.get("reasoning"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        execution_id = None
        if gate_action == "webhook_sent":
            sent, execution_id = send_to_n8n(payload)
            gate_action = "webhook_sent" if sent else "webhook_failed"
            # n8n fans each call out into 1-2 downstream HTTP requests (action + audit-log);
            # a short pause here keeps us under the mocked endpoints' rate limits.
            time.sleep(0.4)
        else:
            append_manual_review(case, classification)

        if verbose:
            print(
                f"{case['case_id']}: {classification['label']} "
                f"(source={classification['source']}, confidence={classification['confidence']:.2f}) "
                f"-> {gate_action}"
            )

        results.append(
            {
                "case_id": case["case_id"],
                "label": classification["label"],
                "source": classification["source"],
                "confidence": classification["confidence"],
                "reasoning": classification.get("reasoning"),
                "gate_action": gate_action,
                "n8n_link": n8n_execution_link(execution_id),
                "ground_truth_label": case.get("ground_truth_label"),
                "kundensegment": case.get("kundensegment"),
                "betrag_eur": case.get("betrag_eur"),
            }
        )
    return results


def load_cases(csv_path: str) -> list:
    df = pd.read_csv(csv_path)
    return df.to_dict(orient="records")


def main():
    parser = argparse.ArgumentParser(description="Run the root-cause classification pipeline.")
    parser.add_argument("--input", type=str, default="data/synthetic_cases.csv")
    parser.add_argument("--n", type=int, default=None, help="Process the first N cases from --input.")
    parser.add_argument(
        "--live",
        type=int,
        default=None,
        help="Live-demo mode: process only N cases, printed verbosely for the audience.",
    )
    parser.add_argument(
        "--sample",
        choices=["first", "random", "curated"],
        default="first",
        help="How to pick the --live subset.",
    )
    args = parser.parse_args()

    cases = load_cases(args.input)

    if args.live:
        if args.sample == "random":
            cases = random.sample(cases, args.live)
        elif args.sample == "curated":
            # Ein Rule-Treffer, ein sicherer LLM-Fall, ein potenzieller manual-review-Fall.
            rule_hit = next((c for c in cases if apply_rules(c) is not None), cases[0])
            others = [c for c in cases if c["case_id"] != rule_hit["case_id"]]
            cases = [rule_hit] + others[: max(0, args.live - 1)]
        else:
            cases = cases[: args.live]
    elif args.n:
        cases = cases[: args.n]

    results = run_pipeline(cases)

    # Bei --live nur an bestehende results.json anhängen/mergen ist für die Demo nicht nötig;
    # der volle Batch-Lauf (--n) überschreibt results.json als alleinige Grundlage fürs Dashboard.
    if not args.live:
        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\nWrote {len(results)} results to {RESULTS_PATH}")

    n_rule = sum(1 for r in results if r["source"] == "rule")
    n_llm = sum(1 for r in results if r["source"] == "llm")
    n_gated = sum(1 for r in results if r["gate_action"] == "webhook_sent")
    n_manual = sum(1 for r in results if r["gate_action"] == "manual_review")
    print(
        f"\nSummary: {len(results)} cases | rule={n_rule} llm={n_llm} | "
        f"webhook_sent={n_gated} manual_review={n_manual}"
    )


if __name__ == "__main__":
    main()
