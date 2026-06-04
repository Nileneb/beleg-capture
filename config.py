"""Beleg-Capture — zentrale Konfiguration."""

import os
from pathlib import Path

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
VLM_MODEL = os.environ.get("VLM_MODEL", "qwen2.5vl:3b")
VLM_TIMEOUT = int(os.environ.get("VLM_TIMEOUT", "120"))

DATA_DIR = Path(os.environ.get("CAPTURE_DATA_DIR", "data"))

# Sachkonto-Vorschlag kommt vom prefilter-api-Endpoint POST /api/suggest
# (Embeddings/Modell bleiben dort — beleg ruft nur HTTP, kein ML lokal).
# Index baut prefilter: python -m src.kontierung build <export> --out data/konto_index
PREFILTER_API_URL = os.environ.get("PREFILTER_API_URL", "http://localhost:8000").rstrip("/")
SUGGEST_TIMEOUT = int(os.environ.get("SUGGEST_TIMEOUT", "15"))

# Kanonische Buchungsfelder — exakt die Keys aus prefilter-api COLUMN_ALIASES,
# damit der CSV-Export dort ohne Mapping-Verluste eingelesen wird.
# sachkonto = die Kontierung selbst: vom VLM NICHT erkennbar (kein Kontenrahmen-
# Wissen) → wird aus dem Präzedenz-Index vorgeschlagen, Mensch bestätigt.
FIELDS = ["kreditor", "betrag", "datum", "belegnummer", "buchungstext", "sachkonto"]

FIELD_LABELS = {
    "kreditor": "Kreditor / Lieferant",
    "betrag": "Betrag",
    "datum": "Datum",
    "belegnummer": "Belegnummer",
    "buchungstext": "Buchungstext",
    "sachkonto": "Sachkonto (konto_soll)",
}
