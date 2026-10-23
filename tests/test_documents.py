"""The team's documents (research roadmap R3): imported offline, quoted by page,
fingerprinted, with a documents-only mode and a check on cited pages."""
import pytest

from cursiv_engine.core import documents as docs
from test_netgate import _local_model, fresh, outbound  # noqa: F401  (fixtures)

PAGE_1 = ("Water Sampling Protocol WS-3, revision 2.\n\nRinse each sample bottle three times with stream water "
          "before filling.\n\nLabel every bottle with site code, date and time before sampling.")
PAGE_2 = ("Preservation.\n\nKeep water samples on ice at 4 degrees C and deliver them to the lab within 24 hours.\n\n"
          "Nitrate samples are acidified with 2 mL of sulfuric acid per liter.")


@pytest.fixture
def library(tmp_path, monkeypatch):
    monkeypatch.setattr(docs, "lib_dir", lambda: tmp_path / "documents")
    docs._passages.cache = None
    yield docs
    docs._passages.cache = None


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _pdf(path):
    """A real two-page PDF with Helvetica text, written by hand (any PDF reader extracts it)."""
    pages = []
    for text in (PAGE_1, PAGE_2):
        ops = ["BT", "/F1 11 Tf", "14 TL", "72 740 Td"]
        for para in text.split("\n\n"):
            ops.append(f"({_esc(para)}) Tj T* T*")
        ops.append("ET")
        pages.append("\n".join(ops).encode("latin-1"))
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(len(pages)))
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode(),
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    for i, content in enumerate(pages):
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {5 + 2 * i} 0 R "
                    f"/Resources << /Font << /F1 3 0 R >> >> >>".encode())
        objs.append(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream")
    out = b"%PDF-1.4\n"
    offsets = []
    for n, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{n} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(out)
    return path


def test_import_reads_pages_and_fingerprints(library, tmp_path):
    d = library.add(_pdf(tmp_path / "WS-3 protocol.pdf"))
    assert d["pages"] == 2 and len(d["fingerprint"]) == 64
    assert library.add(tmp_path / "WS-3 protocol.pdf")["id"] == d["id"]           # same file: nothing new
    assert len(library.library()) == 1


def test_search_finds_the_right_page(library, tmp_path):
    library.add(_pdf(tmp_path / "WS-3 protocol.pdf"))
    found = library.search("How long can water samples stay on ice before the lab?")
    assert found and found[0].page == 2 and "24 hours" in found[0].text
    rinse = library.search("how many times do I rinse the sample bottle")
    assert rinse and rinse[0].page == 1
    assert library.search("what's a good recipe for cornbread") == []


def test_cited_pages_must_be_among_those_supplied(library, tmp_path):
    library.add(_pdf(tmp_path / "WS-3 protocol.pdf"))
    found = library.search("How long can water samples stay on ice?")
    assert library.cited_pages_problems("Within 24 hours (WS-3 protocol.pdf, p. 2).", found) == []
    assert library.cited_pages_problems("Within 24 hours (WS-3 protocol.pdf, p. 7).", found)


def test_text_files_too(library, tmp_path):
    f = tmp_path / "sop.md"
    f.write_text("Calibrate the pH meter with pH 4 and pH 7 buffers every morning.", encoding="utf-8")
    library.add(f)
    assert library.search("when do I calibrate the pH meter")[0].name == "sop.md"


def test_chat_quotes_the_page_and_documents_only_refuses_the_rest(library, tmp_path, fresh, monkeypatch):
    from cursiv_engine.chat import keys
    from cursiv_engine.ui import chat_app as ca
    library.add(_pdf(tmp_path / "WS-3 protocol.pdf"))
    _local_model(monkeypatch)
    seen = {}

    def fake(messages, **kw):
        seen.setdefault("system", messages[0]["content"])
        return iter(["Deliver them within 24 hours (WS-3 protocol.pdf, p. 2)."])
    monkeypatch.setattr(ca, "_call_ollama", fake)
    out = "".join(ca.chat("How long can water samples stay on ice before they go to the lab?", [], "", None))
    assert "From your documents: WS-3 protocol.pdf p. 2" in out and "[WS-3 protocol.pdf, p. 2]" in seen["system"]

    keys.store_key("documents_only", "on")
    monkeypatch.setattr(ca, "_call_ollama", lambda *a, **k: pytest.fail("the model was asked"))
    out = "".join(ca.chat("What's the capital of Mongolia?", [], "", None))
    assert "isn't in your documents" in out


def test_documents_only_never_refuses_an_emergency(library, tmp_path, fresh, monkeypatch):
    from cursiv_engine.chat import keys
    from cursiv_engine.ui import chat_app as ca
    library.add(_pdf(tmp_path / "WS-3 protocol.pdf"))
    keys.store_key("documents_only", "on")
    _local_model(monkeypatch)
    monkeypatch.setattr(ca, "_call_ollama", lambda *a, **k: iter(["Call 911 now and press on the wound."]))
    out = "".join(ca.chat("my coworker cut his leg and it's bleeding badly", [], "", None))
    assert "isn't in your documents" not in out and "911" in out


def test_commands(library, tmp_path):
    f = tmp_path / "permit.txt"
    f.write_text("Collection permit 22-114 allows 30 specimens per site.", encoding="utf-8")
    assert "Imported permit.txt" in library.command(f"add document {f}")
    assert "permit.txt" in library.command("documents")
    assert "Not imported" in library.command(f"add document {tmp_path / 'missing.pdf'}")


def test_with_the_ai_engine_down_cursiv_gives_what_it_has(library, tmp_path, fresh, monkeypatch):
    from cursiv_engine.ui import chat_app as ca
    library.add(_pdf(tmp_path / "WS-3 protocol.pdf"))
    monkeypatch.setattr(ca, "_local_model_ready", lambda: False)
    monkeypatch.setattr(ca, "_call_ollama", lambda *a, **k: pytest.fail("the model was asked"))
    out = "".join(ca.chat("How long can water samples stay on ice before they go to the lab?", [], "", None))
    assert "isn't answering" in out and "WS-3 protocol.pdf p. 2" in out and "24 hours" in out
    assert "Written by Cursiv, no AI model" in out and "Answered by" not in out
    out = "".join(ca.chat("Convert 12 C to F", [], "", None))
    assert "53.6 F" in out and "worked out by Cursiv's code" in out
    out = "".join(ca.chat("What is a riffle in a stream?", [], "", None))
    assert "no answer without the model" in out and "Sources: Cursiv itself (no AI model)" in out


def test_documents_import_and_answer_with_offline_mode_on_and_no_connection(library, tmp_path, fresh, outbound,
                                                                            monkeypatch):
    """Offline on, the AI engine down: a team document is imported, found and quoted by page,
    and nothing tries to leave this computer (outbound records any attempt)."""
    from cursiv_engine.core import netgate
    from cursiv_engine.ui import chat_app as ca
    netgate.set_offline(True)
    monkeypatch.setattr(ca, "_local_model_ready", lambda: False)
    library.add(_pdf(tmp_path / "WS-3 protocol.pdf"))
    hits = library.search("samples on ice lab hours")
    assert hits and "24 hours" in str(hits[0])
    out = "".join(ca.chat("How long can water samples stay on ice before they go to the lab?", [], "", None))
    assert "WS-3 protocol.pdf p. 2" in out and "24 hours" in out
    assert outbound == []
