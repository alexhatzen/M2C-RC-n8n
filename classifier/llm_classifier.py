"""
F3 — LLM-Klassifizierer (Anthropic API).

Wird nur aufgerufen, wenn die Rule Engine (F2) keinen eindeutigen Treffer hatte.
Erhält alle strukturierten Felder + die Freitext-Notiz, liefert
{label, confidence, reasoning} als JSON. Muss immer eine der 5 fixen
Kategorien wählen oder "unklar" (PRD F3).
"""

import hashlib
import json
import re

from classifier.config import ANTHROPIC_MODEL, CATEGORIES, FALLBACK_LABEL, USE_REAL_LLM

_client = None


def _get_client():
    global _client
    if _client is None:
        import anthropic  # lazy import: nicht nötig im Simulationsmodus (USE_REAL_LLM=false)

        _client = anthropic.Anthropic()  # liest ANTHROPIC_API_KEY aus der Umgebung
    return _client


# --- Simulierter LLM-Klassifizierer (Default) --------------------------------
#
# Kein API-Key/Netzwerk/Kosten nötig. Keyword-Heuristik gegen die Freitext-Notiz,
# mit deterministischem, aber pseudo-zufälligem Konfidenz-Rauschen (via Hash des
# case_id), damit manche Fälle absichtlich unter dem Confidence-Threshold landen
# und so den "manual review"-Pfad im Demo zeigen. Der echte Anthropic-Call bleibt
# unten erhalten und ist über USE_REAL_LLM=true aktivierbar.

_KEYWORDS_BY_CATEGORY = {
    "Messdatenerfassung": ["zaehlerstand", "ablesung", "verbrauchswert", "zähler"],
    "Messdatenuebertragung": ["imsys", "gateway", "uebertrag", "übertrag", "messwert"],
    "Rechnungserstellung": ["rechnung", "adresse", "tarif", "postversand"],
    "Mahnverfahren": ["mahn", "sepa", "ruecklastschrift", "rücklastschrift"],
    "Zahlungsbuchung": ["zahlung", "ueberwiesen", "überwiesen", "buchung", "beleg"],
}


def _simulate_llm(case: dict) -> dict:
    note = str(case.get("freitext_notiz", "")).lower()
    scores = {
        cat: sum(1 for kw in kws if kw in note) for cat, kws in _KEYWORDS_BY_CATEGORY.items()
    }
    best_label = max(scores, key=scores.get)
    best_score = scores[best_label]

    # Deterministisches Pseudo-Rauschen pro Fall (stabil über wiederholte Läufe).
    digest = hashlib.sha256(str(case.get("case_id", "")).encode()).hexdigest()
    noise = (int(digest[:8], 16) % 1000) / 1000.0  # 0.0 - 0.999

    if best_score == 0:
        label = FALLBACK_LABEL
        confidence = round(0.35 + noise * 0.25, 2)  # 0.35 - 0.60 -> immer manual review
    else:
        label = best_label
        # Mehr Keyword-Treffer -> tendenziell höhere Konfidenz, plus Rauschen.
        base = min(0.65 + 0.12 * best_score, 0.93)
        confidence = round(min(base + (noise - 0.5) * 0.3, 0.99), 2)
        confidence = max(confidence, 0.55)

    return {
        "label": label,
        "source": "llm",
        "confidence": confidence,
        "reasoning": (
            f"(simuliert) Freitext-Notiz deutet auf '{label}' hin"
            if label != FALLBACK_LABEL
            else "(simuliert) Freitext-Notiz liefert kein eindeutiges Signal"
        ),
    }


SYSTEM_PROMPT = f"""Du bist ein Root-Cause-Klassifizierer für überfällige Forderungsfälle \
im Meter-to-Cash-Prozess eines Energieversorgers. Du bekommst strukturierte Falldaten \
und eine Freitext-Eskalationsnotiz. Ordne den Fall GENAU EINER der folgenden \
5 Kategorien zu, oder "unklar", falls wirklich keine Kategorie passt:

{chr(10).join(f"- {c}" for c in CATEGORIES)}

Antworte AUSSCHLIESSLICH mit kompaktem JSON in genau diesem Format, ohne Fließtext \
davor oder danach:
{{"label": "<eine der 5 Kategorien oder 'unklar'>", "confidence": <Zahl zwischen 0 und 1>, \
"reasoning": "<ein kurzer, nachvollziehbarer Satz auf Deutsch>"}}
"""


def _build_user_prompt(case: dict) -> str:
    fields = {k: v for k, v in case.items() if k != "ground_truth_label"}
    return "Falldaten:\n" + json.dumps(fields, ensure_ascii=False, indent=2)


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"Keine JSON-Struktur in LLM-Antwort gefunden: {text!r}")
    return json.loads(match.group(0))


def classify_with_llm(case: dict) -> dict:
    """Dispatcher: simulierter Klassifizierer (Default) oder echter Anthropic-Call
    (USE_REAL_LLM=true in .env). Gibt immer {label, source='llm', confidence, reasoning} zurück.
    """
    if not USE_REAL_LLM:
        return _simulate_llm(case)
    return _classify_with_llm_api(case)


def _classify_with_llm_api(case: dict) -> dict:
    """Ruft Claude über die Anthropic API auf.

    Ein Parse-Fehler wird einmal per Retry mit einer schärferen Erinnerung
    abgefangen; schlägt auch das fehl, wird "unklar" mit confidence=0.0 zurückgegeben.
    """
    client = _get_client()
    user_prompt = _build_user_prompt(case)

    for attempt in range(2):
        prompt = user_prompt
        if attempt == 1:
            prompt += "\n\nErinnerung: Antworte NUR mit dem JSON-Objekt, sonst nichts."

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = "".join(block.text for block in response.content if block.type == "text")

        try:
            parsed = _parse_json_response(raw_text)
            label = parsed.get("label", FALLBACK_LABEL)
            if label not in CATEGORIES:
                label = FALLBACK_LABEL
            confidence = float(parsed.get("confidence", 0.0))
            reasoning = parsed.get("reasoning", "")
            return {
                "label": label,
                "source": "llm",
                "confidence": confidence,
                "reasoning": reasoning,
            }
        except (ValueError, json.JSONDecodeError):
            if attempt == 0:
                continue
            return {
                "label": FALLBACK_LABEL,
                "source": "llm",
                "confidence": 0.0,
                "reasoning": "LLM-Antwort konnte nicht als JSON geparst werden.",
            }
