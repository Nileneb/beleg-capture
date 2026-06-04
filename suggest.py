"""Sachkonto-Vorschlag über den prefilter-api-Endpoint POST /api/suggest.

beleg bleibt schlank: kein Embedding-Modell, kein Index-Lesen — nur ein
HTTP-Call. prefilter hält den Präzedenz-Index (Kreditor-Häufigkeit + optional
Buchungstext-Embedding-kNN) und das Modell an einer Stelle.

Fail-soft-LAUT: ist der Endpoint nicht erreichbar oder der Index nicht gebaut,
liefert `suggest_konto` eine leere Liste UND einen Grund-String für die UI —
kein stummes Schlucken.
"""

from __future__ import annotations

from dataclasses import dataclass

import requests

import config


@dataclass
class KontoSuggestion:
    konto: str
    bezeichnung: str
    score: float
    reason: str


def suggest_konto(
    kreditor: str = "", buchungstext: str = "", top_k: int = 3
) -> tuple[list[KontoSuggestion], str | None]:
    """Fragt prefilter /api/suggest. Returns (suggestions, error|None)."""
    url = f"{config.PREFILTER_API_URL}/api/suggest"
    try:
        resp = requests.post(
            url,
            json={"kreditor": kreditor, "buchungstext": buchungstext, "top_k": top_k},
            timeout=config.SUGGEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        return [], f"Vorschlags-API nicht erreichbar ({url}): {exc}"

    if resp.status_code == 503:
        return [], resp.json().get("warning", "Kontierungs-Index nicht verfügbar.")
    if resp.status_code != 200:
        return [], f"Vorschlags-API antwortete {resp.status_code}: {resp.text[:200]}"

    data = resp.json()
    sugs = [
        KontoSuggestion(
            konto=s["konto"],
            bezeichnung=s.get("bezeichnung", ""),
            score=s.get("score", 0.0),
            reason=s.get("reason", ""),
        )
        for s in data.get("suggestions", [])
    ]
    if not sugs:
        return [], (
            f"Kein Präzedenzfall für Kreditor „{kreditor.strip()}“ / „{buchungstext.strip()[:40]}“."
        )
    # warning (z.B. Text-kNN-Degradation) als Grund mitgeben, aber Treffer behalten
    return sugs, data.get("warning")
