# Beleg-Capture (Prototyp)

Dreht die Logik von [`prefilter-api`](../prefilter-api) um: **vorne erfassen statt
hinten Fehler suchen.** Ein User fotografiert einen Beleg, ein VLM liest ihn und
schlägt Buchungsfelder vor; der Mensch korrigiert und speichert.

Jede Aufnahme protokolliert **VLM-Vorschlag + menschliche Korrektur** als Paar —
das ist gleichzeitig das Ergebnis und ein Trainingspaar für späteres VLM-Finetuning.

## Ziel dieses Bauschritts

**Konzept beweisen:** Taugt ein lokales VLM (`qwen2.5vl:3b` via `three.linn.games`),
um aus echten Belegen brauchbare Buchungsfelder zu ziehen? Kleiner Prototyp, kein
Produktions-Scope.

## Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py            # UI auf http://localhost:7865
```

Konfiguration über env (Defaults in `config.py`):
`OLLAMA_URL` (Default `http://localhost:11434`), `VLM_MODEL`
(Default `qwen2.5vl:3b`), `VLM_TIMEOUT`, `CAPTURE_DATA_DIR`.

## Module

| Datei          | Zweck |
|----------------|-------|
| `extractor.py` | Bild → VLM (`/api/generate`, `format=json`) → kanonische Felder. Fail-loud. |
| `store.py`     | JSONL-Capture-Store + CSV-Export (Muster: prefilter-api `feedback.py`). |
| `app.py`       | Gradio-UI (Foto → Auslesen → korrigieren → Speichern → CSV-Export). |
| `config.py`    | Endpoint, Modell, Felder. |

Felder = exakt die Kanon-Keys von prefilter-api `parser.COLUMN_ALIASES`
(`kreditor, betrag, datum, belegnummer, buchungstext`) → CSV-Export ist dort ohne
Mapping-Verlust einlesbar.

## Bewusst NICHT enthalten (spätere Schritte)

- **Schritt 2:** Sachkonto-Vorschlag + Kontierungsrichtlinie (braucht Kontenrahmen-Wissen).
- **Schritt 3:** Finetuning-Datensatz aus prefilter-api-Korrekturen + Richtlinie.
- Soll/Haben-Doppelbuchung / volle Diamant-Beleg-Struktur (ein Bon = Teilbuchung).
- VLM-Vergleich (qwen2.5vl vs minicpm-v), Auth, Mobile-Polish, Multi-User.
