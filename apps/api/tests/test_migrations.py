import pytest
from unittest.mock import MagicMock, ANY

from app.migrations import _stamp_existing_phase_1_schema


class FakeInspector:
    def __init__(self, tables, columns_dict=None) -> None:
        self._tables = tables
        self._columns_dict = columns_dict or {}

    def get_table_names(self):
        return list(self._tables)

    def get_columns(self, table_name):
        cols = self._columns_dict.get(table_name, [])
        return [{"name": name} for name in cols]


def test_stamp_existing_phase_1_schema_stamps_initial(monkeypatch) -> None:
    mock_stamp = MagicMock()
    monkeypatch.setattr("app.migrations.command.stamp", mock_stamp)

    fake_inspector = FakeInspector(
        tables={"users", "conversations", "messages"}
    )
    monkeypatch.setattr("app.migrations.inspect", lambda conn: fake_inspector)
    monkeypatch.setattr("app.migrations.create_engine", MagicMock())

    _stamp_existing_phase_1_schema(MagicMock())
    mock_stamp.assert_called_with(ANY, "0001_initial")


def test_stamp_existing_phase_1_schema_stamps_tool_calls(monkeypatch) -> None:
    mock_stamp = MagicMock()
    monkeypatch.setattr("app.migrations.command.stamp", mock_stamp)

    fake_inspector = FakeInspector(
        tables={"users", "conversations", "messages", "tool_calls"},
        columns_dict={"tool_calls": ["id", "conversation_id"]}
    )
    monkeypatch.setattr("app.migrations.inspect", lambda conn: fake_inspector)
    monkeypatch.setattr("app.migrations.create_engine", MagicMock())

    _stamp_existing_phase_1_schema(MagicMock())
    mock_stamp.assert_called_with(ANY, "0002_tool_calls")


def test_stamp_existing_phase_1_schema_stamps_agent_name(monkeypatch) -> None:
    mock_stamp = MagicMock()
    monkeypatch.setattr("app.migrations.command.stamp", mock_stamp)

    fake_inspector = FakeInspector(
        tables={"users", "conversations", "messages", "tool_calls"},
        columns_dict={"tool_calls": ["id", "conversation_id", "agent_name"]}
    )
    monkeypatch.setattr("app.migrations.inspect", lambda conn: fake_inspector)
    monkeypatch.setattr("app.migrations.create_engine", MagicMock())

    _stamp_existing_phase_1_schema(MagicMock())
    mock_stamp.assert_called_with(ANY, "0003_tool_calls_agent_name")


def test_stamp_existing_phase_1_schema_stamps_user_api_keys(monkeypatch) -> None:
    mock_stamp = MagicMock()
    monkeypatch.setattr("app.migrations.command.stamp", mock_stamp)

    fake_inspector = FakeInspector(
        tables={"users", "conversations", "messages", "tool_calls", "user_api_keys"},
        columns_dict={
            "tool_calls": ["id", "conversation_id", "agent_name"],
            "users": ["id", "email"]
        }
    )
    monkeypatch.setattr("app.migrations.inspect", lambda conn: fake_inspector)
    monkeypatch.setattr("app.migrations.create_engine", MagicMock())

    _stamp_existing_phase_1_schema(MagicMock())
    mock_stamp.assert_called_with(ANY, "0004_user_api_keys")


def test_stamp_existing_phase_1_schema_stamps_preferred_provider(monkeypatch) -> None:
    mock_stamp = MagicMock()
    monkeypatch.setattr("app.migrations.command.stamp", mock_stamp)

    fake_inspector = FakeInspector(
        tables={"users", "conversations", "messages", "tool_calls", "user_api_keys"},
        columns_dict={
            "tool_calls": ["id", "conversation_id", "agent_name"],
            "users": ["id", "email", "preferred_provider"]
        }
    )
    monkeypatch.setattr("app.migrations.inspect", lambda conn: fake_inspector)
    monkeypatch.setattr("app.migrations.create_engine", MagicMock())

    _stamp_existing_phase_1_schema(MagicMock())
    mock_stamp.assert_called_with(ANY, "0005_users_preferred_provider")


def test_stamp_existing_phase_1_schema_stamps_head(monkeypatch) -> None:
    mock_stamp = MagicMock()
    monkeypatch.setattr("app.migrations.command.stamp", mock_stamp)

    fake_inspector = FakeInspector(
        tables={"users", "conversations", "messages", "tool_calls", "user_api_keys", "documents"},
        columns_dict={
            "tool_calls": ["id", "conversation_id", "agent_name"],
            "users": ["id", "email", "preferred_provider"]
        }
    )
    monkeypatch.setattr("app.migrations.inspect", lambda conn: fake_inspector)
    monkeypatch.setattr("app.migrations.create_engine", MagicMock())

    _stamp_existing_phase_1_schema(MagicMock())
    mock_stamp.assert_called_with(ANY, "head")
