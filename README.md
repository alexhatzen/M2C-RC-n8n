# Root-Cause-Klassifizierer — M2C Forderungsmanagement (Demo)

MVP für den Case "AI Process Intelligence Engineer" (E.ON): Regel + LLM-Hybrid-Klassifizierer
für überfällige Forderungsfälle, mit Confidence-Gate und automatisiertem n8n-Kreislauf.
Siehe [PRD-RootCauseKlassifizierer.md](PRD-RootCauseKlassifizierer.md) für die volle Spezifikation.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # bereits vorhanden — ggf. Werte anpassen
```

`.env`:
- `ANTHROPIC_API_KEY` — nur nötig, wenn `USE_REAL_LLM=true` gesetzt wird (siehe unten).
- `N8N_WEBHOOK_URL` — Production-Webhook-URL aus dem importierten n8n-Workflow.

### LLM-Klassifizierer: simuliert vs. echt

Standardmäßig läuft der LLM-Schritt (F3) **simuliert** (`classifier/llm_classifier.py`,
Keyword-Heuristik gegen die Freitext-Notiz) — kein API-Key, keine Kosten, kein
Netzwerk-Risiko am Demo-Tag. Um echte Anthropic-Calls zu verwenden:

```bash
export USE_REAL_LLM=true
export ANTHROPIC_API_KEY=sk-ant-...
```

### n8n-Workflow importieren

1. In n8n: **Import from File** → `n8n/root_cause_workflow.json`.
2. Workflow aktivieren, die **Production-Webhook-URL** des Webhook-Trigger-Nodes kopieren.
3. `N8N_WEBHOOK_URL` in `.env` auf diese URL setzen.
4. Die 4 Action-Branches + der Audit-Log-Node posten an vorgenerierte
   [webhook.site](https://webhook.site)-Endpunkte (Platzhalter für Slack/Sheets/Airtable,
   siehe PRD 7.4 — im Interview explizit so benennen). Die URLs stehen direkt in den
   HTTP-Request-Nodes; bei Bedarf gegen eigene webhook.site-Token austauschen
   (`https://webhook.site/#!/` zeigt Live-Requests an).

## Run

```bash
# 1. Synthetische Fälle erzeugen (200, deterministischer Seed)
python data/generate_data.py --n 200

# 2. Vollen Batch klassifizieren -> classifier/results.json (Dashboard-Datenquelle)
#    + POST an n8n für alle Fälle >= Confidence-Threshold 0.8
python -m classifier.pipeline --n 200

# 3. Dashboard: dashboard/dashboard.html öffnen (Daten sind eingebettet,
#    nach jedem pipeline-Lauf mit dem Snippet unten neu einbetten)
```

Dashboard-Daten nach einem neuen Pipeline-Lauf neu einbetten:
```bash
python3 -c "
import json
data = open('classifier/results.json').read()
html = open('dashboard/dashboard.html').read()
# Ersetzt den aktuell eingebetteten JSON-Block (const RESULTS = [...];)
import re
html = re.sub(r'const RESULTS = \[.*?\];', f'const RESULTS = {data};', html, flags=re.S)
open('dashboard/dashboard.html', 'w').write(html)
"
```

## Live-Demo (3 Minuten)

```bash
python -m classifier.pipeline --live 3 --sample curated
```

Zeigt live: einen Regel-Treffer (Konfidenz 1.0, kein LLM-Call), einen LLM-Fall mit
Konfidenz ≥ 0.8 (Webhook wird ausgelöst), und typischerweise einen niedrig-konfidenten
Fall (landet in `classifier/manual_review_log.csv` statt im Webhook).

1. Terminal-Output zeigen (Regel vs. LLM, Konfidenz, Gate-Entscheidung).
2. n8n-Editor: Executions-Tab zeigt die grün aufleuchtenden Nodes für den ausgelösten Fall.
3. Zugehörigen webhook.site-Tab zeigen: eingehender Request mit dem gerouteten Payload.
4. Zum Dashboard wechseln für die Aggregatsicht über alle 200 Fälle.

## Repo-Layout

```
data/generate_data.py         F1 — Synthetischer Datengenerator
classifier/rules.py           F2 — Rule Engine
classifier/llm_classifier.py  F3 — LLM-Klassifizierer (simuliert/echt)
classifier/pipeline.py        F4 — Confidence-Gate & Orchestrierung
n8n/root_cause_workflow.json  F5 — n8n-Workflow (Switch + 4 Action-Branches + Audit-Log)
dashboard/dashboard.html      F6 — Demo-Dashboard (Artifact, rot/weiß, Dark Mode)
```
