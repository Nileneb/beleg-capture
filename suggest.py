"""Sachkonto-Vorschlag aus dem prefilter-Präzedenz-Index.

Der Index wird von prefilter-api aus den Altdaten gebaut:
    python -m src.kontierung build <alt-export.csv> --out data/konto_index

Hier wird nur das portable Artefakt (`index.json`) gelesen — keine prefilter-
Abhängigkeit, kein Embedding, nur stdlib. Primärsignal: Kreditor→Konto-
Häufigkeit aus den Altdaten (gleicher Lieferant → meist gleiches Konto).

Fail-soft-LAUT: fehlt der Index oder der Kreditor, liefert `suggest_konto`
eine leere Liste UND einen Grund-String für die UI — kein stummes Schlucken.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import config


@dataclass
class KontoSuggestion:
    konto: str
    bezeichnung: str
    score: float
    reason: str


_INDEX: dict | None = None
_LOAD_ERROR: str | None = None


def _norm_kreditor(name: object) -> str:
    return " ".join(str(name).strip().lower().split())


def _load() -> None:
    global _INDEX, _LOAD_ERROR
    if _INDEX is not None or _LOAD_ERROR is not None:
        return
    p = Path(config.KONTO_INDEX_PATH) / "index.json"
    if not p.exists():
        _LOAD_ERROR = (
            f"Kein Kontierungs-Index unter {p}. In prefilter-api bauen:\n"
            f"  python -m src.kontierung build <alt-export.csv> --out data/konto_index"
        )
        return
    _INDEX = json.loads(p.read_text(encoding="utf-8"))


def suggest_konto(kreditor: str = "", top_k: int = 3) -> tuple[list[KontoSuggestion], str | None]:
    """Schlägt Sachkonten zu einem Kreditor vor.

    Returns (suggestions, error): error ist None bei Erfolg, sonst ein für die
    UI gedachter Grund (Index fehlt / Kreditor unbekannt).
    """
    _load()
    if _LOAD_ERROR:
        return [], _LOAD_ERROR

    assert _INDEX is not None
    kc = _INDEX.get("kreditor_konto", {}).get(_norm_kreditor(kreditor))
    if not kc:
        n_known = len(_INDEX.get("kreditor_konto", {}))
        return [], (
            f"Kein Präzedenzfall für Kreditor „{kreditor.strip()}“ "
            f"({n_known} bekannte Kreditoren im Index)."
        )

    gt = _INDEX.get("gt", {})
    dia = _INDEX.get("diamant_bezeichnung", {})
    total = sum(kc.values())
    out = [
        KontoSuggestion(
            konto=ko,
            bezeichnung=gt.get(ko) or dia.get(ko, ""),
            score=round(c / total, 3),
            reason=f"{c}× bei „{kreditor.strip()}“ ({c / total:.0%})",
        )
        for ko, c in sorted(kc.items(), key=lambda kv: -kv[1])[:top_k]
    ]
    return out, None
