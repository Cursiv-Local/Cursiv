"""U103: what the phone link sends to cursiv.us (launcher/phone_sync.py, launcher/phone_link.py).

The memory summary is the only memory that leaves the computer. A memory with a key or password stays
here; turning sharing off clears the summary; a failed upload is reported, not called "shared"; and a
photo from the phone space is shown only if it really is an image."""
import json

import pytest

SECRET = "sk-ant-api03-" + "A" * 40


@pytest.fixture
def sync(tmp_path, monkeypatch):
    import phone_link
    import phone_sync
    from cursiv_engine.memory import semantic
    monkeypatch.setattr(phone_link, "SPACE_FILE", tmp_path / "space.json")
    (tmp_path / "space.json").write_text(json.dumps({"token": "t0k", "person": "sam"}), encoding="utf-8")
    facts = [{"text": "Sam studies Willow Creek"}, {"text": f"My Anthropic key is {SECRET}"},
             {"text": "password: hunter2hunter2"}, {"text": "Sam prefers metric units"}]
    monkeypatch.setattr(semantic, "list_facts", lambda person=None, **k: facts)
    calls = []

    def api(path, payload=None, token="", timeout=90):
        calls.append((path, payload))
        if getattr(api, "fail", False) and path == "/api/space/memory":
            raise RuntimeError("the server answered 503")
        return {"messages": []} if path.startswith("/api/space/messages") else {}
    monkeypatch.setattr(phone_link, "api", api)
    phone_sync.calls, phone_sync.fake_api = calls, api
    return phone_sync


def _uploaded(sync):
    return [p for path, p in sync.calls if path == "/api/space/memory"]


def test_the_summary_leaves_out_memories_with_keys_or_passwords(sync):
    assert "summary shared" in sync.sync_once()
    (sent,) = _uploaded(sync)
    assert "Willow Creek" in sent["digest"] and "metric" in sent["digest"]
    assert SECRET not in sent["digest"] and "hunter2" not in sent["digest"] and sent["person"] == "sam"


def test_turning_sharing_off_clears_the_summary(sync, monkeypatch):
    sync.sync_once()
    st = json.loads(sync.pl.SPACE_FILE.read_text(encoding="utf-8"))
    st["share_memory"] = False
    st.pop("digest_hash")
    sync._save_state(st)
    assert "not shared" in sync.sync_once()
    assert _uploaded(sync)[-1]["digest"] == ""


def test_a_failed_upload_is_reported_and_tried_again(sync):
    sync.fake_api.fail = True
    out = sync.sync_once()
    assert "not updated" in out and "503" in out and "shared" not in out.replace("not updated", "")
    assert "digest_hash" not in json.loads(sync.pl.SPACE_FILE.read_text(encoding="utf-8"))
    sync.fake_api.fail = False
    assert "summary shared" in sync.sync_once() and len(_uploaded(sync)) == 2


def test_an_unchanged_summary_is_not_uploaded_again(sync):
    sync.sync_once()
    sync.sync_once()
    assert len(_uploaded(sync)) == 1


def test_only_real_images_from_the_phone_space_are_shown():
    import phone_link
    assert phone_link._image_url("image/jpeg", "/9j/4AAQSkZJRg==") == "data:image/jpeg;base64,/9j/4AAQSkZJRg=="
    assert phone_link._image_url('image/png" onerror="x', "AAAA") == ""
    assert phone_link._image_url("text/html", "PGI+aGk8L2I+") == ""
    assert phone_link._image_url("image/png", 'AAAA" onload="x') == ""
