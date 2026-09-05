# PRD — Root-Cause-Klassifizierer mit Automatisierungs-Kreislauf (M2C Forderungsmanagement)

## 1. Summary

Ein Python-basierter Root-Cause-Klassifizierer (Regeln + LLM-Hybrid) für überfällige Forderungsfälle im Meter-to-Cash-Prozess, der bei ausreichender Konfidenz automatisch eine Aktion in einem n8n-Workflow auslöst. Baustein für die MVP-Präsentation im Case „AI Process Intelligence Engineer" bei Monitoring & Solutions (E.ON), Fokus: geschlossener Steuerungskreislauf (Process Mining → AI-Ursachenanalyse → automatisierte Maßnahme).

## 2. Contacts

| Name | Rolle | Kommentar |
|---|---|---|
| Alex Hatzenbühler | Owner / Bewerber | Baut und präsentiert den MVP im Interview |
| Claude Code | Umsetzung | Erhält dieses PRD als Build-Spezifikation |

## 3. Background

Der Case beschreibt einen Fachbereich (E.ON, Meter-to-Cash), dessen Forderungsbestände steigen, ohne dass systematisch zwischen Ursachen unterschieden wird (Messdatenerfassung, -übertragung, Rechnungserstellung, Mahnverfahren, Zahlungsbuchung). Aktuell wird jeder überfällige Fall manuell gesichtet — es gibt keine automatisierte Triage.

Die Stellenausschreibung (AI Process Intelligence Engineer, München/Würzburg) verlangt explizit einen „geschlossenen Steuerungskreislauf": Process Mining schafft Transparenz, AI analysiert Ursachen, automatisierte Maßnahmen wirken in den Prozess zurück — sowie praktische Erfahrung mit Automatisierungsplattformen (n8n, Make, Zapier, Power Automate) inkl. API-/Webhook-Integration. Dieser MVP bildet genau diesen Kreislauf ab, im Kleinen und mit synthetischen Daten.

Warum jetzt: Zeitbudget für die Präsentation ist 15 Minuten inkl. Diskussion; nur ein Lösungsbaustein soll in Produktionsreife gezeigt werden (siehe Case-Schlussfrage). Dieser Baustein wurde als der mit dem höchsten Deckungsgrad zur Stellenausschreibung ausgewählt.

## 4. Objective

**Ziel:** Im Interview in ca. 6–7 Minuten zeigen, wie aus einem unscharfen Problem (steigende Forderungen) ein funktionierender, produktionsnaher erster Baustein wird — inklusive AI-Urteilsvermögen (Regel vs. LLM) und automatisierter Rückwirkung in den Prozess.

**Erfolg wird gemessen an (informell, Demo-Kontext, kein echtes Produktions-KPI):**
- Klassifizierer ordnet synthetische Testfälle nachvollziehbar einer von 5 Root-Cause-Kategorien zu, inkl. sichtbarer Begründung (Regel-Treffer vs. LLM-Einschätzung mit Konfidenz).
- Mindestens 2 unterschiedliche automatisierte Aktionen lassen sich live im n8n-Workflow demonstrieren (z. B. Slack-Nachricht + Log-Eintrag).
- Präsentierbar in unter 3 Minuten Live-Demo (Rest der Zeit für Erklärung/Diskussion).

**Bezug zur Stellenausschreibung:** trifft direkt „Entwicklung und Betrieb von AI-Lösungen", „aktive Prozesssteuerung durch AI und Automatisierung", „professioneller Umgang mit Workflow- und Automatisierungsplattformen", „Systeme über APIs und Webhooks integrieren".

## 5. Market Segment(s)

**Für wen:** Fiktiver Fachbereich „Forderungsmanagement / Meter-to-Cash" bei E.ON — konkret die Sachbearbeitung, die überfällige Fälle manuell prüft, sowie deren Teamleitung, die Transparenz über Ursachenverteilung braucht.

