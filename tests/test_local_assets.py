import hashlib
from pathlib import Path
import pytest
from tools.restore_local_assets import confined, restore_one


def test_restore_checks_hash_and_preserves_existing_file(tmp_path):
    source, target = tmp_path / "source", tmp_path / "target"
    source.mkdir()
    (source / "model.bin").write_bytes(b"known model")
    entry = {"path": "model.bin", "sha256": hashlib.sha256(b"known model").hexdigest()}
    assert restore_one(target, source, entry)
    assert not restore_one(target, source, entry)
    (target / "model.bin").write_bytes(b"local changes")
    with pytest.raises(ValueError, match="preserved"):
        restore_one(target, source, entry)
    assert (target / "model.bin").read_bytes() == b"local changes"


def test_bad_source_is_not_copied(tmp_path):
    source, target = tmp_path / "source", tmp_path / "target"
    source.mkdir()
    (source / "model.bin").write_bytes(b"different model")
    with pytest.raises(ValueError, match="Source checksum"):
        restore_one(target, source, {"path": "model.bin", "sha256": "0" * 64})
    assert not (target / "model.bin").exists()


@pytest.mark.parametrize("name", ["../escape", "/absolute", "C:/absolute", "model.bin:stream", "nested\\escape"])
def test_manifest_paths_cannot_escape_the_named_directory(tmp_path, name):
    with pytest.raises(ValueError):
        confined(tmp_path, name)
