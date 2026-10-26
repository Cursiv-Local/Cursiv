"""Baseline probes only; no production changes and no live-model score claims."""
import os
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from cursiv_engine.memory import markdown, semantic, session_notes, suggestions


def test_repeated_conversation_switches_keep_notes_separate_and_facts_unique(tmp_path):
    semantic.set_person("baseline")
    fact = "Baseline prefers metric units for field records"
    semantic.add_fact(fact, source="manual", origin="user_said")
    markers = [f"watershed{chr(97 + n)}marker" for n in range(24)]
    for cycle in range(6):
        for marker in markers:
            history = [{"role": "user", "content": f"Survey {marker}. Next sample {marker}."}]
            summary = f"Goal: Survey {marker}\nNext: Sample {marker}"
            session_notes.update(marker, marker, history, lambda messages: summary, force=True)
            session_notes.set_active(marker)
            block = session_notes.prompt_block()
            assert marker in block
            assert all(other not in block for other in markers if other != marker)
            # Repetition, including a stronger requested origin, must not upgrade a memory.
            assert semantic.add_fact(fact, source="verified", origin="verified") is None
            suggestions.add("baseline", ["Baseline uses waterproof notebooks"])
            assert len(suggestions.pending("baseline")) == 1
            assert len(semantic.list_facts("baseline")) == 1
        folder = tmp_path / "readable-copy"
        markdown.export("baseline", folder)
        assert len(list(folder.glob("*.md"))) == 2
        assert semantic.list_facts("baseline")[0]["origin"] == "user_said"
    session_notes.set_active("")
    assert session_notes.prompt_block() == ""
    assert len(list(session_notes.DIR.glob("*.md"))) == 24
    assert "Saved to memory" in suggestions.confirm("baseline", suggestions.pending("baseline")[0]["id"])
    assert len(semantic.list_facts("baseline")) == 2
    assert suggestions.pending("baseline") == []


def test_memory_dialog_renders_origins_searches_and_deduplicates():
    from memory_dialog import MemoryDialog
    from PyQt6.QtGui import QFont, QFontDatabase
    app = QApplication.instance() or QApplication([])
    # Match the existing saved-notes Qt fixture: offscreen Qt needs a font loaded explicitly.
    font = Path(os.environ.get("SystemRoot", "C:/Windows")) / "Fonts" / "segoeui.ttf"
    if font.exists():
        QFontDatabase.addApplicationFont(str(font))
        app.setFont(QFont("Segoe UI", 10))
    semantic.set_person("baseline")
    semantic.add_fact("Baseline prefers metric units", source="manual", origin="user_said")
    semantic.add_fact("The reference thermometer was calibrated on Monday", source="verified", origin="verified")
    semantic.add_fact("The shared field kit is in the blue cupboard", person=semantic.SHARED,
                      source="manual", origin="user_said")
    dialog = MemoryDialog()
    try:
        dialog.show()
        app.processEvents()
        text = "\n".join(dialog._list.item(i).text() for i in range(dialog._list.count()))
        assert dialog._list.count() == 3
        assert "you said" in text and "verified" in text and "family" in text
        for fact in semantic.list_facts("baseline"):
            assert fact["date"] in text
        image = os.environ.get("CURSIV_U106_QT_IMAGE")
        if image:
            assert dialog.grab().save(str(Path(image)))
        dialog._search.setText("thermometer")
        app.processEvents()
        assert dialog._list.count() == 1
        dialog._search.clear()
        dialog._new.setText("Baseline prefers metric units")
        dialog._add()
        assert dialog._status.text() == "Already remembered."
        assert dialog._list.count() == 3
    finally:
        dialog.close()
