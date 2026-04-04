import os

import pytest


@pytest.fixture(autouse=True)
def _set_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject required env vars so EnvSettings() won't fail in CI."""
    monkeypatch.setenv("TIINGO_API_KEY", "test-key")