**Constraints:**
- Kein Zugriff auf echte Celonis-/Snowflake-/Salesforce-Systeme — nur synthetische Daten.
- Muss ohne Enterprise-Lizenzen laufen (n8n Self-Hosted/Docker oder n8n Cloud Free Tier bzw. Make.com Free Tier).
- Muss offline vorbereitbar und live vorführbar sein (keine Abhängigkeit von echtem E.ON-Netzwerk).

## 6. Value Proposition(s)

- **Zeitersparnis:** Sachbearbeitung erhält vorklassifizierte, priorisierte Fälle statt manueller Ursachensuche.
- **Nachvollziehbarkeit:** Jede Entscheidung ist auditierbar — Regel oder LLM, mit Konfidenzwert und Begründungstext.
- **Geschlossener Kreislauf statt reinem Reporting:** Der Case fordert explizit „Fokus auf Ergebnissen, nicht auf Reporting" — dieser Baustein handelt statt nur zu analysieren.
- **Skalierbarkeitsargument:** Regel-Layer deckt die günstigen, eindeutigen Fälle ab; LLM nur für mehrdeutige Fälle — Kostenkontrolle bei AI-Einsatz, ein Kernkriterium für „AI-Urteilsvermögen".

## 7. Solution

### 7.1 UX / Ablauf (Text-Flow für die Demo)

```
[Synthetischer Fall: strukturierte Felder + Freitext-Notiz]
        │
        ▼
[Python: Rule Engine] ──(eindeutig?)──► Ja ──► Root-Cause-Label + confidence=hoch, source="rule"
        │
        Nein
        ▼
[Python: LLM-Klassifizierer via Anthropic API] ──► Root-Cause-Label + confidence-Score, source="llm"
        │
        ▼
[Entscheidung: confidence ≥ Threshold?]
        │
   Ja ──┼── Nein
   ▼         ▼
[Webhook POST an n8n]   [In Manual-Review-Log schreiben]
        │
        ▼
[n8n: Switch-Node nach Root-Cause-Kategorie]
        │
        ├─► Messdatenerfassung/-übertragung → Slack-Nachricht an "Metering Ops"
        ├─► Rechnungserstellung → Zeile in Google Sheet "Billing Review"
        ├─► Mahnverfahren → Task-Eintrag in Airtable/Sheet "Collections Follow-up"
        └─► Zahlungsbuchung → Zeile in Google Sheet "Finance Review"
        │
        ▼
[n8n: Audit-Log-Node] → Append in zentrales Log (Sheet/CSV): case_id, label, source, confidence, action, timestamp
```

### 7.2 Key Features

