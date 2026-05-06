import json
import pytest

import dorkeye
from dorkeye import SessionCheckpoint


@pytest.fixture
def cp(tmp_path, monkeypatch):
    monkeypatch.setattr(SessionCheckpoint, "CHECKPOINT_DIR", tmp_path)
    return SessionCheckpoint("sess_test_abc123")


def test_load_returns_none_when_no_file(cp):
    assert cp.load() is None


def test_checkpoint_file_uses_json_extension(cp):
    assert cp.path.suffix == ".json", "checkpoint must be stored as JSON, not pickle"


def test_save_creates_file(cp):
    cp.save(["dork1"], [{"url": "http://example.com"}], {"total": 1})
    assert cp.path.exists()


def test_save_writes_valid_json(cp):
    cp.save(["dork1", "dork2"], [], {})
    data = json.loads(cp.path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_save_load_roundtrip(cp):
    dorks = ["site:example.com", "inurl:admin"]
    results = [{"url": "http://example.com", "title": "Test", "dork": "site:example.com"}]
    stats = {"total_found": 7, "duplicates": 2}

    cp.save(dorks, results, stats)
    loaded = cp.load()

    assert loaded is not None
    assert loaded["completed_dorks"] == dorks
    assert loaded["results"] == results
    assert loaded["stats"] == stats
    assert "saved_at" in loaded


def test_load_handles_corrupted_json(cp):
    cp.path.write_text("}{not valid json{{", encoding="utf-8")
    assert cp.load() is None


def test_delete_removes_file(cp):
    cp.save([], [], {})
    assert cp.path.exists()
    cp.delete()
    assert not cp.path.exists()


def test_delete_is_safe_when_no_file(cp):
    cp.delete()  # must not raise even if file never existed


def test_save_persists_unicode(cp):
    dorks = ["site:пример.рф", "inurl:ñoño"]
    cp.save(dorks, [], {})
    loaded = cp.load()
    assert loaded["completed_dorks"] == dorks
