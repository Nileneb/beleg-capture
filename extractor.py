"""VLM-Extraktor — Foto eines Belegs → kanonische Buchungsfelder.

Ein VLM end-to-end (kein separates OCR): das Bild geht direkt an Ollama,
zurück kommt erzwungenes JSON (`format=json`).
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import requests

import config


class ExtractionError(RuntimeError):
    """Fehler beim VLM-Aufruf oder JSON-Parsing — wird in der UI sichtbar gemacht."""


_PROMPT = (
    "Du bist ein Buchhaltungs-Assistent. Lies diese Quittung / diesen Beleg und gib "
    "AUSSCHLIESSLICH ein JSON-Objekt mit genau diesen Feldern zurück:\n"
    '{"kreditor": "", "betrag": "", "datum": "", "belegnummer": "", "buchungstext": ""}\n'
    "Bedeutung der Felder:\n"
    "- kreditor: Name des Lieferanten / Händlers / Geschäfts\n"
    "- betrag: Gesamt-/Rechnungsbetrag als Zahl im deutschen Format (z.B. 12,90)\n"
    "- datum: Belegdatum im Format TT.MM.JJJJ\n"
    "- belegnummer: Rechnungs- oder Bonnummer, falls vorhanden\n"
    "- buchungstext: kurze Beschreibung, was gekauft wurde\n"
    "Wenn ein Feld nicht erkennbar ist, gib einen leeren String. "
    "Keine Erklärungen, kein Markdown, nur das JSON-Objekt."
)


def extract_fields(image_path: str) -> dict:
    """Schickt das Bild an das VLM und liefert die kanonischen Felder als dict.

    Wirft ExtractionError bei Netz-/HTTP-/JSON-Fehlern — bewusst fail-loud,
    damit der Fehler in der UI landet statt stumm zu verschwinden.
    """
    path = Path(image_path)
    if not path.exists():
        raise ExtractionError(f"Bilddatei nicht gefunden: {path}")

    img_b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    payload = {
        "model": config.VLM_MODEL,
        "prompt": _PROMPT,
        "images": [img_b64],
        "format": "json",
        "stream": False,
        "options": {"temperature": 0},
    }

    try:
        resp = requests.post(
            f"{config.OLLAMA_URL}/api/generate",
            json=payload,
            timeout=config.VLM_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise ExtractionError(
            f"VLM-Aufruf fehlgeschlagen ({config.OLLAMA_URL}, Modell {config.VLM_MODEL}): {exc}"
        ) from exc

    raw = resp.json().get("response", "")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"VLM lieferte kein gültiges JSON: {raw[:300]!r}") from exc

    if not isinstance(data, dict):
        raise ExtractionError(f"VLM-JSON ist kein Objekt: {raw[:300]!r}")

    return {f: str(data.get(f, "") or "").strip() for f in config.FIELDS}
