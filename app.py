"""Beleg-Capture — Gradio-UI.

Foto → VLM-Vorschlag → menschliche Korrektur → speichern (Vorschlag + Korrektur)
→ optional CSV-Export für prefilter-api.
"""

from __future__ import annotations

import gradio as gr

import config
from extractor import ExtractionError, extract_fields
from store import CaptureStore
from suggest import suggest_konto

store = CaptureStore()

_SACHKONTO_IDX = config.FIELDS.index("sachkonto")


def on_extract(image, mandant):
    """Liest die Felder aus dem Bild aus, schlägt das Sachkonto vor und füllt vor."""
    empties = [gr.update() for _ in config.FIELDS]
    dd_empty = gr.update(choices=[], value=None)
    if not image:
        return empties + [dd_empty, None, "⚠️ Bitte zuerst ein Foto hochladen."]
    try:
        proposal = extract_fields(image)
    except ExtractionError as exc:
        return empties + [dd_empty, None, f"❌ {exc}"]

    # Sachkonto kennt das VLM nicht — aus dem Präzedenz-Index (prefilter /api/suggest)
    # ziehen: Kreditor-Häufigkeit + Buchungstext-kNN.
    suggestions, sug_note_raw = suggest_konto(
        proposal.get("kreditor", ""), proposal.get("buchungstext", "")
    )
    if suggestions:
        proposal["sachkonto"] = suggestions[0].konto
        choices = [f"{s.konto} — {s.bezeichnung} ({s.reason})" for s in suggestions]
        dd_update = gr.update(choices=choices, value=choices[0])
        sug_note = f" · 🧭 Sachkonto-Vorschlag **{suggestions[0].konto}** ({len(suggestions)} Kandidaten)"
        if sug_note_raw:  # Degradations-Hinweis (z.B. Text-kNN aus)
            sug_note += f" ⚠️ {sug_note_raw}"
    else:
        dd_update = gr.update(choices=[], value=None)
        sug_note = f" · 🧭 kein Sachkonto-Vorschlag: {sug_note_raw}"

    field_updates = [proposal[f] for f in config.FIELDS]
    return field_updates + [
        dd_update,
        proposal,
        f"✅ Vorschlag von `{config.VLM_MODEL}` — bitte prüfen.{sug_note}",
    ]


def on_pick_konto(choice):
    """Übernimmt das gewählte Vorschlags-Konto ins Sachkonto-Feld."""
    if not choice:
        return gr.update()
    return choice.split(" — ", 1)[0].strip()


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
            konto_dropdown = gr.Dropdown(
                label="🧭 Sachkonto-Kandidaten (aus Altdaten-Präzedenz)",
                choices=[], interactive=True,
                info="Auswahl füllt das Feld „Sachkonto (konto_soll)“.",
            )
            save_btn = gr.Button("💾 Speichern", variant="primary")
            with gr.Row():
                export_btn = gr.Button("📤 CSV-Export")
            export_file = gr.File(label="Export", interactive=False)

    status = gr.Markdown("")
    proposal_state = gr.State(None)

    extract_btn.click(
        on_extract,
        inputs=[image, mandant],
        outputs=field_boxes + [konto_dropdown, proposal_state, status],
    )
    konto_dropdown.select(
        on_pick_konto,
        inputs=[konto_dropdown],
        outputs=[field_boxes[_SACHKONTO_IDX]],
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
