"""Beleg-Capture — Gradio-UI.

Foto → VLM-Vorschlag → menschliche Korrektur → speichern (Vorschlag + Korrektur)
→ optional CSV-Export für prefilter-api.
"""

from __future__ import annotations

import gradio as gr

import config
from extractor import ExtractionError, extract_fields
from store import CaptureStore

store = CaptureStore()


def on_extract(image, mandant):
    """Liest die Felder aus dem Bild aus und füllt die Textfelder vor."""
    empties = [gr.update() for _ in config.FIELDS]
    if not image:
        return empties + [None, "⚠️ Bitte zuerst ein Foto hochladen."]
    try:
        proposal = extract_fields(image)
    except ExtractionError as exc:
        return empties + [None, f"❌ {exc}"]
    field_updates = [proposal[f] for f in config.FIELDS]
    return field_updates + [
        proposal,
        f"✅ Vorschlag von `{config.VLM_MODEL}` — bitte prüfen und ggf. korrigieren.",
    ]


def on_save(image, mandant, proposal, *field_values):
    if not proposal:
        return "⚠️ Erst „Auslesen“ ausführen."
    if not image:
        return "⚠️ Kein Bild vorhanden."
    human_final = {f: (v or "").strip() for f, v in zip(config.FIELDS, field_values)}
    rec = store.save_capture(
        mandant or "unknown", image, proposal, human_final, config.VLM_MODEL
    )
    note = "mit Korrektur" if rec.edited else "unverändert übernommen"
    n = store.count(mandant or "unknown")
    return f"💾 Gespeichert ({note}, id `{rec.capture_id[:8]}`). Mandant hat jetzt {n} Captures."


def on_export(mandant):
    try:
        path = store.export_csv(mandant or "unknown")
    except ValueError as exc:
        return None, f"⚠️ {exc}"
    return path, f"📤 CSV exportiert: `{path}` — direkt in prefilter-api einlesbar."


with gr.Blocks(title="Beleg-Capture") as demo:
    gr.Markdown(
        "# 📷 Beleg-Capture (Prototyp)\n"
        "Foto eines Belegs hochladen → VLM schlägt Buchungsfelder vor → korrigieren → speichern. "
        "Jede Aufnahme speichert Vorschlag **und** Korrektur (Finetuning-Paar)."
    )

    with gr.Row():
        with gr.Column(scale=1):
            mandant = gr.Textbox(label="Mandant-ID", value="demo")
            image = gr.Image(label="Beleg-Foto", sources=["upload", "webcam"], type="filepath")
            extract_btn = gr.Button("🔍 Auslesen", variant="primary")
        with gr.Column(scale=1):
            field_boxes = [
                gr.Textbox(label=config.FIELD_LABELS[f]) for f in config.FIELDS
            ]
            save_btn = gr.Button("💾 Speichern", variant="primary")
            with gr.Row():
                export_btn = gr.Button("📤 CSV-Export")
            export_file = gr.File(label="Export", interactive=False)

    status = gr.Markdown("")
    proposal_state = gr.State(None)

    extract_btn.click(
        on_extract,
        inputs=[image, mandant],
        outputs=field_boxes + [proposal_state, status],
    )
    save_btn.click(
        on_save,
        inputs=[image, mandant, proposal_state, *field_boxes],
        outputs=[status],
    )
    export_btn.click(
        on_export,
        inputs=[mandant],
        outputs=[export_file, status],
    )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7865)
