"""Zentrale Konfiguration für den Root-Cause-Klassifizierer (F4)."""

import os

from dotenv import load_dotenv

load_dotenv()

# Die 5 fixen Root-Cause-Kategorien (PRD 7.4, "Diagnose Richtung B").
CATEGORIES = [
    "Messdatenerfassung",
    "Messdatenuebertragung",
    "Rechnungserstellung",
    "Mahnverfahren",
    "Zahlungsbuchung",
]
FALLBACK_LABEL = "unklar"

# Demo-Platzhalter, keine kalibrierte Zahl (PRD 7.4).
CONFIDENCE_THRESHOLD = 0.8

# n8n Webhook-URL (Test- oder Production-URL aus dem importierten Workflow).
# Kann per Umgebungsvariable überschrieben werden, ohne Code zu ändern.
N8N_WEBHOOK_URL = os.environ.get(
    "N8N_WEBHOOK_URL",
    "https://REPLACE-ME.app.n8n.cloud/webhook/root-cause-classifier",
)

# n8n Workflow-Editor-URL (ohne trailing slash), zum Bauen von Deep-Links auf die
# jeweilige Execution eines Falls — für die Live-Demo ("in n8n ansehen"-Link je Fall).
N8N_WORKFLOW_URL = os.environ.get(
    "N8N_WORKFLOW_URL",
    "https://azorahai.app.n8n.cloud/workflow/F4PmBWF05PuQVFZE",
)

ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

# Standard: simulierter LLM-Klassifizierer (kein API-Kosten/Netzwerk-Risiko am Demo-Tag).
# Auf "true" setzen, um echte Anthropic-API-Calls zu verwenden (ANTHROPIC_API_KEY nötig).
USE_REAL_LLM = os.environ.get("USE_REAL_LLM", "false").lower() == "true"

MANUAL_REVIEW_LOG_PATH = os.environ.get(
    "MANUAL_REVIEW_LOG_PATH", "classifier/manual_review_log.csv"
)
RESULTS_PATH = os.environ.get("RESULTS_PATH", "classifier/results.json")
