"""Beleg-Capture — zentrale Konfiguration."""

import os
from pathlib import Path

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
VLM_MODEL = os.environ.get("VLM_MODEL", "qwen2.5vl:3b")
VLM_TIMEOUT = int(os.environ.get("VLM_TIMEOUT", "120"))

DATA_DIR = Path(os.environ.get("CAPTURE_DATA_DIR", "data"))

# Kanonische Buchungsfelder — exakt die Keys aus prefilter-api COLUMN_ALIASES,
# damit der CSV-Export dort ohne Mapping-Verluste eingelesen wird.
FIELDS = ["kreditor", "betrag", "datum", "belegnummer", "buchungstext"]

FIELD_LABELS = {
    "kreditor": "Kreditor / Lieferant",
    "betrag": "Betrag",
    "datum": "Datum",
    "belegnummer": "Belegnummer",
    "buchungstext": "Buchungstext",
}
