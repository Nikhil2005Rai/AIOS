import os
import pytest

from app.core.tracing import configure_langsmith


def test_configure_langsmith_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "langchain_tracing_v2", True)
    monkeypatch.setattr(settings, "langchain_api_key", "test-api-key")
    monkeypatch.setattr(settings, "langchain_project", "test-project")

    # Clear any existing env vars that might interfere
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_PROJECT", raising=False)

    configure_langsmith()

    assert os.environ.get("LANGCHAIN_TRACING_V2") == "true"
    assert os.environ.get("LANGCHAIN_API_KEY") == "test-api-key"
    assert os.environ.get("LANGCHAIN_PROJECT") == "test-project"


def test_configure_langsmith_disabled_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "langchain_tracing_v2", True)
    monkeypatch.setattr(settings, "langchain_api_key", "")

    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)

    configure_langsmith()

    assert os.environ.get("LANGCHAIN_TRACING_V2") == "false"


def test_configure_langsmith_disabled_by_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "langchain_tracing_v2", False)
    monkeypatch.setattr(settings, "langchain_api_key", "test-api-key")

    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)

    configure_langsmith()

    assert os.environ.get("LANGCHAIN_TRACING_V2") == "false"
