"""Capture-Store — JSONL-Persistenz, mandant-isoliert.

Muster bewusst gespiegelt von prefilter-api `src/feedback.py`
(JSON-Lines, append-only, Pfad-Traversal-Sanitize) — keine neue
Persistenz-Erfindung. Jeder Record hält VLM-Vorschlag UND menschliche
Korrektur → ist gleichzeitig Ergebnis und Finetuning-Trainingspaar.
"""

from __future__ import annotations

import csv
import json
import shutil
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import config


@dataclass
class CaptureRecord:
    mandant_id: str
    image_ref: str
    vlm_proposal: dict
    human_final: dict
    model: str
    capture_id: str = ""
    edited: bool = False
    ts: str = ""

    def __post_init__(self) -> None:
        if not self.capture_id:
            self.capture_id = uuid.uuid4().hex
        if not self.ts:
            self.ts = datetime.now().isoformat()
        self.edited = self.vlm_proposal != self.human_final


class CaptureStore:
    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.dir = Path(data_dir) if data_dir else config.DATA_DIR
        self.captures_dir = self.dir / "captures"
        self.captures_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe(mandant_id: str) -> str:
        safe = "".join(c for c in (mandant_id or "") if c.isalnum() or c in "-_")
        return safe or "unknown"

    def _jsonl_path(self, mandant_id: str) -> Path:
        return self.dir / f"{self._safe(mandant_id)}_captures.jsonl"

    def _image_dir(self, mandant_id: str) -> Path:
        d = self.captures_dir / self._safe(mandant_id)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_capture(
        self,
        mandant_id: str,
        image_src: str,
        vlm_proposal: dict,
        human_final: dict,
        model: str,
    ) -> CaptureRecord:
        """Kopiert das Bild in den Mandant-Ordner und schreibt den Record."""
        rec = CaptureRecord(
            mandant_id=mandant_id,
            image_ref="",
            vlm_proposal=vlm_proposal,
            human_final=human_final,
            model=model,
        )
        ext = Path(image_src).suffix or ".png"
        dest = self._image_dir(mandant_id) / f"{rec.capture_id}{ext}"
        shutil.copyfile(image_src, dest)
        rec.image_ref = str(dest)

        with open(self._jsonl_path(mandant_id), "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
        return rec

    def load_all(self, mandant_id: str) -> list[CaptureRecord]:
        path = self._jsonl_path(mandant_id)
        if not path.exists():
            return []
        out: list[CaptureRecord] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(CaptureRecord(**json.loads(line)))
        return out

    def count(self, mandant_id: str) -> int:
        return len(self.load_all(mandant_id))

    def export_csv(self, mandant_id: str, out_path: str | Path | None = None) -> str:
        """Bestätigte Captures als CSV mit prefilter-api-Spaltennamen."""
        records = self.load_all(mandant_id)
        if not records:
            raise ValueError(f"Keine Captures für Mandant '{mandant_id}'.")

        out = Path(out_path) if out_path else self.dir / f"{self._safe(mandant_id)}_export.csv"
        columns = config.FIELDS + ["mandant"]
        with open(out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            for rec in records:
                row = {k: rec.human_final.get(k, "") for k in config.FIELDS}
                row["mandant"] = rec.mandant_id
                writer.writerow(row)
        return str(out)
