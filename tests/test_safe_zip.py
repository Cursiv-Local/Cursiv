"""U105 (outside review): downloaded zips are unpacked without trusting them (cursiv_engine/core/safe_zip.py),
and the Vosk voice model is checked against its pinned SHA-256 before it's unpacked."""
import hashlib
import stat
import zipfile
from pathlib import Path

import pytest

from cursiv_engine.core import safe_zip

LIMITS = dict(max_files=50, max_bytes=1 << 20, max_file_bytes=512 << 10)


def _zip(path: Path, files: dict, links=()) -> Path:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
        for name in links:
            info = zipfile.ZipInfo(name)
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(info, "/etc/passwd")
    return path


def test_a_good_zip_is_unpacked_completely(tmp_path):
    z = _zip(tmp_path / "ok.zip", {"model/conf/a.txt": "hello", "model/b.bin": b"\x00" * 1000, "model/empty/": ""})
    n = safe_zip.extract(z, tmp_path / "out", **LIMITS)
    assert n == 1005 and (tmp_path / "out" / "model" / "conf" / "a.txt").read_text() == "hello"
    assert (tmp_path / "out" / "model" / "empty").is_dir()


@pytest.mark.parametrize("name", ["../evil.txt", "model/../../evil.txt", "/etc/evil", "C:/evil.txt",
                                  "model\\..\\evil.txt"])
def test_names_that_leave_the_folder_are_refused_and_nothing_is_left(tmp_path, name):
    z = _zip(tmp_path / "bad.zip", {"model/ok.txt": "fine", name: "x"})
    with pytest.raises(safe_zip.UnsafeZip):
        safe_zip.extract(z, tmp_path / "out", **LIMITS)
    assert not (tmp_path / "out").exists() and not (tmp_path / "evil.txt").exists()
    assert [p.name for p in tmp_path.iterdir()] == ["bad.zip"]           # no half-unpacked temporary folder


def test_links_are_refused(tmp_path):
    z = _zip(tmp_path / "link.zip", {"model/ok.txt": "fine"}, links=["model/passwd"])
    with pytest.raises(safe_zip.UnsafeZip, match="link"):
        safe_zip.extract(z, tmp_path / "out", **LIMITS)
    assert not (tmp_path / "out").exists()


def test_too_many_files_or_too_much_data_is_refused(tmp_path):
    many = _zip(tmp_path / "many.zip", {f"f{i}.txt": "x" for i in range(60)})
    with pytest.raises(safe_zip.UnsafeZip, match="entries"):
        safe_zip.extract(many, tmp_path / "out1", **LIMITS)
    big = _zip(tmp_path / "big.zip", {"bomb.bin": b"\x00" * (2 << 20)})    # 2 MB of zeros compresses to ~2 KB
    assert big.stat().st_size < 50_000
    with pytest.raises(safe_zip.UnsafeZip, match="more than"):
        safe_zip.extract(big, tmp_path / "out2", **LIMITS)
    assert not (tmp_path / "out1").exists() and not (tmp_path / "out2").exists()


def test_declared_sizes_that_lie_are_not_trusted(tmp_path):
    z = _zip(tmp_path / "liar.zip", {"bomb.bin": b"\x00" * (2 << 20)})
    data = bytearray(z.read_bytes())
    # rewrite the central directory's uncompressed size for the entry to 10 bytes
    cd = data.rfind(b"PK\x01\x02")
    data[cd + 24:cd + 28] = (10).to_bytes(4, "little")
    z.write_bytes(bytes(data))
    with pytest.raises(safe_zip.UnsafeZip):
        safe_zip.extract(z, tmp_path / "out", **LIMITS)
    assert not (tmp_path / "out").exists()


def test_an_existing_folder_is_never_overwritten(tmp_path):
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "mine.txt").write_text("keep")
    z = _zip(tmp_path / "ok.zip", {"mine.txt": "replaced?"})
    with pytest.raises(safe_zip.UnsafeZip, match="already exists"):
        safe_zip.extract(z, tmp_path / "out", **LIMITS)
    assert (tmp_path / "out" / "mine.txt").read_text() == "keep"


def test_not_a_zip_is_refused(tmp_path):
    f = tmp_path / "x.zip"
    f.write_bytes(b"<html>not a zip</html>")
    with pytest.raises(safe_zip.UnsafeZip, match="couldn't be read"):
        safe_zip.extract(f, tmp_path / "out", **LIMITS)


# ── the Vosk model ──────────────────────────────────────────────────────────

@pytest.fixture
def voice(tmp_path, monkeypatch):
    from cursiv_engine.agents import voice_agent as va
    monkeypatch.setattr(va, "_VOICE_DIR", tmp_path / "voice")
    monkeypatch.setattr(va, "_VOSK_MODEL_DIR", tmp_path / "voice" / va._VOSK_MODEL_NAME)
    (tmp_path / "voice").mkdir()
    return va


def test_a_vosk_download_that_doesnt_match_its_checksum_is_refused_and_deleted(voice, tmp_path):
    z = _zip(tmp_path / "voice" / "vosk.zip", {f"{voice._VOSK_MODEL_NAME}/am/final.mdl": "tampered"})
    with pytest.raises(Exception, match="checksum"):
        voice._install_vosk_zip(z)
    assert not z.exists() and not voice._VOSK_MODEL_DIR.exists()


def test_a_matching_vosk_download_is_installed(voice, tmp_path, monkeypatch):
    z = _zip(tmp_path / "voice" / "vosk.zip", {f"{voice._VOSK_MODEL_NAME}/am/final.mdl": "model bytes"})
    monkeypatch.setattr(voice, "_VOSK_SHA256", hashlib.sha256(z.read_bytes()).hexdigest())
    assert voice._install_vosk_zip(z) == voice._VOSK_MODEL_DIR
    assert (voice._VOSK_MODEL_DIR / "am" / "final.mdl").read_text() == "model bytes"
    assert not z.exists() and [p.name for p in (tmp_path / "voice").iterdir()] == [voice._VOSK_MODEL_NAME]


def test_the_pinned_vosk_checksum_is_a_real_sha256():
    from cursiv_engine.agents import voice_agent as va
    assert len(va._VOSK_SHA256) == 64 and int(va._VOSK_SHA256, 16)


def test_the_real_vosk_download_matches_the_pin_when_present():
    # The file downloaded while measuring the pin (2026-10-26); skipped where it isn't kept.
    import os
    from cursiv_engine.agents import voice_agent as va
    f = os.environ.get("CURSIV_VOSK_ZIP")
    if not f or not Path(f).exists():
        pytest.skip("set CURSIV_VOSK_ZIP to a downloaded vosk-model-small-en-us-0.15.zip to check the pin")
    assert hashlib.sha256(Path(f).read_bytes()).hexdigest() == va._VOSK_SHA256
