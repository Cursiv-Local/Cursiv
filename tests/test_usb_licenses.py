"""Every Cursiv USB carries the licenses for what's on it."""
import json

import pytest

import usb_maker as um

pytestmark = pytest.mark.usb


def _fake_model(models_dir, name, license_text=None):
    repo, tag = name.split(":")
    blobs = models_dir / "blobs"
    blobs.mkdir(parents=True, exist_ok=True)
    layers = [{"mediaType": "application/vnd.ollama.image.model", "digest": f"sha256:{repo}model"}]
    (blobs / f"sha256-{repo}model").write_text("weights")
    if license_text is not None:
        layers.append({"mediaType": "application/vnd.ollama.image.license", "digest": f"sha256:{repo}lic"})
        (blobs / f"sha256-{repo}lic").write_text(license_text, encoding="utf-8")
    mf = models_dir / "manifests" / "registry.ollama.ai" / "library" / repo / tag
    mf.parent.mkdir(parents=True, exist_ok=True)
    mf.write_text(json.dumps({"layers": layers}), encoding="utf-8")
    return {"name": name, "manifest": mf, "blobs": []}


def test_drive_gets_every_license(tmp_path, monkeypatch):
    models_dir, drive = tmp_path / "models", tmp_path / "drive"
    monkeypatch.setattr(um, "models_dir", lambda: models_dir)
    models = [_fake_model(models_dir, "qwen3:4b-instruct", "Apache License 2.0 text"),
              _fake_model(models_dir, "llama3.1:latest", "LLAMA 3.1 COMMUNITY LICENSE AGREEMENT"),
              _fake_model(models_dir, "mystery:1b")]
    missing = um.write_licenses(drive, models)
    folder = drive / "Licenses"
    assert (folder / "Cursiv-LICENSE.txt").read_text().startswith("MIT License")
    assert "Ollama" in (folder / "Ollama-LICENSE.txt").read_text()
    assert (folder / "model-qwen3_4b-instruct.txt").read_text().startswith("Apache License")
    assert "Built with Llama" in (folder / "model-llama3.1_latest.txt").read_text()
    index = (folder / "README.txt").read_text()
    assert "Built with Llama" in index and "mystery:1b: no license came with this model" in index
    assert missing == ["mystery:1b"]


def test_models_taken_off_the_drive_lose_their_license_file(tmp_path, monkeypatch):
    models_dir, drive = tmp_path / "models", tmp_path / "drive"
    monkeypatch.setattr(um, "models_dir", lambda: models_dir)
    gemma = _fake_model(models_dir, "gemma3:4b", "Gemma Terms of Use")
    um.write_licenses(drive, [gemma])
    assert (drive / "Licenses" / "model-gemma3_4b.txt").exists()
    um.write_licenses(drive, [])
    assert not (drive / "Licenses" / "model-gemma3_4b.txt").exists()