**F1 — Synthetischer Datengenerator (Python, pandas)**
Erzeugt N Fälle (z. B. 200) mit Feldern:
- `case_id`, `meter_type` (iMSys/manuell), `tage_seit_faelligkeit`, `rechnungsweg` (Post/Digital/SEPA), `kundensegment` (B2C/B2B), `betrag_eur`, `bisherige_verzugstage`
- `freitext_notiz` (synthetische Eskalationsnotiz, z. B. „Kunde meldet falschen Zählerstand seit 3 Wochen", „Rechnung nie erhalten laut Kunde", „SEPA-Rücklastschrift, Grund unbekannt")
- Ground-Truth-Label (für Demo-Validierung, wird dem Klassifizierer nicht gezeigt)

**F2 — Rule Engine**
Deterministische Regeln für eindeutige Fälle, z. B.:
- `meter_type == "manuell" AND tage_seit_faelligkeit > 30` → „Messdatenerfassung"
- `rechnungsweg == "Post" AND bisherige_verzugstage > 20` → „Rechnungserstellung"
- `bisherige_verzugstage > 60 AND kein_mahnkontakt_dokumentiert` → „Mahnverfahren ineffektiv"

Jede Regel gibt Label + `source="rule"` + `confidence=1.0` zurück. Regeln, die nicht greifen → Fall geht an F3.

**F3 — LLM-Klassifizierer (Anthropic API)**
Prompt erhält strukturierte Felder + `freitext_notiz`, liefert JSON: `{label, confidence, reasoning}`. Kategorien fix vorgegeben (5 aus Diagnose Richtung B, siehe 7.4). Muss immer eine der 5 Kategorien wählen oder „unklar".

**F4 — Confidence-Gate & Webhook**
Bei `confidence ≥ 0.8` → POST an n8n-Webhook mit vollständigem Payload. Sonst → Zeile in lokales „Manual Review"-Log.

**F5 — n8n-Workflow**
- Webhook-Trigger-Node (empfängt POST)
- Switch-Node (routet nach `label`)
- 4 Action-Branches (Slack/Sheet/Airtable, siehe 7.1)
- Ein zentraler Audit-Log-Node (läuft nach jedem Branch)

**F6 — Demo-Dashboard (optional, falls Zeit reicht)**
Kleines Streamlit- oder einfaches HTML-Dashboard: zeigt Verteilung der klassifizierten Fälle nach Kategorie, Anteil Regel vs. LLM, Konfidenzverteilung — als visueller Abschluss der Demo.

### 7.3 Technology

- **Sprache/Runtime:** Python 3.11+, pandas
- **LLM:** Anthropic API (Claude), über `anthropic` Python SDK
- **Automatisierung:** n8n (Docker/Self-Hosted oder Cloud Free Tier) — alternativ Make.com, falls n8n-Setup zu zeitaufwändig
- **Mock-Zielsysteme:** Google Sheets API oder Airtable API (für „Billing Review", „Collections Follow-up", „Finance Review", Audit-Log); Slack Incoming Webhook für Benachrichtigung
- **Optional:** Streamlit für Dashboard
- **Kein** Bedarf an echter Celonis-/Snowflake-/Salesforce-Anbindung — alles gemockt

### 7.4 Assumptions

- Root-Cause-Kategorien fix auf 5: Messdatenerfassung, Messdatenübertragung, Rechnungserstellung, Mahnverfahren, Zahlungsbuchung (aus „Diagnose Richtung B" der Fallstudien-Lösung).
- „Diagnose Richtung A" (Preis-/Mengen-/Abschreibungseffekt, externe Faktoren) ist ein vorgelagerter Portfolio-Check, kein Fall-Label — wird in der Präsentation als Kontext erwähnt, nicht im Klassifizierer abgebildet.
- Confidence-Threshold 0.8 ist ein Demo-Platzhalter, keine kalibrierte Zahl.
- n8n läuft lokal oder in Free-Tier-Cloud; keine Enterprise-Features nötig.
- Synthetische Daten reichen für die Demo aus — es wird nicht behauptet, dass reale Klassifikationsgüte gemessen wurde.
- Slack/Sheet/Airtable sind Platzhalter für echte Zielsysteme (Salesforce, interne Ticketsysteme) — im Interview explizit so benennen.

## 8. Release

**V1 (bis zum Interview-Termin, Zeitbudget ca. 1–1,5 Tage):**
- F1 Datengenerator, F2 Rule Engine, F3 LLM-Klassifizierer, F4 Confidence-Gate
- F5 n8n-Workflow mit mindestens 2 Action-Branches + Audit-Log
- Kein Dashboard zwingend erforderlich für V1

**V2 (nur falls Zeit reicht, sonst als "nächster Schritt" im Interview mündlich skizzieren):**
- F6 Demo-Dashboard
- Alle 4 Action-Branches statt 2
- Erweiterung um Diagnose-Richtung-A-Portfoliocheck als vorgelagerten Batch-Job

**V3 (nur als Ausblick im Interview, nicht bauen):**
- Anbindung an echte Celonis-Event-Logs statt synthetischer Daten
- Multi-Agent-Orchestrierung (Planner/Critic) statt Single-Call-Klassifizierer
- Self-Service-Erweiterung durch den Fachbereich (Antwort auf Case-Punkt 5 „Nächster Schritt")
