from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.maintenance import copy_database, inspect_database


def test_backup_restore_and_overwrite_guard(tmp_path, monkeypatch):
    source = tmp_path / "original.db"
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(source))
    command.upgrade(Config("alembic.ini"), "head")
    backup = tmp_path / "backup.db"
    restored = tmp_path / "restored.db"
    counts = copy_database(source, backup)
    assert copy_database(backup, restored) == counts == inspect_database(source)
    before = source.read_bytes()
    with pytest.raises(ValueError):
        copy_database(backup, source)
    assert source.read_bytes() == before
    with pytest.raises(ValueError):
        copy_database(Path("not-a-database"), restored)
