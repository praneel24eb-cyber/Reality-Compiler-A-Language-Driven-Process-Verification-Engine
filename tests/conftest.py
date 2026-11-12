"""Never load the developer's real OAuth registration during automated tests."""

import pytest


@pytest.fixture(autouse=True)
def isolated_registration(tmp_path, monkeypatch):
    monkeypatch.setenv("CHATGPT_REGISTRATION_PATH", str(tmp_path / "isolated-registration.json"))
