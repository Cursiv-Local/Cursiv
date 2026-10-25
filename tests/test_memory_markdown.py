"""U100: memory as readable markdown files ("show my memory folder")."""
from cursiv_engine.memory import markdown, semantic


def test_each_memory_becomes_a_file_with_an_index(tmp_path):
    person = semantic.current_person()
    semantic.add_fact("My waders are size 11", person, source="explicit", origin="user_said")
    semantic.add_fact("North Creek site has cattle upstream", person, source="explicit", origin="user_said")
    out = tmp_path / "Cursiv memory"
    done = markdown.export(person, out)
    assert done["memories"] == 2
    index = (out / "MEMORY.md").read_text(encoding="utf-8")
    assert "My waders are size 11" in index and "you said" in index and "Places and sites" in index
    files = [p for p in out.glob("*.md") if p.name != "MEMORY.md"]
    assert len(files) == 2 and all("Memory ID:" in p.read_text(encoding="utf-8") for p in files)
    assert "doesn't change Cursiv's memory" in index


def test_a_fresh_export_replaces_only_its_own_files(tmp_path):
    person = semantic.current_person()
    out = tmp_path / "copy"
    out.mkdir()
    (out / "mine.md").write_text("my own notes", encoding="utf-8")
    semantic.add_fact("Likes early starts", person, source="explicit", origin="user_said")
    markdown.export(person, out)
    semantic.forget("Likes early starts", person) if hasattr(semantic, "forget") else None
    markdown.export(person, out)
    assert (out / "mine.md").read_text(encoding="utf-8") == "my own notes"


def test_on_a_usb_drive_the_folder_is_the_drives(monkeypatch):
    monkeypatch.setenv("CURSIV_PORTABLE", "1")
    assert markdown.portable_folder().name == "memory-files"
    monkeypatch.delenv("CURSIV_PORTABLE")
    assert markdown.portable_folder() is None
